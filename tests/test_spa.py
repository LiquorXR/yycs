"""SPA 静态托管测试：dist 存在时验证前端托管与 API 语义，dist 缺失时自动跳过。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

_DIST_EXISTS = Path(settings.FRONTEND_DIST_DIR).is_dir()

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not _DIST_EXISTS,
    reason="前端构建产物不存在（dev/测试用 Vite，跳过 SPA 托管用例）",
)


def test_root_returns_index_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_spa_route_returns_index_html():
    resp = client.get("/calc")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_unknown_api_path_returns_json_404():
    resp = client.get("/api/not-exist-path")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] != 0
    assert "<html" not in resp.text.lower()


def test_api_health_still_works():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
