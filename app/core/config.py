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
    DEBUG: bool = False

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

    # ===== 收钱吧聚合支付（微信+支付宝）=====
    # 商户参数一律经环境变量注入，禁止硬编码；未配置完整时支付功能优雅降级：
    # 订单仍可创建，payType/payUrl/codeUrl 返回 null（前端已有空态处理）。
    # 终端级凭证（日常下单/查单签名用；终端激活由收钱吧侧完成，密钥由运营配置，有效期到期前手动轮换）
    SQB_TERMINAL_SN: str | None = None
    SQB_TERMINAL_KEY: str | None = None
    # 收钱吧开放平台 API 基址（VSI）
    SQB_API_BASE: str = "https://vsi-api.shouqianba.com"
    # WAP 跳转网关（302 跳转收银台）
    SQB_GATEWAY: str = "https://qr.shouqianba.com/gateway"
    # 支付结果异步回调 URL（公网可访问，HTTPS）
    SQB_NOTIFY_URL: str | None = None
    # 支付完成同步回跳 URL（可含 {orderNo} 占位，否则自动拼 /{orderNo}）
    SQB_RETURN_URL: str | None = None
    # 收钱吧公钥路径（PEM SubjectPublicKeyInfo；验签回调，未配置时 /api/pay/notify 一律返回 fail）
    SQB_PUBLIC_KEY_PATH: str | None = None
    # 门店操作员（WAP/precreate 必填，无默认，须在 env 显式配置）
    SQB_OPERATOR: str | None = None

    # ===== 直连 IP 限流（仅 IP:8000 生效，域名经 NPM 跳过保峰值）=====
    RATE_LIMIT_IP_PROFILE: int = 10
    RATE_LIMIT_IP_ORDERS: int = 10
    RATE_LIMIT_IP_QUERY: int = 30

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
# 生产环境禁止 DEBUG 开启，防 traceback 泄露
if settings.APP_ENV == "prod" and settings.DEBUG:
    raise RuntimeError("prod 环境禁止 DEBUG=true，请设置 DEBUG=false")
