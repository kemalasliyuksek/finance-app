# Finance App - Trading Bot

## Proje Özeti

Binance borsasında teknik analiz ile kısa vadeli kripto al/sat yapan otonom trading bot sistemi. Web tabanlı admin dashboard ile yönetilir. Dinamik piyasa tarama (screener) ile 300+ USDT çiftinden en iyi fırsatları otomatik bulur. Sandbox modda sanal bakiye ile test, live modda gerçek trade yapılır.

## Çalışma Ortamı

Proje Docker Compose ile çalıştırılmak üzere tasarlanmıştır. Lokal geliştirme veya uzak sunucu (VPS) üzerinde aynı `docker compose up -d` komutu ile ayağa kalkar.

### Sorgu / komut akışı
- Eğer proje uzak bir sunucuda çalışıyorsa ve doğrudan SSH yoksa: **gerekli komutları kullanıcıya ver, kullanıcı sunucuda çalıştırıp çıktıyı yapıştırır.**
- Her komutu vermeden önce: kolon adlarını, user/db adını, auth gereksinimini varsaymak yerine **CLAUDE.md'deki bu bölümden doğrula**. Yanlış varsayımla komut verip kullanıcıyı tekrar bocalatma.
- Komutları küçük parçalara böl (3-5 komut/turn), önce şema/auth doğrula sonra detay sorgula.

### Çalışma zamanı bilgileri
- **Container'lar:** `trading-bot`, `trading-dashboard`, `trading-telegram`, `trading-postgres`, `trading-redis`
- **Postgres user/db:** `trading_bot` / `trading_bot` (örnek: `docker exec trading-postgres psql -U trading_bot -d trading_bot -c "..."`)
- **Bot API:** `http://localhost:8000` — **tüm `/api/v1/*` endpoint'leri JWT auth gerektirir** (`/health`, `/metrics/` hariç). Token için `POST /api/v1/auth/login` ile `admin` + dashboard şifresi.
- **Dashboard URL:** `.env` dosyasındaki `NEXT_PUBLIC_API_URL` ile yapılandırılır (lokal varsayılan: `http://localhost:3003`).

### DB şema notları (yanlış kolon adı tuzakları)
- `trading.signals`: kolon adı **`side`** (BUY/SELL), `signal_type` DEĞİL. Diğer kolonlar: `id, symbol, side, strategy, confidence, entry_price, stop_loss, take_profit, indicators(jsonb), sentiment_score, status, approved_at, approved_by, expires_at, notes, created_at, updated_at, deleted_at`
- `trading.signals.created_at` **TIMESTAMP WITH TIME ZONE** (bu tablo özel — geri kalanın çoğu naive UTC). Sorguda dikkat.
- `trading.app_config`: **key/value tablosu DEĞİL**, tek satırlık geniş tablo (her parametre kendi kolonu). Sorgu örneği: `SELECT min_signal_confidence, max_concurrent_positions FROM trading.app_config;`
- `trading.signals.status` enum: `pending | approved | rejected | expired | executed | weak`
- `trading.trades`: PnL kolonu **`realized_pnl`** (`pnl_usdt` DEĞİL). Diğer kolonlar: `id, symbol, entry_order_id, exit_order_id, side, entry_price, exit_price, quantity, realized_pnl, realized_pnl_pct, total_commission, status(open/closed), opened_at, closed_at, duration_seconds, notes, stop_loss, take_profit, created_at, updated_at, deleted_at`
- `trading.orders`: `id, signal_id, binance_order_id, binance_client_oid, symbol, side, order_type, quantity, price, stop_price, status, filled_quantity, avg_fill_price, commission, commission_asset, error_message, created_at, updated_at, deleted_at`
- **Join yolu:** trades → orders (entry_order_id / exit_order_id) → signals (signal_id). Exit sebebi: `trades.exit_order_id → orders.signal_id → signals.strategy` (exit_stop_loss, exit_take_profit, exit_trailing_stop, exit_time_exit vb.)
- Tabloların tamamı `trading` schema'sında

### Tipik tanı sorguları (hazır şablonlar)
```sql
-- Sinyal dağılımı (son 24s)
SELECT status, COUNT(*) FROM trading.signals
WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;

-- Confidence istatistikleri
SELECT ROUND(AVG(confidence)::numeric,3) avg, MAX(confidence) max, MIN(confidence) min, COUNT(*) total
FROM trading.signals WHERE created_at > NOW() - INTERVAL '24 hours';

-- En yüksek confidence sinyaller
SELECT symbol, side, status, ROUND(confidence::numeric,3) conf, strategy, created_at
FROM trading.signals WHERE created_at > NOW() - INTERVAL '6 hours'
ORDER BY confidence DESC LIMIT 15;

-- Aktif config
SELECT * FROM trading.app_config LIMIT 1;

-- Trade istatistikleri (win rate, toplam PnL)
SELECT COUNT(*) total, COUNT(*) FILTER (WHERE status='closed') closed,
  COUNT(*) FILTER (WHERE realized_pnl > 0) wins,
  COUNT(*) FILTER (WHERE realized_pnl < 0) losses,
  ROUND(AVG(realized_pnl)::numeric, 4) avg_pnl,
  ROUND(SUM(realized_pnl)::numeric, 4) total_pnl,
  ROUND((COUNT(*) FILTER (WHERE realized_pnl > 0))::numeric / NULLIF(COUNT(*) FILTER (WHERE status='closed'), 0) * 100, 1) win_rate
FROM trading.trades;

-- Exit sebepleri dağılımı
SELECT s.strategy exit_reason, COUNT(*) cnt,
  ROUND(AVG(t.realized_pnl)::numeric,4) avg_pnl,
  ROUND(SUM(t.realized_pnl)::numeric,4) total_pnl
FROM trading.trades t
JOIN trading.orders o ON o.id = t.exit_order_id
JOIN trading.signals s ON s.id = o.signal_id
WHERE t.status='closed' GROUP BY s.strategy ORDER BY cnt DESC;

-- Coin bazlı performans
SELECT symbol, COUNT(*) trades,
  COUNT(*) FILTER (WHERE realized_pnl>0) wins,
  ROUND(SUM(realized_pnl)::numeric,4) total_pnl
FROM trading.trades WHERE status='closed'
GROUP BY symbol ORDER BY total_pnl DESC;
```

### Log inceleme
```bash
docker logs trading-bot --tail 200 2>&1 | grep -iE "signal|risk|reject|error"
docker logs trading-bot --since 6h 2>&1 | grep -iE "actionable|risk_check|cooldown"
```

### Config değiştirme
İki yol var:
1. **Dashboard Ayarlar sayfası** (kullanıcı tarafından, en güvenli)
2. **Direkt API PATCH** (auth token ile): `curl -X PATCH .../api/v1/config -H "Authorization: Bearer $TOKEN" -d '{"min_signal_confidence":0.45}'` — Redis `config:updated` otomatik publish edilir, hot reload tetiklenir
- DB'ye direkt yazma yapma (Redis publish atlanır, container'lar senkron olmaz).

## Teknoloji Stack

### Backend
- **Dil:** Python 3.12
- **Web Framework:** FastAPI + Uvicorn
- **Veritabanı:** PostgreSQL 16 (asyncpg + SQLAlchemy 2.0 async)
- **Cache/PubSub:** Redis 7 (Lua script ile atomik wallet operasyonları)
- **Borsa:** Binance (python-binance)
- **Teknik Analiz:** pandas-ta
- **Telegram:** python-telegram-bot v21+
- **Auth:** JWT (pyjwt + bcrypt)
- **Logging:** structlog (JSON, Loki uyumlu)
- **Metrikler:** prometheus-client
- **Error Tracking:** sentry-sdk (GlitchTip uyumlu)
- **Migration:** Alembic (7 migration)
- **Config:** pydantic-settings
- **Rate Limiting:** slowapi
- **Containerization:** Docker Compose

### Frontend (Dashboard)
- **Framework:** Next.js 16 (App Router) + TypeScript
- **UI:** shadcn/ui (base-nova) + Tailwind CSS v4 (dark mode)
- **State:** TanStack Query v5 (server state) + zustand (client state)
- **Grafikler:** lightweight-charts (TradingView mum grafiği) + recharts
- **Real-time:** WebSocket (Redis pub/sub bridge) — anlık sayfa güncellemesi
- **Container:** Node.js 22 Alpine (standalone build)

## Proje Yapısı

```
src/
  main.py              # FastAPI + worker başlangıç (lifespan) + startup recovery
  config.py            # Pydantic Settings (env-based, strateji ağırlıkları dahil)
  constants.py         # Enum'lar (SignalStatus: pending/approved/rejected/expired/executed/weak)
  models/              # SQLAlchemy ORM (9 tablo, trading schema)
  schemas/             # Pydantic request/response (SignalDetailRead, TimelineEvent dahil)
  db/                  # Async session + repository pattern
  api/
    auth.py            # JWT token + bcrypt password utilities
    dependencies.py    # get_current_user dependency
    router.py          # Ana router (/api/v1 + health + ws)
    ws_manager.py      # WebSocket connection manager + Redis bridge
    endpoints/
      auth.py          # Login, refresh, me, change-password
      dashboard.py     # Dashboard summary (sandbox bakiye desteği, unrealized PnL)
      signals.py       # Sinyal listesi, onay/red, sinyal detay (timeline + order + trade)
      orders.py        # Emir listesi, detay sheet (server-side sıralama)
      trades.py        # Trade listesi, stats, detay sheet (server-side sıralama)
      market.py        # Piyasa verileri (Binance tüm USDT çiftleri) + kullanıcı favorileri
      portfolio.py     # Portföy snapshot + geçmiş
      candles.py       # Mum verileri
      config_api.py    # Trading config, bot status, pair yönetimi
      sentiment.py     # Sentiment skorları (CryptoPanic devre dışı)
      screener.py      # Screener tarama sonuçları ve durumu
      sandbox.py       # Sandbox cüzdan (deposit/withdraw/reset)
      binance_account.py # Gerçek Binance hesap bilgileri (read-only)
      ws.py            # WebSocket endpoint
      health.py        # Health check
    middleware/
      rate_limit.py    # slowapi rate limiting
  collector/           # Binance veri toplama (REST poller + backfill)
    rest_fetcher.py    # Tarihsel kline backfill (interval bazlı limit)
    rest_poller.py     # Periyodik REST polling (WS fallback), mum kapanışı tespiti
    websocket_manager.py # Binance kline stream, auto-reconnect, exponential backoff
    data_normalizer.py # REST/WS format → CandleCreate dönüşümü
  analysis/            # Teknik indikatörler (EMA, RSI, BB, MACD, ATR, Volume) — NaN-safe
    indicators.py      # 6 indikatör fonksiyonu (EMA, RSI, BB, Volume, ATR, MACD) — NaN-safe
    ta_engine.py       # TAResult aggregator, candles→DataFrame, graceful degradation
  strategy/            # Sinyal üretimi — pozisyon farkındalıklı (BUY/SELL ayrımı)
    ema_crossover.py   # EMA+MACD+RSI+BB+Volume stratejisi + kâr odaklı exit
    signal_generator.py # Mum kapanışı → pozisyon kontrolü → BUY veya exit sinyali
    base_strategy.py   # BaseStrategy + ExitSignal
  risk/                # Pozisyon boyutlama, stop-loss, risk limitleri (asyncio.Lock korumalı)
    risk_manager.py    # 5 aşamalı doğrulama (bakiye, günlük kayıp, pozisyon, cooldown, trade limiti)
    position_sizer.py  # ATR bazlı risk hesabı, komisyon dahil, min notional $10
    stop_loss.py       # ATR×multiplier SL/TP, min/max % sınırlama, trailing stop
  executor/            # Emir yönetimi (Binance veya sandbox simülasyon)
    order_manager.py   # Atomik order+trade oluşturma, audit log, is_exit desteği
    binance_client.py  # Binance API wrapper (circuit breaker + retry)
    fill_monitor.py    # Binance user data stream — gerçek zamanlı fill takibi
  portfolio/           # Bakiye takibi, PnL hesaplama
    balance_tracker.py # Snapshot oluşturma (Binance/sandbox), Prometheus gauge güncelleme
    pnl_calculator.py  # Closed trade analizi (win rate, drawdown, profit factor, günlük PnL)
  notifications/       # Telegram bot (tüm komutlar + risk reddi bildirimi)
    telegram_bot.py    # /start, /help, /status, /balance, /signals, /trades, /pnl, /pause, /resume
    message_formatter.py # Mesaj formatları
    approval_handler.py  # Atomik onay/red (optimistic locking)
  sentiment/           # CryptoPanic (devre dışı — API ücretsiz plan kaldırıldı)
  screener/            # Piyasa tarama — dinamik coin keşfi
    scanner.py         # Binance ticker/24hr → filtre → top adaylar
    analyzer.py        # Batch mum çekme + full TA analizi (memory'de)
    filters.py         # USDT, kaldıraçlı, stablecoin, ASCII-only, kara liste filtreleri
    pair_manager.py    # Dinamik pair ekleme/çıkarma (açık pozisyon korumalı, desired'a dahil)
    screener_worker.py # 5dk periyodik tarama döngüsü
  sandbox/             # Sandbox modu — sanal cüzdan + simüle emir
    wallet.py          # Redis Lua script ile atomik bakiye yönetimi (race condition korumalı)
    executor.py        # Lokal fill simülasyonu + hata durumunda rollback
  backtest/            # Tarihsel veri üzerinde strateji testi
    backtest_runner.py # Tarihsel TA analizi + sanal trade simülasyonu + equity curve
  core/                # Events (Redis), logging, metrics, exceptions, audit
    events.py          # Redis pub/sub + cache (TTL destekli)
    logging.py         # structlog JSON — Loki uyumlu
    metrics.py         # Prometheus counter/gauge/histogram tanımları
    exceptions.py      # Hiyerarşik exception sınıfları (TradingBotError base)
    audit.py           # DB-backed audit trail
    config_reload.py   # Dinamik config hot reload + Redis config:updated listener
    rate_limiter.py    # Token bucket — Binance API rate limit (10 req/s, 1200/dk)
    retry.py           # Exponential backoff decorator
    circuit_breaker.py # CLOSED→OPEN→HALF_OPEN durum makinesi (Binance API koruması)
  workers/
    execution_worker.py # signal:approved → idempotency check → entry/exit ayrımı → emir
    collector_worker.py # Backfill + WS/REST poller başlatma + pair yönetimi
dashboard/
  src/
    app/               # Next.js App Router sayfaları
    components/        # shadcn/ui + layout (sidebar collapse/hamburger) + shared (sortable-header, pagination)
      settings/        # EditableConfigSection (compact form) + ConfigExportImport (JSON export/import + diff dialog)
    contexts/          # PageHeaderContext, SidebarContext
    hooks/             # TanStack Query hooks + useTableSort + useSignalDetail + useMarket + useConfig/useUpdateConfig
    lib/               # API client, WebSocket client, formatters, config-fields.ts (27 alan merkezi tanımı)
    providers/         # Auth, Query, WebSocket providers
    types/             # TypeScript type tanımları (SignalDetail, TimelineEvent, TradingConfig, TradingConfigUpdate dahil)
  Dockerfile           # Multi-stage Node.js build
config-presets/        # JSON config preset'leri (Dashboard İçe Aktar ile yüklenir)
  baseline.json        # Şu an aktif sıkılaştırılmış ilk üretim ayarı
  snapshots/           # Tarih damgalı yedekler (YYYY-MM-DD-not.json)
  README.md            # Preset vs snapshot ayrımı, kullanım rehberi
tests/
  unit/                # 128+ unit test (indicators, risk, strategy, exit, crossover, schema, screener, config)
alembic/               # DB migration dosyaları (001-008)
scripts/
  entrypoint.sh        # Docker entrypoint (Alembic migrate + uvicorn başlatma)
  hash_password.py     # Şifre hash'leme aracı
```

## Veritabanı

- **Schema:** `trading`
- **Tablolar:** candles, signals, orders, trades, portfolio_snapshots, sentiment_scores, users, audit_logs, user_favorites, app_config
- **Migration:** `alembic upgrade head` (Docker Compose içinde otomatik çalışır)
- **Son migration:** 008 — app_config tablosu (runtime düzenlenebilir parametreler, tek satır)

## Dashboard

Admin dashboard, `.env` içinde tanımlanan host üzerinden erişilir (lokal varsayılan: `http://localhost:3003`).

### Güvenlik
- **JWT Auth** — Kullanıcı adı/şifre login (varsayılan)
- **Opsiyonel ek katman:** Reverse proxy önüne Cloudflare Access, Tailscale, basic auth gibi bir katman eklemeniz şiddetle önerilir (özellikle public ortamda).

### İlk Giriş
- İlk açılışta otomatik `admin` / rastgele şifre oluşturulur (loglarda görünür)
- Giriş yaptıktan sonra Ayarlar sayfasından şifre değiştirilmelidir

### Layout
- **Topbar:** Sayfa başlığı (sol) + mod badge'leri (SANDBOX/LIVE, Otomatik/Yarı Otomatik, Canlı) (sağ)
- **Sidebar:** Navigasyon, desktop collapse (sadece ikonlar), mobil hamburger menu, kullanıcı + çıkış
- **Responsive:** Mobil öncelikli, tablolarda yatay scroll + kolon gizleme

### Sayfalar
- **Dashboard:** Bakiye (sandbox/live), anlık kâr/zarar (unrealized PnL), günlük kâr/zarar, kazanma oranı, açık pozisyonlar (canlı fiyat + anlık K/Z + süre), son sinyaller
- **Sinyaller:** Filtrelenebilir liste (Tümü/Bekleyen/Onaylanan/Gerçekleşen/Reddedilen/Süre Aşımı/Zayıf), sıralanabilir kolonlar, sinyal detay sheet (timeline + order + trade + toplam tutar), onay/red butonları
- **Emirler:** Emir geçmişi, server-side sıralama, toplam tutar kolonu, tıklanabilir detay sheet
- **İşlemler:** İşlem geçmişi, istatistikler (kazanma oranı, kâr/zarar), açık trade'lerde canlı unrealized PnL + güncel fiyat + canlı süre, tıklanabilir detay sheet (SL/TP, komisyon dahil)
- **Portföy:** Bakiye grafiği (24h/7d/30d), varlık dağılımı
- **Kriptolar:** Tüm piyasa görünümü (300+ USDT çifti), arama, favori (DB'de), 1s/4s/24s değişim penceresi, pagination (50/sayfa), screener sinyal eşleştirmesi, tıklayınca coin detaya git
- **Takip Edilenler:** Aktif trading çiftleri grid, dinamik ekleme/silme
- **Coin Detay:** TradingView mum grafiği, hacim, son sinyaller
- **Tarama (Screener):** Piyasa tarama sonuçları, skor, hacim, değişim, TA özet, client-side sıralama, tıklanabilir detay sheet (TA detayları: EMA, RSI, BB squeeze, MACD, hacim yoğunluğu)
- **Binance:** Gerçek Binance hesap bakiyeleri ve varlıkları (read-only)
- **Ayarlar:** Bot durumu, sandbox cüzdan (deposit/reset), şifre değiştirme + canlı düzenlenebilir parametre formları compact 3-kolon grid içinde: Trading Modu, Risk (6), Strateji ağırlıkları (7), SL/TP (5), Çıkış (4), Screener (4) — toplam 27 parametre. Her kart kendi kaydet butonuna sahip, dirty-state takibi yapılır, sadece değişen alanlar PATCH'e gönderilir. Number input'larda spin ok'ları gizli ve scroll ile değer değişimi engelli. Sayfa üstünde **JSON Dışa Aktar / İçe Aktar** butonları: import dosyası parse edildikten sonra diff önizleme dialog'u açılır (değişecek / geçersiz / bilinmeyen kategorileri), kullanıcı onaylayınca PATCH tetiklenir. Değişiklikler `trading.app_config` tablosuna yazılır, Redis `config:updated` ile tüm container'lara anında yansır (restart gerekmez). Preset'ler `config-presets/` klasöründe versiyonlanır.

### Real-time
WebSocket ile anlık güncelleme (sinyal, emir, trade, mum kapanışı, screener). Sayfa yenilemeye gerek yok.

### Tablo Özellikleri
- Tüm tablolarda sıra numarası (#) kolonu
- Server-side sıralama (paginated tablolar: sinyaller, emirler, trade'ler)
- Client-side sıralama (non-paginated: screener, binance, kriptolar)
- Mobil responsive: öncelikli kolonlar görünür, ikinciller `hidden sm:table-cell`
- StatusBadge: pending/approved/rejected/expired/executed/weak/BUY/SELL/open/closed/filled

## API Endpoint'leri

| Prefix | Endpoint | Açıklama |
|--------|----------|----------|
| — | `GET /health` | Sağlık kontrolü |
| — | `GET /health/detailed` | Detaylı sağlık kontrolü |
| — | `GET /metrics/` | Prometheus metrikleri |
| — | `WS /ws` | WebSocket (JWT auth) |
| `/api/v1` | `POST /auth/login` | JWT login |
| `/api/v1` | `POST /auth/refresh` | Token yenileme |
| `/api/v1` | `GET /auth/me` | Mevcut kullanıcı |
| `/api/v1` | `POST /auth/change-password` | Şifre değiştirme |
| `/api/v1` | `GET /dashboard/summary` | Dashboard özet |
| `/api/v1` | `GET /signals` | Sinyal listesi (filtrelenebilir, sıralanabilir) |
| `/api/v1` | `GET /signals/{id}` | Tekil sinyal |
| `/api/v1` | `GET /signals/{id}/detail` | Sinyal detay (order + trade + timeline) |
| `/api/v1` | `POST /signals/{id}/approve` | Sinyal onay (atomik, optimistic locking) |
| `/api/v1` | `POST /signals/{id}/reject` | Sinyal red |
| `/api/v1` | `GET /orders` | Emir listesi (sıralanabilir) |
| `/api/v1` | `GET /orders/{id}` | Tekil emir detayı |
| `/api/v1` | `GET /trades` | Trade listesi (sıralanabilir) |
| `/api/v1` | `GET /trades/open` | Açık pozisyonlar |
| `/api/v1` | `GET /trades/stats` | Trade istatistikleri |
| `/api/v1` | `GET /trades/{id}` | Tekil trade detayı |
| `/api/v1` | `GET /portfolio/current` | Son portföy snapshot |
| `/api/v1` | `GET /portfolio/history` | Portföy geçmişi (24h/7d/30d/all) |
| `/api/v1` | `GET /candles/{symbol}/{interval}` | Son N mum verisi (limit 1-500) |
| `/api/v1` | `GET /candles/{symbol}/{interval}/range` | Zaman aralığı ile mum verisi (limit 1-1000) |
| `/api/v1` | `GET /config` | Trading konfigürasyonu (27 düzenlenebilir alan + env alanları) |
| `/api/v1` | `PATCH /config` | Config kısmi güncelleme (DB + hot reload + `config:updated` publish) |
| `/api/v1` | `GET /config/status` | Bot durumu (uptime, mod, çiftler) |
| `/api/v1` | `GET /config/pairs` | Aktif çift listesi |
| `/api/v1` | `POST /config/pairs` | Coin ekleme |
| `/api/v1` | `DELETE /config/pairs/{symbol}` | Coin silme |
| `/api/v1` | `GET /sentiment/{symbol}` | Sentiment skoru (Redis cache) |
| `/api/v1` | `GET /screener/results` | Screener tarama sonuçları |
| `/api/v1` | `GET /screener/status` | Screener durumu |
| `/api/v1` | `GET /sandbox/wallet` | Sandbox cüzdan bakiyeleri |
| `/api/v1` | `POST /sandbox/deposit` | Sandbox bakiye yükleme |
| `/api/v1` | `POST /sandbox/withdraw` | Sandbox bakiye çekme |
| `/api/v1` | `POST /sandbox/reset` | Sandbox sıfırlama |
| `/api/v1` | `GET /binance/account` | Gerçek Binance hesap bilgileri |
| `/api/v1` | `GET /market/coins` | Tüm USDT piyasa verileri (window: 1h/4h/1d) |
| `/api/v1` | `GET /market/favorites` | Kullanıcı favori coinleri |
| `/api/v1` | `POST /market/favorites` | Favori coin ekle |
| `/api/v1` | `DELETE /market/favorites/{symbol}` | Favori coin sil |

## Çalıştırma

### Lokal Geliştirme

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Değerleri doldur
pytest tests/unit/ -v
```

### Docker ile Deploy

```bash
cp .env.example .env  # Değerleri doldur
docker compose up -d --build
```

Container'lar:
- `trading-bot` — FastAPI + tüm worker'lar (port 8000, başlangıçta Alembic migrasyon + startup recovery)
- `trading-dashboard` — Next.js admin dashboard (port 3003→3000)
- `trading-telegram` — Telegram bot (ayrı process)
- `trading-postgres` — PostgreSQL 16
- `trading-redis` — Redis 7

### Doğrulama

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/config/status
docker logs trading-bot --tail 20
docker logs trading-dashboard --tail 10
```

## Konfigürasyondaki Önemli Parametreler

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `APP_MODE` | sandbox | live / sandbox / testnet / backtest |
| `TRADING_MODE` | semi_auto | semi_auto (Telegram/Dashboard onay) / full_auto (otomatik onay) |
| `RISK_PER_TRADE_PCT` | 0.03 | Trade başına risk (%3) |
| `MAX_CONCURRENT_POSITIONS` | 2 | Maks eşzamanlı pozisyon |
| `MAX_ASSET_ALLOCATION_PCT` | 0.50 | Maks pozisyon büyüklüğü (bakiyenin %50'si) |
| `DAILY_LOSS_LIMIT_PCT` | 0.05 | Günlük kayıp limiti (%5) |
| `MIN_BALANCE_USDT` | 20.0 | Min bakiye (altına düşerse trading durur) |
| `COOLDOWN_SECONDS` | 300 | Trade arası bekleme (5 dk) |
| `MIN_SIGNAL_CONFIDENCE` | 0.40 | Sinyal üretim eşiği |
| `STRATEGY_W_EMA` | 0.25 | EMA ağırlığı |
| `STRATEGY_W_MACD` | 0.25 | MACD ağırlığı |
| `STRATEGY_W_RSI` | 0.20 | RSI ağırlığı |
| `STRATEGY_W_BB` | 0.15 | Bollinger Bands ağırlığı |
| `STRATEGY_W_VOLUME` | 0.15 | Volume ağırlığı |
| `EMA_TREND_SCORE` | 0.6 | EMA trend skoru (crossover olmadan) |
| `MACD_FAST_PERIOD` | 12 | MACD hızlı periyot |
| `MACD_SLOW_PERIOD` | 26 | MACD yavaş periyot |
| `MACD_SIGNAL_PERIOD` | 9 | MACD sinyal periyot |
| `SCREENER_ENABLED` | true | Screener aktif/pasif |
| `SCREENER_INTERVAL_SECONDS` | 300 | Tarama periyodu (5 dk) |
| `SCREENER_MIN_VOLUME_USDT` | 500000 | Min 24s hacim ($500K) |
| `SCREENER_MIN_CHANGE_PCT` | 2.0 | Min fiyat değişimi (%) |
| `SCREENER_MAX_CANDIDATES` | 40 | Deep analiz için max aday |
| `SCREENER_ACTIVE_DYNAMIC_PAIRS` | 15 | Dinamik aktif coin sayısı |
| `SCREENER_VOLUME_TOP_N` | 5 | Her zaman aktif hacim top N |
| `SCREENER_BREAKOUT_WEIGHT` | 0.30 | Screener breakout skoru ağırlığı |
| `ATR_SL_MULTIPLIER` | 1.5 | SL mesafesi = ATR × bu değer |
| `ATR_TP_MULTIPLIER` | 3.0 | TP mesafesi = ATR × bu değer |
| `MIN_TP_PCT` | 0.03 | Min %3 take-profit mesafesi |
| `MIN_SL_PCT` | 0.005 | Min %0.5 stop-loss mesafesi |
| `MAX_SL_PCT` | 0.05 | Max %5 stop-loss mesafesi |
| `BB_SQUEEZE_PERCENTILE` | 0.20 | BB bandwidth bu percentile altı = squeeze |
| `BB_SQUEEZE_LOOKBACK` | 20 | Squeeze tespiti kaç mum geriye bakacak |
| `VOLUME_BREAKOUT_MAX_RATIO` | 5.0 | Volume intensity normalizasyon max oranı |
| `VOLUME_MIN_INTENSITY` | 0.3 | Bu yoğunluk altında amplify etme |
| `TRAILING_STOP_ACTIVATION_PCT` | 2.0 | Trailing stop %2 kârda aktive olur |
| `TRAILING_STOP_TRAIL_PCT` | 2.0 | Zirveden %2 düşüşte sat |
| `TRAILING_STOP_LOOKBACK` | 10 | Son kaç mumun zirvesine bak |
| `MAX_HOLD_HOURS` | 4 | Max pozisyon tutma süresi (saat) |
| `TIME_EXIT_MIN_PROFIT_PCT` | 0.5 | Süre aşımında min kâr eşiği (%) |

## Dinamik Config (Runtime Düzenlenebilir Ayarlar)

27 tunable parametre `trading.app_config` DB tablosunda saklanır ve dashboard "Ayarlar" sayfasından canlı düzenlenebilir. Restart gerekmez.

### Kapsam
- **Risk (6):** risk_per_trade_pct, max_concurrent_positions, daily_loss_limit_pct, min_balance_usdt, cooldown_seconds, max_trades_per_day
- **Strateji (7):** min_signal_confidence, strategy_w_ema/macd/rsi/bb/volume, ema_trend_score
- **SL/TP (5):** min_sl_pct, max_sl_pct, min_tp_pct, atr_sl_multiplier, atr_tp_multiplier
- **Exit (4):** trailing_stop_activation_pct, trailing_stop_trail_pct, max_hold_hours, time_exit_min_profit_pct
- **Screener (4):** screener_min_volume_usdt, screener_min_change_pct, screener_active_dynamic_pairs, screener_max_candidates
- **Mode (1):** trading_mode (semi_auto/full_auto)

### Akış
```
İlk boot (lifespan) → AppConfigRepository.get_or_seed_defaults()
  → DB boş mu? Migration 008 tek satır insert etmiştir; değilse settings'ten seed
  → DB dolu mu? → settings'i DB değerleriyle override et (apply_config_to_settings)

Dashboard PATCH /api/v1/config
  → Pydantic field constraint'leri (422)
  → validate_config_updates (cross-field: strategy_w_* toplamı, SL/TP bounds → 422)
  → DB update + audit log (entity_type="config")
  → apply_config_to_settings (yerel singleton)
  → Redis publish "config:updated" {changes, updated_by}

config_listener (trading-bot + trading-telegram, her container'da)
  → Redis config:updated → apply_config_to_settings (yerel singleton senkron)

WebSocket bridge
  → Redis config:updated → WS "config" event → dashboard query invalidate
```

### Seed + Persistence
- Migration 008 tabloyu oluşturur ve `INSERT ... WHERE NOT EXISTS` ile ilk satırı yerleştirir (default değerlerle)
- `AppConfigRepository.get_or_seed_defaults` idempotent güvenlik ağı — mevcut satırı bozmaz
- Redeploy'larda mevcut değerler korunur, reset olmaz
- Secret'lar (API key, DB password vb.) hâlâ `.env`'de — DB'ye hiç yazılmaz

### Hot Reload Garantisi
Tüm worker ve strateji kodu `settings.xyz`'yi **call-time'da** okur (init'te cache yok). Pydantic singleton'a `setattr` ile yapılan değişiklik bir sonraki çağrıda anında etkili olur. İki container (trading-bot + trading-telegram) bağımsız süreçlerde çalıştığı için Redis pub/sub ile senkron tutulur.

### Env'de Kalanlar (Düzenlenemez)
`APP_MODE`, `TRADING_PAIRS`, `CANDLE_INTERVALS`, `DATABASE_URL`, `REDIS_URL`, secret'lar, `LOG_LEVEL`, `SENTRY_DSN`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `SCREENER_ENABLED`, `SCREENER_INTERVAL_SECONDS`, `SCREENER_VOLUME_TOP_N`, `MAX_ASSET_ALLOCATION_PCT`.

### JSON Export / Import + Preset'ler

Dashboard "Ayarlar" sayfasının sağ üstündeki butonlar ile tüm 27 parametre JSON olarak dışa/içe aktarılabilir:

- **Dışa Aktar:** `trading-config-YYYY-MM-DD.json` indirir (tek tıkla yedekleme)
- **İçe Aktar:** Dosya seç → parse → **diff preview dialog** açılır → 3 kategori gösterir:
  - **Değişecek** — `key: old → new` (yeşil)
  - **Geçersiz - atlanacak** — tip/bound ihlali (kırmızı)
  - **Bilinmeyen - yoksayıldı** — 27 alan listesinde olmayan (sarı)
- Kullanıcı onaylayınca sadece değişen alanlar PATCH edilir (hot reload tetiklenir)

**Preset yapısı** (`config-presets/` klasörü, git'te versiyonlanır):

```
config-presets/
├── README.md                                # kullanım rehberi
├── baseline.json                            # adlandırılmış preset (stabil)
└── snapshots/
    └── 2026-04-07-initial-tightening.json   # tarih damgalı yedek
```

- **Preset** (kök klasör): Adlandırılmış stratejiler — `baseline`, (ileride) `conservative`, `aggressive`, `sideways`
- **Snapshot** (`snapshots/`): Belirli bir andaki yedek — `{YYYY-MM-DD}-{kısa-not}.json` formatında, sıralanabilir

Yeni preset eklemek için: dashboard'dan yeni değerleri gir → dışa aktar → dosyayı `config-presets/` altına kopyala → commit. Önemli değişiklik öncesi snapshot almak için: önceki config'i dışa aktar → `config-presets/snapshots/` altına tarihli isimle kopyala → commit.

## Sandbox Modu

Sandbox modda gerçek piyasa verisi kullanılır ama emirler Binance'e gönderilmez:
- **Veri kaynağı:** Mainnet Binance API (public, key gerektirmez)
- **Emir yürütme:** Lokal simülasyon (SandboxExecutor, Lua atomik wallet)
- **Bakiye:** Redis-backed sanal cüzdan, dashboard'dan USDT yüklenir
- **Screener:** Tam aktif (dinamik 20 coin: 5 hacim top + 15 skor bazlı)
- **Live'a geçiş:** `APP_MODE=live` yapılması yeterli

## Screener Sistemi

2 katmanlı piyasa tarama + breakout potansiyeli skorlaması, her 5 dakikada çalışır:

**Katman 1 — Hızlı Tarama:** Binance ticker/24hr → 300+ USDT çifti filtrele (ASCII-only) → top 40 aday
**Katman 2 — Derin Analiz:** 200 mum batch fetch + full TA pipeline → skorla → en iyi 15

**Breakout Potansiyeli Skoru (0-1):**
- BB squeeze (sıkışma): +0.4
- Volume intensity (kademeli hacim yoğunluğu): +0.3
- RSI momentum buildup (30-55 arası yükselen RSI): +0.3
- Sıralama: confidence × (1 - breakout_weight) + breakout_score × breakout_weight

Hacim top 5 (BTC, ETH vb.) momentum filtresinden bağımsız, her zaman aktif.
Açık pozisyonu olan coin desired kümesine dahil edilir (asla watchlist'ten çıkarılmaz).

## Trading Stratejisi: EMA Crossover Multi-Indicator

5 bileşen, ağırlıklı skor (confidence capped [0, 1], config'den okunur):
- EMA Crossover (9/21): %25 (crossover: ±1.0, trend: ±0.6)
- MACD (12/26/9): %25 (crossover: ±1.0, histogram: ±0.5)
- RSI (14): %20 (extreme: ±1.0, partial: ±0.5)
- Bollinger Bands (20,2): %15 + **BB squeeze amplifikasyonu** (sıkışma + kırılım = 0.8 skor)
- Volume: %15 + **kademeli yoğunluk** (volume_intensity 0-1, binary spike yerine)

**SL/TP:** ATR bazlı, config'den okunur (`calculate_atr_stops()` ile min/max SL sınırlaması + min TP garantisi)

Sinyal eşiği: `abs(toplam_skor) >= 0.40`
NaN-safe indikatörler, strict crossover karşılaştırma.
CryptoPanic sentiment devre dışı (API ücretsiz plan kaldırıldı).

### Pozisyon Farkındalıklı Sinyal Üretimi

```
Mum kapanışı →
├── Açık pozisyon YOK → strateji çalıştır → sadece BUY sinyali (SELL filtrelenir)
└── Açık pozisyon VAR → exit kontrol et → koşullar uygunsa SELL sinyali üret
```

### Exit (Çıkış) Stratejisi — Kâr Odaklı

1. **Stop-loss hit** → her zaman çık
2. **Take-profit hit** → her zaman çık
3. **Trailing stop** → kâr ≥ %2 ve zirveden %2 düştüyse çık (kâr koruma)
4. **RSI > 80 + %1 kâr** → aşırı alımda kârı koru
5. **EMA ters crossover + %2 kâr** → trend dönüyor, kârı koru
6. **EMA+MACD ters + %3 zarar** → trend tamamen döndü, zararı kes
7. **Zaman bazlı çıkış** → 4 saat geçti ve kâr < %0.5 ise çık (ölü pozisyon temizleme)
8. **EMA ters crossover + kâr yok** → ÇIKMA (erken satış engeli)

## Execution Pipeline

### Sinyal Akışı
```
Signal Generator → signal:new → Telegram + Dashboard
    ↓ (semi_auto: kullanıcı onaylar / full_auto: otomatik onay)
signal:approved → Execution Worker
    ↓ (idempotency check → entry/exit ayrımı)
    ├── Entry: Risk kontrolü → pozisyon boyutlama → emir → trade oluştur (SL/TP ile)
    └── Exit: Açık trade'den miktar al → emir → trade kapat (PnL hesapla)
    ↓
order:executed → WebSocket → Dashboard güncelleme
```

### Güvenlik Mekanizmaları
- **Atomik sinyal onayı:** Optimistic locking (expected_status WHERE koşulu)
- **İdempotent işleme:** Sinyal durumu kontrol (EXECUTED/REJECTED → atla)
- **Atomik wallet:** Redis Lua script (race condition korumalı)
- **Wallet rollback:** Sandbox executor hata durumunda geri yükleme
- **Risk manager lock:** asyncio.Lock ile concurrent erişim koruması
- **Startup recovery:** Bot başlangıcında orphan approved sinyalleri replay
- **Çift tetiklenme koruması:** Exit'te bakiye kontrolü → bakiye yoksa trade'i otomatik kapat
- **Exit sinyal deduplikasyonu:** Aynı trade için 60 saniye içinde çift exit sinyali engellenir (multi-interval koruma)
- **Coin bazlı cooldown:** Farklı coinler birbirini engellemez, exit emirleri cooldown tetiklemez
- **Audit trail:** Her adımda audit log (approve, order_created, order_filled, trade_opened, execution_failed)

### Trading Modları
- **semi_auto:** Sinyal → Telegram butonları (Onayla/Reddet) → kullanıcı karar verir
- **full_auto:** Sinyal → otomatik onaylanır → hemen emir → Telegram'a "⚡ Otomatik onaylandı" bildirimi
- Risk reddi durumunda: Telegram'a "⚠️ Sinyal Reddedildi — sebep" bildirimi

## Telegram Komutları

| Komut | Açıklama |
|-------|----------|
| `/start` | Bot başlatma mesajı |
| `/help` | Komut listesi |
| `/status` | Bot durumu (mod, trading modu, çiftler, risk parametreleri) |
| `/balance` | Portföy bakiyesi |
| `/signals` | Son 5 sinyal |
| `/trades` | Açık + son kapanan trade'ler |
| `/pnl` | Kâr/zarar özeti (win rate, toplam PnL, ort. kazanç/kayıp) |
| `/pause` | Sinyal üretimini duraklat |
| `/resume` | Sinyal üretimini devam ettir |

## Veri Akışı

```
[Her 5dk] Screener → Binance ticker/24hr → Filtre → Deep TA → Pair Manager
    ↓ (top 5 hacim + top 15 skor + korunan coinler = ~20 aktif coin)
Binance REST API → REST Poller (periyodik) → PostgreSQL (candles)
    ↓ (mum kapanışında)
Redis "candle:closed" → Signal Generator → Pozisyon kontrolü
    ↓ (pozisyon yoksa BUY, varsa exit kontrolü)
    ↓ (confidence >= 0.40)
Redis "signal:new" → Dashboard + Telegram bildirim
    ↓ (semi_auto: onaylandığında / full_auto: otomatik)
Redis "signal:approved" → Execution Worker → Risk Manager → Order Manager
    ↓ (sandbox: lokal simülasyon / live: Binance API)
Redis "order:executed" → WebSocket bridge → Dashboard (anlık güncelleme)
    ↓ (30sn) Sinyal expire döngüsü → süresi dolan pending sinyalleri expire et
```

## Test

```bash
pytest tests/unit/ -v          # 128+ test
pytest tests/unit/ -v --cov    # Coverage ile
```

## Git Kuralları

- Commit mesajları `git commit -m "mesaj"` ile atılır — `cat <<EOF` veya HEREDOC kullanılmaz
- Conventional Commits formatı: `feat(scope): açıklama`, `fix(scope): açıklama`, `chore(scope): açıklama`
- Commit mesajları Türkçe yazılır (ç, ş, ı, ğ, ö, ü kullanılır)

## Deployment Notları

Proje, herhangi bir Docker Compose destekli ortamda (lokal makine, VPS, cloud VM, kubernetes pod) çalıştırılabilir. Aşağıdaki notlar tipik bir self-hosted Linux sunucu kurulumu içindir.

- PostgreSQL ve Redis kendi container'larında (izole)
- REST polling kullanılıyor (mainnet public API)
- Structured JSON logging (Loki / başka log toplayıcılarla uyumlu)
- Prometheus `/metrics/` endpoint'i mevcut
- Health check: `GET /health`
- Public erişim için bir reverse proxy (nginx, Caddy, Nginx Proxy Manager, Traefik vb.) ile koymanız önerilir:
  - `/api/*` → `trading-bot:8000`
  - `/ws` → `trading-bot:8000` (WebSocket upgrade'i destekleyen)
  - `/` → `trading-dashboard:3000`
- **Önerilen güvenlik katmanı:** Reverse proxy önüne Cloudflare Access, Tailscale veya basic auth gibi bir doğrulama katmanı ekleyin.

### CI/CD (Opsiyonel)

Repo, push edildiğinde container image'ları GHCR'a publish eden bir GitHub Actions workflow'u içerir (`.github/workflows/docker-publish.yml`). Image isimleri repo sahibinin GitHub kullanıcı adıyla otomatik şekillenir:

```
ghcr.io/<your-github-username>/finance-app-bot:latest
ghcr.io/<your-github-username>/finance-app-dashboard:latest
```

Kendi fork'unuzda bu workflow değişiklik gerektirmeden çalışır — sadece repo `Settings → Actions → Workflow permissions` altında "Read and write permissions" verilmiş olmalı.

**docker-compose.yml** hem `image:` hem `build:` içerir; production'da `image:` (pull) lokal dev'de `build:` (build) tercih edilir. `.env` içindeki `DOCKER_REGISTRY`, `DOCKER_OWNER`, `DOCKER_IMAGE_TAG` değişkenleriyle hangi image'ın çekileceği yapılandırılır.

Otomatik image güncellemesi için [Watchtower](https://containrrr.dev/watchtower/) eklenebilir. Private GHCR image'ları için Watchtower'a `~/.docker/config.json` üzerinden GitHub PAT (read:packages izinli) tanıtılması gerekir; alternatif olarak image'ı public yapabilirsiniz (kaynak kod private kalsa da).

## Önemli Notlar

- DB kolonları `TIMESTAMP WITHOUT TIME ZONE` — her yerde naive UTC datetime kullanılmalı (`.replace(tzinfo=None)`)
- Sinyal status geçişleri: pending → approved → executed VEYA pending → rejected/expired, weak (eşik altı)
- Exit sinyalleri `exit_` prefix'li strateji adıyla kaydedilir (exit_stop_loss, exit_take_profit, exit_trailing_stop, exit_rsi_overbought_profit, exit_profit_protect, exit_stop_trend_loss, exit_time_exit)
- Trade modeli SL/TP içerir — evaluate_exit bu değerleri trade'den okur
- CryptoPanic API ücretsiz plan Nisan 2026'da kaldırıldı — sentiment devre dışı

## Bilinen Sınırlamalar

- **Trading pair persistence yok:** `POST /config/pairs` değişiklikleri in-memory; container restart'ta `.env`'deki listeye döner. (27 tunable parametre DB'de, persistent — sadece pair listesi değil.)
- **Portfolio unrealized PnL:** `balance_tracker.py`'de hardcoded `Decimal("0")` — gerçek hesaplama dashboard endpoint'inde yapılıyor
- **Partial fill takibi eksik:** İlk fill sonrası kalan miktar izlenmiyor (fill_monitor var ama race condition riski)
- **Backtest SL/TP tespiti:** `backtest_runner.py`'de basitleştirilmiş — mum içi SL/TP hit tespiti eksik
- **Bot pause state:** Telegram `/pause` komutu global değişkende tutuluyor, Redis'te değil — restart'ta sıfırlanır
- **Exit sinyal deduplication:** Monotonic time ile 60s pencere, restart'ta sıfırlanır — çift exit riski
- **Integration/E2E test yok:** Sadece 105 unit test mevcut; DB, API, Telegram testleri eksik
