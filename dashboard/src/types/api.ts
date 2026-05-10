export interface Signal {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  strategy: string;
  confidence: number;
  entry_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  indicators: Record<string, unknown>;
  sentiment_score: number | null;
  status: "pending" | "approved" | "rejected" | "expired" | "executed" | "weak";
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
  expires_at: string;
}

export interface Order {
  id: string;
  signal_id: string | null;
  binance_order_id: number | null;
  binance_client_oid: string | null;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: string;
  quantity: number;
  price: number | null;
  stop_price: number | null;
  status: string;
  filled_quantity: number;
  avg_fill_price: number | null;
  commission: number;
  commission_asset: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  quantity: number;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  total_commission: number;
  status: "open" | "closed";
  opened_at: string;
  closed_at: string | null;
  duration_seconds: number | null;
}

export interface TradeStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
}

export interface Candle {
  id: number;
  symbol: string;
  interval: string;
  open_time: string;
  close_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  quote_volume: number;
  trade_count: number;
  created_at: string;
}

export interface PortfolioSnapshot {
  id: number;
  total_balance_usdt: number;
  free_balance_usdt: number;
  locked_balance_usdt: number;
  unrealized_pnl: number;
  open_positions: number;
  asset_breakdown: Record<string, string>;
  snapshot_at: string;
}

export interface DashboardSummary {
  total_balance_usdt: number;
  free_balance_usdt: number;
  unrealized_pnl: number;
  open_positions: number;
  today_pnl: number;
  today_trades_count: number;
  win_rate: number;
  recent_signals: Signal[];
  app_mode: string;
  trading_mode: string;
  active_pairs: string[];
  is_sandbox: boolean;
}

export interface TradingConfig {
  // Env-only (salt okunur)
  app_mode: string;
  trading_pairs: string[];
  candle_intervals: string[];

  // Risk (6)
  risk_per_trade_pct: number;
  max_concurrent_positions: number;
  daily_loss_limit_pct: number;
  min_balance_usdt: number;
  cooldown_seconds: number;
  max_trades_per_day: number;

  // Strateji (7)
  min_signal_confidence: number;
  strategy_w_ema: number;
  strategy_w_macd: number;
  strategy_w_rsi: number;
  strategy_w_bb: number;
  strategy_w_volume: number;
  ema_trend_score: number;

  // SL/TP (5)
  min_sl_pct: number;
  max_sl_pct: number;
  min_tp_pct: number;
  atr_sl_multiplier: number;
  atr_tp_multiplier: number;

  // Exit (4)
  trailing_stop_activation_pct: number;
  trailing_stop_trail_pct: number;
  max_hold_hours: number;
  time_exit_min_profit_pct: number;

  // Screener (4)
  screener_min_volume_usdt: number;
  screener_min_change_pct: number;
  screener_active_dynamic_pairs: number;
  screener_max_candidates: number;

  // Mode (1)
  trading_mode: "semi_auto" | "full_auto";
}

/** PATCH /config body — 27 düzenlenebilir alanın kısmi güncellemesi. */
export type TradingConfigUpdate = Partial<
  Omit<TradingConfig, "app_mode" | "trading_pairs" | "candle_intervals">
>;

export interface BotStatus {
  app_mode: string;
  trading_mode: string;
  uptime_seconds: number;
  active_pairs: string[];
  candle_intervals: string[];
  is_sandbox: boolean;
}

export interface SentimentData {
  symbol: string;
  score: number | null;
  article_count: number;
  source: string;
  scored_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  must_change_password?: boolean;
}

export interface ScreenerResultItem {
  symbol: string;
  price: number;
  change_24h: number;
  volume_24h: number;
  side: "BUY" | "SELL";
  confidence: number;
  ta_summary: Record<string, unknown>;
  scan_score: number;
  is_active: boolean;
  is_volume_top: boolean;
}

export interface ScreenerResultsResponse {
  results: ScreenerResultItem[];
  total_scanned: number;
}

export interface ScreenerStatus {
  enabled: boolean;
  last_scan_at: string | null;
  cycle_duration_seconds: number | null;
  total_pairs_scanned: number;
  candidates_analyzed: number;
  active_pairs: string[];
  volume_top_pairs: string[];
  dynamic_pairs: string[];
}

export interface SandboxBalanceItem {
  asset: string;
  free: number;
  locked: number;
  total: number;
}

export interface SandboxWalletResponse {
  balances: SandboxBalanceItem[];
  mode: string;
}

export interface BinanceAccountResponse {
  balances: SandboxBalanceItem[];
  can_trade: boolean;
  account_type: string;
}

export interface TimelineEvent {
  action: string;
  timestamp: string;
  user: string | null;
  details: Record<string, unknown> | null;
}

export interface SignalDetail {
  signal: Signal;
  order: Order | null;
  trade: Trade | null;
  timeline: TimelineEvent[];
}

export interface MarketCoinItem {
  symbol: string;
  price: number;
  change_pct: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  has_signal: boolean;
  signal_side: "BUY" | "SELL" | null;
  signal_confidence: number | null;
}

export interface MarketCoinsResponse {
  coins: MarketCoinItem[];
  total: number;
  cached_at: string | null;
}

export interface FavoritesResponse {
  favorites: string[];
}
