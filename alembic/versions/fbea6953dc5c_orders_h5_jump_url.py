"""orders: 新增 H5 直达收银台地址列（短链解析，best-effort）

Revision ID: fbea6953dc5c
Revises: 27db9620e834
Create Date: 2026-09-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fbea6953dc5c"
down_revision: Union[str, Sequence[str], None] = "27db9620e834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("h5_jump_url", sa.String(length=512), nullable=True, comment="H5直达收银台地址（短链解析，best-effort）"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders", recreate="always") as batch_op:
        batch_op.drop_column("h5_jump_url")
