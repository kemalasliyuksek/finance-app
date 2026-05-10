"""Add app_config table for runtime-editable settings.

Revision ID: 008
Revises: 007
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("id", sa.Uuid(), nullable=False),
        # Risk (6)
        sa.Column("risk_per_trade_pct", sa.Float(), nullable=False, server_default="0.02"),
        sa.Column("max_concurrent_positions", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("daily_loss_limit_pct", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("min_balance_usdt", sa.Float(), nullable=False, server_default="50"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("max_trades_per_day", sa.Integer(), nullable=False, server_default="15"),
        # Strateji (7)
        sa.Column("min_signal_confidence", sa.Float(), nullable=False, server_default="0.40"),
        sa.Column("strategy_w_ema", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("strategy_w_macd", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("strategy_w_rsi", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("strategy_w_bb", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("strategy_w_volume", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("ema_trend_score", sa.Float(), nullable=False, server_default="0.6"),
        # SL/TP (5)
        sa.Column("min_sl_pct", sa.Float(), nullable=False, server_default="0.005"),
        sa.Column("max_sl_pct", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("min_tp_pct", sa.Float(), nullable=False, server_default="0.03"),
        sa.Column("atr_sl_multiplier", sa.Float(), nullable=False, server_default="1.5"),
        sa.Column("atr_tp_multiplier", sa.Float(), nullable=False, server_default="3.0"),
        # Exit (4)
        sa.Column("trailing_stop_activation_pct", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("trailing_stop_trail_pct", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("max_hold_hours", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("time_exit_min_profit_pct", sa.Float(), nullable=False, server_default="0.5"),
        # Screener (4)
        sa.Column("screener_min_volume_usdt", sa.Float(), nullable=False, server_default="500000"),
        sa.Column("screener_min_change_pct", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("screener_active_dynamic_pairs", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("screener_max_candidates", sa.Integer(), nullable=False, server_default="40"),
        # Trading mode (1)
        sa.Column("trading_mode", sa.String(20), nullable=False, server_default="semi_auto"),
        # Audit + timestamps
        sa.Column("updated_by", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_app_config"),
        schema="trading",
    )

    # Migration sırasında tek satır oluştur (default'lardan). Mevcut satır varsa atla.
    # Böylece ilk boot'ta repository seed etmeye gerek kalmasa bile tablo dolu olur.
    op.execute(
        """
        INSERT INTO trading.app_config (id)
        SELECT gen_random_uuid()
        WHERE NOT EXISTS (SELECT 1 FROM trading.app_config);
        """
    )


def downgrade() -> None:
    op.drop_table("app_config", schema="trading")
