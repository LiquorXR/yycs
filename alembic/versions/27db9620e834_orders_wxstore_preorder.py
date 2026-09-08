"""orders: 微信小店切换新增预订单/正式订单映射列

Revision ID: 27db9620e834
Revises: 8c9d1e2f3a4b
Create Date: 2026-09-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "27db9620e834"
down_revision: Union[str, Sequence[str], None] = "8c9d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("pre_order_id", sa.String(length=256), nullable=True, comment="微信小店预订单号（代客下单返回，全局唯一）"))
    op.add_column("orders", sa.Column("order_sn", sa.String(length=64), nullable=True, comment="微信小店正式订单号（支付推送返回）"))
    op.add_column("orders", sa.Column("order_signature", sa.String(length=64), nullable=True, comment="微信小店订单签名（支付推送返回）"))
    op.create_index("ix_orders_pre_order_id", "orders", ["pre_order_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders", recreate="always") as batch_op:
        batch_op.drop_index("ix_orders_pre_order_id")
        batch_op.drop_column("order_signature")
        batch_op.drop_column("order_sn")
        batch_op.drop_column("pre_order_id")
