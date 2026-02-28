"""add created_at to items

Revision ID: faa7b5a268ae
Revises:
Create Date: 2026-02-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "faa7b5a268ae"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_items_created_at", "items", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_items_created_at", table_name="items")
    op.drop_column("items", "created_at")
