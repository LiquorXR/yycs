"""pytest 共享夹具：独立内存 SQLite + 种子产品，避免污染开发库。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  注册全部模型
from app.db.session import Base, get_db
from app.main import app
from app.services.seed import seed_products


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with test_session() as db:
        seed_products(db)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


VALID_PROFILE = {
    "nameA": "张三",
    "birthA": "1995-08-15",
    "birthHourA": "子",
    "nameB": "李四",
    "birthB": "1997-02-03",
    "birthHourB": "午",
    "isLunar": False,
}


def create_profile(client, **overrides) -> dict:
    """便捷函数：创建测算信息，返回响应 data。"""
    payload = dict(VALID_PROFILE)
    payload.update(overrides)
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": overrides.pop("_key", "profile-key")})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]
