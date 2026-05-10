"""EMA Crossover Multi-Indicator Stratejisi.

5 bileşenli ağırlıklı skor sistemi (config'den okunur):
- EMA Crossover (9/21):   %25 ağırlık
- MACD (12/26/9):         %25 ağırlık
- RSI (14):               %20 ağırlık
- Bollinger Bands (20,2): %15 ağırlık
- Volume Spike:           %15 ağırlık

Sinyal eşiği: abs(toplam_skor) >= min_signal_confidence (varsayılan 0.40)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.analysis.ta_engine import TAResult
from src.config import settings
from src.constants import Side
from src.core.logging import get_logger
from src.risk.stop_loss import calculate_atr_stops
from src.schemas.signal import SignalCreate
from src.strategy.base_strategy import BaseStrategy, ExitSignal

logger = get_logger("ema_crossover")


class EMACrossoverStrategy(BaseStrategy):
    """EMA Crossover + RSI + Bollinger + Volume + Sentiment stratejisi."""

    @property
    def name(self) -> str:
        return "ema_crossover_v1"

    def evaluate(
        self,
        ta_result: TAResult,
        sentiment_score: float | None = None,
    ) -> SignalCreate | None:
        """Tüm indikatörleri değerlendir, skor hesapla, sinyal üret."""

        if not ta_result.ema.get("ema_fast"):
            return None  # Yeterli veri yok

        # Ağırlıkları config'den oku
        w_ema = settings.strategy_w_ema
        w_macd = settings.strategy_w_macd
        w_rsi = settings.strategy_w_rsi
        w_bb = settings.strategy_w_bb
        w_volume = settings.strategy_w_volume

        components: dict[str, float] = {}

        # Tüm bileşen skorlarını bağımsız hesapla
        ema_score = self._score_ema(ta_result.ema)
        components["ema"] = ema_score

        macd_score = self._score_macd(ta_result.macd)
        components["macd"] = macd_score

        rsi_score = self._score_rsi(ta_result.rsi)
        components["rsi"] = rsi_score

        bb_score = self._score_bollinger(ta_result.bollinger)
        components["bb"] = bb_score

        # Volume hariç yön skoru (volume, tam yön bilgisine göre amplify edecek)
        directional_score = (
            ema_score * w_ema
            + macd_score * w_macd
            + rsi_score * w_rsi
            + bb_score * w_bb
        )

        # Volume: yön skoru yeterince güçlüyse amplify et
        vol_score = self._score_volume(ta_result.volume, directional_score)
        components["volume"] = vol_score

        score = directional_score + vol_score * w_volume
        confidence = min(1.0, abs(score))

        logger.info(
            "strategy_evaluation",
            symbol=ta_result.symbol,
            interval=ta_result.interval,
            score=round(score, 4),
            confidence=round(confidence, 4),
            threshold=settings.min_signal_confidence,
            components=components,
        )

        # Çok düşük güvenli sinyalleri filtrele (gürültü)
        if confidence < 0.1:
            return None

        # Sinyal yönü
        side = Side.BUY if score > 0 else Side.SELL

        # Stop-loss ve take-profit (ATR tabanlı, config'den)
        entry_price = Decimal(str(ta_result.current_price))
        atr = ta_result.atr.get("atr")

        if atr and atr > 0:
            stops = calculate_atr_stops(
                entry_price=entry_price,
                atr=atr,
                side=side,
                sl_multiplier=settings.atr_sl_multiplier,
                tp_multiplier=settings.atr_tp_multiplier,
                min_sl_pct=settings.min_sl_pct,
                max_sl_pct=settings.max_sl_pct,
            )
            stop_loss = stops["stop_loss"]
            take_profit = stops["take_profit"]

            # Min TP garantisi — SL mesafesine orantılı (R:R en az 1.5x)
            # Eski sabit %3 garanti, tight SL'lerde R:R'ı 5:1'e çıkarıp
            # TP'nin gerçekleşme olasılığını neredeyse sıfırlıyordu.
            if side == Side.BUY:
                sl_distance = entry_price - stop_loss
                min_tp_from_rr = entry_price + (sl_distance * Decimal("1.5"))
                min_tp_absolute = entry_price * (Decimal("1") + Decimal(str(settings.min_tp_pct)))
                # İkisinden küçüğü — R:R orantısını koruyup absürt uzak TP'yi engelle
                take_profit = max(take_profit, min(min_tp_from_rr, min_tp_absolute))
            else:
                sl_distance = stop_loss - entry_price
                min_tp_from_rr = entry_price - (sl_distance * Decimal("1.5"))
                min_tp_absolute = entry_price * (Decimal("1") - Decimal(str(settings.min_tp_pct)))
                take_profit = min(take_profit, max(min_tp_from_rr, min_tp_absolute))
        else:
            # ATR yoksa yüzdesel fallback
            pct = Decimal("0.02")  # %2
            if side == Side.BUY:
                stop_loss = entry_price * (1 - pct)
                take_profit = entry_price * (1 + pct * 2)
            else:
                stop_loss = entry_price * (1 + pct)
                take_profit = entry_price * (1 - pct * 2)

        return SignalCreate(
            symbol=ta_result.symbol,
            side=side,
            strategy=self.name,
            confidence=Decimal(str(round(confidence, 4))),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            indicators=ta_result.to_dict(),
            sentiment_score=Decimal(str(round(sentiment_score or 0, 4))),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(seconds=settings.signal_approval_timeout_seconds),
        )

    def _score_ema(self, ema: dict) -> float:
        """EMA skor: crossover +1/-1, trend devam ±ema_trend_score."""
        crossover = ema.get("crossover", "none")
        if crossover == "bullish":
            return 1.0
        elif crossover == "bearish":
            return -1.0

        # Crossover yoksa trend yönü
        trend_score = settings.ema_trend_score
        trend = ema.get("trend", "neutral")
        if trend == "up":
            return trend_score
        elif trend == "down":
            return -trend_score
        return 0.0

    def _score_macd(self, macd: dict) -> float:
        """MACD skor: crossover +1/-1, histogram yönü ±0.5."""
        crossover = macd.get("macd_crossover", "none")
        if crossover == "bullish":
            return 1.0
        elif crossover == "bearish":
            return -1.0

        # Crossover yoksa histogram yönü
        histogram = macd.get("macd_histogram")
        if histogram is not None and histogram > 0:
            return 0.5
        elif histogram is not None and histogram < 0:
            return -0.5
        return 0.0

    def _score_rsi(self, rsi: dict) -> float:
        """RSI skor: oversold +1, overbought -1, geçiş bölgeleri kısmi skor."""
        rsi_val = rsi.get("rsi")
        if rsi_val is None:
            return 0.0

        if rsi_val <= 30:
            return 1.0  # Güçlü oversold
        elif rsi_val <= 40:
            return 0.5  # Hafif oversold
        elif rsi_val >= 70:
            return -1.0  # Güçlü overbought
        elif rsi_val >= 60:
            return -0.5  # Hafif overbought
        return 0.0

    def _score_bollinger(self, bb: dict) -> float:
        """Bollinger skor: band pozisyonu + squeeze breakout tespiti."""
        position = bb.get("bb_position", "within")
        price_vs_bb = bb.get("price_vs_bb", 0.5)
        bb_squeeze = bb.get("bb_squeeze", False)

        # Temel skor: band pozisyonuna göre
        if position == "below_lower":
            base_score = 1.0  # Potansiyel bounce
        elif position == "above_upper":
            base_score = -1.0  # Potansiyel reversal
        elif price_vs_bb < 0.3:
            base_score = 0.5
        elif price_vs_bb > 0.7:
            base_score = -0.5
        else:
            base_score = 0.0

        # Squeeze amplifikasyonu: sıkışma varsa ve fiyat band kenarına yakınsa
        # breakout potansiyeli yüksek → skoru güçlendir
        if bb_squeeze:
            if price_vs_bb >= 0.85:
                # Squeeze + üst banda yakın → güçlü yukarı kırılım potansiyeli
                return max(base_score, 0.8)
            elif price_vs_bb <= 0.15:
                # Squeeze + alt banda yakın → güçlü yukarı bounce potansiyeli
                return max(base_score, 0.8)
            elif base_score != 0.0:
                # Squeeze + yön sinyali varsa amplify et
                return base_score * 1.3 if abs(base_score * 1.3) <= 1.0 else base_score

        return base_score

    def _score_volume(self, volume: dict, directional_score: float) -> float:
        """Volume skor: kademeli yoğunluk ile orantılı amplify et.

        volume_intensity (0-1) kullanarak kademeli amplification.
        Zayıf sinyalleri (|directional_score| < 0.15) amplify etmez.
        """
        intensity = volume.get("volume_intensity", 0.0)
        min_intensity = settings.volume_min_intensity

        # Yoğunluk eşiğinin altındaysa amplify etme
        if intensity < min_intensity:
            return 0.0

        abs_dir = abs(directional_score)

        # Çok zayıf yön sinyali — volume amplify etmemeli
        if abs_dir < 0.15:
            return 0.0

        # Kademeli amplification: yön gücü × volume yoğunluğu
        dir_magnitude = min(1.0, abs_dir / 0.5)
        magnitude = dir_magnitude * intensity
        sign = 1.0 if directional_score > 0 else -1.0
        return sign * magnitude

    def evaluate_exit(
        self,
        ta_result: TAResult,
        open_trade: object,
    ) -> ExitSignal | None:
        """Açık pozisyon için çıkış koşullarını değerlendir.

        Çıkış koşulları (öncelik sırasıyla):
        1. Stop-loss hit — fiyat stop seviyesine ulaştı (her zaman çık)
        2. Take-profit hit — fiyat hedef seviyesine ulaştı (her zaman çık)
        3. Trailing stop — kâr eşiğinin üstünde, zirveden % düşüş varsa çık
        4. RSI aşırı bölge + kâr — RSI >80 ve kârdaysa çık (aşırı alım)
        5. Kâr koruma — %2+ kârdaysa ve trend dönüyorsa çık
        6. Zarar kesme — %3+ zarardaysa ve trend kötüyse çık
        7. Zaman bazlı çıkış — X saat geçti ve kâr yetersizse çık
        """
        current_price = ta_result.current_price
        if current_price is None:
            return None

        symbol = getattr(open_trade, "symbol", ta_result.symbol)
        side = getattr(open_trade, "side", "BUY")
        stop_loss = getattr(open_trade, "stop_loss", None)
        take_profit = getattr(open_trade, "take_profit", None)
        entry_price = getattr(open_trade, "entry_price", None)

        exit_side = Side.SELL if side == Side.BUY else Side.BUY

        # Mevcut kâr/zarar yüzdesi
        pnl_pct = 0.0
        if entry_price:
            ep = float(entry_price)
            if side == Side.BUY:
                pnl_pct = ((current_price - ep) / ep) * 100
            else:
                pnl_pct = ((ep - current_price) / ep) * 100

        # 1) Stop-loss hit — her zaman çık
        if stop_loss:
            sl = float(stop_loss)
            if side == Side.BUY and current_price <= sl:
                return ExitSignal(symbol=symbol, side=exit_side, reason="stop_loss", confidence=1.0)
            if side == Side.SELL and current_price >= sl:
                return ExitSignal(symbol=symbol, side=exit_side, reason="stop_loss", confidence=1.0)

        # 2) Take-profit hit — her zaman çık
        if take_profit:
            tp = float(take_profit)
            if side == Side.BUY and current_price >= tp:
                return ExitSignal(symbol=symbol, side=exit_side, reason="take_profit", confidence=1.0)
            if side == Side.SELL and current_price <= tp:
                return ExitSignal(symbol=symbol, side=exit_side, reason="take_profit", confidence=1.0)

        # 3) Trailing stop — kâr belli eşiğin üstünde ve zirveden düşüş varsa
        trail_activation = settings.trailing_stop_activation_pct
        trail_pct = settings.trailing_stop_trail_pct
        recent_high = ta_result.recent_high

        if pnl_pct >= trail_activation and recent_high is not None:
            if side == Side.BUY:
                trail_price = recent_high * (1 - trail_pct / 100)
                if current_price <= trail_price:
                    return ExitSignal(symbol=symbol, side=exit_side, reason="trailing_stop", confidence=0.95)
            else:
                recent_low = ta_result.recent_low
                if recent_low is not None:
                    trail_price = recent_low * (1 + trail_pct / 100)
                    if current_price >= trail_price:
                        return ExitSignal(symbol=symbol, side=exit_side, reason="trailing_stop", confidence=0.95)

        # 4) RSI aşırı bölge + kâr — aşırı alımda kârı koru
        rsi = ta_result.rsi
        rsi_value = rsi.get("rsi")
        if rsi_value is not None:
            if side == Side.BUY and rsi_value > 80 and pnl_pct > 1.0:
                return ExitSignal(symbol=symbol, side=exit_side, reason="rsi_overbought_profit", confidence=0.9)
            if side == Side.SELL and rsi_value < 20 and pnl_pct > 1.0:
                return ExitSignal(symbol=symbol, side=exit_side, reason="rsi_oversold_profit", confidence=0.9)

        # 5) Kâr koruma — %2+ kârdaysa ve EMA ters crossover oluyorsa, kârı koru
        ema = ta_result.ema
        crossover = ema.get("crossover", "none")
        if pnl_pct >= 2.0:
            if side == Side.BUY and crossover == "bearish":
                return ExitSignal(symbol=symbol, side=exit_side, reason="profit_protect", confidence=0.85)
            if side == Side.SELL and crossover == "bullish":
                return ExitSignal(symbol=symbol, side=exit_side, reason="profit_protect", confidence=0.85)

        # 6) Zarar kesme — %3+ zarardaysa ve tüm göstergeler ters yöndeyse çık
        if pnl_pct <= -3.0:
            macd = ta_result.macd
            macd_cross = macd.get("macd_crossover", "none")
            if side == Side.BUY and crossover == "bearish" and macd_cross == "bearish":
                return ExitSignal(symbol=symbol, side=exit_side, reason="stop_trend_loss", confidence=0.9)
            if side == Side.SELL and crossover == "bullish" and macd_cross == "bullish":
                return ExitSignal(symbol=symbol, side=exit_side, reason="stop_trend_loss", confidence=0.9)

        # 7) Zaman bazlı çıkış — pozisyon çok uzun süredir açık ve kâr yetersiz
        opened_at = getattr(open_trade, "opened_at", None)
        if opened_at is not None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            # opened_at naive UTC olmalı
            if hasattr(opened_at, "replace"):
                opened_at_naive = opened_at.replace(tzinfo=None)
            else:
                opened_at_naive = opened_at
            hold_hours = (now - opened_at_naive).total_seconds() / 3600
            if hold_hours >= settings.max_hold_hours and pnl_pct < settings.time_exit_min_profit_pct:
                return ExitSignal(symbol=symbol, side=exit_side, reason="time_exit", confidence=0.7)

        return None
