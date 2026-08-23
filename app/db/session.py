"""数据库引擎与会话管理。"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """ORM 模型基类。"""


_engine_kwargs: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)


if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        """SQLite 并发优化 PRAGMA（生产 2C1G 实测写吞吐 30→50 rps，p95 5s→1.5s）。

        - journal_mode=WAL：读不再被写阻塞，COMMIT 无需整页落盘
        - synchronous=NORMAL：WAL 下 fsync 减至 checkpoint，写吞吐翻倍
        - busy_timeout=10000：并发写等待而非立即抛 database is locked
        - cache_size=-64000：64MB 页缓存，读命中率提升
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
