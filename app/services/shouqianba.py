"""收钱吧聚合支付客户端（微信+支付宝双通道）。

覆盖能力：
- WAP 跳转支付：本地拼 `GET {gateway}?QUERY` 302 跳转收银台，无需服务端预下单外呼
- 聚合码预下单：`POST /upay/v2/precreate` 拿短链/二维码（快手 WebView 拦截降级用）
- 主动查单：`POST /upay/v2/query`（对账/轮询用）
- 回调验签：`Authorization: sign` RSA-SHA256 验签，业务成功回纯文本 "success"

签名规则：
- WAP 网关：ASCII 排序拼 `k=v&...&key=terminal_key` 后 MD5 大写
- VSI 接口：`sign = MD5(body_bytes + key_bytes)` 大写，头 `Authorization: {sn} {sign}`
  （body 为紧凑 JSON `separators=(",", ":") + ensure_ascii=False` 的 UTF-8 字节，待沙箱对照确认）

回调协议假设（待沙箱真报文复核确认，任一不符即全量 fail，需对照修订）：
- 回调头为 `Authorization: {terminal_sn} {base64(RSA-SHA256)}` 两段式
- 验签原文为回调 HTTP body 整体字节
- 正文含 `terminal_sn/client_sn/total_amount(分)/order_status`，成功态为 `PAID`

配置缺失时 is_ready 为 False，调用方应优雅降级（订单仍可创建、pay 字段返回 null）；
公钥未配置时验签一律失败（回调返回 fail），不静默放行。
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings

logger = logging.getLogger(__name__)


class ShouqianbaError(Exception):
    """收钱吧 API 错误（HTTP 非 2xx 或业务失败）。"""

    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message}")


# 支付通道：1=支付宝、3=微信（附录《支付方式》）
PAYWAY_ALIPAY = "1"
PAYWAY_WECHAT = "3"

# 终态判定（开放平台《交易结果和异常处理》，待沙箱真报文复核确认）
PAID_STATUS = "PAID"
FAILED_STATUSES = {"PAY_CANCELED"}
PENDING_STATUSES = {"CREATED", "PAY_ERROR"}
# 退款类状态不应出现在 CREATED 扫描集合；若出现按待处理保留并告警（人工核账）
REFUND_FINAL_STATUSES = {"REFUNDED", "PARTIAL_REFUNDED"}
REFUND_PENDING_STATUSES = {"REFUND_INPROGRESS", "REFUND_ERROR"}
REFUND_FAILED_STATUSES = {"FAIL_CANCELED"}


def md5_upper(content: bytes) -> str:
    return hashlib.md5(content).hexdigest().upper()


def sign_wap_params(params: dict[str, str], key: str) -> str:
    """WAP 网关签名：排序拼串后 MD5 大写。"""
    string_a = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return md5_upper(f"{string_a}&key={key}".encode("utf-8"))


def sign_vsi_body(body: str, key: str) -> str:
    """VSI 接口签名：MD5(body_bytes + key_bytes) 大写。"""
    return md5_upper(body.encode("utf-8") + key.encode("utf-8"))


def resolve_payway(payment_method: str | None) -> str:
    """按订单支付方式解析收钱吧 payway。默认微信。"""
    if (payment_method or "").lower().startswith("ali"):
        return PAYWAY_ALIPAY
    return PAYWAY_WECHAT


def normalize_amount(value: object) -> int | None:
    """归一化金额（分）：接受非负整数 int / 纯数字字符串；float 仅当 is_integer 时兼容，其余拒绝。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 9999999999 else None
    if isinstance(value, float):
        if value.is_integer() and 0 <= value <= 9999999999:
            return int(value)
        return None
    if isinstance(value, str):
        t = value.strip()
        if not t or len(t) > 10 or not t.isdigit():
            return None
        try:
            return int(t)
        except ValueError:
            return None
    return None


def _is_valid_https_url(value: str | None, allow_orderno_placeholder: bool = False) -> bool:
    """回调/回跳 URL 合法性：须 https:// 开头，且不含未替换占位（YOUR_DOMAIN 等示例值）。"""
    if not value or not isinstance(value, str):
        return False
    t = value.strip()
    if not t.lower().startswith("https://"):
        return False
    if "YOUR_DOMAIN" in t or "{" in t.replace("{orderNo}", "") if allow_orderno_placeholder else ("{" in t or "}" in t):
        return False
    return True


def missing_sqb_config(cfg=None) -> list[str]:
    """缺失的收钱吧配置项名（不回显值），供 /api/health 定位。"""
    c = cfg or settings
    missing: list[str] = []
    if not (c.SQB_TERMINAL_SN or "").strip():
        missing.append("SQB_TERMINAL_SN")
    if not (c.SQB_TERMINAL_KEY or "").strip():
        missing.append("SQB_TERMINAL_KEY")
    if not (c.SQB_OPERATOR or "").strip():
        missing.append("SQB_OPERATOR")
    if not _is_valid_https_url(c.SQB_NOTIFY_URL):
        missing.append("SQB_NOTIFY_URL")
    if not _is_valid_https_url(getattr(c, "SQB_REFUND_NOTIFY_URL", None)):
        missing.append("SQB_REFUND_NOTIFY_URL")
    if not _is_valid_https_url(c.SQB_RETURN_URL, allow_orderno_placeholder=True):
        missing.append("SQB_RETURN_URL")
    if not (c.SQB_PUBLIC_KEY_PATH or "").strip():
        missing.append("SQB_PUBLIC_KEY_PATH")
    return missing


def resolve_return_url(order_no: str, base: str | None = None) -> str | None:
    """解析同步回跳地址：支持 {orderNo} 占位，否则自动拼 /{orderNo}；非 https 直接返回 None。"""
    template = base if base is not None else settings.SQB_RETURN_URL
    if not template:
        return None
    template = template.strip()
    if "{orderNo}" in template:
        url = template.replace("{orderNo}", order_no)
    elif order_no and order_no not in template:
        url = template.rstrip("/") + f"/{order_no}"
    else:
        url = template
    return url if _is_valid_https_url(url) else None


class ShouqianbaClient:
    """收钱吧客户端。所有配置项实时读取 settings（便于测试 monkeypatch）。"""

    def __init__(self, cfg=None) -> None:
        self._cfg = cfg or settings
        self._public_keys: dict[str, object] = {}

    # ---- 配置就绪判定 ----

    @property
    def is_ready(self) -> bool:
        """下单所需参数是否齐备（缺任一则支付功能降级；URL 须合法 https 且无占位）。"""
        c = self._cfg
        return bool(
            (c.SQB_TERMINAL_SN or "").strip()
            and (c.SQB_TERMINAL_KEY or "").strip()
            and (c.SQB_OPERATOR or "").strip()
            and _is_valid_https_url(c.SQB_NOTIFY_URL)
            and _is_valid_https_url(c.SQB_RETURN_URL, allow_orderno_placeholder=True)
        )

    @property
    def verify_ready(self) -> bool:
        """验签就绪：notify 验签仅需 TERMINAL_SN + 公钥，与回跳/操作员配置解耦。"""
        c = self._cfg
        return bool((c.SQB_TERMINAL_SN or "").strip() and (c.SQB_PUBLIC_KEY_PATH or "").strip())

    # ---- WAP 跳转（纯本地拼串，无网络） ----

    def build_wap_url(
        self,
        client_sn: str,
        total_amount: int,
        subject: str,
        payway: str | None = None,
        operator: str | None = None,
        notify_url: str | None = None,
        return_url: str | None = None,
    ) -> str:
        c = self._cfg
        terminal_sn = (c.SQB_TERMINAL_SN or "").strip()
        terminal_key = (c.SQB_TERMINAL_KEY or "").strip()
        notify = (notify_url or c.SQB_NOTIFY_URL or "").strip()
        ret = (return_url or resolve_return_url(client_sn) or "").strip()
        op = (operator or c.SQB_OPERATOR or "").strip()
        if not (terminal_sn and terminal_key and notify and ret and op):
            raise ShouqianbaError("CONFIG_ERROR", "收钱吧终端/回调/操作员配置缺失")
        params: dict[str, str] = {
            "terminal_sn": str(terminal_sn),
            "client_sn": str(client_sn),
            "total_amount": str(int(total_amount)),
            "subject": (subject or "振凡命理·测算服务")[:64],
            "operator": str(op)[:32],
            "notify_url": str(notify),
            "return_url": str(ret),
        }
        if payway:
            params["payway"] = str(payway)
        params["sign"] = sign_wap_params(params, str(terminal_key))
        return f"{c.SQB_GATEWAY}?{urllib.parse.urlencode(params)}"

    # ---- VSI 接口通用请求 ----

    def _auth_header(self, body: str) -> str:
        c = self._cfg
        sn = str(c.SQB_TERMINAL_SN or "").strip()
        key = str(c.SQB_TERMINAL_KEY or "").strip()
        return f"{sn} {sign_vsi_body(body, key)}"

    def _post_sync(self, path: str, payload: dict, timeout: float = 10.0) -> dict:
        url = str(self._cfg.SQB_API_BASE).rstrip("/") + path
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", self._auth_header(body))
        req.add_header("User-Agent", "ZhenFan/1.0")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            logger.error("sqb request failed path=%s err=%s", path, e)
            raise ShouqianbaError("NETWORK_ERROR", f"网络错误: {e}") from None
        try:
            return json.loads(raw) if raw else {}
        except Exception as e:  # noqa: BLE001
            raise ShouqianbaError("RESPONSE_ERROR", f"响应解析失败: {e}") from None

    async def _post_async(self, path: str, payload: dict, timeout: float = 10.0) -> dict:
        url = str(self._cfg.SQB_API_BASE).rstrip("/") + path
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._auth_header(body),
            "User-Agent": "ZhenFan/1.0",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as hc:
                resp = await hc.post(url, content=body.encode("utf-8"), headers=headers)
        except Exception as e:  # noqa: BLE001
            logger.error("sqb request failed path=%s err=%s", path, e)
            raise ShouqianbaError("NETWORK_ERROR", f"网络错误: {e}") from None
        if resp.status_code >= 400:
            raise ShouqianbaError("HTTP_ERROR", f"HTTP {resp.status_code}", resp.status_code)
        try:
            return json.loads(resp.text) if resp.text else {}
        except Exception as e:  # noqa: BLE001
            raise ShouqianbaError("RESPONSE_ERROR", f"响应解析失败: {e}") from None

    # ---- 预下单（聚合码降级） ----

    @staticmethod
    def _extract_precreate_link(data: dict) -> str:
        """兼容新老两种返回形状，提取二维码短链/内容。"""
        biz = data.get("biz_response") or {}
        inner = biz.get("data") or {}
        for key in ("qr_code", "qrCode", "code_url", "codeUrl", "short_link", "shortLink", "url"):
            val = inner.get(key) or data.get(key)
            if val:
                return str(val)
        # 兼容 biz_response.data 为字符串的形状
        if isinstance(inner, str) and inner.startswith("http"):
            return inner
        return ""

    async def precreate_qr(
        self,
        client_sn: str,
        total_amount: int,
        subject: str,
        payway: str | None = None,
        operator: str | None = None,
        timeout: float = 10.0,
    ) -> str:
        c = self._cfg
        op = (operator or c.SQB_OPERATOR or "").strip()
        if not op:
            raise ShouqianbaError("CONFIG_ERROR", "收钱吧操作员配置缺失")
        payload: dict = {
            "terminal_sn": str(c.SQB_TERMINAL_SN or ""),
            "client_sn": str(client_sn),
            "total_amount": str(int(total_amount)),
            "subject": (subject or "振凡命理·测算服务")[:64],
            "operator": str(op)[:32],
        }
        if payway:
            payload["payway"] = str(payway)
        data = await self._post_async("/upay/v2/precreate", payload, timeout=timeout)
        # 业务成功判定：兼容 result_code / biz_response.result_code
        ok = data.get("result_code") in ("200", 200, "SUCCESS") or (data.get("biz_response") or {}).get("result_code") in (
            "PRECREATE_SUCCESS",
            "SUCCESS",
            "200",
        )
        link = self._extract_precreate_link(data)
        if not ok or not link:
            raise ShouqianbaError("PRECREATE_FAILED", f"预下单失败: {json.dumps(data, ensure_ascii=False)[:300]}")
        return link

    # ---- 查单 ----

    @staticmethod
    def normalize_query(data: dict) -> dict:
        """归一化查单结果为 {order_status, total_amount(int), sn, client_sn, payway}。"""
        biz = data.get("biz_response") or {}
        inner = biz.get("data") or {}
        src = inner if isinstance(inner, dict) and inner else (biz if biz else data)
        status = src.get("order_status") or src.get("status") or data.get("order_status") or ""
        total_int = normalize_amount(src.get("total_amount"))
        return {
            "order_status": str(status),
            "total_amount": total_int,
            "sn": src.get("sn") or data.get("sn"),
            "client_sn": src.get("client_sn") or data.get("client_sn"),
            "payway": src.get("payway"),
        }

    def query_order(self, client_sn: str, timeout: float = 10.0) -> dict:
        """主动查单（同步，供对账线程用），返回归一化结果。"""
        payload = {"terminal_sn": str(self._cfg.SQB_TERMINAL_SN or "").strip(), "client_sn": str(client_sn)}
        data = self._post_sync("/upay/v2/query", payload, timeout=timeout)
        return self.normalize_query(data)

    def cancel_order(self, client_sn: str, timeout: float = 10.0) -> dict:
        """撤单/关单（best-effort，供用户关单时同步上游；失败由调用方吞掉不阻塞本地关单）。"""
        payload = {"terminal_sn": str(self._cfg.SQB_TERMINAL_SN or "").strip(), "client_sn": str(client_sn)}
        return self._post_sync("/upay/v2/cancel", payload, timeout=timeout)

    # ---- 回调验签 ----

    def _load_public_key(self):
        path = str(self._cfg.SQB_PUBLIC_KEY_PATH or "").strip()
        try:
            mtime = Path(path).stat().st_mtime
        except OSError:
            # 文件缺失：清缓存并上抛，由调用方记 error（含路径）后 fail
            self._public_keys.pop(path, None)
            raise
        cached = self._public_keys.get(path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        pem = Path(path).read_bytes()
        key = serialization.load_pem_public_key(pem)
        self._public_keys[path] = (mtime, key)
        return key

    def verify_callback(self, raw_body: bytes, signature_b64: str) -> bool:
        """RSA-SHA256 验签回调正文（原文为回调 HTTP body 整体字节，待沙箱真报文复核确认）。任何异常视为失败。"""
        try:
            public_key = self._load_public_key()
            public_key.verify(
                base64.b64decode(signature_b64.strip()),
                raw_body,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except (InvalidSignature, ValueError, KeyError, OSError):
            return False
        except Exception:  # noqa: BLE001
            logger.exception("sqb 回调验签异常")
            return False


client = ShouqianbaClient()
