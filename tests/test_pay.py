"""微信小店·代客下单闭环测试：建预订单+H5短链、推送验签/幂等/恰好一次、查单推进、关单、降级路径。

用自生成 RSA 密钥对按文档第六章规则签名推送，端到端走 /api/pay/notify 与
/api/pay/refund-notify（纯文本 success/fail）。
"""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.services import pay_service, reconcile, wxstore
from app.services.seed import seed_products
from tests.conftest import create_profile

APPID = "2099010100000001"
MALL_SN = "2099010100000000001"
MALL_SIG = "test-mall-signature"
MERCHANT_ID = "11111111-1111-4111-8111-111111111111"
MERCHANT_USER_ID = "22222222-2222-4222-8222-222222222222"
NOTIFY_URL = "https://www.sxzfcm.top/api/pay/notify"
REFUND_NOTIFY_URL = "https://www.sxzfcm.top/api/pay/refund-notify"
RETURN_URL = "https://www.sxzfcm.top/pay/{orderNo}"


def _configure_wxs(monkeypatch):
    """注入完整微信小店配置；打桩网络方法返回假数据，避免真实外呼。"""
    monkeypatch.setattr(settings, "WXS_APPID", APPID)
    monkeypatch.setattr(settings, "WXS_APPKEY", "test-appkey")
    monkeypatch.setattr(settings, "WXS_API_BASE", "https://open-api.shouqianba.com")
    monkeypatch.setattr(settings, "WXS_MALL_SN", MALL_SN)
    monkeypatch.setattr(settings, "WXS_MALL_SIGNATURE", MALL_SIG)
    monkeypatch.setattr(settings, "WXS_MERCHANT_ID", MERCHANT_ID)
    monkeypatch.setattr(settings, "WXS_MERCHANT_USER_ID", MERCHANT_USER_ID)
    monkeypatch.setattr(settings, "WXS_NOTIFY_URL", NOTIFY_URL)
    monkeypatch.setattr(settings, "WXS_REFUND_NOTIFY_URL", REFUND_NOTIFY_URL)
    monkeypatch.setattr(settings, "WXS_RETURN_URL", RETURN_URL)

    async def _fake_save(amount, request_id, **k):
        return f"PRE-{request_id}"

    async def _fake_h5(pre_order_id, **k):
        return f"https://h5.test/pay/{pre_order_id}"

    monkeypatch.setattr(wxstore.client, "save_pre_order", _fake_save)
    monkeypatch.setattr(wxstore.client, "generate_h5_link", _fake_h5)
    monkeypatch.setattr(
        wxstore.client, "query_pre_order",
        lambda pre, **k: {"state": "0", "amount": 1, "order_sn": None, "pre_order_id": pre},
    )
    monkeypatch.setattr(wxstore.client, "delete_pre_order", lambda pre, **k: {})


def _configure_push_key(monkeypatch):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    monkeypatch.setattr(settings, "WXS_PUSH_PUBLIC_KEY", pub_pem)
    wxstore.client._push_keys.clear()
    return priv


def _make_push(priv_key, content: dict, event_id=1001, timestamp=1706679507593, nonce="n0nce") -> bytes:
    content_str = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    plaintext = (str(event_id) + str(timestamp) + str(nonce) + content_str).encode("utf-8")
    sig = priv_key.sign(plaintext, padding.PKCS1v15(), hashes.SHA256())
    outer = {
        "eventId": event_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "content": content_str,
        "signature": base64.b64encode(sig).decode("ascii"),
    }
    return json.dumps(outer, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _pay_content(pre_order_id, order_sn="WXSN001", amount=2, **extra):
    content = {
        "orderSn": order_sn,
        "orderSignature": "sig001",
        "orderAmount": amount,
        "preOrderList": [{"preOrderId": pre_order_id, "preOrderSn": "PSN001"}],
        "payments": [{"amount": amount}],
    }
    content.update(extra)
    return content


@pytest.fixture()
def client_and_factory():
    """独立内存 SQLite + 种子，返回 (TestClient, session 工厂) 便于直查 DB。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with factory() as db:
        seed_products(db)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def _create_order(client, key="wxs-test-order", paymentMethod="auto") -> str:
    pid = create_profile(client, _key=f"{key}-profile")["profileId"]
    resp = client.post(
        "/api/orders",
        json={"profileId": pid, "productId": 1, "paymentMethod": paymentMethod},
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["orderNo"]


def _pre_order_id(factory, order_no) -> str:
    with factory() as db:
        return db.query(Order).filter(Order.order_no == order_no).one().pre_order_id


def _make_order_stale(factory, order_no):
    import datetime

    from sqlalchemy import text

    with factory() as db:
        db.execute(
            text("UPDATE orders SET created_at=:t WHERE order_no=:o"),
            {"t": datetime.datetime(2020, 1, 1), "o": order_no},
        )
        db.commit()


# ===================== 建单：H5 短链与降级 =====================


def test_create_order_not_configured_returns_null_pay_fields(client):
    pid = create_profile(client, _key="wxs-degrade-profile")["profileId"]
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1}, headers={"Idempotency-Key": "wxs-degrade"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payType"] is None and data["payUrl"] is None and data["codeUrl"] is None


def test_create_order_h5_returns_short_link(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-h5")
    data = client.get(f"/api/orders/{order_no}").json()["data"]
    assert data["payType"] == "h5"
    assert data["payUrl"] == f"https://h5.test/pay/PRE-{order_no}"
    assert data["codeUrl"] is None
    assert data["payChannel"] == "wx_h5"
    assert _pre_order_id(factory, order_no) == f"PRE-{order_no}"


def test_create_order_upstream_failure_degrades_to_null(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    _configure_wxs(monkeypatch)

    async def _fail(*a, **k):
        raise wxstore.WxstoreError("NETWORK_ERROR", "x")

    monkeypatch.setattr(wxstore.client, "save_pre_order", _fail)
    pid = create_profile(client, _key="wxs-fail-profile")["profileId"]
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1}, headers={"Idempotency-Key": "wxs-fail"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payType"] is None and data["payUrl"] is None


def test_create_order_h5_link_failure_keeps_preorder(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)

    async def _fail_h5(*a, **k):
        raise wxstore.WxstoreError("BIZ_FAIL", "x")

    monkeypatch.setattr(wxstore.client, "generate_h5_link", _fail_h5)
    order_no = _create_order(client, key="wxs-h5fail")
    data = client.get(f"/api/orders/{order_no}").json()["data"]
    assert data["payUrl"] is None
    # 预订单已建并落库，对账仍可查
    assert _pre_order_id(factory, order_no) == f"PRE-{order_no}"


# ===================== 支付推送 =====================


def test_pay_push_success_unlocks_exactly_once(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-push-ok")
    pre = _pre_order_id(factory, order_no)
    raw = _make_push(priv, _pay_content(pre, amount=1), event_id=2001)
    for _ in range(2):
        resp = client.post("/api/pay/notify", content=raw, headers={"Content-Type": "application/json"})
        assert resp.status_code == 200 and resp.text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert order.order_sn == "WXSN001"
        txns = db.query(PayTransaction).filter(PayTransaction.order_no == order_no).all()
        assert len(txns) == 1 and txns[0].pay_state == "SUCCESS"


def test_pay_push_bad_signature_fail(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-push-bad")
    pre = _pre_order_id(factory, order_no)
    raw = _make_push(priv_other(), _pay_content(pre, amount=1), event_id=2002)
    resp = client.post("/api/pay/notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "fail"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def priv_other():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_pay_push_unknown_preorder_stops_retry(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    raw = _make_push(priv, _pay_content("PRE-NOT-EXIST", amount=1), event_id=2003)
    resp = client.post("/api/pay/notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "success"


def test_pay_push_amount_mismatch_stops_retry(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-push-amt")
    pre = _pre_order_id(factory, order_no)
    raw = _make_push(priv, _pay_content(pre, amount=2), event_id=2004)
    resp = client.post("/api/pay/notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "success"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_pay_push_closed_order_stops_retry(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-push-closed")
    pre = _pre_order_id(factory, order_no)
    assert client.post(f"/api/orders/{order_no}/close").status_code == 200
    raw = _make_push(priv, _pay_content(pre, amount=1), event_id=2005)
    resp = client.post("/api/pay/notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "success"
    with factory() as db:
        assert "paid_after_close" in (db.query(Order).filter(Order.order_no == order_no).one().fail_reason or "")


def test_pay_push_garbage_body_fail(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    _configure_wxs(monkeypatch)
    _configure_push_key(monkeypatch)
    resp = client.post("/api/pay/notify", content=b"not-json", headers={"Content-Type": "application/json"})
    assert resp.text == "fail"


# ===================== 对账 =====================


def test_reconcile_success_advances_order(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-ok")
    _make_order_stale(factory, order_no)
    monkeypatch.setattr(
        wxstore.client, "query_pre_order",
        lambda pre, **k: {"state": "1", "amount": 1, "order_sn": "WXSN-R1", "pre_order_id": pre},
    )
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["success"] == 1
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.UNLOCKED.value


def test_reconcile_canceled_marks_closed(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-cancel")
    _make_order_stale(factory, order_no)
    monkeypatch.setattr(
        wxstore.client, "query_pre_order",
        lambda pre, **k: {"state": "2", "amount": 1, "order_sn": None, "pre_order_id": pre},
    )
    with factory() as db:
        assert reconcile.reconcile_once(db)["closed"] == 1
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CLOSED.value


def test_reconcile_pending_keeps_created(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-pending")
    _make_order_stale(factory, order_no)
    with factory() as db:
        assert reconcile.reconcile_once(db)["pending"] == 1
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_reconcile_skips_fresh_orders(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    _create_order(client, key="wxs-reconcile-fresh")

    def _boom(pre, **k):
        raise AssertionError("新鲜订单不应被查单")

    monkeypatch.setattr(wxstore.client, "query_pre_order", _boom)
    with factory() as db:
        assert reconcile.reconcile_once(db)["checked"] == 0


def test_reconcile_skips_unconfigured_orders(client_and_factory, monkeypatch):
    """降级建单（无 pre_order_id）跳过本轮，不计 checked。"""
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-nopre")
    _make_order_stale(factory, order_no)
    with factory() as db:
        db.query(Order).filter(Order.order_no == order_no).one().pre_order_id = None
        db.commit()
        assert reconcile.reconcile_once(db)["checked"] == 0


def test_reconcile_unknown_state_goes_dead(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-unknown")
    _make_order_stale(factory, order_no)
    monkeypatch.setattr(
        wxstore.client, "query_pre_order",
        lambda pre, **k: {"state": "9", "amount": 1, "order_sn": None, "pre_order_id": pre},
    )
    with factory() as db:
        assert reconcile.reconcile_once(db)["dead"] == 1


def test_reconcile_query_error_counts_error(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    order_no = _create_order(client, key="wxs-reconcile-err")
    _make_order_stale(factory, order_no)

    def _boom(pre, **k):
        raise wxstore.WxstoreError("NETWORK_ERROR", "x")

    monkeypatch.setattr(wxstore.client, "query_pre_order", _boom)
    with factory() as db:
        assert reconcile.reconcile_once(db)["error"] == 1


# ===================== 关单 =====================


def test_close_order_deletes_preorder(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    calls = []
    monkeypatch.setattr(wxstore.client, "delete_pre_order", lambda pre, **k: calls.append(pre) or {})
    order_no = _create_order(client, key="wxs-close")
    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 200
    assert calls == [f"PRE-{order_no}"]
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CLOSED.value


# ===================== 恰好一次 =====================


def test_apply_payment_result_threaded_cas(monkeypatch, tmp_path):
    """真线程并发推送仅一个获胜（恰好一次）：文件库+每线程独立连接。"""
    import threading

    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services.seed import seed_products
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    _configure_wxs(monkeypatch)
    db_path = tmp_path / "race.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with factory() as db:
        seed_products(db)
        from app.models.profile import Profile
        from app.models.report import Report
        from app.services.seq import next_order_no

        profile = Profile(id="P20260901001", name_a="张三", birth_a="x", combo_data="x", preview_report="{}")
        db.add(profile)
        db.commit()
        order_no = next_order_no(db)
        db.add(Order(order_no=order_no, profile_id=profile.id, product_id=1, out_trade_no=order_no,
                     pre_order_id=f"PRE-{order_no}", amount=1, state="CREATED"))
        db.add(Report(profile_id=profile.id, full_report="{}", state="locked"))
        db.commit()

    payload = {"order_sn": "TXN-THREAD", "order_signature": "s", "amount": 1, "pre_order_id": f"PRE-{order_no}"}
    results = []

    def _work():
        with factory() as s:
            st, _ = pay_service.apply_payment_result(s, f"PRE-{order_no}", payload, "raw")
            s.commit()
            results.append(st)

    threads = [threading.Thread(target=_work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results).count("ok") == 1
    assert sorted(results).count("already") == 3
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1
    engine.dispose()


# ===================== 退款推送：只记录可查 =====================


def _refund_content(order_sn="WXSN001", target=20, ticket="TCK001"):
    return {
        "ticketSn": ticket,
        "ticketSignature": "tsig",
        "orderSn": order_sn,
        "sourceState": 0,
        "targetState": target,
        "applyAmount": 990,
    }


def test_refund_push_records_without_changing_state(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-refund-ok")
    # 先支付成功拿到 order_sn
    pre = _pre_order_id(factory, order_no)
    pay_raw = _make_push(priv, _pay_content(pre, amount=1), event_id=3000)
    assert client.post("/api/pay/notify", content=pay_raw, headers={"Content-Type": "application/json"}).text == "success"
    raw = _make_push(priv, _refund_content(), event_id=3001)
    resp = client.post("/api/pay/refund-notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200 and resp.text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert "refund:20" in (order.fail_reason or "")
        txn = db.query(PayTransaction).filter(PayTransaction.transaction_id == "TCK001").one()
        assert txn.order_no == order_no and txn.pay_state == "REFUNDED"


def test_refund_push_idempotent_on_retry(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-refund-idem")
    pre = _pre_order_id(factory, order_no)
    pay_raw = _make_push(priv, _pay_content(pre, amount=1), event_id=3010)
    assert client.post("/api/pay/notify", content=pay_raw, headers={"Content-Type": "application/json"}).text == "success"
    raw = _make_push(priv, _refund_content(ticket="TCK-IDEM"), event_id=3011)
    for _ in range(2):
        resp = client.post("/api/pay/refund-notify", content=raw, headers={"Content-Type": "application/json"})
        assert resp.text == "success"
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.transaction_id == "TCK-IDEM").count() == 1


def test_refund_push_bad_signature_returns_fail(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    _configure_wxs(monkeypatch)
    _configure_push_key(monkeypatch)
    raw = _make_push(priv_other(), _refund_content(), event_id=3012)
    resp = client.post("/api/pay/refund-notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "fail"


def test_refund_push_unknown_order_stops_retry(client_and_factory, monkeypatch):
    client, _ = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    content = _refund_content(order_sn="WXSN-NONE")
    raw = _make_push(priv, content, event_id=3013)
    resp = client.post("/api/pay/refund-notify", content=raw, headers={"Content-Type": "application/json"})
    assert resp.text == "success"


def test_refund_push_non_final_noop(client_and_factory, monkeypatch):
    client, factory = client_and_factory
    _configure_wxs(monkeypatch)
    priv = _configure_push_key(monkeypatch)
    order_no = _create_order(client, key="wxs-refund-nonfinal")
    pre = _pre_order_id(factory, order_no)
    pay_raw = _make_push(priv, _pay_content(pre, amount=1), event_id=3020)
    assert client.post("/api/pay/notify", content=pay_raw, headers={"Content-Type": "application/json"}).text == "success"
    raw = _make_push(priv, _refund_content(target=10, ticket="TCK-PENDING"), event_id=3021)
    assert client.post("/api/pay/refund-notify", content=raw, headers={"Content-Type": "application/json"}).text == "success"
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.transaction_id == "TCK-PENDING").count() == 0


def test_health_reports_missing_config(client):
    data = client.get("/api/health").json()["data"]
    assert isinstance(data["sqbMissing"], list)
    assert "WXS_APPID" in data["sqbMissing"] or data["sqbReady"] is False
