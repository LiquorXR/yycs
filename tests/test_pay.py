"""微信支付 V3 闭环测试：统一下单参数、notify 验签/解密/幂等/恰好一次、查单推进、关单、退款、降级路径。

用生成的 RSA 密钥对与 AES-GCM 构造真实签名回调，端到端走 /api/pay/notify。
"""

from __future__ import annotations

import base64
import datetime
import json

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID
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
from app.services import pay_service, reconcile, wechatpay
from app.services.seed import seed_products
from app.services.wechatpay import WechatPayClient, WechatPayError
from tests.conftest import create_profile

APIV3_KEY = "0123456789abcdef0123456789abcdef"  # 32 字节
MCHID = "1900000001"
APPID = "wx1234567890abcdef"


def _make_platform_cert(path):
    """生成自签名平台证书（验签用），返回私钥供测试构造回调签名。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "wechatpay test platform")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key


def _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=True):
    """注入完整微信支付配置。

    生成真实商户私钥（merchant.pem）与平台证书（platform.pem）；
    默认打桩 create_h5_payment/create_native_payment 返回假 URL，避免测试触发真实网络。
    """
    merchant_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (tmp_path / "merchant.pem").write_bytes(
        merchant_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    platform_key = _make_platform_cert(tmp_path / "platform.pem") if with_platform_cert else None
    monkeypatch.setattr(settings, "WXPAY_MCHID", MCHID)
    monkeypatch.setattr(settings, "WXPAY_APPID", APPID)
    monkeypatch.setattr(settings, "WXPAY_APIV3_KEY", APIV3_KEY)
    monkeypatch.setattr(settings, "WXPAY_CERT_SERIAL", "SERIAL0001")
    monkeypatch.setattr(settings, "WXPAY_PRIVATE_KEY_PATH", str(tmp_path / "merchant.pem"))
    monkeypatch.setattr(settings, "WXPAY_PLATFORM_CERT_PATH", str(tmp_path / "platform.pem") if with_platform_cert else None)
    monkeypatch.setattr(settings, "WXPAY_NOTIFY_URL", "https://example.com/api/pay/notify")
    monkeypatch.setattr(settings, "WXPAY_REFUND_NOTIFY_URL", "https://example.com/api/refund/notify")

    # 默认打桩统一下单，避免真实网络；需要自定义时测试内覆盖
    monkeypatch.setattr(wechatpay.client, "create_h5_payment", lambda *a, **k: "https://wx.tenpay.com/cgi-bin/mmpayweb/bin/checkmweb?pr=TEST")
    monkeypatch.setattr(wechatpay.client, "create_native_payment", lambda *a, **k: "weixin://wxpay/bizpayurl?pr=TEST")
    return platform_key


def _make_callback(platform_key, payload, sign=True, timestamp="1787000000", nonce="1787000000", tamper_amount=None):
    """构造微信回调：resource 用 APIv3 密钥 AES-256-GCM 加密，头部用平台私钥签名。"""
    if tamper_amount is not None:
        payload = json.loads(json.dumps(payload))
        payload["amount"]["total"] = tamper_amount
    aad = "transaction"
    plain = json.dumps(payload, ensure_ascii=False)
    cipher = AESGCM(APIV3_KEY.encode()).encrypt(nonce.encode(), plain.encode(), aad.encode())
    body = {
        "id": "EV-123",
        "create_time": "2026-08-18T10:00:00+08:00",
        "resource_type": "encrypt-resource",
        "event_type": "TRANSACTION.SUCCESS",
        "resource": {
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": base64.b64encode(cipher).decode("ascii"),
            "nonce": nonce,
            "associated_data": aad,
        },
    }
    raw = json.dumps(body, ensure_ascii=False)
    sig = ""
    if sign and platform_key is not None:
        message = f"{timestamp}\n{nonce}\n{raw}\n"
        signature = platform_key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        sig = base64.b64encode(signature).decode("ascii")
    headers = {
        "Wechatpay-Timestamp": timestamp,
        "Wechatpay-Nonce": nonce,
        "Wechatpay-Signature": sig,
        "Wechatpay-Serial": "PLATFORM_SERIAL",
    }
    return raw, headers


def _success_payload(out_trade_no, total=9900, transaction_id="4200001234567890", trade_state="SUCCESS"):
    return {
        "appid": APPID,
        "mchid": MCHID,
        "out_trade_no": out_trade_no,
        "transaction_id": transaction_id,
        "trade_type": "NATIVE",
        "trade_state": trade_state,
        "trade_state_desc": "",
        "success_time": "2026-08-18T10:00:00+08:00",
        "payer": {"openid": "o_openid_test"},
        "amount": {"total": total, "payer_total": total, "currency": "CNY", "payer_currency": "CNY"},
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


def _create_order(client, key="pay-test-order") -> str:
    pid = create_profile(client, _key="pay-test-profile")["profileId"]
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1}, headers={"Idempotency-Key": key})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["orderNo"]


# ===================== 客户端单元测试 =====================


class TestClientUnits:
    def test_build_h5_payment_body(self, tmp_path):
        client = WechatPayClient(settings)
        body = client.build_h5_payment("S20260818001", 9900, "https://e.com/n", "测试", "1.2.3.4")
        assert body["out_trade_no"] == "S20260818001"
        assert "mchid" in body and "appid" in body
        assert body["amount"]["total"] == 9900
        assert body["amount"]["currency"] == "CNY"
        assert body["notify_url"] == "https://e.com/n"
        assert body["scene_info"]["payer_client_ip"] == "1.2.3.4"
        assert body["scene_info"]["h5_info"]["type"] == "Wap"

    def test_build_native_payment_body(self, tmp_path):
        body = WechatPayClient(settings).build_native_payment("S20260818002", 9900, "https://e.com/n", "测试")
        assert body["out_trade_no"] == "S20260818002"
        assert body["amount"]["total"] == 9900
        assert "scene_info" not in body

    def test_sign_verify_roundtrip(self, tmp_path):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        message = "1\n2\n3\n"
        signature = key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = base64.b64encode(signature).decode()
        assert wechatpay._verify_message(key.public_key(), message, sig_b64)
        assert not wechatpay._verify_message(key.public_key(), message + "x", sig_b64)
        # 反例：非 RSA 密钥类型校验失败
        wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assert not wechatpay._verify_message(wrong.public_key(), message, sig_b64)

    def test_decrypt_resource_roundtrip(self, monkeypatch, tmp_path):
        _configure_wxpay(monkeypatch, tmp_path)
        client = WechatPayClient(settings)
        nonce = "abcdefghijkl"
        plain = '{"out_trade_no":"S1","amount":{"total":9900}}'
        cipher = AESGCM(APIV3_KEY.encode()).encrypt(nonce.encode(), plain.encode(), b"transaction")
        resource = {
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": base64.b64encode(cipher).decode("ascii"),
            "nonce": nonce,
            "associated_data": "transaction",
        }
        assert json.loads(client.decrypt_resource(resource))["out_trade_no"] == "S1"

    def test_auth_header_shape(self, monkeypatch, tmp_path):
        _configure_wxpay(monkeypatch, tmp_path)
        client = WechatPayClient(settings)
        auth = client._auth_header("POST", "/v3/pay/transactions/h5", '{"x":1}')
        assert auth.startswith("WECHATPAY2-SHA256-RSA2048 ")
        assert f'mchid="{MCHID}"' in auth
        assert 'serial_no="SERIAL0001"' in auth
        assert "signature=" in auth


# ===================== 创建订单：支付参数填充与降级 =====================


def test_create_order_not_configured_returns_null_pay_fields(client):
    pid = create_profile(client, _key="pay-degrade-profile")["profileId"]
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1}, headers={"Idempotency-Key": "pay-degrade"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payType"] is None and data["payUrl"] is None and data["codeUrl"] is None
    detail = client.get(f"/api/orders/{data['orderNo']}").json()["data"]
    assert detail["payUrl"] is None and detail["codeUrl"] is None
    assert detail["payType"] == "auto"


def test_create_order_h5_returns_pay_url(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path)
    monkeypatch.setattr(wechatpay.client, "create_h5_payment", lambda *a, **k: "https://wx.tenpay.com/cgi-bin/mmpayweb/bin/checkmweb?x=1")
    monkeypatch.setattr(wechatpay.client, "create_native_payment", lambda *a, **k: pytest.fail("不应走 native"))

    order_no = _create_order(client, key="pay-h5")
    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["payType"] == "h5"
    assert detail["payUrl"].startswith("https://wx.tenpay.com")
    assert detail["codeUrl"] is None


def test_create_order_h5_fallback_native(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path)

    def fail_h5(*a, **k):
        raise WechatPayError("PAY_ERROR", "h5 拉起失败")

    monkeypatch.setattr(wechatpay.client, "create_h5_payment", fail_h5)
    monkeypatch.setattr(wechatpay.client, "create_native_payment", lambda *a, **k: "weixin://wxpay/bizpayurl?pr=TEST")

    resp = client.post(
        "/api/orders",
        json={"profileId": create_profile(client, _key="pay-fb-profile")["profileId"], "productId": 1, "paymentMethod": "auto"},
        headers={"Idempotency-Key": "pay-fallback"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payType"] == "native"
    assert data["codeUrl"] == "weixin://wxpay/bizpayurl?pr=TEST"
    assert data["payUrl"] is None
    # 幂等键命中：重复下单返回同样结果
    again = client.post(
        "/api/orders",
        json={"profileId": create_profile(client, _key="pay-fb2-profile")["profileId"], "productId": 1},
        headers={"Idempotency-Key": "pay-fallback"},
    )
    assert again.json()["data"] == data


def test_create_order_upstream_failure_degrades_to_null(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path)
    monkeypatch.setattr(wechatpay.client, "create_h5_payment", lambda *a, **k: (_ for _ in ()).throw(WechatPayError("X", "boom")))
    monkeypatch.setattr(wechatpay.client, "create_native_payment", lambda *a, **k: (_ for _ in ()).throw(WechatPayError("X", "boom")))
    order_no = _create_order(client, key="pay-fail-degrade")
    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["payUrl"] is None and detail["codeUrl"] is None
    assert detail["state"] == "CREATED"


# ===================== 支付回调 /api/pay/notify =====================


def _notify(client, raw, headers):
    return client.post("/api/pay/notify", content=raw.encode("utf-8"), headers=headers)


def test_pay_notify_success_unlocks_exactly_once(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="notify-ok")

    payload = _success_payload(order_no)
    raw, headers = _make_callback(platform_key, payload)

    resp = _notify(client, raw, headers)
    assert resp.status_code == 200
    assert resp.json() == {"code": "SUCCESS"}

    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert order.paid_at is not None
        assert order.openid == "o_openid_test"
        report = db.query(Report).filter(Report.profile_id == order.profile_id).one()
        assert report.state == "unlocked"
        assert report.unlocked_at is not None
        txns = db.query(PayTransaction).filter(PayTransaction.order_no == order_no).all()
        assert len(txns) == 1
        assert txns[0].transaction_id == "4200001234567890"
        assert txns[0].pay_state == "SUCCESS"
        assert txns[0].raw_callback is not None

    # 重复回调：幂等返回 SUCCESS，不重复解锁/不重复落流水
    resp2 = _notify(client, raw, headers)
    assert resp2.json() == {"code": "SUCCESS"}
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value

    # 报告接口返回完整内容
    report_resp = client.get(f"/api/orders/{order_no}/report").json()["data"]
    assert report_resp["state"] == "UNLOCKED"
    assert report_resp["report"]["locked"] is False


def test_pay_notify_bad_signature_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="notify-badsig")

    raw, headers = _make_callback(platform_key, _success_payload(order_no), sign=False)
    resp = _notify(client, raw, headers)
    assert resp.json()["code"] == "FAIL"

    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CREATED.value
        assert db.query(PayTransaction).count() == 0


def test_pay_notify_wrong_signature_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="notify-wrongsig")

    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raw, headers = _make_callback(wrong_key, _success_payload(order_no))
    resp = _notify(client, raw, headers)
    assert resp.json()["code"] == "FAIL"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_pay_notify_amount_mismatch_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="notify-amt")

    raw, headers = _make_callback(platform_key, _success_payload(order_no), tamper_amount=1)
    resp = _notify(client, raw, headers)
    assert resp.json()["code"] == "FAIL"
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CREATED.value
        assert db.query(PayTransaction).count() == 0


def test_pay_notify_not_configured_fail(client_and_factory):
    client, _ = client_and_factory
    resp = client.post("/api/pay/notify", content=b"{}", headers={"Wechatpay-Signature": "x", "Wechatpay-Timestamp": "1", "Wechatpay-Nonce": "2"})
    assert resp.json()["code"] == "FAIL"


def test_pay_notify_closed_order_fail(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="notify-closed")
    client.post(f"/api/orders/{order_no}/close")

    raw, headers = _make_callback(platform_key, _success_payload(order_no))
    resp = _notify(client, raw, headers)
    assert resp.json()["code"] == "FAIL"
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CLOSED.value


def test_pay_notify_unknown_order_fail(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    raw, headers = _make_callback(platform_key, _success_payload("S20991231001"))
    resp = _notify(client, raw, headers)
    assert resp.json()["code"] == "FAIL"


# ===================== 查单推进 / 对账 =====================


def _make_order_stale(factory, order_no, minutes=40):
    with factory() as db:
        db.execute(
            update(Order).where(Order.order_no == order_no).values(created_at=utcnow() - datetime.timedelta(minutes=minutes))
        )
        db.commit()


def test_reconcile_success_advances_order(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="reconcile-ok")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(wechatpay.client, "query_order", lambda no: _success_payload(no, transaction_id="4200009999"))
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["checked"] == 1 and summary["success"] == 1
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.UNLOCKED.value
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1


def test_reconcile_closed_trade_marks_closed(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="reconcile-closed")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(wechatpay.client, "query_order", lambda no: {"trade_state": "CLOSED"})
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["checked"] == 1 and summary["closed"] == 1
    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.CLOSED.value
        assert order.fail_reason == "微信查单: CLOSED"


def test_reconcile_pending_keeps_created(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="reconcile-pending")
    _make_order_stale(factory, order_no)

    monkeypatch.setattr(wechatpay.client, "query_order", lambda no: {"trade_state": "NOTPAY"})
    with factory() as db:
        summary = reconcile.reconcile_once(db)

    assert summary["pending"] == 1
    with factory() as db:
        assert db.query(Order).filter(Order.order_no == order_no).one().state == OrderState.CREATED.value


def test_reconcile_skips_fresh_orders(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    _create_order(client, key="reconcile-fresh")

    monkeypatch.setattr(wechatpay.client, "query_order", lambda no: pytest.fail("不应查新订单"))
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["checked"] == 0


def test_reconcile_skips_already_unlocked_orders(client_and_factory, monkeypatch, tmp_path):
    """已解锁订单不在对账扫描集合（仅扫描 CREATED），不重复落流水。"""
    client, factory = client_and_factory
    platform_key = _configure_wxpay(monkeypatch, tmp_path)
    order_no = _create_order(client, key="reconcile-already")
    _make_order_stale(factory, order_no)

    raw, headers = _make_callback(platform_key, _success_payload(order_no, transaction_id="TXN-A"))
    assert _notify(client, raw, headers).json() == {"code": "SUCCESS"}

    monkeypatch.setattr(wechatpay.client, "query_order", lambda no: pytest.fail("已解锁订单不应被查单"))
    with factory() as db:
        summary = reconcile.reconcile_once(db)
    assert summary["checked"] == 0
    with factory() as db:
        assert db.query(PayTransaction).filter(PayTransaction.order_no == order_no).count() == 1


# ===================== 关单 =====================


def test_close_order_calls_wechat_when_configured(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="close-wechat")
    calls = []
    monkeypatch.setattr(wechatpay.client, "close_order", lambda no: calls.append(no))

    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "CLOSED"
    assert calls == [order_no]

    # 重复关单 → 12003，不再调微信
    resp2 = client.post(f"/api/orders/{order_no}/close")
    assert resp2.status_code == 409
    assert resp2.json()["code"] == 12003
    assert len(calls) == 1


def test_close_order_wechat_error_still_closes(client_and_factory, monkeypatch, tmp_path):
    client, _ = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="close-wechat-err")
    monkeypatch.setattr(wechatpay.client, "close_order", lambda no: (_ for _ in ()).throw(WechatPayError("X", "close failed")))
    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "CLOSED"


# ===================== 退款 =====================


def _paid_order(client, key) -> str:
    order_no = _create_order(client, key=key)
    resp = client.post(f"/api/orders/{order_no}/pay-success-mock")
    assert resp.status_code == 200
    return order_no


def test_refund_requires_paid_state(client):
    order_no = _create_order(client, key="refund-notpaid")
    resp = client.post(f"/api/orders/{order_no}/refund")
    assert resp.status_code == 409
    assert resp.json()["code"] == 12003


def test_refund_success_flow(client_and_factory, monkeypatch, tmp_path):
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _paid_order(client, "refund-ok")
    calls = {}
    monkeypatch.setattr(wechatpay.client, "create_refund", lambda **kw: calls.update(kw) or {"refund_id": "REF-1"})

    resp = client.post(f"/api/orders/{order_no}/refund", json={"reason": "用户申请退款"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["refundNo"] == f"R{order_no}"
    assert data["state"] == "REFUNDING"
    assert calls["out_trade_no"] == order_no
    assert calls["out_refund_no"] == f"R{order_no}"
    assert calls["total"] == 9900 and calls["refund_amount"] == 9900

    with factory() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert order.state == OrderState.REFUNDING.value

    # 重复发起 → 409 冲突
    resp2 = client.post(f"/api/orders/{order_no}/refund")
    assert resp2.status_code == 409
    assert resp2.json()["code"] == 10005


def test_refund_not_configured_raises(client):
    order_no = _paid_order(client, "refund-nocfg")
    resp = client.post(f"/api/orders/{order_no}/refund")
    assert resp.status_code == 502
    assert resp.json()["code"] == 12004


def test_refund_notify_placeholder(client):
    resp = client.post("/api/refund/notify", content=b'{"out_refund_no":"R1"}', headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.json()["code"] == "FAIL"


# ===================== 恰好一次（CAS） =====================

def test_apply_payment_result_cas_exactly_once(client_and_factory, monkeypatch, tmp_path):
    """CAS 保证恰好一次：首个会话推进成功，第二个会话判定已处理（不重复解锁/落流水）。"""
    client, factory = client_and_factory
    _configure_wxpay(monkeypatch, tmp_path, with_platform_cert=False)
    order_no = _create_order(client, key="cas-exactly-once")

    payload = _success_payload(order_no, transaction_id="TXN-CAS")
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