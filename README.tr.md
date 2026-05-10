# Finance App — Kripto Trading Botu

> 🇬🇧 **For English: [README.md](README.md)**

Binance üzerinde otonom çalışan, kendi sunucunda barındırılabilen (self-hosted) bir kripto para trading botu. Next.js admin paneli, Telegram entegrasyonu, dinamik piyasa tarayıcısı (screener) ve risksiz test için sandbox modu yerleşik olarak gelir.

Kendi API anahtarlarını, kendi risk parametrelerini ve kendi takip listeni gir — her şey environment variable ve runtime'da düzenlenebilir bir config tablosu üzerinden çalışır.

---

## ⚠️ Sorumluluk Reddi — Önce Bunu Oku

**Bu yazılım olduğu gibi (as-is), yalnızca eğitim ve araştırma amacıyla sunulmaktadır. Kullanım riski tamamen size aittir.**

- 🚨 **Kripto para işlemleri son derece risklidir.** Tüm yatırımınızı kaybedebilirsiniz. Geçmiş performans — backtest sonuçları, paper-trading verileri, başkasının ekran görüntüleri — gelecekteki sonuçların **garantisi değildir**.
- 🤖 **Bu bot finansal tavsiye değildir.** Sizin seçtiğiniz bir stratejiyi otomatize eden bir araçtır. Botun ne yaptığını, neden yaptığını ve sizin durumunuza uygun olup olmadığını anlamak sizin sorumluluğunuzdadır.
- 🔬 **Gerçek parayla işlem yapmadan önce, uzun bir süre `sandbox` veya `testnet` modunda test edin.** Sandbox'ta birkaç günlük yeşil PnL, botun canlıya alınmaya hazır olduğu anlamına gelmez.
- 🐛 **Yazılımda hata olabilir.** Trading botları karmaşıktır ve borsa API'leri beklenmedik şekilde davranabilir (kısmi fill, rate limit, ağ kopmaları, borsa duruşları, flash crash). Yazılımın yazarları ve katkıda bulunanları, kullanımdan doğan herhangi bir **finansal kayıptan, kaçırılmış kârdan, hesap kapanmasından, regülasyon sorunundan, vergiden veya diğer zararlardan sorumlu değildir**.
- 🌍 **Bulunduğunuz ülkenin yasalarını kontrol edin.** Algoritmik kripto işlemleri yaşadığınız yerde regüle, kısıtlı veya farklı şekilde vergilendirilmiş olabilir. Geçerli tüm yasalara uymak sizin sorumluluğunuzdadır.
- 🔐 **API anahtarlarınızı koruyun.** IP allowlist kullanın, çekim (withdrawal) iznini kapatın ve `.env` dosyanızı asla commit etmeyin. API anahtarlarınıza sahip olan kişi, paranızı taşıyabilir biri demektir.

Bu yazılımı çalıştırarak yukarıdaki riskleri anladığınızı ve sonuçlarına ilişkin tüm sorumluluğu kabul ettiğinizi beyan etmiş olursunuz.

---

## Özellikler

- **Birden fazla mod** — `sandbox` (gerçek piyasa verisi, sanal cüzdan), `testnet` (Binance testnet), `live` (gerçek para), `backtest`
- **Teknik analiz pipeline'ı** — EMA crossover, RSI, MACD, Bollinger Bands (squeeze tespiti dahil), ATR bazlı stop'lar, hacim yoğunluğu skoru
- **Dinamik piyasa tarayıcısı** — 5 dakikada bir 300+ USDT çiftini tarar, hacim + breakout potansiyeline göre ~20 aktif coin'lik bir watchlist'i dinamik olarak rotasyona sokar
- **Risk yönetimi** — trade başına risk %, maks eşzamanlı pozisyon, günlük kayıp limiti, min bakiye guardrail'i, coin bazlı cooldown, varlık tahsis tavanı
- **İki trading modu** — `semi_auto` (sinyaller Telegram veya panel üzerinden manuel onay ister) veya `full_auto` (otomatik onay)
- **Kâr odaklı çıkışlar** — stop-loss, take-profit, trailing stop, RSI-aşırı-alım-kârla, EMA-ters-dönüş-kârla, zaman bazlı çıkış
- **Admin paneli (Next.js 16)** — canlı sinyaller, emirler, trade'ler, portföy, mum grafikleri, screener sonuçları, runtime'da düzenlenebilir 27 parametreli config, JSON config dışa/içe aktarma
- **Telegram bot** — onay/red butonlu sinyal bildirimleri, `/status`, `/balance`, `/signals`, `/trades`, `/pnl`, `/pause`, `/resume`
- **Gerçek zamanlı güncelleme** — Redis pub/sub üzerinden WebSocket köprüsü, polling yok
- **Üretime hazır ops** — Prometheus metrikleri, structured JSON logging (Loki uyumlu), Sentry/GlitchTip hata izleme, JWT auth, audit log, graceful shutdown, startup recovery
- **Atomik güvenlik** — Lua-scripted Redis cüzdanı, sinyal onayında optimistic locking, idempotent execution worker

---

## Hızlı Başlangıç

### Gereksinimler

- Docker & Docker Compose
- Bir Binance hesabı (ücretsiz test için testnet, gerçek para için live) — **sandbox modu için opsiyonel**
- (İsteğe bağlı) Bildirimler için [@BotFather](https://t.me/BotFather)'dan alınmış bir Telegram bot token'ı

### 1. Repoyu klonla ve yapılandır

```bash
git clone https://github.com/<senin-fork-un>/finance-app.git
cd finance-app
cp .env.example .env
```

`.env` dosyasını aç ve **en azından** şunları doldur:

| Değişken | Ne girmeli |
|---|---|
| `POSTGRES_PASSWORD` | Güçlü, rastgele bir şifre |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` ile üret |
| `DATABASE_URL` | İçindeki şifre placeholder'ını `POSTGRES_PASSWORD` ile aynı yap |

Geri kalanın hepsi mantıklı varsayılanlarla gelir. Live veya testnet modu kullanacaksan, ilgili Binance API key/secret çiftini de doldur. Telegram bildirimleri istiyorsan `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID`'yi de set et.

### 2. Stack'i başlat

```bash
docker compose up -d --build
```

Bu komut beş container ayağa kaldırır: `trading-bot`, `trading-dashboard`, `trading-telegram`, `trading-postgres`, `trading-redis`.

### 3. Çalıştığını doğrula

```bash
curl http://localhost:8000/health
docker logs trading-bot --tail 30
```

Bot ilk kez başladığında otomatik olarak bir `admin` kullanıcısı oluşturur ve loglara rastgele bir şifre yazar. **Loglardan o şifreyi bul ve panel girişinde kullan.**

### 4. Paneli aç

**http://localhost:3003** adresine git. `admin` kullanıcı adı ve loglardaki şifre ile gir. **Ayarlar** sayfasında:

1. Admin şifresini değiştir
2. Sandbox cüzdanına bakiye yükle (Ayarlar → Sandbox Cüzdan → Yatır)
3. Risk ve strateji parametrelerini canlı olarak ayarla (restart gerekmez)

Bot artık piyasayı tarıyor, sinyal üretiyor ve `full_auto` modunda + sandbox'ta bakiyen varsa simüle trade'ler açıyor.

---

## Canlıya Geçiş (Gerçek Parayla)

> **Bir kez daha: bu risklidir. Anahtarı çevirmeden önce gerçekçi parametrelerle en az 1-2 hafta `sandbox` modunda çalıştır.**

1. [Binance API Management](https://www.binance.com/en/my/settings/api-management) sayfasından API key oluştur.
   - **Çekim (withdrawal) iznini kapat.** Bot sadece Spot Trading iznine ihtiyaç duyar.
   - Sunucunun statik IP'si için IP allowlist ekle.
2. `.env` içinde:
   ```bash
   APP_MODE=live
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
3. Küçük başla. `RISK_PER_TRADE_PCT=0.01`, `MAX_CONCURRENT_POSITIONS=1`, `MIN_BALANCE_USDT=20.0`.
4. Yeniden başlat: `docker compose up -d`. İlk 24 saat panel ve logları yakından takip et.

---

## Mimari

```
Binance REST API
       │
  REST Poller (periyodik, mum kapanışı tespiti)
       │
  PostgreSQL (mumlar, sinyaller, emirler, trade'ler)
       │
  Teknik Analiz Motoru (EMA, RSI, MACD, BB, ATR, Volume)
       │
  Sinyal Üretici  ◄──── Screener (5 dk'da bir, top ~20 coin)
       │
  Risk Yöneticisi (5 aşamalı doğrulama)
       │
  Telegram / Panel onayı  (semi_auto)  veya  Otomatik onay  (full_auto)
       │
  Order Manager  →  Binance API (live) veya Sandbox Executor (simüle)
       │
  WebSocket köprüsü → Panel (gerçek zamanlı güncelleme)
```

İç detaylar (veritabanı şeması, sinyal yaşam döngüsü, çıkış stratejisi mantığı) için: [CLAUDE.md](CLAUDE.md).

---

## Konfigürasyon

### Environment değişkenleri

Tüm ayarlar `.env` içinde. Tam yorumlu liste için [.env.example](.env.example) dosyasına bak.

### Runtime config (restart gerektirmez)

27 trading parametresi panelin **Ayarlar** sayfasından veya `PATCH /api/v1/config` ile **canlı** olarak değiştirilebilir. Değişiklikler `trading.app_config` tablosuna yazılır ve Redis pub/sub ile tüm container'lara broadcast edilir. Şunları içerir:

- **Risk:** `risk_per_trade_pct`, `max_concurrent_positions`, `daily_loss_limit_pct`, `min_balance_usdt`, `cooldown_seconds`, `max_trades_per_day`
- **Strateji:** `min_signal_confidence`, `strategy_w_ema/macd/rsi/bb/volume`, `ema_trend_score`
- **SL/TP:** `min_sl_pct`, `max_sl_pct`, `min_tp_pct`, `atr_sl_multiplier`, `atr_tp_multiplier`
- **Çıkış:** `trailing_stop_activation_pct`, `trailing_stop_trail_pct`, `max_hold_hours`, `time_exit_min_profit_pct`
- **Screener:** `screener_min_volume_usdt`, `screener_min_change_pct`, `screener_active_dynamic_pairs`, `screener_max_candidates`
- **Mod:** `trading_mode` (`semi_auto` / `full_auto`)

### Preset'ler

[`config-presets/baseline.json`](config-presets/baseline.json) panelden içe aktarabileceğin (Ayarlar → JSON İçe Aktar) ayarlanmış bir başlangıç preset'idir. Kendi snapshot'ların `config-presets/snapshots/` altında tutulur ve `.gitignore` ile dışarıda bırakılır.

---

## Strateji

Varsayılan strateji 5 bileşenli ağırlıklı bir skor (yapılandırılabilir):

| Bileşen | Varsayılan Ağırlık | Sinyal |
|---|---|---|
| EMA Crossover (9/21) | %25 | Bullish/bearish crossover veya trend yönü |
| MACD (12/26/9) | %25 | Crossover (±1.0) veya histogram (±0.5) |
| RSI (14) | %20 | Aşırı alım / aşırı satım bölgeleri |
| Bollinger Bands (20, 2) | %15 | Bant ihlali + squeeze amplifikasyonu |
| Volume | %15 | Kademeli yoğunluk (binary değil 0-1) |

Sinyal `|toplam_skor| >= min_signal_confidence` (varsayılan 0.40) olduğunda tetiklenir. Stop'lar ATR × çarpan ile, min/max % sınırları içinde belirlenir.

**Çıkışlar** kâr odaklıdır: SL/TP her zaman tetiklenir, ama trend dönüş indikatörleri ancak pozisyon kârdaysa (veya gerçek bir dönüşü teyit edecek kadar zararda ise) çıkışı tetikler. Tam karar ağacı için: [CLAUDE.md](CLAUDE.md) → "Exit Stratejisi".

---

## API

Bot, `http://localhost:8000` adresinde JSON REST API'si ve `/ws` üzerinde WebSocket sunar. `/health` ve `/metrics` hariç tüm `/api/v1/*` endpoint'leri, `POST /api/v1/auth/login` ile alınmış bir JWT gerektirir.

Önemli endpoint'ler:

| Method | Path | Açıklama |
|---|---|---|
| `POST` | `/api/v1/auth/login` | JWT token al |
| `GET` | `/api/v1/dashboard/summary` | Panel özeti |
| `GET` | `/api/v1/signals` | Sayfalanmış sinyaller |
| `POST` | `/api/v1/signals/{id}/approve` | Bekleyen sinyali onayla |
| `GET` | `/api/v1/trades` | Sayfalanmış trade'ler |
| `GET` | `/api/v1/trades/stats` | Win rate, toplam PnL vb. |
| `GET` | `/api/v1/config` | Mevcut trading config |
| `PATCH` | `/api/v1/config` | Config güncelle (hot reload) |
| `GET` | `/api/v1/screener/results` | En son piyasa taraması |
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics/` | Prometheus metrikleri |

Tam liste: [CLAUDE.md](CLAUDE.md).

---

## Geliştirme

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Testleri çalıştır
pytest tests/unit/ -v
```

Panel:

```bash
cd dashboard
npm install
npm run dev
```

---

## Proje Yapısı

Yorumlu ağaç, veritabanı şeması notları ve geliştirici dokümantasyonu için [CLAUDE.md](CLAUDE.md) dosyasına bak.

```
src/                # Python backend (FastAPI + worker'lar)
dashboard/          # Next.js 16 admin paneli
tests/unit/         # Unit testler (~128)
alembic/            # DB migration'ları
config-presets/     # İçe aktarılabilir config JSON'ları
.github/workflows/  # CI: GHCR'a Docker image build + publish
```

---

## Katkı

PR'lara açığım. Lütfen:

- Mevcut koddaki stile uy (şemalarda Pydantic, async SQLAlchemy, log için structlog).
- Yeni strateji/risk mantığı için unit test ekle.
- Yeni hardcoded credential, domain veya kişisel bilgi sokma.
- Conventional Commits kullan (`feat:`, `fix:`, `chore:`, `docs:`, …).

---

## Lisans

[MIT](LICENSE) — istediğini yap, ama yukarıdaki sorumluluk reddi geçerli olmaya devam eder.

---

## Teşekkürler

Şu projelerin omuzlarında yükseliyor: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [pandas-ta](https://github.com/twopirllc/pandas-ta), [python-binance](https://github.com/sammchardy/python-binance), [Next.js](https://nextjs.org/), [shadcn/ui](https://ui.shadcn.com/), [TanStack Query](https://tanstack.com/query), [lightweight-charts](https://github.com/tradingview/lightweight-charts).

---

**Son hatırlatma:** burada yazılan hiçbir şey yatırım tavsiyesi değildir. Sorumlu işlem yapın.
