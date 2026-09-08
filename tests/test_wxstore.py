"""微信小店客户端基座测试：请求签名 golden、推送验签往返/防篡改、配置自检。

签名与验签规则来自代客下单对接文档 v1.0（四、六章）。
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import settings
from app.services import wxstore
from app.services.wxstore import (
    WxstoreClient,
    WxstoreError,
    missing_wxs_config,
    sign_request_body,
)


def _make_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    return priv, pub_pem


def _sign_push(priv, event_id, timestamp, nonce, content: str) -> str:
    plaintext = (str(event_id) + str(timestamp) + str(nonce) + content).encode("utf-8")
    sig = priv.sign(plaintext, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def _push_body(event_id, timestamp, nonce, content: str, sig: str) -> bytes:
    return json.dumps(
        {
            "eventId": event_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "content": content,
            "signature": sig,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


@pytest.fixture()
def push_key(monkeypatch):
    priv, pub_pem = _make_keypair()
    monkeypatch.setattr(settings, "WXS_PUSH_PUBLIC_KEY", pub_pem)
    wxstore.client._push_keys.clear()
    yield priv
    wxstore.client._push_keys.clear()


class TestSign:
    def test_sign_is_lower_md5_of_raw_plus_key(self):
        raw = '{"appid":"2099010100000001","source":3}'
        key = "k3y"
        expected = hashlib.md5((raw + key).encode("utf-8")).hexdigest().lower()
        assert sign_request_body(raw, key) == expected
        assert sign_request_body(raw, key) == sign_request_body(raw, key).lower()
        assert len(sign_request_body(raw, key)) == 32

    def test_sign_changes_with_whitespace(self, monkeypatch):
        """签名绑定原始字符串：重排空白即不同签名（签后不得格式化）。"""
        monkeypatch.setattr(settings, "WXS_APPID", "2099010100000001")
        monkeypatch.setattr(settings, "WXS_APPKEY", "k")
        a = '{"a":1,"b":2}'
        b = '{"a": 1, "b": 2}'
        assert sign_request_body(a, "k") != sign_request_body(b, "k")

    def test_auth_header_format(self, monkeypatch):
        monkeypatch.setattr(settings, "WXS_APPID", "2099010100000001")
        monkeypatch.setattr(settings, "WXS_APPKEY", "k")
        raw = '{"a":1}'
        header = WxstoreClient(settings)._auth_header(raw)
        sn, sign = header.split(" ")
        assert sn == "2099010100000001"
        assert sign == sign_request_body(raw, "k")


class TestVerifyPush:
    def test_roundtrip_with_doc_shaped_content(self, push_key):
        content = json.dumps(
            {"orderSn": "71655367906162", "orderAmount": 2, "orderStateCode": 35,
             "preOrderList": [{"preOrderId": "abc=="}], "items": [{"title": "大瓶可乐+炒饭", "quantity": "1"}]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sig = _sign_push(push_key, 2024013000594610646, 1706679507593, "j9xd5kc7ixcryy7at5rrrv24xty783th", content)
        event_id, parsed = wxstore.client.verify_push(_push_body(2024013000594610646, 1706679507593, "j9xd5kc7ixcryy7at5rrrv24xty783th", content, sig))
        assert event_id == "2024013000594610646"
        assert parsed["orderSn"] == "71655367906162"
        assert parsed["preOrderList"][0]["preOrderId"] == "abc=="

    def test_unicode_content_verifies_without_reserialize(self, push_key):
        """中文/转义内容按原字符串验签，不做二次序列化。"""
        content = json.dumps({"fieldName": "姓名", "content": "张三·备注"}, ensure_ascii=False, separators=(",", ":"))
        sig = _sign_push(push_key, 1, 2, "n", content)
        _, parsed = wxstore.client.verify_push(_push_body(1, 2, "n", content, sig))
        assert parsed["content"] == "张三·备注"

    def test_tampered_content_fails(self, push_key):
        content = json.dumps({"orderSn": "1", "orderAmount": 2}, separators=(",", ":"))
        sig = _sign_push(push_key, 1, 2, "n", content)
        bad = json.dumps({"orderSn": "1", "orderAmount": 3}, separators=(",", ":"))
        with pytest.raises(WxstoreError, match="SIGN_FAILED"):
            wxstore.client.verify_push(_push_body(1, 2, "n", bad, sig))

    def test_missing_field_rejected(self):
        with pytest.raises(WxstoreError):
            wxstore.client.verify_push(b'{"eventId":1}')

    def test_default_public_key_parses(self, monkeypatch):
        monkeypatch.setattr(settings, "WXS_PUSH_PUBLIC_KEY", None)
        wxstore.client._push_keys.clear()
        key = wxstore.client._push_public_key()
        assert key is not None


class TestEnvelopeAndConfig:
    def test_check_success_rejects(self):
        with pytest.raises(WxstoreError):
            WxstoreClient._check_success("/x", {"success": True, "code": "1001", "msg": "x"})
        with pytest.raises(WxstoreError):
            WxstoreClient._check_success("/x", {"success": False, "code": "0000"})
        assert WxstoreClient._check_success("/x", {"success": True, "code": "0000", "data": {}})

    def test_missing_config(self, monkeypatch):
        for k in ("WXS_APPID", "WXS_APPKEY", "WXS_MALL_SN", "WXS_MALL_SIGNATURE",
                  "WXS_MERCHANT_ID", "WXS_MERCHANT_USER_ID", "WXS_NOTIFY_URL",
                  "WXS_REFUND_NOTIFY_URL", "WXS_RETURN_URL"):
            monkeypatch.setattr(settings, k, None)
        missing = missing_wxs_config()
        assert "WXS_APPID" in missing and "WXS_APPKEY" in missing
        assert WxstoreClient(settings).is_ready is False

    def test_ready_when_full(self, monkeypatch):
        monkeypatch.setattr(settings, "WXS_APPID", "2099010100000001")
        monkeypatch.setattr(settings, "WXS_APPKEY", "k")
        monkeypatch.setattr(settings, "WXS_MALL_SN", "2099010100000000001")
        monkeypatch.setattr(settings, "WXS_MALL_SIGNATURE", "s")
        monkeypatch.setattr(settings, "WXS_MERCHANT_ID", "m")
        monkeypatch.setattr(settings, "WXS_MERCHANT_USER_ID", "u")
        monkeypatch.setattr(settings, "WXS_NOTIFY_URL", "https://www.sxzfcm.top/api/pay/notify")
        monkeypatch.setattr(settings, "WXS_REFUND_NOTIFY_URL", "https://www.sxzfcm.top/api/pay/refund-notify")
        monkeypatch.setattr(settings, "WXS_RETURN_URL", "https://www.sxzfcm.top/pay/{orderNo}")
        assert WxstoreClient(settings).is_ready is True
