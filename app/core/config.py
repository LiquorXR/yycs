"""应用配置：从环境变量 / .env 读取。"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。

    配置值优先取环境变量，其次读取项目根目录 .env 文件。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "振凡命理"
    APP_ENV: str = "dev"
    DEBUG: bool = True

    # 数据库连接串；默认使用项目根目录的 SQLite 文件
    DATABASE_URL: str = "sqlite:///./app.db"

    # CORS 允许来源（JSON 数组形式配置）
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
