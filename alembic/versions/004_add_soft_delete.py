"""Add deleted_at column to signals, orders, trades tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ('signals', 'orders', 'trades'):
        op.add_column(
            table,
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            schema='trading',
        )


def downgrade() -> None:
    for table in ('signals', 'orders', 'trades'):
        op.drop_column(table, 'deleted_at', schema='trading')
