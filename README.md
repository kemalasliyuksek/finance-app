# Finance App — Crypto Trading Bot

> 🇹🇷 **Türkçe için: [README.tr.md](README.tr.md)**

A self-hosted, autonomous cryptocurrency trading bot for Binance, with a built-in Next.js admin dashboard, Telegram integration, dynamic market screener, and a sandbox mode for risk-free testing.

Configure it with your own API keys, your own risk parameters, and your own watchlist — everything is driven by environment variables and a runtime-editable config table.

---

## ⚠️ Disclaimer — Read This First

**This software is provided as-is, for educational and research purposes only. Use it at your own risk.**

- 🚨 **Cryptocurrency trading is extremely risky.** You can lose your entire investment. Past performance — backtests, paper-trading results, anyone else's screenshots — does **not** predict future results.
- 🤖 **This bot is not financial advice.** It is a tool that automates a strategy you choose. You are responsible for understanding what it does, why it does it, and whether it makes sense for your situation.
- 🔬 **Always test in `sandbox` or `testnet` mode for an extended period before risking real money.** A few days of green PnL in sandbox does not mean the bot is safe to switch to live.
- 🐛 **There may be bugs.** Trading bots are complex and exchange APIs can behave in unexpected ways (partial fills, rate limits, network outages, exchange downtime, flash crashes). The authors and contributors are **not liable** for any financial losses, missed profits, account bans, regulatory issues, taxes, or any other damages arising from your use of this software.
- 🌍 **Check your jurisdiction.** Algorithmic crypto trading may be regulated, restricted, or taxed differently where you live. You are responsible for complying with all applicable laws.
- 🔐 **Protect your API keys.** Use IP allowlists, disable withdrawal permissions, and never commit your `.env` file. Treat anyone with your keys as someone who can move your money.

By running this software you acknowledge that you understand these risks and accept full responsibility for any outcome.

---

## Features

- **Multiple modes** — `sandbox` (real market data, virtual wallet), `testnet` (Binance testnet), `live` (real money), `backtest`
- **Technical analysis pipeline** — EMA crossover, RSI, MACD, Bollinger Bands (with squeeze detection), ATR-based stops, volume intensity scoring
- **Dynamic market screener** — scans 300+ USDT pairs every 5 minutes, dynamically rotates a watchlist of ~20 active coins based on volume + breakout potential
- **Risk management** — per-trade risk %, max concurrent positions, daily loss limit, min balance guard, per-coin cooldowns, asset allocation cap
- **Two trading modes** — `semi_auto` (signals require human approval via Telegram or dashboard) or `full_auto` (auto-approve)
- **Profit-aware exits** — stop-loss, take-profit, trailing stop, RSI-overbought-with-profit, EMA-reversal-with-profit, time-based exit
- **Admin dashboard (Next.js 16)** — live signals, orders, trades, portfolio, candle charts, market screener results, runtime-editable config (27 parameters), JSON config export/import
- **Telegram bot** — signal notifications with approve/reject buttons, `/status`, `/balance`, `/signals`, `/trades`, `/pnl`, `/pause`, `/resume`
- **Real-time updates** — WebSocket bridge over Redis pub/sub, no polling
- **Production-ready ops** — Prometheus metrics, structured JSON logging (Loki-compatible), Sentry/GlitchTip error tracking, JWT auth, audit log, graceful shutdown, startup recovery
- **Atomic safety** — Lua-scripted Redis wallet, optimistic locking on signal approval, idempotent execution worker

---

## Quick Start

### Requirements

- Docker & Docker Compose
- A Binance account (testnet for free testing, or live for real money) — **optional for sandbox mode**
- (Optional) A Telegram bot token from [@BotFather](https://t.me/BotFather) for notifications

### 1. Clone and configure

```bash
git clone https://github.com/<your-fork>/finance-app.git
cd finance-app
cp .env.example .env
```

Open `.env` and fill in **at minimum**:

| Variable | What to set |
|---|---|
| `POSTGRES_PASSWORD` | A strong random password |
| `JWT_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Replace the password placeholder with the same value as `POSTGRES_PASSWORD` |

Everything else has working defaults. If you want Binance live/testnet trading, also set the API key/secret pair for the mode you'll use. If you want Telegram notifications, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

### 2. Start the stack

```bash
docker compose up -d --build
```

This launches five containers: `trading-bot`, `trading-dashboard`, `trading-telegram`, `trading-postgres`, `trading-redis`.

### 3. Verify it's running

```bash
curl http://localhost:8000/health
docker logs trading-bot --tail 30
```

The first time the bot starts, it auto-generates an `admin` user and prints a random password to the logs. **Find that password in the logs and use it for the dashboard login.**

### 4. Open the dashboard

Visit **http://localhost:3003**. Log in as `admin` with the password from the logs. Go to **Settings** to:

1. Change the admin password
2. Top up the sandbox wallet (Settings → Sandbox Wallet → Deposit)
3. Tune risk and strategy parameters live (no restart needed)

The bot is now scanning the market, generating signals, and (if you enabled `full_auto` and topped up the sandbox wallet) opening simulated trades.

---

## Going Live (with Real Money)

> **One more time: this is risky. Run for at least 1–2 weeks in `sandbox` mode with realistic parameters before flipping the switch.**

1. Create API keys at [Binance API Management](https://www.binance.com/en/my/settings/api-management).
   - **Disable withdrawals.** The bot only needs Spot Trading.
   - Add an IP allowlist for your server's static IP.
2. Set in `.env`:
   ```bash
   APP_MODE=live
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
3. Start small. `RISK_PER_TRADE_PCT=0.01`, `MAX_CONCURRENT_POSITIONS=1`, `MIN_BALANCE_USDT=20.0`.
4. Restart: `docker compose up -d`. Watch the dashboard and logs closely for the first day.

---

## Architecture

```
Binance REST API
       │
  REST Poller (periodic, candle-close detection)
       │
  PostgreSQL (candles, signals, orders, trades)
       │
  Technical Analysis Engine (EMA, RSI, MACD, BB, ATR, Volume)
       │
  Signal Generator  ◄──── Screener (every 5 min, top ~20 coins)
       │
  Risk Manager (5-stage validation)
       │
  Telegram / Dashboard approval  (semi_auto)  or  Auto-approve  (full_auto)
       │
  Order Manager  →  Binance API (live) or Sandbox Executor (simulated)
       │
  WebSocket bridge → Dashboard (real-time updates)
```

For deeper internals (database schema, signal lifecycle, exit strategy logic), see [CLAUDE.md](CLAUDE.md).

---

## Configuration

### Environment variables

All knobs live in `.env`. See [.env.example](.env.example) for the full annotated list.

### Runtime config (no restart needed)

27 trading parameters can be tuned **live** from the dashboard's **Settings** page or via `PATCH /api/v1/config`. Changes are persisted in the `trading.app_config` table and broadcast to all containers via Redis pub/sub. Includes:

- Risk: `risk_per_trade_pct`, `max_concurrent_positions`, `daily_loss_limit_pct`, `min_balance_usdt`, `cooldown_seconds`, `max_trades_per_day`
- Strategy: `min_signal_confidence`, `strategy_w_ema/macd/rsi/bb/volume`, `ema_trend_score`
- SL/TP: `min_sl_pct`, `max_sl_pct`, `min_tp_pct`, `atr_sl_multiplier`, `atr_tp_multiplier`
- Exit: `trailing_stop_activation_pct`, `trailing_stop_trail_pct`, `max_hold_hours`, `time_exit_min_profit_pct`
- Screener: `screener_min_volume_usdt`, `screener_min_change_pct`, `screener_active_dynamic_pairs`, `screener_max_candidates`
- Mode: `trading_mode` (`semi_auto` / `full_auto`)

### Presets

[`config-presets/baseline.json`](config-presets/baseline.json) is a tuned starting preset you can import from the dashboard (Settings → Import JSON). Your own snapshots live in `config-presets/snapshots/` and are git-ignored.

---

## Strategy

The default strategy is a 5-component weighted score (configurable):

| Component | Default Weight | Signal |
|---|---|---|
| EMA Crossover (9/21) | 25% | Bullish/bearish crossover or trend direction |
| MACD (12/26/9) | 25% | Crossover (±1.0) or histogram (±0.5) |
| RSI (14) | 20% | Overbought/oversold zones |
| Bollinger Bands (20, 2) | 15% | Band breach + squeeze amplification |
| Volume | 15% | Graduated intensity (0-1, not binary) |

A signal fires when `|total_score| >= min_signal_confidence` (default 0.40). Stops use ATR × multiplier with min/max % bounds.

**Exits** are profit-aware: SL/TP always trigger, but trend-reversal indicators only trigger an exit if the position is profitable (or down enough to confirm a real reversal). See [CLAUDE.md](CLAUDE.md) → "Exit Strategy" for the full decision tree.

---

## API

The bot exposes a JSON REST API at `http://localhost:8000` and a WebSocket at `/ws`. All `/api/v1/*` endpoints (except `/health` and `/metrics`) require a JWT obtained from `POST /api/v1/auth/login`.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Get JWT token |
| `GET` | `/api/v1/dashboard/summary` | Dashboard summary |
| `GET` | `/api/v1/signals` | Paginated signals |
| `POST` | `/api/v1/signals/{id}/approve` | Approve a pending signal |
| `GET` | `/api/v1/trades` | Paginated trades |
| `GET` | `/api/v1/trades/stats` | Win rate, total PnL, etc. |
| `GET` | `/api/v1/config` | Current trading config |
| `PATCH` | `/api/v1/config` | Update trading config (hot reload) |
| `GET` | `/api/v1/screener/results` | Latest market scan |
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics/` | Prometheus metrics |

Full list in [CLAUDE.md](CLAUDE.md).

---

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Type checking / linting (whatever you've configured)
```

Dashboard:

```bash
cd dashboard
npm install
npm run dev
```

---

## Project Layout

See [CLAUDE.md](CLAUDE.md) for an annotated tree, database schema notes, and developer-oriented documentation.

```
src/                # Python backend (FastAPI + workers)
dashboard/          # Next.js 16 admin UI
tests/unit/         # Unit tests (~128)
alembic/            # DB migrations
config-presets/     # Importable config JSONs
.github/workflows/  # CI: builds + publishes Docker images to GHCR
```

---

## Contributing

PRs welcome. Please:

- Keep style consistent with existing code (Pydantic for schemas, async SQLAlchemy, structlog for logs).
- Add unit tests for new strategy/risk logic.
- Don't introduce new hardcoded credentials, domains, or personal info.
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, …).

---

## License

[MIT](LICENSE) — do whatever you want, but the disclaimer above still applies.

---

## Acknowledgements

Built on the shoulders of: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [pandas-ta](https://github.com/twopirllc/pandas-ta), [python-binance](https://github.com/sammchardy/python-binance), [Next.js](https://nextjs.org/), [shadcn/ui](https://ui.shadcn.com/), [TanStack Query](https://tanstack.com/query), [lightweight-charts](https://github.com/tradingview/lightweight-charts).

---

**Final reminder:** none of this is investment advice. Trade responsibly.
