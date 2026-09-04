"""健康检查接口测试。"""

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "success"
    data = body["data"]
    assert data["status"] == "ok"
    assert "dbSizeBytes" in data
    assert isinstance(data["reconcileEnabled"], bool)
    assert isinstance(data["sqbReady"], bool)
    assert isinstance(data["wxpayReady"], bool)
    assert isinstance(data["sqbMissing"], list)
    assert data["lastReconcileAt"] is None
    assert data["lastReconcileSummary"] is None