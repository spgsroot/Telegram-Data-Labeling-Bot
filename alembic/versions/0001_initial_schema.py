"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("telegram_id"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_hash"),
    )
    op.create_index("ix_items_status", "items", ["status"])

    op.create_table(
        "labels",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"]),
        sa.PrimaryKeyConstraint("item_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("labels")
    op.drop_index("ix_items_status", table_name="items")
    op.drop_table("items")
    op.drop_table("users")
