"""迁移测试：验证 6f3a9d2c5b1e 升级/降级往返后 profiles 三列 nullable 与初始 schema 对齐。

初始 schema（572f7403f3db）：name_b/birth_b NOT NULL，birth_hour_b 可空。
head（6f3a9d2c5b1e）：name_b/birth_b/birth_hour_b 均可空。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings

ALEMBIC_DIR = str(Path(__file__).resolve().parents[1] / "alembic")
ALEMBIC_INI = str(Path(__file__).resolve().parents[1] / "alembic.ini")


def _profile_nullability(engine) -> dict[str, bool]:
    cols = inspect(engine).get_columns("profiles")
    return {c["name"]: c["nullable"] for c in cols if c["name"] in ("name_b", "birth_b", "birth_hour_b")}


@pytest.fixture()
def migrate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "migrate.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("script_location", ALEMBIC_DIR)
    return url, cfg


def test_upgrade_head_nullable_all(migrate_db):
    url, cfg = migrate_db
    command.upgrade(cfg, "6f3a9d2c5b1e")
    engine = create_engine(url)
    assert _profile_nullability(engine) == {
        "name_b": True,
        "birth_b": True,
        "birth_hour_b": True,
    }
    engine.dispose()


def test_downgrade_aligns_with_init_schema(migrate_db):
    url, cfg = migrate_db
    command.upgrade(cfg, "6f3a9d2c5b1e")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (id, name_a, birth_a, birth_hour_a, name_b, birth_b, "
                "birth_hour_b, is_lunar, combo_data, preview_report, created_at) "
                "VALUES ('P0000000000001', '甲', 'encA', NULL, '乙', 'encB', NULL, 0, NULL, NULL, '2026-08-15 00:00:00')"
            )
        )
    command.downgrade(cfg, "572f7403f3db")
    assert _profile_nullability(engine) == {
        "name_b": False,
        "birth_b": False,
        "birth_hour_b": True,
    }
    engine.dispose()


def test_upgrade_downgrade_upgrade_roundtrip(migrate_db):
    url, cfg = migrate_db
    command.upgrade(cfg, "6f3a9d2c5b1e")
    command.downgrade(cfg, "572f7403f3db")
    command.upgrade(cfg, "6f3a9d2c5b1e")
    engine = create_engine(url)
    assert _profile_nullability(engine) == {
        "name_b": True,
        "birth_b": True,
        "birth_hour_b": True,
    }
    engine.dispose()


def _order_columns(engine) -> list[str]:
    return [c["name"] for c in inspect(engine).get_columns("orders")]


def test_orders_pay_checkout_columns_upgrade(migrate_db):
    """升级到 head：orders 具备 pay_url/code_url（支付模块 B 阶段）。"""
    url, cfg = migrate_db
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    cols = _order_columns(engine)
    assert "pay_url" in cols and "code_url" in cols
    engine.dispose()


def test_orders_pay_checkout_columns_downgrade(migrate_db):
    """降级回 6f3a9d2c5b1e：pay_url/code_url 移除，与既有 schema 对齐。"""
    url, cfg = migrate_db
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "6f3a9d2c5b1e")
    engine = create_engine(url)
    cols = _order_columns(engine)
    assert "pay_url" not in cols and "code_url" not in cols
    assert "pay_type" in cols and "ad_params" in cols
    engine.dispose()


def test_orders_pay_checkout_columns_roundtrip(migrate_db):
    url, cfg = migrate_db
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "6f3a9d2c5b1e")
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    cols = _order_columns(engine)
    assert "pay_url" in cols and "code_url" in cols
    engine.dispose()
