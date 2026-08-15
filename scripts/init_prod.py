"""生产一次性初始化：alembic 迁移 + 幂等种子商品。

供 docker-compose migrate 服务调用（command: python scripts/init_prod.py）。
连接串等配置经环境变量注入（compose env_file）。
"""

from __future__ import annotations

import os
import sys

# 脚本位于 scripts/ 下，将项目根目录加入 sys.path 以导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config

from app.db.session import SessionLocal
from app.services.seed import seed_products


def main() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    command.upgrade(cfg, "head")

    with SessionLocal() as db:
        seed_products(db)


if __name__ == "__main__":
    main()
