"""Add audit_logs table.

Revision ID: 005
Revises: 004
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(50), nullable=False),
        sa.Column('user', sa.String(50), nullable=False),
        sa.Column('changes', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')),
        schema='trading',
    )
    op.create_index(
        'ix_audit_logs_entity',
        'audit_logs',
        ['entity_type', 'entity_id'],
        schema='trading',
    )
    op.create_index(
        'ix_audit_logs_created',
        'audit_logs',
        ['created_at'],
        schema='trading',
    )


def downgrade() -> None:
    op.drop_index('ix_audit_logs_created', table_name='audit_logs', schema='trading')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs', schema='trading')
    op.drop_table('audit_logs', schema='trading')
