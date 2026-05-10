import type { FieldDef } from "@/components/settings/editable-config-section";

/** 27 düzenlenebilir parametrenin merkezi tanımı.
 *
 * Backend `src/db/repositories/app_config_repo.py:APP_CONFIG_FIELDS`
 * listesi ile senkron tutulmalıdır.
 */

export const MODE_FIELDS: FieldDef[] = [
  {
    key: "trading_mode",
    label: "Trading Modu",
    type: "mode",
    hint: "Yarı otomatik: Telegram/Dashboard onayı. Tam otomatik: anında uygulanır.",
  },
];

export const RISK_FIELDS: FieldDef[] = [
  {
    key: "risk_per_trade_pct",
    label: "Trade Başına Risk",
    type: "percent",
    min: 0.001,
    max: 0.1,
    step: 0.005,
    hint: "Bakiyenin riske edilecek oranı",
  },
  {
    key: "max_concurrent_positions",
    label: "Maks Eşzamanlı Pozisyon",
    type: "integer",
    min: 1,
    max: 10,
  },
  {
    key: "daily_loss_limit_pct",
    label: "Günlük Kayıp Limiti",
    type: "percent",
    min: 0.01,
    max: 0.5,
    step: 0.005,
  },
  {
    key: "min_balance_usdt",
    label: "Min Bakiye (USDT)",
    type: "number",
    min: 5,
    max: 10000,
    step: 1,
  },
  {
    key: "cooldown_seconds",
    label: "Cooldown (sn)",
    type: "integer",
    min: 0,
    max: 86400,
    hint: "Aynı coin için iki trade arası",
  },
  {
    key: "max_trades_per_day",
    label: "Günlük Max Trade",
    type: "integer",
    min: 1,
    max: 100,
  },
];

export const STRATEGY_FIELDS: FieldDef[] = [
  {
    key: "min_signal_confidence",
    label: "Min Sinyal Güveni",
    type: "number",
    min: 0.1,
    max: 1.0,
    step: 0.01,
  },
  {
    key: "strategy_w_ema",
    label: "EMA Ağırlık",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "strategy_w_macd",
    label: "MACD Ağırlık",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "strategy_w_rsi",
    label: "RSI Ağırlık",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "strategy_w_bb",
    label: "BB Ağırlık",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "strategy_w_volume",
    label: "Volume Ağırlık",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
    hint: "5 ağırlık toplamı 1.0 olmalı",
  },
  {
    key: "ema_trend_score",
    label: "EMA Trend Skoru",
    type: "number",
    min: 0,
    max: 1,
    step: 0.1,
  },
];

export const SL_TP_FIELDS: FieldDef[] = [
  {
    key: "min_sl_pct",
    label: "Min SL Mesafesi",
    type: "percent",
    min: 0.001,
    max: 0.1,
    step: 0.001,
  },
  {
    key: "max_sl_pct",
    label: "Max SL Mesafesi",
    type: "percent",
    min: 0.005,
    max: 0.2,
    step: 0.005,
  },
  {
    key: "min_tp_pct",
    label: "Min TP Mesafesi",
    type: "percent",
    min: 0.001,
    max: 0.2,
    step: 0.001,
  },
  {
    key: "atr_sl_multiplier",
    label: "ATR SL Çarpanı",
    type: "number",
    min: 0.5,
    max: 10,
    step: 0.1,
  },
  {
    key: "atr_tp_multiplier",
    label: "ATR TP Çarpanı",
    type: "number",
    min: 0.5,
    max: 20,
    step: 0.1,
    hint: "SL çarpanından büyük olmalı",
  },
];

export const EXIT_FIELDS: FieldDef[] = [
  {
    key: "trailing_stop_activation_pct",
    label: "Trailing Aktivasyon (%)",
    type: "number",
    min: 0.1,
    max: 20,
    step: 0.1,
  },
  {
    key: "trailing_stop_trail_pct",
    label: "Trailing Trail (%)",
    type: "number",
    min: 0.1,
    max: 20,
    step: 0.1,
  },
  {
    key: "max_hold_hours",
    label: "Max Tutma (saat)",
    type: "integer",
    min: 1,
    max: 168,
  },
  {
    key: "time_exit_min_profit_pct",
    label: "Zaman Çıkış Min Kâr (%)",
    type: "number",
    min: 0,
    max: 10,
    step: 0.1,
  },
];

export const SCREENER_FIELDS: FieldDef[] = [
  {
    key: "screener_min_volume_usdt",
    label: "Min 24s Hacim (USDT)",
    type: "number",
    min: 10_000,
    max: 100_000_000,
    step: 100_000,
  },
  {
    key: "screener_min_change_pct",
    label: "Min Değişim (%)",
    type: "number",
    min: 0,
    max: 50,
    step: 0.5,
  },
  {
    key: "screener_active_dynamic_pairs",
    label: "Dinamik Aktif Coin",
    type: "integer",
    min: 1,
    max: 50,
  },
  {
    key: "screener_max_candidates",
    label: "Max Derin Analiz Adayı",
    type: "integer",
    min: 5,
    max: 200,
  },
];

/** Tüm 27 düzenlenebilir alanın birleşik listesi. */
export const ALL_CONFIG_FIELDS: FieldDef[] = [
  ...MODE_FIELDS,
  ...RISK_FIELDS,
  ...STRATEGY_FIELDS,
  ...SL_TP_FIELDS,
  ...EXIT_FIELDS,
  ...SCREENER_FIELDS,
];

/** Hızlı arama için key seti. */
export const ALL_CONFIG_KEYS = new Set(ALL_CONFIG_FIELDS.map((f) => f.key as string));
