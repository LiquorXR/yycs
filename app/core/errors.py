"""统一业务异常与错误码常量。"""

from __future__ import annotations


class ErrorCode:
    """业务错误码常量。

    错误码分为多个业务域：
    - 100xx：通用错误
    - 120xx：支付相关
    - 130xx：产品相关
    - 140xx：测算/报告相关
    - 50000：服务器内部错误
    """

    PARAM_VALIDATION = 10001  # 参数校验
    UNAUTHENTICATED = 10002  # 未认证
    FORBIDDEN = 10003  # 无权限
    NOT_FOUND = 10004  # 资源不存在
    CONFLICT = 10005  # 资源冲突
    RATE_LIMITED = 10006  # 限流

    AMOUNT_INVALID = 12001  # 金额校验
    ORDER_ALREADY_PAID = 12002  # 订单已支付
    ORDER_STATUS_INVALID = 12003  # 订单状态不允许
    PAYMENT_RAISE_FAILED = 12004  # 支付拉起失败
    CALLBACK_SIGN_FAILED = 12005  # 回调验签失败

    PRODUCT_NOT_FOUND = 13001  # 产品不存在

    DIVINATION_INFO_INVALID = 14001  # 测算信息无效
    REPORT_NOT_UNLOCKED = 14002  # 报告未解锁

    INTERNAL_ERROR = 50000  # 服务器内部错误


_HTTP_STATUS_MAP: dict[int, int] = {
    ErrorCode.PARAM_VALIDATION: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.AMOUNT_INVALID: 400,
    ErrorCode.ORDER_ALREADY_PAID: 409,
    ErrorCode.ORDER_STATUS_INVALID: 409,
    ErrorCode.PAYMENT_RAISE_FAILED: 502,
    ErrorCode.CALLBACK_SIGN_FAILED: 400,
    ErrorCode.PRODUCT_NOT_FOUND: 404,
    ErrorCode.DIVINATION_INFO_INVALID: 422,
    ErrorCode.REPORT_NOT_UNLOCKED: 403,
    ErrorCode.INTERNAL_ERROR: 500,
}


def http_status_for(code: int) -> int:
    """返回错误码对应的 HTTP 状态码，未知错误码回退为 500。"""
    return _HTTP_STATUS_MAP.get(code, 500)


class BizError(Exception):
    """统一业务异常。

    携带业务错误码（code）、错误信息（message）与对外 HTTP 状态码（http_status）。
    http_status 未显式指定时依据错误码自动映射。
    """

    def __init__(
        self,
        code: int = ErrorCode.INTERNAL_ERROR,
        message: str = "服务器内部错误",
        http_status: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status if http_status is not None else http_status_for(code)
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.code}] {self.message}"
