# Trading Config Presetleri

Dashboard "Ayarlar" sayfasındaki **JSON İçe Aktar** butonuyla yüklenebilen hazır config dosyaları.

## Yapı

```
config-presets/
├── README.md           # bu dosya
├── baseline.json       # versiyon kontrole giren başlangıç preseti
└── snapshots/          # senin lokal yedeklerin (.gitignore — paylaşılmaz)
    └── {YYYY-MM-DD}-{kısa-not}.json
```

- **Presetler** (kök klasör) — adlandırılmış stratejiler, projeyle birlikte paylaşılır, herkes kullanabilir
- **Snapshotlar** (`snapshots/` altı) — kendi tunings'in için yerel yedekler, `.gitignore` ile dışarıda tutulur ki kişisel parametrelerin başkalarının repo'sunu kirletmesin

## Mevcut Presetler

### `baseline.json`

İlk başarılı tuning. Sıkılaştırılmış ilk üretim ayarı:

| Parametre | Değer | Amaç |
|-----------|-------|------|
| `trading_mode` | `full_auto` | Onaysız çalışma |
| `risk_per_trade_pct` | 0.02 (%2) | Trade başına düşük risk |
| `max_concurrent_positions` | 2 | Eşzamanlı pozisyon limiti |
| `min_signal_confidence` | 0.55 | Seçici sinyal eşiği |
| `min_sl_pct` | 0.015 (%1.5) | Gürültüye karşı geniş SL |
| `atr_sl_multiplier` | 2.0 | ATR bazlı geniş SL |
| `atr_tp_multiplier` | 3.5 | R:R ~1.75 |
| `screener_min_volume_usdt` | 2,000,000 | Mikro-cap coin filtresi |
| `cooldown_seconds` | 600 | 10 dakika trade arası bekleme |

**Ne zaman kullan:** Sorun olduğunda veya farklı bir preset denedikten sonra geri dönmek istediğinde.

## Kullanım

### Preset yüklemek

1. Dashboard → **Ayarlar** sayfası
2. Sağ üstte **JSON İçe Aktar** butonu
3. İlgili preset dosyasını seç (örn. `config-presets/baseline.json`)
4. Açılan diff dialog'unda değişikliklere bak
5. **N Değişikliği Uygula** tıkla — hot reload ile anında etkili olur

### Snapshot almak

Önemli bir değişiklik yapmadan önce mevcut config'i yedekle:

1. Dashboard → **Ayarlar** → **JSON Dışa Aktar**
2. İndirilen dosyayı `config-presets/snapshots/` altına kopyala:
   ```bash
   cp ~/Downloads/trading-config-YYYY-MM-DD.json \
      config-presets/snapshots/YYYY-MM-DD-<kısa-not>.json
   git add config-presets/snapshots/
   git commit -m "chore(config): <kısa-not> snapshot'ı eklendi"
   ```

### Dosya adı kuralı

- **Preset:** kısa, semantik isim — `baseline.json`, `conservative.json`, `aggressive.json`
- **Snapshot:** `YYYY-MM-DD-<kısa-not>.json` — sıralanabilir, aranabilir

## İleride Eklenecek Presetler (Öneri)

- **`conservative.json`** — Çok daha düşük risk: trade başına %1, max 1 pozisyon, confidence 0.65+. Volatil piyasada veya test dönemlerinde.
- **`aggressive.json`** — Daha fazla işlem, daha geniş ağ: confidence 0.45, max 3 pozisyon, ATR çarpanları küçük. Trend piyasasında.
- **`sideways.json`** — Yatay piyasa için: `max_hold_hours` düşük, trailing stop sıkı, screener değişim eşiği yüksek.

Yeni preset ekleme kararı için en az 24-48 saatlik trade verisi analizi yapılmalı.
