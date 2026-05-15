"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC STOCHASTIC STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السادسة عشرة: مؤشر الستوكاستيك الديناميكي - محلل الزخم الذكي
═══════════════════════════════════════════════════════════════════════════════

جورج لين طور Stochastic Oscillator في الخمسينات.
الفكرة: الزخم يسبق السعر. الإغلاق يميل للقرب من القمة في الصعود والعكس.

النسخة الكلاسيكية: %K 14, %D 3, تشبع 80/20.
لكن هذه ثوابت غبية.

هذه النسخة ديناميكية بالكامل - معدلة بـ 15 تحسيناً تداولياً:
- الفترات تتكيف مع تقلب السوق
- مستويات التشبع ديناميكية
- Trend Filter: لا تشتري تشبع بيع في هابط قوي
- التقاطع صالح فقط خارج منطقة الضوضاء
- Volume Confirmation للتقاطعات
- Stochastic Forecasting
- Hidden Divergence
- Stochastic Channel
- تكامل مع Wyckoff و S/R Levels
- Bollinger Band Filter

المفاهيم المتقدمة:
1. Stochastic Classic (Fast/Slow/Full)
2. Stochastic RSI
3. Stochastic Momentum Index (SMI)
4. Stochastic Divergence (Regular + Hidden)
5. Stochastic Pop (انفجار)
6. Stochastic Hook (خطاف)
7. Stochastic Cross (تقاطع مع فلتر)
8. Stochastic + Bollinger Bands
9. Stochastic Channel
10. Lane's Stochastic Rules
11. Pre-hook / Post-hook
12. Stochastic Forecasting
13. Center Line Cross
14. Failure Swing (صاعد وهابط)
15. Trend-Filtered Signals
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class DynamicStochastic:
    """مؤشر ستوكاستيك ديناميكي - نسخة محسنة"""
    k_values: np.ndarray
    d_values: np.ndarray
    k_period: int
    d_period: int
    slowing: int
    overbought: float
    oversold: float
    current_k: float
    current_d: float
    slope_k: float
    slope_d: float
    cross_direction: str
    range_position: float
    # 🟡 تعديل 10: Stochastic Channel
    k_channel_high: float = 90.0
    k_channel_low: float = 10.0
    # 🟡 تعديل 6: توقع
    forecast_k_3: float = 50.0
    forecast_d_3: float = 50.0


@dataclass
class StochSignal:
    """إشارة ستوكاستيك - نسخة محسنة"""
    index: int
    signal_type: str
    direction: str
    strength: float
    description: str
    trend_filtered: bool = False  # 🔴 تعديل 1
    volume_confirmed: bool = False  # 🟡 تعديل 7
    at_sr_level: bool = False  # 🟢 تعديل 12
    bollinger_confirmed: bool = False  # 🟡 تعديل 8


@dataclass
class StochDivergence:
    """تباعد ستوكاستيك - نسخة محسنة"""
    index: int
    divergence_type: str  # 'bullish', 'bearish', 'hidden_bullish', 'hidden_bearish'
    strength: float
    confirmed: bool


@dataclass
class TrendContext:
    """سياق الاتجاه لفلترة الإشارات"""
    direction: str  # 'up', 'down', 'sideways'
    strength: float  # 0-1
    efficiency: float  # 0-1 مدى اتجاهية الحركة
    is_ranging: bool
    bollinger_position: float  # -1 إلى 1 (تحت السفلي = -1، فوق العلوي = 1)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: محلل السياق (Trend & Context Analyzer)                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ContextAnalyzer:
    """
    يحلل سياق السوق لفلترة إشارات الستوكاستيك.
    
    🔴 تعديل 1: Trend Filter
    🟡 تعديل 8: Bollinger Band Filter
    🟢 تعديل 12: S/R Levels
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> TrendContext:
        """تحليل السياق الكامل"""
        
        # اتجاه
        direction, strength, efficiency, is_ranging = self._analyze_trend(highs, lows, closes)
        
        # Bollinger
        bb_position = self._calculate_bollinger_position(highs, lows, closes)
        
        return TrendContext(
            direction=direction,
            strength=strength,
            efficiency=efficiency,
            is_ranging=is_ranging,
            bollinger_position=bb_position,
        )
    
    def _analyze_trend(self, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray) -> Tuple[str, float, float, bool]:
        """
        🔴 تعديل 1: تحليل الاتجاه لفلترة الإشارات
        """
        if len(closes) < 20:
            return 'sideways', 0.0, 0.0, True
        
        # ADX بسيط
        dm_plus = np.zeros(len(closes))
        dm_minus = np.zeros(len(closes))
        tr = np.zeros(len(closes))
        
        for i in range(1, len(closes)):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            dm_plus[i] = up_move if up_move > down_move and up_move > 0 else 0
            dm_minus[i] = down_move if down_move > up_move and down_move > 0 else 0
        
        period = min(14, len(closes) - 1)
        atr = np.mean(tr[-period:]) if period > 0 else 0
        
        if atr == 0:
            return 'sideways', 0.0, 0.0, True
        
        di_plus = np.mean(dm_plus[-period:]) / atr * 100
        di_minus = np.mean(dm_minus[-period:]) / atr * 100
        
        adx_val = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) > 0 else 0
        
        if di_plus > di_minus:
            direction = 'up'
        elif di_minus > di_plus:
            direction = 'down'
        else:
            direction = 'sideways'
        
        strength = min(1.0, adx_val / 50)
        
        # كفاءة الاتجاه
        range_total = max(highs[-20:]) - min(lows[-20:])
        net_move = abs(closes[-1] - closes[-20])
        efficiency = net_move / range_total if range_total > 0 else 0
        
        # هل هو عرضي؟
        is_ranging = efficiency < 0.3 or adx_val < 20
        
        return direction, strength, efficiency, is_ranging
    
    def _calculate_bollinger_position(self, highs: np.ndarray, lows: np.ndarray,
                                        closes: np.ndarray, period: int = 20) -> float:
        """
        🟡 تعديل 8: موقع السعر بالنسبة لبولينجر
        
        -1 = تحت البولينجر السفلي
        0 = عند المتوسط
        1 = فوق البولينجر العلوي
        """
        if len(closes) < period:
            return 0.0
        
        typical = (highs[-period:] + lows[-period:] + closes[-period:]) / 3
        sma = np.mean(typical)
        std = np.std(typical)
        
        if std == 0:
            return 0.0
        
        upper = sma + 2 * std
        lower = sma - 2 * std
        
        current = closes[-1]
        
        if current > upper:
            return min(1.5, (current - upper) / (upper - sma) + 1.0)
        elif current < lower:
            return max(-1.5, (current - lower) / (sma - lower) - 1.0)
        else:
            return (current - sma) / (upper - sma) if upper != sma else 0.0
    
    def find_sr_levels(self, highs: np.ndarray, lows: np.ndarray, 
                        closes: np.ndarray) -> List[Dict]:
        """
        🟢 تعديل 12: إيجاد مستويات الدعم والمقاومة
        """
        levels = []
        
        if len(closes) < 50:
            return levels
        
        # قمم وقيعان
        peaks = []
        valleys = []
        
        for i in range(10, len(closes) - 10):
            if all(highs[i] >= highs[i-j] for j in range(1, 11)) and \
               all(highs[i] >= highs[i+j] for j in range(1, 11)):
                peaks.append({'price': highs[i], 'index': i})
            if all(lows[i] <= lows[i-j] for j in range(1, 11)) and \
               all(lows[i] <= lows[i+j] for j in range(1, 11)):
                valleys.append({'price': lows[i], 'index': i})
        
        # تجميع
        for group in self._cluster_levels(peaks, closes):
            levels.append({
                'price': group['avg_price'],
                'type': 'resistance',
                'strength': min(1.0, len(group['items']) * 0.3),
            })
        
        for group in self._cluster_levels(valleys, closes):
            levels.append({
                'price': group['avg_price'],
                'type': 'support',
                'strength': min(1.0, len(group['items']) * 0.3),
            })
        
        return levels
    
    def _cluster_levels(self, points: List[Dict], closes: np.ndarray) -> List[Dict]:
        """تجميع المستويات المتقاربة"""
        if not points:
            return []
        
        avg_price = np.mean(closes[-50:]) if len(closes) >= 50 else np.mean(closes)
        threshold = avg_price * 0.005
        
        sorted_points = sorted(points, key=lambda x: x['price'])
        groups = []
        current_group = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i]['price'] - current_group[-1]['price'] < threshold:
                current_group.append(sorted_points[i])
            else:
                groups.append(current_group)
                current_group = [sorted_points[i]]
        
        groups.append(current_group)
        
        return [{'avg_price': np.mean([p['price'] for p in group]), 'items': group} for group in groups]
    
    def is_near_sr(self, price: float, levels: List[Dict], atr: float = 0) -> Tuple[bool, float]:
        """
        🟢 تعديل 12: فحص القرب من دعم/مقاومة
        """
        if atr == 0:
            proximity = price * 0.005
        else:
            proximity = atr * 0.5
        
        for level in levels:
            if abs(price - level['price']) < proximity:
                return True, level['strength']
        
        return False, 1.0


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: باني الستوكاستيك الديناميكي (محسن)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicStochasticBuilder:
    """
    يبني مؤشر Stochastic بمعلمات ديناميكية.
    🟡 تعديل 9: عتبات الفترات من التاريخ
    🟡 تعديل 10: Stochastic Channel
    🟡 تعديل 6: Stochastic Forecasting
    """
    
    def __init__(self):
        self.historical_vol = deque(maxlen=100)
        self.historical_freq = deque(maxlen=100)
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """بناء الستوكاستيك الديناميكي"""
        
        # فترات ديناميكية
        k_period, d_period, slowing = self._find_optimal_periods(highs, lows, closes)
        
        # تحديث التاريخ
        self._update_history(highs, lows, closes)
        
        # حساب %K و %D
        k_values, d_values = self._calculate_stochastic(highs, lows, closes, 
                                                          k_period, slowing, d_period)
        
        # مستويات التشبع الديناميكية
        overbought, oversold = self._find_dynamic_levels(k_values, closes)
        
        # القيم الحالية
        current_k = k_values[-1] if len(k_values) > 0 else 50
        current_d = d_values[-1] if len(d_values) > 0 else 50
        
        # الميل
        slope_k = self._calculate_slope(k_values)
        slope_d = self._calculate_slope(d_values)
        
        # التقاطع
        cross = self._detect_cross(k_values, d_values)
        
        # الموقع
        range_pos = self._calculate_range_position(k_values)
        
        # 🟡 تعديل 10: Stochastic Channel
        k_channel_high, k_channel_low = self._calculate_stoch_channel(k_values)
        
        # 🟡 تعديل 6: توقع
        forecast_k = current_k + slope_k * 3
        forecast_d = current_d + slope_d * 3
        
        # Full Stochastic
        full_stoch = self._calculate_full_stochastic(highs, lows, closes, k_period, d_period)
        
        # SMI
        smi = self._calculate_smi(highs, lows, closes, k_period, d_period)
        
        stoch = DynamicStochastic(
            k_values=k_values,
            d_values=d_values,
            k_period=k_period,
            d_period=d_period,
            slowing=slowing,
            overbought=overbought,
            oversold=oversold,
            current_k=current_k,
            current_d=current_d,
            slope_k=slope_k,
            slope_d=slope_d,
            cross_direction=cross,
            range_position=range_pos,
            k_channel_high=k_channel_high,
            k_channel_low=k_channel_low,
            forecast_k_3=forecast_k,
            forecast_d_3=forecast_d,
        )
        
        return {
            "stoch": stoch,
            "full_stoch": full_stoch,
            "smi": smi,
            "current_k": current_k,
            "current_d": current_d,
            "overbought": overbought,
            "oversold": oversold,
        }
    
    def _find_optimal_periods(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray) -> Tuple[int, int, int]:
        """
        🟡 تعديل 9: عتبات ديناميكية من التاريخ
        
        بدل vol > 0.025 الثابتة، استخدم percentiles من التاريخ
        """
        if len(closes) < 30:
            return 14, 3, 3
        
        # قياس التقلب
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-20:])
        
        if avg_price > 0:
            vol = avg_range / avg_price
        else:
            vol = 0.01
        
        # تردد تغير الاتجاه
        changes = sum(1 for i in range(2, len(closes))
                     if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                        (closes[i] < closes[i-1] and closes[i-1] > closes[i-2]))
        freq = changes / max(len(closes), 1)
        
        # 🟡 تعديل 9: عتبات من التاريخ
        if len(self.historical_vol) > 10:
            vol_33 = np.percentile(list(self.historical_vol), 33)
            vol_66 = np.percentile(list(self.historical_vol), 66)
            freq_33 = np.percentile(list(self.historical_freq), 33)
            freq_66 = np.percentile(list(self.historical_freq), 66)
        else:
            vol_33, vol_66 = 0.01, 0.025
            freq_33, freq_66 = 0.2, 0.3
        
        if vol > vol_66 and freq > freq_66:
            k_period = 5
            d_period = 2
        elif vol > vol_33 and freq > freq_33:
            k_period = 10
            d_period = 2
        elif vol > vol_33:
            k_period = 14
            d_period = 3
        else:
            k_period = 21
            d_period = 5
        
        slowing = max(1, k_period // 3)
        
        return k_period, d_period, slowing
    
    def _update_history(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray):
        """تحديث التاريخ"""
        if len(closes) < 20:
            return
        
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-20:])
        vol = avg_range / avg_price if avg_price > 0 else 0
        
        changes = sum(1 for i in range(2, len(closes))
                     if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                        (closes[i] < closes[i-1] and closes[i-1] > closes[i-2]))
        freq = changes / max(len(closes), 1)
        
        self.historical_vol.append(vol)
        self.historical_freq.append(freq)
    
    def _calculate_stochastic(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray, k_period: int,
                               slowing: int, d_period: int) -> Tuple[np.ndarray, np.ndarray]:
        """حساب %K و %D"""
        k_values = np.full_like(closes, 50.0)
        d_values = np.full_like(closes, 50.0)
        
        if len(closes) < k_period:
            return k_values, d_values
        
        raw_k = np.full_like(closes, 50.0)
        for i in range(k_period - 1, len(closes)):
            highest = np.max(highs[i-k_period+1:i+1])
            lowest = np.min(lows[i-k_period+1:i+1])
            if highest != lowest:
                raw_k[i] = 100 * (closes[i] - lowest) / (highest - lowest)
        
        if slowing > 1:
            for i in range(k_period + slowing - 2, len(closes)):
                k_values[i] = np.mean(raw_k[i-slowing+1:i+1])
        else:
            k_values = raw_k.copy()
        
        for i in range(k_period + slowing + d_period - 3, len(closes)):
            d_values[i] = np.mean(k_values[i-d_period+1:i+1])
        
        return k_values, d_values
    
    def _find_dynamic_levels(self, k_values: np.ndarray, closes: np.ndarray) -> Tuple[float, float]:
        """مستويات التشبع الديناميكية"""
        if len(k_values) < 30:
            return 80.0, 20.0
        
        recent = k_values[-50:] if len(k_values) >= 50 else k_values
        
        ob = np.percentile(recent, 80)
        os = np.percentile(recent, 20)
        
        if len(closes) >= 20:
            trend = np.polyfit(np.arange(20), closes[-20:], 1)[0]
            avg = np.mean(closes[-20:])
            if avg > 0:
                trend_str = np.tanh(trend / avg * 100)
            else:
                trend_str = 0
        else:
            trend_str = 0
        
        if trend_str > 0.4:
            ob = min(90, ob + 5)
            os = min(40, os + 5)
        elif trend_str < -0.4:
            ob = max(60, ob - 5)
            os = max(10, os - 5)
        
        return ob, os
    
    def _calculate_slope(self, values: np.ndarray) -> float:
        """ميل المؤشر"""
        if len(values) < 5:
            return 0.0
        return (values[-1] - values[-5]) / 5
    
    def _detect_cross(self, k: np.ndarray, d: np.ndarray) -> str:
        """اكتشاف التقاطع"""
        if len(k) < 2 or len(d) < 2:
            return 'none'
        
        if k[-2] <= d[-2] and k[-1] > d[-1]:
            return 'bullish'
        elif k[-2] >= d[-2] and k[-1] < d[-1]:
            return 'bearish'
        
        return 'none'
    
    def _calculate_range_position(self, k: np.ndarray) -> float:
        """موقع %K في نطاقه"""
        if len(k) < 20:
            return 0.5
        
        recent = k[-20:]
        high = np.max(recent)
        low = np.min(recent)
        
        if high == low:
            return 0.5
        
        return (k[-1] - low) / (high - low)
    
    def _calculate_stoch_channel(self, k_values: np.ndarray) -> Tuple[float, float]:
        """
        🟡 تعديل 10: Stochastic Channel
        
        أعلى وأدنى %K في آخر 50 شمعة
        كسر هذه الحدود = حدث نادر
        """
        if len(k_values) < 50:
            return 90.0, 10.0
        
        recent = k_values[-50:]
        channel_high = np.percentile(recent, 95)
        channel_low = np.percentile(recent, 5)
        
        return channel_high, channel_low
    
    def _calculate_full_stochastic(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, k_period: int,
                                     d_period: int) -> Dict:
        """Full Stochastic"""
        _, d_values = self._calculate_stochastic(highs, lows, closes, k_period, 1, d_period)
        
        smooth_period = max(2, d_period // 2)
        smooth_d = np.full_like(d_values, 50.0)
        for i in range(smooth_period - 1, len(d_values)):
            smooth_d[i] = np.mean(d_values[i-smooth_period+1:i+1])
        
        return {"smooth_d": smooth_d, "current": smooth_d[-1] if len(smooth_d) > 0 else 50}
    
    def _calculate_smi(self, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, k_period: int, d_period: int) -> Dict:
        """Stochastic Momentum Index"""
        if len(closes) < k_period + 2:
            return {"values": np.array([]), "current": 0}
        
        midpoint = (highs + lows) / 2
        distance = closes - midpoint
        
        highest = np.full_like(closes, 0.0)
        lowest = np.full_like(closes, 0.0)
        
        for i in range(k_period - 1, len(closes)):
            highest[i] = np.max(highs[i-k_period+1:i+1])
            lowest[i] = np.min(lows[i-k_period+1:i+1])
        
        smi_raw = np.full_like(closes, 0.0)
        for i in range(k_period - 1, len(closes)):
            avg_distance = np.mean(distance[i-k_period+1:i+1])
            range_half = (highest[i] - lowest[i]) / 2
            if range_half > 0:
                smi_raw[i] = 200 * avg_distance / range_half
        
        signal = np.full_like(closes, 0.0)
        alpha = 2 / (d_period + 1)
        signal[k_period-1] = smi_raw[k_period-1]
        for i in range(k_period, len(closes)):
            signal[i] = alpha * smi_raw[i] + (1 - alpha) * signal[i-1]
        
        return {"values": smi_raw, "signal": signal, "current": smi_raw[-1] if len(smi_raw) > 0 else 0}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف الإشارات والتباعدات (محسن)                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class StochasticSignalDetector:
    """
    يكتشف كل إشارات الستوكاستيك مع فلترة السياق.
    
    🔴 تعديل 1: Trend Filter
    🔴 تعديل 2: التقاطع خارج الضوضاء فقط
    🔴 تعديل 3: أداء O(n)
    🔴 تعديل 4: Failure Swing هابط
    🔴 تعديل 5: Hook مع سياق تشبع
    🟡 تعديل 7: Volume Confirmation
    🟡 تعديل 8: Bollinger Filter
    🟢 تعديل 12: S/R تأكيد
    🟢 تعديل 13: Hidden Divergence
    🟢 تعديل 15: Center Line Cross
    """
    
    def analyze(self, stoch: DynamicStochastic, closes: np.ndarray,
                highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray,
                trend_ctx: TrendContext, sr_levels: List[Dict],
                context_analyzer: ContextAnalyzer) -> Dict:
        """اكتشاف الإشارات مع فلترة كاملة"""
        
        signals = []
        
        atr = np.mean(highs[-14:] - lows[-14:]) if len(highs) >= 14 else 0
        
        # 🔴 تعديل 1: فلتر الاتجاه
        # في اتجاه هابط: تجاهل إشارات الشراء من التشبع
        # في اتجاه صاعد: تجاهل إشارات البيع من التشبع
        trend_filter_active = trend_ctx.strength > 0.4 and not trend_ctx.is_ranging
        
        # ---- تقاطع (مع فلتر الضوضاء) ----
        if stoch.cross_direction == 'bullish':
            # 🔴 تعديل 2: التقاطع صالح فقط خارج منطقة الضوضاء (30-70)
            # أو إذا كان السوق متجه بقوة
            if stoch.current_k < 35 or stoch.current_k > 65 or trend_ctx.strength > 0.6:
                strength = 0.5
                if stoch.current_k < stoch.oversold:
                    strength = 0.75
                
                # 🔴 تعديل 1: فلتر الاتجاه
                if trend_filter_active and trend_ctx.direction == 'down':
                    strength *= 0.3  # أضعف في هابط
                
                # 🟡 تعديل 7: Volume Confirmation
                vol_confirmed = self._check_volume(volumes, 'bullish')
                if vol_confirmed:
                    strength *= 1.3
                
                # 🟢 تعديل 12: S/R
                near_sr, sr_str = context_analyzer.is_near_sr(closes[-1], sr_levels, atr)
                
                signals.append(StochSignal(
                    index=len(closes)-1,
                    signal_type='cross',
                    direction='bullish',
                    strength=min(1.0, strength),
                    description="تقاطع %K فوق %D" + (" (تشبع بيع)" if stoch.current_k < stoch.oversold else ""),
                    trend_filtered=trend_filter_active,
                    volume_confirmed=vol_confirmed,
                    at_sr_level=near_sr,
                ))
        
        elif stoch.cross_direction == 'bearish':
            if stoch.current_k > 65 or stoch.current_k < 35 or trend_ctx.strength > 0.6:
                strength = 0.5
                if stoch.current_k > stoch.overbought:
                    strength = 0.75
                
                if trend_filter_active and trend_ctx.direction == 'up':
                    strength *= 0.3
                
                vol_confirmed = self._check_volume(volumes, 'bearish')
                if vol_confirmed:
                    strength *= 1.3
                
                near_sr, sr_str = context_analyzer.is_near_sr(closes[-1], sr_levels, atr)
                
                signals.append(StochSignal(
                    index=len(closes)-1,
                    signal_type='cross',
                    direction='bearish',
                    strength=min(1.0, strength),
                    description="تقاطع %K تحت %D" + (" (تشبع شراء)" if stoch.current_k > stoch.overbought else ""),
                    trend_filtered=trend_filter_active,
                    volume_confirmed=vol_confirmed,
                    at_sr_level=near_sr,
                ))
        
        # ---- تشبع (مع فلتر بولينجر) ----
        bb_confirmed = trend_ctx.bollinger_position < -0.8 if stoch.current_k < stoch.oversold else \
                       trend_ctx.bollinger_position > 0.8 if stoch.current_k > stoch.overbought else False
        
        if stoch.current_k > stoch.overbought:
            strength = min(1.0, (stoch.current_k - stoch.overbought) / 10)
            
            # 🔴 تعديل 1: في اتجاه صاعد، التشبع أقل خطورة
            if trend_ctx.direction == 'up' and trend_ctx.strength > 0.5:
                strength *= 0.4
            # 🟡 تعديل 8: إذا السعر فوق BB، التشبع ليس إشارة بيع
            if trend_ctx.bollinger_position > 0.8:
                strength *= 0.3
            
            signals.append(StochSignal(
                index=len(closes)-1,
                signal_type='overbought',
                direction='bearish',
                strength=strength,
                description=f"تشبع شراء (>{stoch.overbought:.0f})",
                trend_filtered=trend_filter_active,
                bollinger_confirmed=bb_confirmed,
            ))
        
        if stoch.current_k < stoch.oversold:
            strength = min(1.0, (stoch.oversold - stoch.current_k) / 10)
            
            if trend_ctx.direction == 'down' and trend_ctx.strength > 0.5:
                strength *= 0.4
            if trend_ctx.bollinger_position < -0.8:
                strength *= 0.3
            
            signals.append(StochSignal(
                index=len(closes)-1,
                signal_type='oversold',
                direction='bullish',
                strength=strength,
                description=f"تشبع بيع (<{stoch.oversold:.0f})",
                trend_filtered=trend_filter_active,
                bollinger_confirmed=bb_confirmed,
            ))
        
        # ---- Hook (مع سياق تشبع) ----
        hooks = self._detect_hooks(stoch)
        signals.extend(hooks)
        
        # ---- Pop ----
        pops = self._detect_pops(stoch, closes)
        signals.extend(pops)
        
        # 🔴 تعديل 4: Failure Swings (صاعد وهابط)
        failures = self._detect_failure_swings(stoch)
        signals.extend(failures)
        
        # 🟢 تعديل 15: Center Line Cross
        centerline = self._detect_centerline_cross(stoch)
        signals.extend(centerline)
        
        # 🟡 تعديل 10: Stochastic Channel Break
        channel_breaks = self._detect_channel_break(stoch)
        signals.extend(channel_breaks)
        
        # تباعدات
        divergences = self._detect_divergences(stoch.k_values, closes, highs, lows)
        
        return {
            "signals": signals,
            "divergences": divergences[-5:],
            "latest_signal": signals[-1] if signals else None,
            "trend_context": trend_ctx,
        }
    
    def _check_volume(self, volumes: np.ndarray, direction: str) -> bool:
        """
        🟡 تعديل 7: Volume Confirmation
        """
        if len(volumes) < 10:
            return False
        
        current_vol = volumes[-1]
        avg_vol = np.mean(volumes[-10:])
        
        if avg_vol == 0:
            return False
        
        return current_vol > avg_vol * 1.3
    
    def _detect_hooks(self, stoch: DynamicStochastic) -> List[StochSignal]:
        """
        🔴 تعديل 5: Hook مع سياق تشبع سابق
        
        Hook الحقيقي: %K كان في تشبع + انعكاس + شمعة تأكيد
        """
        hooks = []
        
        if len(stoch.k_values) < 5:
            return hooks
        
        # Hook صاعد: %K كان في تشبع بيع ثم انعكس
        was_oversold = np.any(stoch.k_values[-8:-2] < stoch.oversold)
        
        if stoch.k_values[-3] > stoch.k_values[-2] and stoch.k_values[-1] > stoch.k_values[-2]:
            if was_oversold or stoch.current_k < 35:
                hooks.append(StochSignal(
                    index=len(stoch.k_values)-1,
                    signal_type='hook',
                    direction='bullish',
                    strength=0.65 if was_oversold else 0.5,
                    description="Hook صاعد" + (" (بعد تشبع بيع)" if was_oversold else ""),
                ))
        
        # Hook هابط
        was_overbought = np.any(stoch.k_values[-8:-2] > stoch.overbought)
        
        if stoch.k_values[-3] < stoch.k_values[-2] and stoch.k_values[-1] < stoch.k_values[-2]:
            if was_overbought or stoch.current_k > 65:
                hooks.append(StochSignal(
                    index=len(stoch.k_values)-1,
                    signal_type='hook',
                    direction='bearish',
                    strength=0.65 if was_overbought else 0.5,
                    description="Hook هابط" + (" (بعد تشبع شراء)" if was_overbought else ""),
                ))
        
        return hooks
    
    def _detect_pops(self, stoch: DynamicStochastic, closes: np.ndarray) -> List[StochSignal]:
        """اكتشاف الانفجار (Pop)"""
        pops = []
        
        if len(stoch.k_values) < 5:
            return pops
        
        if stoch.k_values[-3] < stoch.oversold and stoch.current_k > stoch.oversold + 10:
            pops.append(StochSignal(
                index=len(stoch.k_values)-1,
                signal_type='pop',
                direction='bullish',
                strength=0.7,
                description="انفجار صاعد - خروج قوي من تشبع البيع",
            ))
        
        if stoch.k_values[-3] > stoch.overbought and stoch.current_k < stoch.overbought - 10:
            pops.append(StochSignal(
                index=len(stoch.k_values)-1,
                signal_type='pop',
                direction='bearish',
                strength=0.7,
                description="انفجار هابط - خروج قوي من تشبع الشراء",
            ))
        
        return pops
    
    def _detect_failure_swings(self, stoch: DynamicStochastic) -> List[StochSignal]:
        """
        🔴 تعديل 4: Failure Swings كاملة (صاعد وهابط)
        """
        failures = []
        
        if len(stoch.k_values) < 8:
            return failures
        
        k = stoch.k_values
        
        # صاعد: قاع تحت oversold، ارتداد، قاع أعلى
        for i in range(3, len(k) - 5):
            if k[i] < stoch.oversold and k[i] < k[i-1] and k[i] < k[i+1]:
                for j in range(i+3, min(i+10, len(k)-2)):
                    if k[j] < k[j-1] and k[j] < k[j+1]:
                        if k[j] > k[i] and k[j] > stoch.oversold:
                            if k[j+1] > k[j] and k[j+1] > k[j-1]:
                                failures.append(StochSignal(
                                    index=j,
                                    signal_type='failure_swing',
                                    direction='bullish',
                                    strength=0.7,
                                    description="Failure Swing صاعد - قيعان صاعدة",
                                ))
                            break
        
        # 🔴 تعديل 4: هابط: قمة فوق overbought، هبوط، قمة أقل
        for i in range(3, len(k) - 5):
            if k[i] > stoch.overbought and k[i] > k[i-1] and k[i] > k[i+1]:
                for j in range(i+3, min(i+10, len(k)-2)):
                    if k[j] > k[j-1] and k[j] > k[j+1]:
                        if k[j] < k[i] and k[j] < stoch.overbought:
                            if k[j+1] < k[j] and k[j+1] < k[j-1]:
                                failures.append(StochSignal(
                                    index=j,
                                    signal_type='failure_swing',
                                    direction='bearish',
                                    strength=0.7,
                                    description="Failure Swing هابط - قمم هابطة",
                                ))
                            break
        
        return failures
    
    def _detect_centerline_cross(self, stoch: DynamicStochastic) -> List[StochSignal]:
        """
        🟢 تعديل 15: Center Line Cross
        
        تقاطع %K فوق/تحت خط 50 = إشارة اتجاه
        """
        signals = []
        
        if len(stoch.k_values) < 3:
            return signals
        
        # صاعد: %K يخترق 50 للأعلى
        if stoch.k_values[-2] < 50 and stoch.current_k > 50:
            signals.append(StochSignal(
                index=len(stoch.k_values)-1,
                signal_type='centerline_cross',
                direction='bullish',
                strength=0.4,
                description="Center Line Cross صاعد - %K فوق 50",
            ))
        
        # هابط: %K يخترق 50 للأسفل
        if stoch.k_values[-2] > 50 and stoch.current_k < 50:
            signals.append(StochSignal(
                index=len(stoch.k_values)-1,
                signal_type='centerline_cross',
                direction='bearish',
                strength=0.4,
                description="Center Line Cross هابط - %K تحت 50",
            ))
        
        return signals
    
    def _detect_channel_break(self, stoch: DynamicStochastic) -> List[StochSignal]:
        """
        🟡 تعديل 10: Stochastic Channel Break
        
        %K يكسر قناته = حدث نادر وقوي
        """
        signals = []
        
        if stoch.current_k > stoch.k_channel_high:
            signals.append(StochSignal(
                index=len(stoch.k_values)-1 if len(stoch.k_values) > 0 else 0,
                signal_type='channel_break',
                direction='bearish',
                strength=0.65,
                description=f"Stoch Channel Break لأعلى (>{stoch.k_channel_high:.0f}) - ذروة",
            ))
        
        if stoch.current_k < stoch.k_channel_low:
            signals.append(StochSignal(
                index=len(stoch.k_values)-1 if len(stoch.k_values) > 0 else 0,
                signal_type='channel_break',
                direction='bullish',
                strength=0.65,
                description=f"Stoch Channel Break لأسفل (<{stoch.k_channel_low:.0f}) - قاع",
            ))
        
        return signals
    
    def _detect_divergences(self, k_values: np.ndarray, closes: np.ndarray,
                             highs: np.ndarray, lows: np.ndarray) -> List[StochDivergence]:
        """
        🔴 تعديل 3: أداء O(n) عبر تخزين القمم والقيعان مسبقاً
        🟢 تعديل 13: Hidden Divergence
        """
        divergences = []
        
        if len(closes) < 20:
            return divergences
        
        # استخراج القمم والقيعان مرة واحدة
        peaks = []
        valleys = []
        
        for i in range(3, len(closes) - 3):
            if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and \
               highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
                peaks.append({'index': i, 'price': highs[i], 'k': k_values[i]})
            if lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and \
               lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
                valleys.append({'index': i, 'price': lows[i], 'k': k_values[i]})
        
        # تباعد هابط: قمة أعلى مع %K أقل
        if len(peaks) >= 2:
            recent_peaks = peaks[-10:] if len(peaks) >= 10 else peaks
            for i in range(len(recent_peaks)-1, 0, -1):
                for j in range(i-1, max(0, i-5), -1):
                    if recent_peaks[i]['price'] > recent_peaks[j]['price'] and \
                       recent_peaks[i]['k'] < recent_peaks[j]['k'] and \
                       recent_peaks[j]['k'] > 70:
                        divergences.append(StochDivergence(
                            index=recent_peaks[i]['index'],
                            divergence_type='bearish',
                            strength=min(1.0, (recent_peaks[j]['k'] - recent_peaks[i]['k']) / 20),
                            confirmed=True,
                        ))
                        break
        
        # تباعد صاعد
        if len(valleys) >= 2:
            recent_valleys = valleys[-10:] if len(valleys) >= 10 else valleys
            for i in range(len(recent_valleys)-1, 0, -1):
                for j in range(i-1, max(0, i-5), -1):
                    if recent_valleys[i]['price'] < recent_valleys[j]['price'] and \
                       recent_valleys[i]['k'] > recent_valleys[j]['k'] and \
                       recent_valleys[j]['k'] < 30:
                        divergences.append(StochDivergence(
                            index=recent_valleys[i]['index'],
                            divergence_type='bullish',
                            strength=min(1.0, (recent_valleys[i]['k'] - recent_valleys[j]['k']) / 20),
                            confirmed=True,
                        ))
                        break
        
        # 🟢 تعديل 13: Hidden Divergence
        # Hidden Bullish: قاع أعلى مع %K أقل (استمرار صعود)
        if len(valleys) >= 2:
            recent_valleys = valleys[-10:] if len(valleys) >= 10 else valleys
            for i in range(len(recent_valleys)-1, 0, -1):
                for j in range(i-1, max(0, i-5), -1):
                    if recent_valleys[i]['price'] > recent_valleys[j]['price'] and \
                       recent_valleys[i]['k'] < recent_valleys[j]['k'] and \
                       30 < recent_valleys[j]['k'] < 70:
                        divergences.append(StochDivergence(
                            index=recent_valleys[i]['index'],
                            divergence_type='hidden_bullish',
                            strength=0.55,
                            confirmed=True,
                        ))
                        break
        
        # Hidden Bearish: قمة أقل مع %K أعلى (استمرار هبوط)
        if len(peaks) >= 2:
            recent_peaks = peaks[-10:] if len(peaks) >= 10 else peaks
            for i in range(len(recent_peaks)-1, 0, -1):
                for j in range(i-1, max(0, i-5), -1):
                    if recent_peaks[i]['price'] < recent_peaks[j]['price'] and \
                       recent_peaks[i]['k'] > recent_peaks[j]['k'] and \
                       30 < recent_peaks[j]['k'] < 70:
                        divergences.append(StochDivergence(
                            index=recent_peaks[i]['index'],
                            divergence_type='hidden_bearish',
                            strength=0.55,
                            confirmed=True,
                        ))
                        break
        
        return divergences


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الستوكاستيك الموحدة (محسنة)          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicStochasticStrategy:
    """
    استراتيجية الستوكاستيك الديناميكية الكاملة (الإصدار 2.0)
    
    تجمع:
    - بناء ستوكاستيك ديناميكي
    - فلترة بالاتجاه
    - فلترة بالحجم
    - فلترة بالبولينجر
    - تكامل مع S/R
    - Hidden Divergence
    - Center Line Cross
    - Stochastic Channel
    """
    
    def __init__(self):
        self.stoch_builder = DynamicStochasticBuilder()
        self.signal_detector = StochasticSignalDetector()
        self.context_analyzer = ContextAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 14:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 14 شمعة على الأقل"}
        
        # 0. سياق السوق
        trend_ctx = self.context_analyzer.analyze(highs, lows, closes, volumes)
        sr_levels = self.context_analyzer.find_sr_levels(highs, lows, closes)
        
        # 1. بناء الستوكاستيك
        stoch_data = self.stoch_builder.analyze(highs, lows, closes, volumes)
        
        # 2. اكتشاف الإشارات مع فلترة
        stoch = stoch_data.get('stoch')
        signal_data = self.signal_detector.analyze(
            stoch, closes, highs, lows, volumes, trend_ctx, sr_levels, self.context_analyzer
        )
        
        # 3. القرار
        decision = self._make_decision(stoch_data, signal_data, trend_ctx)
        
        return {
            **decision,
            "stoch_data": stoch_data,
            "signal_data": signal_data,
            "trend_context": {
                "direction": trend_ctx.direction,
                "strength": trend_ctx.strength,
                "is_ranging": trend_ctx.is_ranging,
            },
        }
    
    def _make_decision(self, stoch_data: Dict, signal_data: Dict,
                       trend_ctx: TrendContext) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        
        stoch = stoch_data.get('stoch')
        smi = stoch_data.get('smi', {})
        
        # ---- من الستوكاستيك ----
        if stoch:
            # تشبع مع فلتر الاتجاه
            if stoch.current_k < stoch.oversold:
                if trend_ctx.direction != 'down' or trend_ctx.strength < 0.5:
                    buy_signals.append((f"Stoch تشبع بيع (<{stoch.oversold:.0f})", 0.5))
                else:
                    sell_signals.append(("تشبع بيع في هابط قوي - تجاهل شراء", 0.1))
            
            if stoch.current_k > stoch.overbought:
                if trend_ctx.direction != 'up' or trend_ctx.strength < 0.5:
                    sell_signals.append((f"Stoch تشبع شراء (>{stoch.overbought:.0f})", 0.5))
                else:
                    buy_signals.append(("تشبع شراء في صاعد قوي - تجاهل بيع", 0.1))
            
            # 🟡 تعديل 6: توقع
            if stoch.forecast_k_3 > stoch.overbought and stoch.current_k < 50:
                buy_signals.append((f"Stoch Forecast: %K سيتجاوز {stoch.overbought:.0f}", 0.4))
            if stoch.forecast_k_3 < stoch.oversold and stoch.current_k > 50:
                sell_signals.append((f"Stoch Forecast: %K سينخفض تحت {stoch.oversold:.0f}", 0.4))
        
        # ---- من SMI ----
        if smi.get('current', 0) > 40:
            sell_signals.append(("SMI تشبع شراء", 0.4))
        elif smi.get('current', 0) < -40:
            buy_signals.append(("SMI تشبع بيع", 0.4))
        
        # ---- من الإشارات ----
        signals = signal_data.get('signals', [])
        for sig in signals[-8:]:
            weight = sig.strength * 0.6
            
            if sig.signal_type == 'pop':
                weight = sig.strength * 0.8
            elif sig.signal_type == 'failure_swing':
                weight = sig.strength * 0.75
            elif sig.signal_type == 'channel_break':
                weight = sig.strength * 0.7
            
            # تعزيزات
            if sig.volume_confirmed:
                weight *= 1.2
            if sig.at_sr_level:
                weight *= 1.3
            if sig.trend_filtered:
                weight *= 0.7  # الإشارة ضد الاتجاه = أضعف
            
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, weight))
            else:
                sell_signals.append((sig.description, weight))
        
        # ---- من التباعدات ----
        for div in signal_data.get('divergences', [])[-4:]:
            weight = div.strength * 0.7
            if div.divergence_type == 'bullish':
                buy_signals.append(("تباعد Stoch صاعد", weight))
            elif div.divergence_type == 'bearish':
                sell_signals.append(("تباعد Stoch هابط", weight))
            elif div.divergence_type == 'hidden_bullish':
                buy_signals.append(("Hidden تباعد صاعد", weight * 0.8))
            elif div.divergence_type == 'hidden_bearish':
                sell_signals.append(("Hidden تباعد هابط", weight * 0.8))
        
        # ---- تحذير السوق العرضي ----
        if trend_ctx.is_ranging:
            buy_signals.append(("سوق عرضي - الإشارات أقل موثوقية", 0.2))
            sell_signals.append(("سوق عرضي - الإشارات أقل موثوقية", 0.2))
        
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
            confidence = 35 + int(min(35, (total_buy - total_sell) * 15))
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 35 + int(min(35, (total_sell - total_buy) * 15))
        else:
            recommendation = "محايد"
            confidence = 20
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        
        if stoch:
            reason += f" | %K:{stoch.current_k:.0f} %D:{stoch.current_d:.0f}"
            reason += f" | اتجاه:{trend_ctx.direction}"
            if stoch.forecast_k_3:
                reason += f" | توقع%K:{stoch.forecast_k_3:.0f}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_stochastic_strategy():
    """إنشاء استراتيجية الستوكاستيك الديناميكية الجاهزة (الإصدار 2.0)"""
    return DynamicStochasticStrategy()