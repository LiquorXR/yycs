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
        # monorepo 场景 .env 可能混入前端 VITE_* 变量，未声明字段一律忽略
        extra="ignore",
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

    # 生辰数据加密密钥（AES-256-GCM，base64 编码 32 字节）
    # 生成方式：openssl rand -base64 32；未配置时 dev 生成临时密钥、prod 启动报错
    BIRTH_DATA_KEY: str | None = None

    # 企微「联系我」活码二维码 URL；未配置时已解锁报告 wecom 字段返回 null
    WECOM_QRCODE_URL: str | None = None

    # 前端构建产物目录（容器内 WORKDIR 为 /app，默认 ./dist 即 /app/dist）；
    # 生产由 backend 容器内托管前端静态产物，nginx 仅反代 127.0.0.1:8000；
    # dev/测试使用 Vite，目录不存在时静默跳过静态托管
    FRONTEND_DIST_DIR: str = "./dist"


settings = Settings()
