"""Add user_favorites table.

Revision ID: 007
Revises: 006
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["trading.users.id"], name="fk_user_favorites_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_user_favorites"),
        sa.UniqueConstraint("user_id", "symbol", name="uq_user_favorites_user_symbol"),
        schema="trading",
    )
    op.create_index("ix_user_favorites_user_id", "user_favorites", ["user_id"], schema="trading")


def downgrade() -> None:
    op.drop_index("ix_user_favorites_user_id", table_name="user_favorites", schema="trading")
    op.drop_table("user_favorites", schema="trading")
