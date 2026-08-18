"""订单模块接口测试：创建/防改价 12001/幂等/10004/13001/关单 12003/查询/报告。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.session import Base, get_db
from app.main import app
from app.models.report import Report
from app.services.seed import seed_products
from tests.conftest import create_profile

ORDER_KEY = "order-key-0001"


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


def _profile_id(client) -> str:
    return create_profile(client, _key="order-profile")["profileId"]


def _create_order(client, profile_id, key=ORDER_KEY, **overrides) -> dict:
    payload = {"profileId": profile_id, "productId": 1}
    payload.update(overrides)
    resp = client.post("/api/orders", json=payload, headers={"Idempotency-Key": key})
    return resp


def test_create_order_success(client):
    pid = _profile_id(client)
    resp = _create_order(client, pid)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["orderNo"].startswith("S")
    assert data["amount"] == 9900
    assert data["payType"] is None
    assert data["payUrl"] is None
    assert data["codeUrl"] is None


def test_create_order_anti_tamper_amount_12001(client):
    pid = _profile_id(client)
    resp = _create_order(client, pid, key="order-key-amt", amount=1)
    assert resp.status_code == 400
    assert resp.json()["code"] == 12001


def test_create_order_matching_amount_ok(client):
    pid = _profile_id(client)
    resp = _create_order(client, pid, key="order-key-okamt", amount=9900)
    assert resp.status_code == 200
    assert resp.json()["data"]["amount"] == 9900


def test_create_order_idempotent(client):
    pid = _profile_id(client)
    first = _create_order(client, pid, key="idem-order").json()["data"]
    second = _create_order(client, pid, key="idem-order").json()["data"]
    assert second == first
    assert first["orderNo"] == second["orderNo"]


def test_create_order_requires_idempotency_key(client):
    pid = _profile_id(client)
    resp = client.post("/api/orders", json={"profileId": pid, "productId": 1})
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


def test_create_order_profile_not_found_10004(client):
    resp = _create_order(client, "P99999999", key="order-key-nopf")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_create_order_product_not_found_13001(client):
    pid = _profile_id(client)
    resp = _create_order(client, pid, key="order-key-nopd", productId=99999)
    assert resp.status_code == 404
    assert resp.json()["code"] == 13001


def test_create_order_invalid_payment_method_10001(client):
    pid = _profile_id(client)
    resp = _create_order(client, pid, key="order-key-method", paymentMethod="alipay")
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


def test_get_order_detail(client):
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="order-key-detail").json()["data"]["orderNo"]
    resp = client.get(f"/api/orders/{order_no}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["orderNo"] == order_no
    assert data["profileId"] == pid
    assert data["amount"] == 9900
    assert data["state"] == "CREATED"
    assert data["payType"] == "auto"
    assert data["outTradeNo"] == order_no
    assert data["createdAt"].endswith("Z")
    assert data["paidAt"] is None


def test_get_order_not_found_10004(client):
    resp = client.get("/api/orders/S20991231001")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_close_order_success(client):
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="order-key-close").json()["data"]["orderNo"]
    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "CLOSED"
    # 已关单再次关单 → 12003
    resp = client.post(f"/api/orders/{order_no}/close")
    assert resp.status_code == 409
    assert resp.json()["code"] == 12003


def test_close_order_not_found_10004(client):
    resp = client.post("/api/orders/S20991231001/close")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_get_order_report_locked(client):
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="report-locked").json()["data"]["orderNo"]
    resp = client.get(f"/api/orders/{order_no}/report")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["orderNo"] == order_no
    assert data["state"] == "CREATED"
    report = data["report"]
    assert report["locked"] is True
    assert report["title"]
    assert len(report["lockedPreview"]) == 2
    assert all(k["title"] and k["body"] for k in report["lockedPreview"])
    assert data["wecom"] is None


def test_get_order_report_not_found_10004(client):
    resp = client.get("/api/orders/S20991231001/report")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_mock_pay_success_report_stays_locked(client):
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="mock-unlock").json()["data"]["orderNo"]

    locked = client.get(f"/api/orders/{order_no}/report").json()["data"]
    assert locked["report"]["locked"] is True

    resp = client.post(f"/api/orders/{order_no}/pay-success-mock")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["orderNo"] == order_no
    assert data["state"] == "UNLOCKED"

    detail = client.get(f"/api/orders/{order_no}").json()["data"]
    assert detail["state"] == "UNLOCKED"
    assert detail["paidAt"]

    unlocked = client.get(f"/api/orders/{order_no}/report").json()["data"]
    assert unlocked["state"] == "UNLOCKED"
    report = unlocked["report"]
    # 解锁状态机照常推进，但报告接口不返回完整测算内容
    assert report["locked"] is True
    for key in ("title", "lockedPreview"):
        assert key in report
    for key in ("score", "rank", "scoreNote", "analysis", "karma"):
        assert key not in report
    assert len(report["lockedPreview"]) == 2
    assert all(k["title"] and k["body"] for k in report["lockedPreview"])
    # 未配置 WECOM_QRCODE_URL → wecom 为 null
    assert unlocked["wecom"] is None


def test_mock_pay_success_not_found_10004(client):
    resp = client.post("/api/orders/S20991231001/pay-success-mock")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_mock_pay_success_already_unlocked_12002(client):
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="mock-twice").json()["data"]["orderNo"]
    assert client.post(f"/api/orders/{order_no}/pay-success-mock").status_code == 200
    resp = client.post(f"/api/orders/{order_no}/pay-success-mock")
    assert resp.status_code == 409
    assert resp.json()["code"] == 12002


def test_report_wecom_qrcode_when_configured(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "WECOM_QRCODE_URL", "https://qywx.example.com/qr")
    pid = _profile_id(client)
    order_no = _create_order(client, pid, key="mock-wecom").json()["data"]["orderNo"]
    client.post(f"/api/orders/{order_no}/pay-success-mock")
    data = client.get(f"/api/orders/{order_no}/report").json()["data"]
    # 已支付且配置企微 → 返回 wecom 引导，但报告仍为锁定预览
    assert data["wecom"]["qrcodeUrl"] == "https://qywx.example.com/qr"
    assert data["wecom"]["note"]
    assert data["report"]["locked"] is True
    for key in ("score", "analysis", "karma"):
        assert key not in data["report"]


def test_report_missing_returns_default_preview(client_and_factory):
    client, factory = client_and_factory
    pid = create_profile(client, _key="report-no-record")["profileId"]
    resp = client.post(
        "/api/orders",
        json={"profileId": pid, "productId": 1},
        headers={"Idempotency-Key": "report-no-record-order"},
    )
    order_no = resp.json()["data"]["orderNo"]
    with factory() as db:
        db.query(Report).filter(Report.profile_id == pid).delete()
        db.commit()

    data = client.get(f"/api/orders/{order_no}/report").json()["data"]
    report = data["report"]
    assert report["locked"] is True
    assert report["title"] == "八字命盘详批（姻缘预览）"
    assert len(report["lockedPreview"]) == 2
    assert all(k["title"] and k["body"] for k in report["lockedPreview"])
    assert data["wecom"] is None


def test_pay_success_mock_disabled_in_prod(monkeypatch):
    import importlib

    import app.routers.orders as orders_mod
    from app.core.config import settings

    # prod 环境：mock 路由不注册
    monkeypatch.setattr(settings, "APP_ENV", "prod")
    importlib.reload(orders_mod)
    paths = [r.path for r in orders_mod.router.routes]
    assert not any(p.endswith("/pay-success-mock") for p in paths)

    # 恢复 dev，避免影响其它用例
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    importlib.reload(orders_mod)
    paths = [r.path for r in orders_mod.router.routes]
    assert any(p.endswith("/pay-success-mock") for p in paths)
