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

    # ===== 微信支付 V3 =====
    # 商户参数一律经环境变量注入，禁止硬编码；未配置完整时支付功能优雅降级：
    # 订单仍可创建，payType/payUrl/codeUrl 返回 null（前端已有空态处理）。
    # 商户号（微信支付商户平台获取）
    WXPAY_MCHID: str | None = None
    # 公众号/小程序 appid（H5/Native 统一下单必填）
    WXPAY_APPID: str | None = None
    # APIv3 密钥（32 字节，商户平台「APIv3 密钥」设置，用于回调报文解密）
    WXPAY_APIV3_KEY: str | None = None
    # 商户 API 私钥路径（apiclient_key.pem，仅服务端持有）
    WXPAY_PRIVATE_KEY_PATH: str | None = None
    # 商户证书序列号（Authorization 头 serial_no）
    WXPAY_CERT_SERIAL: str | None = None
    # 微信支付平台证书路径（验签回调/响应；未配置时 notify 一律返回 FAIL）
    WXPAY_PLATFORM_CERT_PATH: str | None = None
    # 支付结果回调 URL（公网可访问，HTTPS）
    WXPAY_NOTIFY_URL: str | None = None
    # 微信支付 API 基址（沙箱联调可改）
    WXPAY_API_BASE: str = "https://api.mch.weixin.qq.com"

    # ===== 对账/补偿定时任务 =====
    # 总开关：dev 默认关闭（避免后台线程干扰联调），prod 需显式开启
    RECONCILE_ENABLED: bool = False
    # 扫描周期（秒），默认 5 分钟
    RECONCILE_INTERVAL_SECONDS: int = 300
    # 超时阈值：创建超过该分钟数仍为 CREATED 的订单进入查单补偿
    RECONCILE_STALE_MINUTES: int = 30

    # ===== 隐私政策 =====
    PRIVACY_VERSION: str = "v1.0"
    PRIVACY_EFFECTIVE_DATE: str = "2026-08-21"
    COMPANY_NAME: str = "四川蜀兴振凡传媒有限公司"
    ICP_NO: str = "蜀ICP备2026047533号"
    CONTACT_EMAIL: str = "2444107425@qq.com"
    CONTACT_ADDRESS: str = "四川省绵阳市高新区永兴镇兴业南路18号汇昌.华兴名城6栋一层8号"
    DATA_RETENTION_DAYS_UNPAID: int = 30
    DATA_RETENTION_DAYS_PAID: int = 365


settings = Settings()
