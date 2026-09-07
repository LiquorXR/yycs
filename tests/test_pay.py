"""收钱吧聚合支付闭环测试：WAP 拼串、预下单、notify RSA 验签/幂等/恰好一次、查单推进、关单、降级路径。

用生成的 RSA 密钥对构造真实签名回调，端到端走 /api/pay/notify（纯文本 success/fail）。
"""

from __future__ import annotations

import base64
import datetime
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.timeutil import utcnow
from app.db.session import Base, get_db
from app.main import app
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.report import Report
from app.services import pay_service, reconcile, shouqianba
from app.services.seed import seed_products
from app.services.shouqianba import ShouqianbaClient, ShouqianbaError
from tests.conftest import create_profile

TERMINAL_SN = "123456789012"
TERMINAL_KEY = "test_terminal_key_123456"
NOTIFY_URL = "https://www.sxzfcm.top/api/pay/notify"
RETURN_URL = "https://www.sxzfcm.top/pay/{orderNo}"


def _configure_sqb(monkeypatch, tmp_path, with_pubkey=True):
    """注入完整收钱吧配置；默认打桩预下单返回假短链，避免真实网络。"""
    monkeypatch.setattr(settings, "SQB_TERMINAL_SN", TERMINAL_SN)
    monkeypatch.setattr(settings, "SQB_TERMINAL_KEY", TERMINAL_KEY)
    monkeypatch.setattr(settings, "SQB_API_BASE", "https://vsi-api.shouqianba.com")
    monkeypatch.setattr(settings, "SQB_GATEWAY", "https://qr.shouqianba.com/gateway")
    monkeypatch.setattr(settings, "SQB_NOTIFY_URL", NOTIFY_URL)
    monkeypatch.setattr(settings, "SQB_RETURN_URL", RETURN_URL)
    monkeypatch.setattr(settings, "SQB_OPERATOR", "zhenfan")

    priv = None
    if with_pubkey:
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub_pem = priv.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        (tmp_path / "sqb_pub.pem").write_bytes(pub_pem)
        monkeypatch.setattr(settings, "SQB_PUBLIC_KEY_PATH", str(tmp_path / "sqb_pub.pem"))
        # 清掉客户端缓存的公钥，确保读到新路径
        shouqianba.client._public_keys.clear()
    else:
        monkeypatch.setattr(settings, "SQB_PUBLIC_KEY_PATH", None)
        shouqianba.client._public_keys.clear()

    async def _fake_precreate(*a, **k):
        return "https://qr.shouqianba.com/s/TEST123"

    monkeypatch.setattr(shouqianba.client, "precreate_qr", _fake_precreate)
    # 关单上游撤单打桩，避免真实网络
    monkeypatch.setattr(shouqianba.client, "cancel_order", lambda *a, **k: {})
    return priv


def _sign_body(priv_key, raw: bytes) -> str:
    sig = priv_key.sign(raw, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def _make_callback(priv_key, payload: dict) -> tuple[str, dict]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sig = _sign_body(priv_key, raw.encode("utf-8")) if priv_key is not None else ""
    headers = {"Authorization": f"{TERMINAL_SN} {sig}"} if sig else {}
    return raw, headers


def _paid_payload(client_sn, total=990, sn="SQB20260001"):
    return {
        "terminal_sn": TERMINAL_SN,
        "sn": sn,
        "client_sn": client_sn,
        "order_status": "PAID",
        "total_amount": str(total),
        "payway": "3",
    }


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


def _create_order(client, key="sqb-test-order", paymentMethod="auto") -> str:
    pid = create_profile(client, _key=f"{key}-profile")["profileId"]
    resp = client.post(
        "/api/orders",
        json={"profileId": pid, "productId": 1, "paymentMethod": paymentMethod},
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["orderNo"]


# ===================== 客户端单元测试 =====================


class TestClientUnits:
    def test_sign_wap_deterministic_and_upper(self):
        params = {"terminal_sn": "1", "client_sn": "S1", "total_amount": "990"}
        s1 = shouqianba.sign_wap_params(params, "k")
        s2 = shouqianba.sign_wap_params(dict(reversed(list(params.items()))), "k")
        assert s1 == s2 == s1.upper()
        assert len(s1) == 32

    def test_sign_vsi_body(self):
        s = shouqianba.sign_vsi_body('{"a":1}', "k")
        assert s == s.upper() and len(s) == 32

    def test_resolve_payway(self):
        assert shouqianba.resolve_payway("ali_h5") == "1"
        assert shouqianba.resolve_payway("wx_h5") == "3"
        assert shouqianba.resolve_payway("auto") == "3"
        assert shouqianba.resolve_payway(None) == "3"

    def test_resolve_return_url(self, monkeypatch):
        monkeypatch.setattr(settings, "SQB_RETURN_URL", "https://www.sxzfcm.top/pay/{orderNo}")
        assert shouqianba.resolve_return_url("S1") == "https://www.sxzfcm.top/pay/S1"
        monkeypatch.setattr(settings, "SQB_RETURN_URL", "https://www.sxzfcm.top/pay")
        assert shouqianba.resolve_return_url("S1") == "https://www.sxzfcm.top/pay/S1"

    def test_build_wap_url(self, monkeypatch, tmp_path):
        _configure_sqb(monkeypatch, tmp_path)
        url = ShouqianbaClient(settings).build_wap_url("S20260001", 990, "测试商品", payway="3")
        assert url.startswith("https://qr.shouqianba.com/gateway?")
        qs = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(url.split("?", 1)[1]))
        assert qs["client_sn"] == "S20260001"
        assert qs["total_amount"] == "990"
        assert qs["payway"] == "3"
        assert qs["notify_url"] == NOTIFY_URL
        assert qs["return_url"] == "https://www.sxzfcm.top/pay/S20260001"
        assert len(qs["sign"]) == 32

    def test_verify_callback_roundtrip(self, monkeypatch, tmp_path):
        priv = _configure_sqb(monkeypatch, tmp_path)
        raw = b'{"client_sn":"S1"}'
        sig = _sign_body(priv, raw)
        assert shouqianba.client.verify_callback(raw, sig)
        assert not shouqianba.client.verify_callback(raw + b"x", sig)

    def test_normalize_query(self):
        n = ShouqianbaClient.normalize_query(
            {"biz_response": {"data": {"order_status": "PAID", "total_amount": "990", "sn": "X", "client_sn": "S1"}}}
        )
        assert n["order_status"] == "PAID" and n["total_amount"] == 990


# ===================== 创建订单：支付参数填充与降级 =====================


def test_create_order_not_configured_returns_null_pay_fields(client):
    pid = create_profile(client, _key="sqb-degrade-profile")["profileId"]
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1}, headers={"Idempotency-Key": "sqb-degrade"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payType"] is None and data["payUrl"] is None and data["codeUrl"] is None


def test_create_order_wx_h5_returns_gateway_url(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-wx-h5", paymentMethod="wx_h5")
    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["payType"] == "h5"
    assert detail["payUrl"].startswith("https://qr.shouqianba.com/gateway?")
    assert "client_sn=" in detail["payUrl"]
    # H5 主路径附带聚合码备选
    assert detail["codeUrl"] == "https://qr.shouqianba.com/s/TEST123"


def test_create_order_ali_h5_uses_alipay_payway(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-ali-h5", paymentMethod="ali_h5")
    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["payType"] == "h5"
    assert "payway=1" in detail["payUrl"]


def test_create_order_native_returns_qr_only(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-native", paymentMethod="native")
    data = client.get(f"/api/orders/{order_no}").json()["data"]
    assert data["payType"] == "native"
    assert data["codeUrl"] == "https://qr.shouqianba.com/s/TEST123"
    assert data["payUrl"] is None


def test_create_order_upstream_failure_degrades_to_null(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)

    async def _fail(*a, **k):
        raise ShouqianbaError("X", "boom")

    monkeypatch.setattr(shouqianba.client, "precreate_qr", _fail)

    def _fail_wap(*a, **k):
        raise ShouqianbaError("Y", "wap boom")

    monkeypatch.setattr(shouqianba.client, "build_wap_url", _fail_wap)
    # native 预下单失败 + WAP 回退失败 → 全 null 降级
    order_no = _create_order(client, key="sqb-fail-degrade", paymentMethod="native")
    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["payUrl"] is None and detail["codeUrl"] is None
    assert detail["state"] == "CREATED"


# ===================== 支付回调 /api/pay/notify =====================


def _notify(client, raw, headers):
    return client.post("/api/pay/notify", content=raw.encode("utf-8"), headers={**headers, "Content-Type": "application/json"})


def test_pay_notify_success_unlocks_exactly_once(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-ok")

    raw, headers = _make_callback(priv, _paid_payload(order_no))
    resp = _notify(client, raw, headers)
    assert resp.status_code == 200
    assert resp.text == "success"

    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert order.paid_at is not None
        report = db.query(Report).filter(Report.profile_id == order.profile_id).one()
        assert report.state == "unlocked"
        assert report.unlocked_at is not None
        txns = db.query(PayTransaction).filter(PayTransaction.order_no == order_no).all()
        assert len(txns) == 1
        assert txns[0].transaction_id == "SQB20260001"
        assert txns[0].pay_state == "SUCCESS"

    # 重复回调：幂等返回 success，不重复解锁/不重复落流水
    resp2 = _notify(client, raw, headers)
    assert resp2.text == "success"
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value

    report_resp = client.get(f"/api/orders/{order_no}/report").json()["data"]
    assert report_resp["state"] == "UNLOCKED"
    assert report_resp["report"]["locked"] is True
    for key in ("score", "rank", "scoreNote", "analysis", "karma"):
        assert key not in report_resp["report"]


def test_pay_notify_bad_signature_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-badsig")

    raw = json.dumps(_paid_payload(order_no), ensure_ascii=False)
    resp = _notify(client, raw, {})
    assert resp.text == "fail"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value
        assert db.query(PayTransaction).count() == 0


def test_pay_notify_wrong_signature_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-wrongsig")

    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raw, headers = _make_callback(wrong, _paid_payload(order_no))
    resp = _notify(client, raw, headers)
    assert resp.text == "fail"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_pay_notify_amount_mismatch_stops_retry(client_and_factory, monkeypatch, tmp_path):
    """确定性失败（金额不符）记日志后回 success 止血，避免无意义重试。"""
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-amt")

    raw, headers = _make_callback(priv, _paid_payload(order_no, total=1))
    resp = _notify(client, raw, headers)
    assert resp.text == "success"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value
        assert db.query(PayTransaction).count() == 0


def test_pay_notify_not_configured_fail(client_and_factory):
    client, _ = client_and_factory
    resp = client.post("/api/pay/notify", content=b"{}", headers={"Authorization": "x y"})
    assert resp.text == "fail"


def test_pay_notify_closed_order_stops_retry(client_and_factory, monkeypatch, tmp_path):
    """关单后到账记 paid_after_close 后回 success 止血，转人工核账。"""
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-closed")
    client.post(f"/api/orders/{order_no}/close")

    raw, headers = _make_callback(priv, _paid_payload(order_no))
    resp = _notify(client, raw, headers)
    assert resp.text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CLOSED.value
        assert "paid_after_close" in (order.fail_reason or "")


def test_pay_notify_unknown_order_stops_retry(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    raw, headers = _make_callback(priv, _paid_payload("S20991231001"))
    resp = _notify(client, raw, headers)
    assert resp.text == "success"


# ===================== 查单推进 / 对账 =====================


def _make_order_stale(factory, order_no, minutes=40):
    with factory() as db:
        db.execute(
            update(Order).where(Order.order_no == order_no).values(created_at=utcnow() - datetime.timedelta(minutes=minutes))
        )
        db.commit()


def test_reconcile_success_advances_order(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-ok")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(
        shouqianba.client, "query_order", lambda no, **k: {"order_status": "PAID", "total_amount": 990, "sn": "SQB9999", "client_sn": no}
    )
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["checked"] == 1 and summary["success"] == 1
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1


def test_reconcile_canceled_marks_closed(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-closed")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: {"order_status": "PAY_CANCELED", "total_amount": 990})
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["checked"] == 1 and summary["closed"] == 1
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CLOSED.value
        assert order.fail_reason == "收钱吧查单: PAY_CANCELED"


def test_reconcile_pending_keeps_created(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-pending")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: {"order_status": "CREATED", "total_amount": 990})
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["pending"] == 1
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_reconcile_skips_fresh_orders(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    _create_order(client, key="sqb-reconcile-fresh")

    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: pytest.fail("不应查新订单"))
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["checked"] == 0


def test_reconcile_skips_already_unlocked_orders(client_and_factory, monkeypatch, tmp_path):
    """已解锁订单不在对账扫描集合（仅扫描 CREATED），不重复落流水。"""
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-already")
    _make_order_stale(factory, order_no)

    raw, headers = _make_callback(priv, _paid_payload(order_no, sn="TXN-A"))
    assert _notify(client, raw, headers).text == "success"

    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: pytest.fail("已解锁订单不应被查单"))
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["checked"] == 0
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1


# ===================== 关单（仅本地） =====================


def test_close_order_local_only(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-close-local")

    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "CLOSED"

    resp2 = client.post(f"/api/orders/{order_no}/close")
    assert resp2.status_code == 409
    assert resp2.json()["code"] == 12003


# ===================== 恰好一次（CAS） =====================


def test_apply_payment_result_cas_exactly_once(client_and_factory, monkeypatch, tmp_path):
    """CAS 保证恰好一次：首个会话推进成功，第二个会话判定已处理（不重复解锁/落流水）。"""
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-cas-once")

    payload = {"order_status": "PAID", "total_amount": 990, "sn": "TXN-CAS", "client_sn": order_no}
    with factory() as s1:
        st1, _ = pay_service.apply_payment_result(s1, order_no, payload, "raw1")
        s1.commit()
    with factory() as s2:
        st2, _ = pay_service.apply_payment_result(s2, order_no, payload, "raw2")
        s2.commit()

    assert st1 == "ok"
    assert st2 == "already"
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert db.query(Report).filter(Report.profile_id == order.profile_id).one().unlocked_at is not None


# ===================== 必要修复回归 =====================


def test_pay_channel_preserved_and_display_normalized(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-channel", paymentMethod="ali_h5")
    data = client.get(f"/api/orders/{order_no}").json()["data"]
    assert data["payType"] == "h5"
    assert data["payChannel"] == "ali_h5"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().pay_type == "ali_h5"


def test_is_ready_requires_operator(client_and_factory, monkeypatch, tmp_path):
    _configure_sqb(monkeypatch, tmp_path)
    assert shouqianba.client.is_ready
    monkeypatch.setattr(settings, "SQB_OPERATOR", None)
    assert not shouqianba.client.is_ready


def test_normalize_amount_rejects_decimal():
    assert shouqianba.normalize_amount(990) == 990
    assert shouqianba.normalize_amount("990") == 990
    assert shouqianba.normalize_amount("9.90") is None
    assert shouqianba.normalize_amount(" 990 ") == 990
    assert shouqianba.normalize_amount(None) is None


def test_pay_notify_terminal_mismatch_stops_retry(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-terminal-mismatch")
    payload = _paid_payload(order_no)
    payload["terminal_sn"] = "WRONG_SN"
    raw, _ = _make_callback(priv, payload)
    # 头 sn 正确但正文 terminal 不一致 → success 止血
    sig = raw  # _make_callback 已签名含 WRONG 正文
    resp = _notify(client, sig, {"Authorization": f"{TERMINAL_SN} {_sign_body(priv, sig.encode())}"})
    assert resp.text == "success"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_pay_notify_header_sn_mismatch_stops_retry(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-header-mismatch")
    raw, _ = _make_callback(priv, _paid_payload(order_no))
    resp = _notify(client, raw, {"Authorization": f"WRONG_SN {_sign_body(priv, raw.encode())}"})
    assert resp.text == "success"


def test_pay_notify_malformed_auth_fails(client_and_factory, monkeypatch, tmp_path):
    """畸形 Authorization（缺头/一段/三段/非法 base64）一律 fail（可重试）。"""
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-malformed-auth")
    raw, headers = _make_callback(priv, _paid_payload(order_no))
    assert _notify(client, raw, {}).text == "fail"
    assert _notify(client, raw, {"Authorization": "onlyonepart"}).text == "fail"
    assert _notify(client, raw, {"Authorization": "a b c"}).text == "fail"
    assert _notify(client, raw, {"Authorization": f"{TERMINAL_SN} !!!not-base64!!!"}).text == "fail"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_pay_notify_canceled_closes_order(client_and_factory, monkeypatch, tmp_path):
    """非 PAID 失败态通知：CREATED→CLOSED，success。"""
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-canceled")
    payload = _paid_payload(order_no)
    payload["order_status"] = "PAY_CANCELED"
    raw, headers = _make_callback(priv, payload)
    assert _notify(client, raw, headers).text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CLOSED.value


def test_pay_notify_pending_state_noop(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-notify-pending")
    payload = _paid_payload(order_no)
    payload["order_status"] = "CREATED"
    raw, headers = _make_callback(priv, payload)
    assert _notify(client, raw, headers).text == "success"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_paid_after_close_marks_manual_review(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-paid-after-close")
    client.post(f"/api/orders/{order_no}/close")
    raw, headers = _make_callback(priv, _paid_payload(order_no, sn="SQB-AFTER-CLOSE"))
    resp = _notify(client, raw, headers)
    assert resp.text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CLOSED.value
        assert order.fail_reason is not None and "paid_after_close" in order.fail_reason


# ===================== 加固回归（第二轮） =====================


def test_normalize_amount_float_integer_compat():
    assert shouqianba.normalize_amount(990.0) == 990
    assert shouqianba.normalize_amount(9.9) is None
    assert shouqianba.normalize_amount(True) is None
    assert shouqianba.normalize_amount(-1) is None
    assert shouqianba.normalize_amount("12345678901") is None


def test_normalize_payment_method_and_channel():
    assert pay_service.normalize_payment_method("auto") == "wx_h5"
    assert pay_service.normalize_payment_method("H5") == "wx_h5"
    assert pay_service.normalize_payment_method("WX_H5") == "wx_h5"
    assert pay_service.normalize_payment_method("native") == "wx_native"
    assert pay_service.normalize_payment_method("ali_h5") == "ali_h5"
    assert pay_service.display_pay_type("wx_h5", "https://x", "https://y") == "h5"
    assert pay_service.display_pay_type("wx_h5", None, "https://y") == "native"
    assert pay_service.display_pay_type("wx_h5", None, None) is None


def test_create_order_uppercase_method_accepted(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-upper-method", paymentMethod="WX_H5")
    data = client.get(f"/api/orders/{order_no}").json()["data"]
    assert data["payType"] == "h5"
    assert data["payChannel"] == "wx_h5"


def test_create_order_same_key_different_method_conflicts(client):
    pid = create_profile(client, _key="sqb-idem-diff-profile")["profileId"]
    first = client.post(
        "/api/orders",
        json={"profileId": pid, "productId": 1, "paymentMethod": "wx_h5"},
        headers={"Idempotency-Key": "sqb-idem-diff"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/orders",
        json={"profileId": pid, "productId": 1, "paymentMethod": "ali_h5"},
        headers={"Idempotency-Key": "sqb-idem-diff"},
    )
    assert second.status_code == 409
    assert second.json()["code"] == 10005


def test_close_order_calls_cancel_best_effort(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(shouqianba.client, "cancel_order", lambda no, **k: calls.append(no))
    order_no = _create_order(client, key="sqb-close-cancel")
    assert client.post(f"/api/orders/{order_no}/close").status_code == 200
    assert calls == [order_no]


def test_close_order_cancel_failure_still_closes(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)

    def _boom(*a, **k):
        raise ShouqianbaError("X", "cancel boom")

    monkeypatch.setattr(shouqianba.client, "cancel_order", _boom)
    order_no = _create_order(client, key="sqb-close-cancel-err")
    assert client.post(f"/api/orders/{order_no}/close").status_code == 200


def test_reconcile_query_error_counts_error(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-err")
    _make_order_stale(factory, order_no)

    def _boom(no, **k):
        raise ShouqianbaError("NETWORK_ERROR", "boom")

    monkeypatch.setattr(shouqianba.client, "query_order", _boom)
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["error"] == 1 and summary["checked"] == 0


def test_reconcile_missing_amount_goes_dead(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-dead")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(
        shouqianba.client, "query_order", lambda no, **k: {"order_status": "PAID", "total_amount": None, "sn": "X", "client_sn": no}
    )
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["dead"] == 1
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert "reconcile_dead" in (order.fail_reason or "")
    # 第二轮不再扫描死信
    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: pytest.fail("死信不应重查"))
    with factory() as db:
        assert reconcile.reconcile_once(db)["checked"] == 0


def test_reconcile_unknown_state_goes_dead(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-reconcile-unknown")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(shouqianba.client, "query_order", lambda no, **k: {"order_status": "WEIRD_NEW", "total_amount": 990})
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["dead"] == 1
    with factory() as db:
        assert "unknown=WEIRD_NEW" in (db.query(Order).filter(Order.order_no == order_no).one().fail_reason or "")


def test_apply_payment_result_threaded_cas(monkeypatch, tmp_path):
    """真线程并发回调仅一个获胜（恰好一次）：文件库+每线程独立连接，还原真实并发语义。"""
    import threading

    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services.seed import seed_products

    _configure_sqb(monkeypatch, tmp_path)
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
        db.add(Order(order_no=order_no, profile_id=profile.id, product_id=1, out_trade_no=order_no, amount=990, state="CREATED"))
        db.add(Report(profile_id=profile.id, full_report="{}", state="locked"))
        db.commit()

    payload = {"order_status": "PAID", "total_amount": 990, "sn": "TXN-THREAD", "client_sn": order_no}
    results = []

    def _work():
        with factory() as s:
            st, _ = pay_service.apply_payment_result(s, order_no, payload, "raw")
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


def test_health_reports_missing_config(client):
    data = client.get("/api/health").json()["data"]
    assert isinstance(data["sqbMissing"], list)
    assert "SQB_TERMINAL_SN" in data["sqbMissing"] or data["sqbReady"] is False


# ===================== 退款回调：只记录可查 =====================

REFUND_NOTIFY_URL = "https://www.sxzfcm.top/api/pay/refund-notify"


def _refund_payload(client_sn, status="REFUNDED", total=990, sn="RFD20260001"):
    return {
        "terminal_sn": TERMINAL_SN,
        "sn": sn,
        "client_sn": client_sn,
        "order_status": status,
        "total_amount": str(total),
        "payway": "3",
    }


def test_refund_notify_records_without_changing_state(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-refund-ok")
    raw, headers = _make_callback(priv, _refund_payload(order_no))
    resp = client.post("/api/pay/refund-notify", content=raw, headers={**headers, "Content-Type": "application/json"})
    assert resp.status_code == 200 and resp.text == "success"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CREATED.value
        assert "refund:REFUNDED" in (order.fail_reason or "")
        txn = db.query(PayTransaction).filter(PayTransaction.transaction_id == "RFD20260001").one()
        assert txn.order_no == order_no and txn.pay_state == "REFUNDED"


def test_refund_notify_idempotent_on_retry(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-refund-idem")
    raw, headers = _make_callback(priv, _refund_payload(order_no, sn="RFD-IDEM-1"))
    for _ in range(2):
        resp = client.post("/api/pay/refund-notify", content=raw, headers={**headers, "Content-Type": "application/json"})
        assert resp.text == "success"
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.transaction_id == "RFD-IDEM-1").count() == 1


def test_refund_notify_bad_signature_returns_fail(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path)
    resp = client.post(
        "/api/pay/refund-notify",
        content=b'{"client_sn":"S1"}',
        headers={"Authorization": f"{TERMINAL_SN} invalidsig", "Content-Type": "application/json"},
    )
    assert resp.text == "fail"


def test_refund_notify_missing_pubkey_returns_fail(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_sqb(monkeypatch, tmp_path, with_pubkey=False)
    resp = client.post("/api/pay/refund-notify", content=b"{}", headers={"Content-Type": "application/json"})
    assert resp.text == "fail"


def test_refund_notify_unknown_order_stops_retry(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    raw, headers = _make_callback(priv, _refund_payload("S-NOT-EXIST", sn="RFD-NONE-1"))
    resp = client.post("/api/pay/refund-notify", content=raw, headers={**headers, "Content-Type": "application/json"})
    assert resp.text == "success"


def test_refund_notify_amount_mismatch_stops_retry(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    priv = _configure_sqb(monkeypatch, tmp_path)
    order_no = _create_order(client, key="sqb-refund-amt")
    raw, headers = _make_callback(priv, _refund_payload(order_no, total=1, sn="RFD-AMT-1"))
    resp = client.post("/api/pay/refund-notify", content=raw, headers={**headers, "Content-Type": "application/json"})
    assert resp.text == "success"
    with factory() as db:
        assert "refund_amount_mismatch" in (db.query(Order).filter(Order.order_no == order_no).one().fail_reason or "")
        assert db.query(PayTransaction).filter(PayTransaction.transaction_id == "RFD-AMT-1").count() == 0
