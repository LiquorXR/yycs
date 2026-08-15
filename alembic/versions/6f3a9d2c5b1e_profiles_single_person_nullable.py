"""profiles: name_b/birth_b/birth_hour_b 改可空（单人测算弃用）

Revision ID: 6f3a9d2c5b1e
Revises: 572f7403f3db
Create Date: 2026-08-15 18:40:00.000000

SQLite 不支持 ALTER COLUMN，经 batch_alter_table 重建表实现。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f3a9d2c5b1e'
down_revision: Union[str, Sequence[str], None] = '572f7403f3db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("profiles", recreate="always") as batch_op:
        batch_op.alter_column("name_b", existing_type=sa.String(length=64), nullable=True)
        batch_op.alter_column("birth_b", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column("birth_hour_b", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("profiles", recreate="always") as batch_op:
        batch_op.alter_column("birth_hour_b", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("birth_b", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("name_b", existing_type=sa.String(length=64), nullable=False)
