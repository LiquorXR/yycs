"""收钱吧微信小店·代客下单客户端（open-api.shouqianba.com）。

协议来源：代客下单对接文档 v1.0（2026-08-19，基于官方在线文档快照）。
核心规范：
- 全部 HTTPS POST + JSON（含查询类）；金额 Long，单位分；字符 UTF-8
- 请求签名 sign = MD5(raw body + appKey)，输出小写十六进制；
  头 Authorization: "{appid} {sign}"（单空格）；签名必须使用实际发送的
  JSON 原始字符串（紧凑 separators=(",", ":") ensure_ascii=False），签后不得重排
- 同步成功判定：success 为 True 且 code == "0000"
- 推送验签：明文 eventId + timestamp + nonce + content（content 取业务内容
  字符串本身，禁止解析后再序列化），SHA256WithRSA；eventId 做幂等键
- appKey 只存服务端，严禁下发前端、严禁打印日志
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.request
from urllib.parse import quote, urlencode

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings

logger = logging.getLogger(__name__)


class WxstoreError(Exception):
    """微信小店 API 错误（HTTP 非 2xx 或业务失败）。"""

    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message}")


# 产线公共业务推送 RSA 公钥（对接文档第六章明文；WXS_PUSH_PUBLIC_KEY 为空时使用）。
# 公钥本身可公开；发票推送使用专用公钥（本期无发票流程，不涉及）。
DEFAULT_PUSH_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuf1oOZm3u5NraTs4F8AA
BXbtU2jSiWYp+IWmQ36vokuq6s2s3eKQR6l4RkrPPxjC86bIvjT4pApJZJrFMA4Y
cjY4G49wFZySfom4IPaZlKsOrNGJH0Kag0BSO9U5el1z7dMz7oP9cChbdl4mjKuq
YtgnNtaPT+SqhXRQdFcc9kiVybAGs8WEGqsdwxsmD9aZTd4rQMvLEGWIj/MLdo7w
1avc0WVSPQSM5jRHjjQmUzEuusv+QGcDt3ttNaip2uo1xoQdcwILYmS6fnWL8xKw
4V8lX0CWypUKIZcIc1Y/1N8VeUN+8MirdrS5JSghq62Yifu9A3W/mANB+S6yYwD+
WQIDAQAB
-----END PUBLIC KEY-----"""

# H5 直达收银台地址白名单（短链解析后校验，防开放重定向劫持）
JUMP_URL_HOST = "optimus-c-share.shouqianba.com"
JUMP_URL_PATH_PREFIX = "/jumpMallLandingPage/"

# 微信小店小程序直跳（复刻官方中转页行为，解决普通浏览器/快手 WebView 内
# 拉起微信 App 支付；失败一律回落 H5 短链流程）。
# 微信小程序 appId/pagePath 按商城经公开接口获取后缓存。
MINIAPP_ENV_VERSION = "release"


def build_wechat_jump_url(appid: str, page_path: str, mall_sn: str, signature: str, pre_order_id: str) -> str:
    """构造微信直跳 URL：weixin://dl/business/?appid=..&path=..&query=..&env_version=release。

    query 内层为标准 urlencode({mallSn, signature, pageType, preOrderId})，
    外层整体再编码一次（与官方中转页逐字节对齐）。
    """
    inner = urlencode(
        {"mallSn": mall_sn, "signature": signature, "pageType": "5", "preOrderId": pre_order_id}
    )
    return (
        f"weixin://dl/business/?appid={appid}"
        f"&path={page_path.lstrip('/')}"
        f"&query={quote(inner, safe='')}"
        f"&env_version={MINIAPP_ENV_VERSION}"
    )


# 预订单状态（queryPreOrder state）：0 待支付；1 已完成；2 已取消
PREORDER_PENDING = "0"
PREORDER_DONE = "1"
PREORDER_CANCELED = "2"


def _is_valid_https_url(value: str | None, allow_orderno_placeholder: bool = False) -> bool:
    """推送/回跳 URL 合法性：须 https:// 开头，且不含未替换占位。"""
    if not value or not isinstance(value, str):
        return False
    t = value.strip()
    if not t.lower().startswith("https://"):
        return False
    if "YOUR_DOMAIN" in t:
        return False
    rest = t.replace("{orderNo}", "") if allow_orderno_placeholder else t
    if "{" in rest or "}" in rest:
        return False
    return True


def missing_wxs_config(cfg=None) -> list[str]:
    """缺失的微信小店配置项名（不回显值），供 /api/health 定位。"""
    c = cfg or settings
    missing: list[str] = []
    if not (c.WXS_APPID or "").strip():
        missing.append("WXS_APPID")
    if not (c.WXS_APPKEY or "").strip():
        missing.append("WXS_APPKEY")
    if not (c.WXS_MALL_SN or "").strip():
        missing.append("WXS_MALL_SN")
    if not (c.WXS_MALL_SIGNATURE or "").strip():
        missing.append("WXS_MALL_SIGNATURE")
    if not (c.WXS_MERCHANT_ID or "").strip():
        missing.append("WXS_MERCHANT_ID")
    if not (c.WXS_MERCHANT_USER_ID or "").strip():
        missing.append("WXS_MERCHANT_USER_ID")
    if not _is_valid_https_url(c.WXS_NOTIFY_URL):
        missing.append("WXS_NOTIFY_URL")
    if not _is_valid_https_url(getattr(c, "WXS_REFUND_NOTIFY_URL", None)):
        missing.append("WXS_REFUND_NOTIFY_URL")
    if not _is_valid_https_url(c.WXS_RETURN_URL, allow_orderno_placeholder=True):
        missing.append("WXS_RETURN_URL")
    return missing


def sign_request_body(raw_body: str, appkey: str) -> str:
    """请求签名：MD5(raw body + appKey)，小写十六进制。raw_body 须为实际发送串。"""
    return hashlib.md5((raw_body + appkey).encode("utf-8")).hexdigest().lower()


def _compact_dumps(payload: dict) -> str:
    """紧凑 JSON 序列化（签名与发送共用同一字符串，防二次格式化）。"""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class WxstoreClient:
    """微信小店客户端。所有配置项实时读取 settings（便于测试 monkeypatch）。"""

    def __init__(self, cfg=None) -> None:
        self._cfg = cfg or settings
        self._push_keys: dict[str, object] = {}

    # ---- 配置就绪判定 ----

    @property
    def is_ready(self) -> bool:
        """下单所需参数是否齐备（缺任一则支付功能降级；URL 须合法 https）。"""
        c = self._cfg
        return bool(
            (c.WXS_APPID or "").strip()
            and (c.WXS_APPKEY or "").strip()
            and (c.WXS_MALL_SN or "").strip()
            and (c.WXS_MALL_SIGNATURE or "").strip()
            and (c.WXS_MERCHANT_ID or "").strip()
            and (c.WXS_MERCHANT_USER_ID or "").strip()
            and _is_valid_https_url(c.WXS_NOTIFY_URL)
            and _is_valid_https_url(c.WXS_RETURN_URL, allow_orderno_placeholder=True)
        )

    # ---- 通用请求 ----

    def _auth_header(self, raw_body: str) -> str:
        c = self._cfg
        appid = str(c.WXS_APPID or "").strip()
        appkey = str(c.WXS_APPKEY or "").strip()
        return f"{appid} {sign_request_body(raw_body, appkey)}"

    def _post_sync(self, path: str, payload: dict, timeout: float = 10.0) -> dict:
        url = str(self._cfg.WXS_API_BASE).rstrip("/") + path
        raw_body = _compact_dumps(payload)
        req = urllib.request.Request(url, data=raw_body.encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", self._auth_header(raw_body))
        req.add_header("User-Agent", "ZhenFan/1.0")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            logger.error("wxs request failed path=%s err=%s", path, type(e).__name__)
            raise WxstoreError("NETWORK_ERROR", "网络错误") from None
        try:
            data = json.loads(raw) if raw else {}
        except Exception as e:  # noqa: BLE001
            raise WxstoreError("RESPONSE_ERROR", f"响应解析失败: {e}") from None
        return self._check_success(path, data)

    async def _post_async(self, path: str, payload: dict, timeout: float = 10.0) -> dict:
        url = str(self._cfg.WXS_API_BASE).rstrip("/") + path
        raw_body = _compact_dumps(payload)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": self._auth_header(raw_body),
            "User-Agent": "ZhenFan/1.0",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as hc:
                resp = await hc.post(url, content=raw_body.encode("utf-8"), headers=headers)
        except Exception as e:  # noqa: BLE001
            logger.error("wxs request failed path=%s err=%s", path, type(e).__name__)
            raise WxstoreError("NETWORK_ERROR", "网络错误") from None
        if resp.status_code >= 400:
            raise WxstoreError("HTTP_ERROR", f"HTTP {resp.status_code}", resp.status_code)
        try:
            data = json.loads(resp.text) if resp.text else {}
        except Exception as e:  # noqa: BLE001
            raise WxstoreError("RESPONSE_ERROR", f"响应解析失败: {e}") from None
        return self._check_success(path, data)

    @staticmethod
    def _check_success(path: str, data: dict) -> dict:
        if not isinstance(data, dict) or data.get("success") is not True or str(data.get("code")) != "0000":
            raise WxstoreError(str(data.get("code", "BIZ_FAIL") if isinstance(data, dict) else "BIZ_FAIL"), f"业务失败: {str(data)[:300]}")
        return data

    def _base_fields(self) -> dict:
        c = self._cfg
        return {
            "appid": str(c.WXS_APPID or "").strip(),
            "seller": {
                "merchantId": str(c.WXS_MERCHANT_ID or "").strip(),
                "merchantUserId": str(c.WXS_MERCHANT_USER_ID or "").strip(),
                "role": str(c.WXS_SELLER_ROLE or "super_admin").strip() or "super_admin",
            },
        }

    def _mall_fields(self) -> dict:
        c = self._cfg
        return {
            "mallSn": str(c.WXS_MALL_SN or "").strip(),
            "signature": str(c.WXS_MALL_SIGNATURE or "").strip(),
        }

    # ---- 代客下单 ----

    async def save_pre_order(self, amount: int, request_id: str, timeout: float = 10.0) -> str:
        """创建代客下单（金额结算 type=2），返回全局唯一 preOrderId。"""
        c = self._cfg
        payload = {
            **self._base_fields(),
            "mallID": self._mall_fields(),
            "source": 3,
            "amount": {"oriAmount": int(amount)},
            "checkout": {"type": 2},
            "scenes": str(c.WXS_SCENES or "[]"),
            "requestId": str(request_id),
        }
        data = await self._post_async("/optimus/module/open/preOrder/savePreOrder", payload, timeout=timeout)
        pre_order_id = ((data.get("data") or {}).get("preOrderId") or "")
        if not pre_order_id:
            raise WxstoreError("BIZ_FAIL", "创建预订单未返回 preOrderId")
        return str(pre_order_id)

    async def generate_h5_link(self, pre_order_id: str, timeout: float = 10.0) -> str:
        """按 preOrderId 生成 H5 短链（pageType=5 固定）。"""
        payload = {**self._base_fields(), "preOrderId": str(pre_order_id), "pageType": "5"}
        data = await self._post_async("/optimus/module/open/preOrder/generatePreOrderH5Link", payload, timeout=timeout)
        link = ((data.get("data") or {}).get("preOrderH5Link") or "")
        if not link:
            raise WxstoreError("BIZ_FAIL", "生成 H5 链接失败")
        return str(link)

    @staticmethod
    def is_jump_url(url: str | None) -> bool:
        """直达收银台地址合法性：限定官方 host + 跳转路径前缀，防开放重定向。"""
        if not url or not isinstance(url, str):
            return False
        try:
            from urllib.parse import urlparse

            u = urlparse(url.strip())
            return (
                u.scheme == "https"
                and u.hostname == JUMP_URL_HOST
                and (u.path or "").startswith(JUMP_URL_PATH_PREFIX)
            )
        except Exception:  # noqa: BLE001
            return False

    async def resolve_h5_jump_url(self, short_link: str, timeout: float = 5.0) -> str:
        """解析 H5 短链得直达收银台地址（跟随跳转一次，无状态变更）。

        短链由官方生成，直达地址 path-id 随单变化，不可硬编码/自拼。
        非法目标直接抛错，由调用方降级（绝不阻塞建单）。
        """
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=5) as hc:
                resp = await hc.get(
                    short_link.strip(),
                    headers={"User-Agent": "ZhenFan/1.0"},
                )
        except Exception as e:  # noqa: BLE001
            raise WxstoreError("NETWORK_ERROR", "短链解析网络错误") from None
        final_url = str(resp.url)
        if not self.is_jump_url(final_url):
            raise WxstoreError("BIZ_FAIL", f"短链目标非法: {final_url[:120]}")
        return final_url

    def query_pre_order(self, pre_order_id: str, timeout: float = 10.0) -> dict:
        """查询预订单（同步，供对账线程用），返回归一化 {state, amount, order_sn}。

        state: "0" 待支付；"1" 已完成；"2" 已取消（原文 stateDesc 仅展示用）。
        """
        payload = {**self._base_fields(), "preOrderId": str(pre_order_id)}
        data = self._post_sync("/optimus/module/open/preOrder/queryPreOrder", payload, timeout=timeout)
        inner = data.get("data") or {}
        amount = inner.get("amount") or {}
        disc = amount.get("discAmount", amount.get("oriAmount"))
        try:
            total = int(disc) if disc is not None else None
        except (TypeError, ValueError):
            total = None
        return {
            "state": str(inner.get("state", "")),
            "amount": total,
            "order_sn": inner.get("orderSn"),
            "pre_order_id": inner.get("preOrderId") or pre_order_id,
        }

    def delete_pre_order(self, pre_order_id: str, timeout: float = 10.0) -> dict:
        """删除/取消未支付预订单（best-effort，供关单时同步上游）。"""
        payload = {**self._base_fields(), "preOrderId": str(pre_order_id)}
        return self._post_sync("/optimus/module/open/preOrder/deletePreOrder", payload, timeout=timeout)

    # ---- 小程序直跳信息（公开接口，无鉴权，按商城缓存） ----

    _miniapp_cache: dict[str, dict] = {}

    def get_miniapp_info(self, timeout: float = 10.0) -> dict:
        """查询商城小程序信息 {appid, page_path}。

        优先取配置 WXS_MINIAPP_APPID/WXS_MINIAPP_PAGE_PATH（开通资料固定值，跳过运行时
        无鉴权接口）；未配置才实时调用 queryMallUsingAppId（按商城缓存）。失败抛
        WxstoreError（携带具体原因），由调用方回落短链流程。
        """
        c = self._cfg
        cfg_appid = (c.WXS_MINIAPP_APPID or "").strip()
        cfg_path = (c.WXS_MINIAPP_PAGE_PATH or "").strip()
        if cfg_appid and cfg_path:
            return {"appid": cfg_appid, "page_path": cfg_path}

        mall_sn = str(c.WXS_MALL_SN or "").strip()
        if not mall_sn:
            raise WxstoreError("CONFIG_ERROR", "商城号缺失")
        cached = self._miniapp_cache.get(mall_sn)
        if cached:
            return cached
        url = "https://mapi.shouqianba.com/optimus/mall/queryMallUsingAppId?client_version=1.0.0"
        payload = {"mallID": self._mall_fields(), "environment": "weixin"}
        raw_body = _compact_dumps(payload)
        req = urllib.request.Request(url, data=raw_body.encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json;charset=UTF-8")
        req.add_header("User-Agent", "ZhenFan/1.0")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            logger.error("queryMallUsingAppId 请求异常: %s", e)
            raise WxstoreError("NETWORK_ERROR", "小程序信息查询网络错误") from None
        try:
            data = json.loads(raw)
        except Exception as e:  # noqa: BLE001
            logger.error("queryMallUsingAppId 响应解析失败: %s raw=%s", e, raw[:300])
            raise WxstoreError("RESPONSE_ERROR", "小程序信息响应解析失败") from None
        try:
            inner = (data.get("data") or {}).get("data") or {}
            appid = inner.get("appId") or inner.get("appid")
            page_path = inner.get("pagePath")
            if not appid or not page_path:
                raise KeyError("appId/pagePath")
        except (KeyError, AttributeError, TypeError) as e:
            logger.error("queryMallUsingAppId 缺字段: %s raw=%s", e, raw[:300])
            raise WxstoreError("BIZ_FAIL", f"小程序信息缺失: {raw[:200]}") from None
        info = {"appid": str(appid), "page_path": str(page_path)}
        self._miniapp_cache[mall_sn] = info
        return info

    def build_wechat_jump(self, pre_order_id: str) -> str:
        """构造微信直跳 URL；失败抛错由调用方回落短链。"""
        c = self._cfg
        info = self.get_miniapp_info()
        mall_sn = str(c.WXS_MALL_SN or "").strip()
        signature = str(c.WXS_MALL_SIGNATURE or "").strip()
        return build_wechat_jump_url(info["appid"], info["page_path"], mall_sn, signature, str(pre_order_id))

    # ---- 推送验签 ----

    def _push_public_key(self):
        pem = str(self._cfg.WXS_PUSH_PUBLIC_KEY or "").strip() or DEFAULT_PUSH_PUBLIC_KEY_PEM
        cached = self._push_keys.get(pem)
        if cached is not None:
            return cached
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
        self._push_keys[pem] = key
        return key

    def verify_push(self, raw_body: bytes) -> tuple[str, dict]:
        """验签推送并返回 (event_id, content_dict)。

        明文 eventId + timestamp + nonce + content（content 取业务内容字符串
        本身，禁止解析后再序列化；eventId/timestamp 取原文数值转字符串）。
        任何异常视为验签失败抛 WxstoreError。
        """
        try:
            outer = json.loads(raw_body.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise WxstoreError("INVALID_BODY", f"推送正文解析失败: {e}") from None
        try:
            event_id = str(outer["eventId"])
            timestamp = str(outer["timestamp"])
            nonce = str(outer["nonce"])
            content = outer["content"]
            signature_b64 = outer["signature"]
            if not isinstance(content, str) or not signature_b64:
                raise KeyError("content/signature")
        except KeyError as e:
            raise WxstoreError("INVALID_BODY", f"推送缺字段: {e}") from None
        plaintext = (event_id + timestamp + nonce + content).encode("utf-8")
        try:
            public_key = self._push_public_key()
            public_key.verify(
                base64.b64decode(signature_b64.strip()),
                plaintext,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError, KeyError, OSError) as e:
            raise WxstoreError("SIGN_FAILED", "推送验签失败") from None
        try:
            return event_id, json.loads(content)
        except Exception as e:  # noqa: BLE001
            raise WxstoreError("INVALID_BODY", f"content 解析失败: {e}") from None


client = WxstoreClient()
