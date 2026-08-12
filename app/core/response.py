"""统一响应封装。"""

from __future__ import annotations


def ok_response(data=None, message: str = "success") -> dict:
    """统一成功响应：{code, message, data}。"""
    return {"code": 0, "message": message, "data": data}
