"""微信支付 V3 客户端：轻量自实现（cryptography + stdlib urllib，无新增依赖）。

覆盖能力：
- 统一下单：H5（h5_url）与 Native（code_url）
- 主动查单、关单
- 请求签名（SHA256-RSA）与响应/回调验签（微信平台证书公钥）
- 回调 resource 报文 AES-256-GCM 解密（APIv3 密钥）

配置缺失时 is_ready 为 False，调用方应优雅降级（订单仍可创建、pay 字段返回 null）；
平台证书未配置时验签一律失败（回调返回 FAIL），不静默放行。
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)


class WechatPayError(Exception):
    """微信支付 API 错误（HTTP 非 2xx 或响应异常）。"""

    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message}")


def _sign_message(private_key: RSAPrivateKey, message: str) -> str:
    """SHA256-RSA（PKCS1v15）签名，返回 base64。"""
    signature = private_key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _verify_message(public_key, message: str, signature_b64: str) -> bool:
    """校验 SHA256-RSA 签名；任何异常视为验签失败。"""
    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


class WechatPayClient:
    """微信支付 V3 客户端。

    所有配置项实时读取 settings（便于测试 monkeypatch），私钥/公钥按路径懒加载缓存。
    """

    def __init__(self, cfg=None) -> None:
        self._cfg = cfg or settings
        self._private_keys: dict[str, RSAPrivateKey] = {}
        self._platform_keys: dict[str, object] = {}

    # ---- 配置就绪判定 ----

    @property
    def is_ready(self) -> bool:
        """统一下单所需商户参数是否齐备（缺任一则支付功能降级）。"""
        c = self._cfg
        return bool(
            c.WXPAY_MCHID
            and c.WXPAY_APPID
            and c.WXPAY_APIV3_KEY
            and c.WXPAY_PRIVATE_KEY_PATH
            and c.WXPAY_CERT_SERIAL
            and c.WXPAY_NOTIFY_URL
        )

    @property
    def platform_ready(self) -> bool:
        """平台证书就绪：notify 验签 / 响应验签的前提。"""
        return self.is_ready and bool(self._cfg.WXPAY_PLATFORM_CERT_PATH)

    # ---- 密钥加载 ----

    def _load_private_key(self) -> RSAPrivateKey:
        path = str(self._cfg.WXPAY_PRIVATE_KEY_PATH)
        if path not in self._private_keys:
            pem = Path(path).read_bytes()
            self._private_keys[path] = serialization.load_pem_private_key(pem, password=None)
        return self._private_keys[path]

    def _load_platform_key(self):
        path = str(self._cfg.WXPAY_PLATFORM_CERT_PATH)
        if path not in self._platform_keys:
            pem = Path(path).read_bytes()
            cert = x509.load_pem_x509_certificate(pem)
            self._platform_keys[path] = cert.public_key()
        return self._platform_keys[path]

    # ---- 签名 / 验签 / 解密 ----

    def verify_signature(self, timestamp: str, nonce: str, body_bytes: bytes, signature: str) -> bool:
        """校验微信回调/响应签名：message = {timestamp}\\n{nonce}\\n{body}\\n。"""
        if not self.platform_ready:
            logger.error("微信支付平台证书未配置，无法验签")
            return False
        message = f"{timestamp}\n{nonce}\n{body_bytes.decode('utf-8')}\n"
        return _verify_message(self._load_platform_key(), message, signature)

    def decrypt_resource(self, resource: dict) -> str:
        """解密回调 resource：AES-256-GCM（key=APIv3 密钥，aad=associated_data）。"""
        key = self._cfg.WXPAY_APIV3_KEY.encode("utf-8")
        if len(key) != 32:
            raise WechatPayError("CONFIG_ERROR", "WXPAY_APIV3_KEY 必须为 32 字节")
        plaintext = AESGCM(key).decrypt(
            resource["nonce"].encode("utf-8"),
            base64.b64decode(resource["ciphertext"]),
            (resource.get("associated_data") or "").encode("utf-8"),
        )
        return plaintext.decode("utf-8")

    # ---- 请求签名与 HTTP ----

    def _auth_header(self, method: str, path: str, body: str) -> str:
        timestamp = str(int(time.time()))
        nonce = str(int(time.time() * 1000))
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
        signature = _sign_message(self._load_private_key(), message)
        return (
            'WECHATPAY2-SHA256-RSA2048 mchid="%s",nonce_str="%s",signature="%s",'
            'timestamp="%s",serial_no="%s"' % (self._cfg.WXPAY_MCHID, nonce, signature, timestamp, self._cfg.WXPAY_CERT_SERIAL)
        )

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        """发起 V3 请求并校验响应签名，返回 JSON 对象。"""
        url = self._cfg.WXPAY_API_BASE + path
        payload = json.dumps(body, ensure_ascii=False) if body is not None else ""
        req = urllib.request.Request(url, data=payload.encode("utf-8") if body is not None else None, method=method)
        req.add_header("Authorization", self._auth_header(method, path, payload))
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "ZhenFan/1.0")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_raw = resp.read().decode("utf-8")
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as e:
            err_raw = e.read().decode("utf-8", errors="replace")
            try:
                err = json.loads(err_raw)
            except Exception:
                err = {"message": err_raw}
            raise WechatPayError(
                err.get("code", "HTTP_ERROR"),
                err.get("message", f"HTTP {e.code}"),
                e.code,
            ) from None
        except urllib.error.URLError as e:
            raise WechatPayError("NETWORK_ERROR", f"网络错误: {e.reason}") from None

        if self.platform_ready:
            sig = resp_headers.get("wechatpay-signature")
            ts = resp_headers.get("wechatpay-timestamp")
            nonce = resp_headers.get("wechatpay-nonce")
            if not (sig and ts and nonce) or not self.verify_signature(ts, nonce, resp_raw.encode("utf-8"), sig):
                raise WechatPayError("SIGN_ERROR", "微信响应验签失败")
        else:
            logger.warning("微信支付平台证书未配置，跳过响应验签（不推荐生产使用）")

        return json.loads(resp_raw) if resp_raw else {}

    # ---- 统一下单 ----

    def build_h5_payment(self, out_trade_no: str, total: int, notify_url: str, description: str, client_ip: str) -> dict:
        """H5 统一下单请求体（单位分）。"""
        return {
            "appid": self._cfg.WXPAY_APPID,
            "mchid": self._cfg.WXPAY_MCHID,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": total, "currency": "CNY"},
            "scene_info": {
                "payer_client_ip": client_ip,
                "h5_info": {"type": "Wap"},
            },
        }

    def build_native_payment(self, out_trade_no: str, total: int, notify_url: str, description: str) -> dict:
        """Native 统一下单请求体（单位分）。"""
        return {
            "appid": self._cfg.WXPAY_APPID,
            "mchid": self._cfg.WXPAY_MCHID,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": total, "currency": "CNY"},
        }

    def create_h5_payment(self, out_trade_no: str, total: int, description: str, client_ip: str) -> str:
        """H5 下单，返回 h5_url（mweb_url）。"""
        body = self.build_h5_payment(out_trade_no, total, self._cfg.WXPAY_NOTIFY_URL, description, client_ip)
        data = self._request("POST", "/v3/pay/transactions/h5", body)
        return data.get("h5_url") or ""

    def create_native_payment(self, out_trade_no: str, total: int, description: str) -> str:
        """Native 下单，返回 code_url（二维码内容）。"""
        body = self.build_native_payment(out_trade_no, total, self._cfg.WXPAY_NOTIFY_URL, description)
        data = self._request("POST", "/v3/pay/transactions/native", body)
        return data.get("code_url") or ""

    # ---- 查单 / 关单 ----

    def query_order(self, out_trade_no: str) -> dict:
        """主动查单：GET /v3/pay/transactions/out-trade-no/{no}?mchid=...。"""
        encoded = urllib.parse.quote(out_trade_no, safe="")
        path = f"/v3/pay/transactions/out-trade-no/{encoded}?mchid={self._cfg.WXPAY_MCHID}"
        return self._request("GET", path)

    def close_order(self, out_trade_no: str) -> None:
        """关单（幂等）：POST /v3/pay/transactions/out-trade-no/{no}/close。"""
        encoded = urllib.parse.quote(out_trade_no, safe="")
        self._request("POST", f"/v3/pay/transactions/out-trade-no/{encoded}/close", {"mchid": self._cfg.WXPAY_MCHID})


client = WechatPayClient()