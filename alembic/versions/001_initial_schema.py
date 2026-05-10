"""Initial schema - tum tablolar.

Revision ID: 001
Revises:
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema olustur
    op.execute("CREATE SCHEMA IF NOT EXISTS trading")

    # candles
    op.create_table(
        'candles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('interval', sa.String(5), nullable=False),
        sa.Column('open_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('close_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(20, 8), nullable=False),
        sa.Column('high', sa.Numeric(20, 8), nullable=False),
        sa.Column('low', sa.Numeric(20, 8), nullable=False),
        sa.Column('close', sa.Numeric(20, 8), nullable=False),
        sa.Column('volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('quote_volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('trade_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_candles'),
        sa.UniqueConstraint('symbol', 'interval', 'open_time', name='uq_candles_symbol_interval_time'),
        schema='trading',
    )
    op.create_index('ix_candles_lookup', 'candles', ['symbol', 'interval', 'open_time'], schema='trading')

    # signals
    op.create_table(
        'signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('stop_loss', sa.Numeric(20, 8), nullable=True),
        sa.Column('take_profit', sa.Numeric(20, 8), nullable=True),
        sa.Column('indicators', postgresql.JSONB(), nullable=False),
        sa.Column('sentiment_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(50), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_signals'),
        schema='trading',
    )
    op.create_index('ix_signals_status', 'signals', ['status', 'created_at'], schema='trading')
    op.create_index('ix_signals_symbol', 'signals', ['symbol', 'created_at'], schema='trading')

    # orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('binance_order_id', sa.BigInteger(), nullable=True),
        sa.Column('binance_client_oid', sa.String(36), nullable=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('price', sa.Numeric(20, 8), nullable=True),
        sa.Column('stop_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='new'),
        sa.Column('filled_quantity', sa.Numeric(20, 8), nullable=False, server_default='0'),
        sa.Column('avg_fill_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('commission', sa.Numeric(20, 8), nullable=False, server_default='0'),
        sa.Column('commission_asset', sa.String(10), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['trading.signals.id'], name='fk_orders_signal_id_signals'),
        sa.PrimaryKeyConstraint('id', name='pk_orders'),
        sa.UniqueConstraint('binance_client_oid', name='uq_orders_binance_client_oid'),
        schema='trading',
    )
    op.create_index('ix_orders_signal', 'orders', ['signal_id'], schema='trading')
    op.create_index('ix_orders_status', 'orders', ['status'], schema='trading')
    op.create_index('ix_orders_binance', 'orders', ['binance_order_id'], schema='trading')

    # trades
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('entry_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('exit_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('exit_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('realized_pnl_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_commission', sa.Numeric(20, 8), nullable=False, server_default='0'),
        sa.Column('status', sa.String(10), nullable=False, server_default='open'),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['entry_order_id'], ['trading.orders.id'], name='fk_trades_entry_order_id_orders'),
        sa.ForeignKeyConstraint(['exit_order_id'], ['trading.orders.id'], name='fk_trades_exit_order_id_orders'),
        sa.PrimaryKeyConstraint('id', name='pk_trades'),
        schema='trading',
    )
    op.create_index('ix_trades_status', 'trades', ['status', 'opened_at'], schema='trading')
    op.create_index('ix_trades_symbol', 'trades', ['symbol', 'opened_at'], schema='trading')

    # portfolio_snapshots
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('total_balance_usdt', sa.Numeric(20, 8), nullable=False),
        sa.Column('free_balance_usdt', sa.Numeric(20, 8), nullable=False),
        sa.Column('locked_balance_usdt', sa.Numeric(20, 8), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(20, 8), nullable=False, server_default='0'),
        sa.Column('open_positions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('asset_breakdown', postgresql.JSONB(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_portfolio_snapshots'),
        schema='trading',
    )
    op.create_index('ix_snapshots_time', 'portfolio_snapshots', ['snapshot_at'], schema='trading')

    # sentiment_scores
    op.create_table(
        'sentiment_scores',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('source', sa.String(30), nullable=False),
        sa.Column('score', sa.Numeric(5, 4), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_sentiment_scores'),
        schema='trading',
    )
    op.create_index('ix_sentiment_lookup', 'sentiment_scores', ['symbol', 'scored_at'], schema='trading')


def downgrade() -> None:
    op.drop_table('sentiment_scores', schema='trading')
    op.drop_table('portfolio_snapshots', schema='trading')
    op.drop_table('trades', schema='trading')
    op.drop_table('orders', schema='trading')
    op.drop_table('signals', schema='trading')
    op.drop_table('candles', schema='trading')
    op.execute("DROP SCHEMA IF EXISTS trading")
