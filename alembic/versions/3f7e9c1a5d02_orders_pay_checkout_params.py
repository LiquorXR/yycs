"""orders: 新增 pay_url/code_url（支付拉起参数，B 阶段支付模块）

Revision ID: 3f7e9c1a5d02
Revises: 6f3a9d2c5b1e
Create Date: 2026-08-18 12:00:00.000000

SQLite 支持原生 ADD COLUMN（upgrade 直接追加）；downgrade 经 batch 重建表删除列。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f7e9c1a5d02'
down_revision: Union[str, Sequence[str], None] = '6f3a9d2c5b1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("pay_url", sa.Text(), nullable=True, comment="H5 支付拉起 URL（mweb_url）"))
    op.add_column("orders", sa.Column("code_url", sa.Text(), nullable=True, comment="Native 扫码支付二维码内容"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders", recreate="always") as batch_op:
        batch_op.drop_column("pay_url")
        batch_op.drop_column("code_url")