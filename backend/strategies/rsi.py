"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC RSI STRATEGY - النسخة الديناميكية المتكاملة
المدرسة الخامسة عشرة: مؤشر القوة النسبية الديناميكي
═══════════════════════════════════════════════════════════════════════════════

ويليس وايلدر ابتكر RSI في 1978.
الفكرة: قياس سرعة وتغير حركة السعر (الزخم).

النسخة الكلاسيكية: فترة 14، تشبع شراء 70، تشبع بيع 30.
لكن هذه ثوابت غبية في سوق متغير.

هذه النسخة ديناميكية بالكامل:
- الفترة تتكيف مع تقلب السوق (سوق سريع = فترة أقصر)
- مستويات التشبع تتغير مع نظام السوق
- في اتجاه قوي: التشبع 80/40 بدلاً من 70/30
- في نطاق: التشبع 60/40 قد يكون أفضل
- نوع RSI يتغير (RSI, Stochastic RSI, Connors RSI, Dynamic RSI)

المفاهيم المتقدمة:
1. RSI Classic
2. RSI Divergence (تباعد)
3. RSI Hidden Divergence (تباعد مخفي)
4. RSI Failure Swings (تأرجحات فشل)
5. RSI Support/Resistance
6. RSI Trendlines
7. RSI Range Shift (تحول النطاق)
8. Stochastic RSI
9. Connors RSI
10. RSI + Bollinger Bands
11. RSI + Moving Averages
12. RSI Overbought/Oversold في الاتجاه
13. RSI Reversal Signals
14. RSI Centerline Crossover
15. RSI Slope Analysis
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class DynamicRSI:
    """مؤشر RSI ديناميكي"""
    values: np.ndarray
    period: int
    overbought: float      # ديناميكي
    oversold: float        # ديناميكي
    centerline: float      # 50
    current: float
    slope: float           # الميل
    acceleration: float    # التسارع
    range_position: float  # 0-1 موقع RSI في نطاقه المعتاد
    trend_state: str       # 'bullish_range', 'bearish_range', 'neutral'


@dataclass
class RSIDivergence:
    """تباعد RSI"""
    index: int
    divergence_type: str   # 'bullish', 'bearish', 'hidden_bullish', 'hidden_bearish'
    price_peak1: float
    price_peak2: float
    rsi_peak1: float
    rsi_peak2: float
    strength: float
    confirmed: bool


@dataclass
class RSISignal:
    """إشارة RSI"""
    index: int
    signal_type: str  # 'oversold', 'overbought', 'divergence', 'failure_swing', 'centerline_cross', 'trendline_break'
    direction: str
    price_level: float
    rsi_value: float
    strength: float
    description: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: باني RSI الديناميكي                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicRSIBuilder:
    """
    يبني RSI بمعلمات ديناميكية.
    الفترة ومستويات التشبع تتكيف مع السوق.
    """
    
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """
        بناء RSI الديناميكي
        """
        # فترة مثلى
        optimal_period = self._find_optimal_period(closes, highs, lows)
        
        # حساب RSI
        rsi_values = self._calculate_rsi(closes, optimal_period)
        
        # مستويات التشبع الديناميكية
        overbought, oversold = self._find_dynamic_levels(rsi_values, closes)
        
        # RSI الحالي وميله
        current_rsi = rsi_values[-1] if len(rsi_values) > 0 else 50
        slope = self._calculate_slope(rsi_values)
        acceleration = self._calculate_acceleration(rsi_values)
        
        # موقع RSI في نطاقه
        range_position = self._calculate_range_position(rsi_values)
        
        # حالة الاتجاه
        trend_state = self._determine_trend_state(rsi_values, overbought, oversold)
        
        # Stochastic RSI
        stoch_rsi = self._calculate_stoch_rsi(rsi_values)
        
        # Connors RSI
        connors_rsi = self._calculate_connors_rsi(closes, optimal_period)
        
        rsi = DynamicRSI(
            values=rsi_values,
            period=optimal_period,
            overbought=overbought,
            oversold=oversold,
            centerline=50,
            current=current_rsi,
            slope=slope,
            acceleration=acceleration,
            range_position=range_position,
            trend_state=trend_state,
        )
        
        return {
            "rsi": rsi,
            "stoch_rsi": stoch_rsi,
            "connors_rsi": connors_rsi,
            "current": current_rsi,
            "overbought": overbought,
            "oversold": oversold,
        }
    
    def _find_optimal_period(self, closes: np.ndarray, highs: np.ndarray,
                              lows: np.ndarray) -> int:
        """
        إيجاد الفترة المثلى ديناميكياً.
        """
        if len(closes) < 30:
            return 14
        
        # قياس "سرعة" السوق
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-20:])
        
        if avg_price > 0:
            volatility = avg_range / avg_price
        else:
            volatility = 0.01
        
        # تردد تغير الاتجاه
        changes = sum(1 for i in range(2, len(closes)) 
                     if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                        (closes[i] < closes[i-1] and closes[i-1] > closes[i-2]))
        change_freq = changes / max(len(closes), 1)
        
        # سوق سريع التغير = فترة أقصر
        if volatility > 0.03 and change_freq > 0.3:
            period = 5
        elif volatility > 0.02 and change_freq > 0.2:
            period = 8
        elif volatility > 0.015:
            period = 11
        elif volatility > 0.01:
            period = 14
        elif volatility > 0.005:
            period = 21
        else:
            period = 28
        
        return period
    
    def _calculate_rsi(self, closes: np.ndarray, period: int) -> np.ndarray:
        """
        حساب RSI الكلاسيكي.
        """
        if len(closes) < period + 1:
            return np.full_like(closes, 50.0)
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi = np.full_like(closes, 50.0, dtype=float)
        
        # أول متوسط
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi[period] = 100 - (100 / (1 + rs))
        else:
            rsi[period] = 100 if avg_gain > 0 else 50
        
        # باقي القيم
        for i in range(period + 1, len(closes)):
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))
            else:
                rsi[i] = 100 if avg_gain > 0 else 50
        
        return rsi
    
    def _find_dynamic_levels(self, rsi: np.ndarray, closes: np.ndarray) -> Tuple[float, float]:
        """
        إيجاد مستويات التشبع الديناميكية.
        في اتجاه قوي: 80/40. في نطاق: 60/40.
        """
        if len(rsi) < 30:
            return 70.0, 30.0
        
        # قياس قوة الاتجاه
        trend_strength = self._measure_trend_strength(closes)
        
        # توزيع RSI في الفترة الأخيرة
        recent_rsi = rsi[-50:] if len(rsi) >= 50 else rsi
        
        # النسبة المئوية 85 و 15 كبداية
        if len(recent_rsi) >= 10:
            ob_base = np.percentile(recent_rsi, 85)
            os_base = np.percentile(recent_rsi, 15)
        else:
            ob_base = 70
            os_base = 30
        
        # تعديل حسب قوة الاتجاه
        if trend_strength > 0.5:  # اتجاه صاعد قوي
            overbought = max(ob_base, 75) + trend_strength * 5
            oversold = max(os_base, 40) + trend_strength * 3
        elif trend_strength < -0.5:  # اتجاه هابط قوي
            overbought = min(ob_base, 60) + trend_strength * 3
            oversold = min(os_base, 25) + trend_strength * 5
        else:
            overbought = ob_base
            oversold = os_base
        
        return min(85, overbought), max(15, oversold)
    
    def _measure_trend_strength(self, closes: np.ndarray) -> float:
        """قياس قوة الاتجاه"""
        if len(closes) < 20:
            return 0.0
        
        x = np.arange(20)
        y = closes[-20:]
        slope = np.polyfit(x, y, 1)[0]
        
        avg = np.mean(y)
        if avg > 0:
            normalized = slope / avg * 100
        else:
            normalized = 0
        
        return np.tanh(normalized)
    
    def _calculate_slope(self, rsi: np.ndarray) -> float:
        """ميل RSI"""
        if len(rsi) < 5:
            return 0.0
        return (rsi[-1] - rsi[-5]) / 5
    
    def _calculate_acceleration(self, rsi: np.ndarray) -> float:
        """تسارع RSI"""
        if len(rsi) < 10:
            return 0.0
        slope_now = (rsi[-1] - rsi[-5]) / 5
        slope_prev = (rsi[-6] - rsi[-10]) / 5
        return slope_now - slope_prev
    
    def _calculate_range_position(self, rsi: np.ndarray) -> float:
        """موقع RSI في نطاقه المعتاد"""
        if len(rsi) < 20:
            return 0.5
        
        recent = rsi[-20:]
        high = np.max(recent)
        low = np.min(recent)
        
        if high == low:
            return 0.5
        
        return (rsi[-1] - low) / (high - low)
    
    def _determine_trend_state(self, rsi: np.ndarray, ob: float, os: float) -> str:
        """
        تحديد حالة اتجاه RSI.
        RSI في نطاق 40-80 = اتجاه صاعد
        RSI في نطاق 20-60 = اتجاه هابط
        """
        if len(rsi) < 10:
            return 'neutral'
        
        recent = rsi[-10:]
        avg = np.mean(recent)
        
        if avg > 55 and np.min(recent) > os + 10:
            return 'bullish_range'
        elif avg < 45 and np.max(recent) < ob - 10:
            return 'bearish_range'
        else:
            return 'neutral'
    
    def _calculate_stoch_rsi(self, rsi: np.ndarray, stoch_period: int = 14) -> np.ndarray:
        """
        Stochastic RSI.
        """
        if len(rsi) < stoch_period:
            return np.full_like(rsi, 0.5)
        
        stoch_rsi = np.full_like(rsi, 0.5)
        
        for i in range(stoch_period - 1, len(rsi)):
            window = rsi[i-stoch_period+1:i+1]
            high = np.max(window)
            low = np.min(window)
            
            if high == low:
                stoch_rsi[i] = 0.5
            else:
                stoch_rsi[i] = (rsi[i] - low) / (high - low)
        
        return stoch_rsi
    
    def _calculate_connors_rsi(self, closes: np.ndarray, period: int) -> np.ndarray:
        """
        Connors RSI (يجمع RSI + Streak RSI + Percent Rank)
        """
        if len(closes) < period + 2:
            return np.full_like(closes, 50.0)
        
        # RSI الأساسي
        rsi_comp = self._calculate_rsi(closes, 3)  # فترة قصيرة
        
        # Streak (عدد الشموع المتتالية في نفس الاتجاه)
        streak = np.zeros(len(closes))
        current_streak = 0
        
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                current_streak = max(1, current_streak + 1) if current_streak > 0 else 1
            elif closes[i] < closes[i-1]:
                current_streak = min(-1, current_streak - 1) if current_streak < 0 else -1
            streak[i] = current_streak
        
        # Streak RSI
        streak_rsi_comp = self._calculate_rsi(streak, 2)
        
        # Percent Rank
        pct_rank = np.zeros(len(closes))
        for i in range(period, len(closes)):
            lookback = closes[i-period:i+1]
            pct_rank[i] = sum(1 for c in lookback if c < closes[i]) / period * 100
        
        # Connors RSI = متوسط الثلاثة
        connors = (rsi_comp + streak_rsi_comp + pct_rank) / 3
        
        return connors


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف التباعدات والإشارات                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class RSIDivergenceDetector:
    """
    يكتشف التباعدات وإشارات RSI.
    """
    
    def analyze(self, rsi: DynamicRSI, closes: np.ndarray, highs: np.ndarray,
                lows: np.ndarray) -> Dict:
        """
        اكتشاف التباعدات والإشارات
        """
        divergences = self._find_all_divergences(rsi.values, closes, highs, lows)
        hidden_divs = self._find_hidden_divergences(rsi.values, closes, highs, lows)
        failure_swings = self._detect_failure_swings(rsi, closes)
        signals = self._generate_all_signals(rsi, closes, divergences, hidden_divs, failure_swings)
        
        return {
            "divergences": divergences[-5:],
            "hidden_divergences": hidden_divs[-5:],
            "failure_swings": failure_swings[-3:],
            "signals": signals[-10:],
            "latest_signal": signals[-1] if signals else None,
        }
    
    def _find_all_divergences(self, rsi: np.ndarray, closes: np.ndarray,
                               highs: np.ndarray, lows: np.ndarray) -> List[RSIDivergence]:
        """
        اكتشاف كل التباعدات.
        """
        divergences = []
        
        if len(closes) < 20:
            return divergences
        
        # البحث عن قمم في السعر و RSI
        for i in range(10, len(closes) - 5):
            # قمة سعرية
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                # البحث عن قمة سابقة
                for j in range(i-5, max(0, i-20), -1):
                    if highs[j] > highs[j-1] and highs[j] > highs[j-2] and highs[j] > highs[j+1] and highs[j] > highs[j+2]:
                        # تباعد هابط: سعر أعلى + RSI أقل
                        if highs[i] > highs[j] and rsi[i] < rsi[j] and rsi[j] > 60:
                            divergences.append(RSIDivergence(
                                index=i,
                                divergence_type='bearish',
                                price_peak1=highs[j],
                                price_peak2=highs[i],
                                rsi_peak1=rsi[j],
                                rsi_peak2=rsi[i],
                                strength=min(1.0, (rsi[j] - rsi[i]) / 20),
                                confirmed=True,
                            ))
                        break
        
        # تباعد صاعد (قيعان)
        for i in range(10, len(closes) - 5):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                for j in range(i-5, max(0, i-20), -1):
                    if lows[j] < lows[j-1] and lows[j] < lows[j-2] and lows[j] < lows[j+1] and lows[j] < lows[j+2]:
                        if lows[i] < lows[j] and rsi[i] > rsi[j] and rsi[j] < 40:
                            divergences.append(RSIDivergence(
                                index=i,
                                divergence_type='bullish',
                                price_peak1=lows[j],
                                price_peak2=lows[i],
                                rsi_peak1=rsi[j],
                                rsi_peak2=rsi[i],
                                strength=min(1.0, (rsi[i] - rsi[j]) / 20),
                                confirmed=True,
                            ))
                        break
        
        return divergences
    
    def _find_hidden_divergences(self, rsi: np.ndarray, closes: np.ndarray,
                                   highs: np.ndarray, lows: np.ndarray) -> List[RSIDivergence]:
        """
        اكتشاف التباعدات المخفية (استمرارية).
        """
        hidden = []
        
        if len(closes) < 20:
            return hidden
        
        # Hidden Bearish: قمة سعرية أقل + RSI أعلى
        for i in range(10, len(highs) - 5):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1]:
                for j in range(i-5, max(0, i-20), -1):
                    if highs[j] > highs[j-1] and highs[j] > highs[j-2] and highs[j] > highs[j+1]:
                        if highs[i] < highs[j] and rsi[i] > rsi[j] and rsi[i] > 50:
                            hidden.append(RSIDivergence(
                                index=i,
                                divergence_type='hidden_bearish',
                                price_peak1=highs[j],
                                price_peak2=highs[i],
                                rsi_peak1=rsi[j],
                                rsi_peak2=rsi[i],
                                strength=min(1.0, (rsi[i] - rsi[j]) / 15),
                                confirmed=True,
                            ))
                        break
        
        # Hidden Bullish: قاع سعري أعلى + RSI أقل
        for i in range(10, len(lows) - 5):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1]:
                for j in range(i-5, max(0, i-20), -1):
                    if lows[j] < lows[j-1] and lows[j] < lows[j-2] and lows[j] < lows[j+1]:
                        if lows[i] > lows[j] and rsi[i] < rsi[j] and rsi[i] < 50:
                            hidden.append(RSIDivergence(
                                index=i,
                                divergence_type='hidden_bullish',
                                price_peak1=lows[j],
                                price_peak2=lows[i],
                                rsi_peak1=rsi[j],
                                rsi_peak2=rsi[i],
                                strength=min(1.0, (rsi[j] - rsi[i]) / 15),
                                confirmed=True,
                            ))
                        break
        
        return hidden
    
    def _detect_failure_swings(self, rsi: DynamicRSI, closes: np.ndarray) -> List[Dict]:
        """
        اكتشاف تأرجحات الفشل.
        """
        swings = []
        
        if len(rsi.values) < 10:
            return swings
        
        # Failure Swing صاعد: RSI يهبط تحت 30، يرتد، يصحح، يكسر القمة
        for i in range(5, len(rsi.values) - 5):
            if rsi.values[i] < rsi.oversold:
                # وجدنا تشبع بيع
                bounce_peak = 0
                for j in range(i+1, min(i+8, len(rsi.values))):
                    if rsi.values[j] > rsi.values[j-1]:
                        bounce_peak = max(bounce_peak, rsi.values[j])
                
                if bounce_peak > rsi.oversold:
                    # ارتد من التشبع
                    for k in range(j+1, min(j+8, len(rsi.values))):
                        if rsi.values[k] > bounce_peak:
                            swings.append({
                                "index": k,
                                "type": "bullish_failure_swing",
                                "strength": 0.7,
                                "description": "Failure Swing صاعد",
                            })
                            break
        
        # Failure Swing هابط
        for i in range(5, len(rsi.values) - 5):
            if rsi.values[i] > rsi.overbought:
                bounce_low = 100
                for j in range(i+1, min(i+8, len(rsi.values))):
                    if rsi.values[j] < rsi.values[j-1]:
                        bounce_low = min(bounce_low, rsi.values[j])
                
                if bounce_low < rsi.overbought:
                    for k in range(j+1, min(j+8, len(rsi.values))):
                        if rsi.values[k] < bounce_low:
                            swings.append({
                                "index": k,
                                "type": "bearish_failure_swing",
                                "strength": 0.7,
                                "description": "Failure Swing هابط",
                            })
                            break
        
        return swings
    
    def _generate_all_signals(self, rsi: DynamicRSI, closes: np.ndarray,
                               divergences: List[RSIDivergence],
                               hidden_divs: List[RSIDivergence],
                               failure_swings: List[Dict]) -> List[RSISignal]:
        """
        توليد كل الإشارات.
        """
        signals = []
        
        idx = len(closes) - 1
        
        # تشبع شراء/بيع
        if rsi.current > rsi.overbought:
            signals.append(RSISignal(
                index=idx, signal_type='overbought', direction='bearish',
                price_level=closes[-1], rsi_value=rsi.current,
                strength=min(1.0, (rsi.current - rsi.overbought) / 10),
                description=f"تشبع شراء ديناميكي (>{rsi.overbought:.0f})",
            ))
        
        if rsi.current < rsi.oversold:
            signals.append(RSISignal(
                index=idx, signal_type='oversold', direction='bullish',
                price_level=closes[-1], rsi_value=rsi.current,
                strength=min(1.0, (rsi.oversold - rsi.current) / 10),
                description=f"تشبع بيع ديناميكي (<{rsi.oversold:.0f})",
            ))
        
        # عبور المنتصف
        if len(rsi.values) >= 2:
            if rsi.values[-2] < 50 and rsi.current > 50:
                signals.append(RSISignal(
                    index=idx, signal_type='centerline_cross', direction='bullish',
                    price_level=closes[-1], rsi_value=rsi.current,
                    strength=0.5,
                    description="عبور RSI فوق 50",
                ))
            elif rsi.values[-2] > 50 and rsi.current < 50:
                signals.append(RSISignal(
                    index=idx, signal_type='centerline_cross', direction='bearish',
                    price_level=closes[-1], rsi_value=rsi.current,
                    strength=0.5,
                    description="عبور RSI تحت 50",
                ))
        
        # تباعدات
        for div in divergences[-3:]:
            if div.divergence_type == 'bullish':
                signals.append(RSISignal(
                    index=div.index, signal_type='divergence', direction='bullish',
                    price_level=closes[div.index], rsi_value=div.rsi_peak2,
                    strength=div.strength,
                    description=f"تباعد صاعد (RSI: {div.rsi_peak1:.0f}→{div.rsi_peak2:.0f})",
                ))
            else:
                signals.append(RSISignal(
                    index=div.index, signal_type='divergence', direction='bearish',
                    price_level=closes[div.index], rsi_value=div.rsi_peak2,
                    strength=div.strength,
                    description=f"تباعد هابط (RSI: {div.rsi_peak1:.0f}→{div.rsi_peak2:.0f})",
                ))
        
        # Hidden
        for div in hidden_divs[-3:]:
            if div.divergence_type == 'hidden_bullish':
                signals.append(RSISignal(
                    index=div.index, signal_type='divergence', direction='bullish',
                    price_level=closes[div.index], rsi_value=div.rsi_peak2,
                    strength=div.strength * 0.9,
                    description=f"تباعد مخفي صاعد (استمرار)",
                ))
            else:
                signals.append(RSISignal(
                    index=div.index, signal_type='divergence', direction='bearish',
                    price_level=closes[div.index], rsi_value=div.rsi_peak2,
                    strength=div.strength * 0.9,
                    description=f"تباعد مخفي هابط (استمرار)",
                ))
        
        # Failure Swings
        for fs in failure_swings[-2:]:
            signals.append(RSISignal(
                index=fs['index'], signal_type='failure_swing',
                direction='bullish' if 'bullish' in fs['type'] else 'bearish',
                price_level=closes[fs['index']], rsi_value=rsi.values[fs['index']],
                strength=fs['strength'],
                description=fs['description'],
            ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية RSI الموحدة                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicRSIStrategy:
    """
    استراتيجية RSI الديناميكية الكاملة.
    """
    
    def __init__(self):
        self.rsi_builder = DynamicRSIBuilder()
        self.divergence_detector = RSIDivergenceDetector()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 14:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 14 شمعة على الأقل"}
        
        # 1. بناء RSI
        rsi_data = self.rsi_builder.analyze(closes, highs, lows, volumes)
        
        # 2. اكتشاف التباعدات
        rsi = rsi_data.get('rsi')
        signal_data = self.divergence_detector.analyze(rsi, closes, highs, lows)
        
        # 3. القرار
        decision = self._make_decision(rsi_data, signal_data, closes)
        
        return {
            **decision,
            "rsi_data": rsi_data,
            "signal_data": signal_data,
        }
    
    def _make_decision(self, rsi_data: Dict, signal_data: Dict,
                       closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        rsi = rsi_data.get('rsi')
        stoch_rsi = rsi_data.get('stoch_rsi')
        connors_rsi = rsi_data.get('connors_rsi')
        
        current_rsi = rsi_data.get('current', 50)
        
        # ---- من RSI مباشرة ----
        if current_rsi > rsi_data.get('overbought', 70):
            sell_signals.append(("RSI تشبع شراء ديناميكي", 0.55))
        elif current_rsi < rsi_data.get('oversold', 30):
            buy_signals.append(("RSI تشبع بيع ديناميكي", 0.55))
        
        # ميل RSI
        if rsi and rsi.slope > 0.5 and current_rsi > 50:
            buy_signals.append(("RSI صاعد بقوة", 0.4))
        elif rsi and rsi.slope < -0.5 and current_rsi < 50:
            sell_signals.append(("RSI هابط بقوة", 0.4))
        
        # حالة الاتجاه
        if rsi:
            if rsi.trend_state == 'bullish_range' and current_rsi < rsi.overbought:
                buy_signals.append(("RSI في نطاق صاعد", 0.45))
            elif rsi.trend_state == 'bearish_range' and current_rsi > rsi.oversold:
                sell_signals.append(("RSI في نطاق هابط", 0.45))
        
        # ---- من Stochastic RSI ----
        if stoch_rsi is not None and len(stoch_rsi) > 0:
            if stoch_rsi[-1] > 0.8:
                sell_signals.append(("Stoch RSI تشبع شراء", 0.5))
            elif stoch_rsi[-1] < 0.2:
                buy_signals.append(("Stoch RSI تشبع بيع", 0.5))
        
        # ---- من Connors RSI ----
        if connors_rsi is not None and len(connors_rsi) > 0:
            if connors_rsi[-1] > 80:
                sell_signals.append(("Connors RSI تشبع شراء", 0.5))
            elif connors_rsi[-1] < 20:
                buy_signals.append(("Connors RSI تشبع بيع", 0.5))
        
        # ---- من الإشارات ----
        signals = signal_data.get('signals', [])
        for sig in signals[-5:]:
            if sig.signal_type == 'divergence':
                if sig.direction == 'bullish':
                    buy_signals.append((f"تباعد RSI صاعد", sig.strength * 0.7))
                else:
                    sell_signals.append((f"تباعد RSI هابط", sig.strength * 0.7))
            
            elif sig.signal_type == 'failure_swing':
                if sig.direction == 'bullish':
                    buy_signals.append(("Failure Swing صاعد", 0.6))
                else:
                    sell_signals.append(("Failure Swing هابط", 0.6))
            
            elif sig.signal_type == 'centerline_cross':
                if sig.direction == 'bullish':
                    buy_signals.append(("عبور RSI 50 للأعلى", 0.4))
                else:
                    sell_signals.append(("عبور RSI 50 للأسفل", 0.4))
        
        # ---- القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            confidence = min(95, int(total_buy / max(total_buy + total_sell, 1) * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            confidence = min(95, int(total_sell / max(total_buy + total_sell, 1) * 100))
        elif total_buy > total_sell:
            recommendation = "شراء ضعيف"
            confidence = 40
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 40
        else:
            recommendation = "محايد"
            confidence = 25
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        reason += f" | RSI: {current_rsi:.0f} (فترة:{rsi_data.get('rsi').period if rsi else '?'})"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_rsi_strategy():
    """إنشاء استراتيجية RSI الديناميكية الجاهزة"""
    return DynamicRSIStrategy()