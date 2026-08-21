"""profiles: 新增隐私同意版本与时间（privacy consent）

Revision ID: 8c9d1e2f3a4b
Revises: 3f7e9c1a5d02
Create Date: 2026-08-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c9d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "3f7e9c1a5d02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("profiles", sa.Column("agreed_privacy_version", sa.String(length=32), nullable=True, comment="已同意的隐私政策版本"))
    op.add_column("profiles", sa.Column("consented_at", sa.DateTime(), nullable=True, comment="同意时间 UTC"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("profiles", recreate="always") as batch_op:
        batch_op.drop_column("consented_at")
        batch_op.drop_column("agreed_privacy_version")
