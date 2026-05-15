"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC MACD STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السابعة عشرة: مؤشر MACD الديناميكي
═══════════════════════════════════════════════════════════════════════════════

جيرالد أبل ابتكر MACD في السبعينات.
الفكرة: تقاطع متوسطين أسيين + رسم بياني للفرق بينهما.

النسخة الكلاسيكية: 12, 26, 9. ثوابت غبية.

هذه النسخة ديناميكية بالكامل - محسنة بـ 6 تعديلات:
- الفترات تتكيف مع سرعة السوق
- MACD-V (Volume-Weighted) بصيغة صحيحة
- Trend Filter للتقاطعات
- Divergence + Histogram تأكيد مضاعف
- Zero Line Magnetism
- Convergence Detection محسن

المفاهيم المتقدمة:
1. MACD Classic
2. MACD Histogram
3. MACD Divergence (مع تأكيد الهيستوجرام)
4. MACD Hidden Divergence
5. MACD Zero Line Cross + Magnetism
6. MACD Signal Line Cross (مع Trend Filter)
7. MACD Histogram Reversal
8. MACD-V (Volume-Weighted)
9. Convergence Detection
10. Zero Line Magnetism
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class DynamicMACD:
    """مؤشر MACD ديناميكي - محسن"""
    macd_line: np.ndarray
    signal_line: np.ndarray
    histogram: np.ndarray
    fast_period: int
    slow_period: int
    signal_period: int
    current_macd: float
    current_signal: float
    current_histogram: float
    histogram_direction: str
    histogram_color: str
    macd_slope: float
    signal_cross: str
    zero_cross: str
    divergence_present: bool
    # 🟡 تعديل 6: Zero Line Magnetism
    zero_line_distance: float = 0.0
    zero_line_magnetism: float = 0.0


@dataclass
class MACDSignal:
    """إشارة MACD"""
    index: int
    signal_type: str
    direction: str
    strength: float
    histogram_confirm: bool
    description: str
    # 🟡 تعديل 4: Trend Filtered
    trend_filtered: bool = False
    # 🟡 تعديل 5: Divergence + Histogram
    divergence_histogram_confirm: bool = False


@dataclass
class MACDDivergence:
    """تباعد MACD"""
    index: int
    divergence_type: str
    price_level: float
    macd_value: float
    strength: float
    bars_between: int
    histogram_confirm: bool
    # 🟡 تعديل 5: تأكيد مضاعف
    double_confirm: bool = False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: باني MACD الديناميكي (محسن)                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicMACDBuilder:
    """
    يبني MACD بمعلمات ديناميكية.
    
    🔴 تعديل 2: MACD-V بصيغة صحيحة
    🟡 تعديل 6: Zero Line Magnetism
    """
    
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """بناء MACD الديناميكي"""
        fast, slow, signal_p = self._find_optimal_periods(closes, highs, lows)
        macd_line, signal_line, histogram = self._calculate_macd(closes, fast, slow, signal_p)
        
        current_macd = macd_line[-1] if len(macd_line) > 0 else 0.0
        current_signal = signal_line[-1] if len(signal_line) > 0 else 0.0
        current_hist = histogram[-1] if len(histogram) > 0 else 0.0
        
        hist_dir = self._histogram_direction(histogram)
        hist_color = 'green' if current_hist > 0 else 'red'
        macd_slope = self._calculate_slope(macd_line)
        signal_cross = self._detect_cross(macd_line, signal_line)
        zero_cross = self._detect_zero_cross(macd_line)
        
        # 🟡 تعديل 6: Zero Line Magnetism
        zero_distance, zero_magnetism = self._calculate_zero_magnetism(macd_line)
        
        # MACD-V (Volume-Weighted) بصيغة صحيحة
        macd_v = self._calculate_macd_v(closes, volumes, fast, slow, signal_p)
        
        return {
            "macd": DynamicMACD(
                macd_line=macd_line, signal_line=signal_line, histogram=histogram,
                fast_period=fast, slow_period=slow, signal_period=signal_p,
                current_macd=current_macd, current_signal=current_signal,
                current_histogram=current_hist,
                histogram_direction=hist_dir, histogram_color=hist_color,
                macd_slope=macd_slope, signal_cross=signal_cross,
                zero_cross=zero_cross, divergence_present=False,
                zero_line_distance=zero_distance, zero_line_magnetism=zero_magnetism,
            ),
            "macd_v": macd_v,
            "current_macd": current_macd,
            "current_signal": current_signal,
            "current_histogram": current_hist,
        }
    
    def _find_optimal_periods(self, closes: np.ndarray, highs: np.ndarray,
                               lows: np.ndarray) -> Tuple[int, int, int]:
        """إيجاد الفترات المثلى ديناميكياً"""
        if len(closes) < 40:
            return 12, 26, 9
        
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-20:])
        
        if avg_price > 0:
            vol = avg_range / avg_price
        else:
            vol = 0.01
        
        changes = sum(1 for i in range(2, len(closes))
                     if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                        (closes[i] < closes[i-1] and closes[i-1] > closes[i-2]))
        freq = changes / max(len(closes), 1)
        
        if vol > 0.025 and freq > 0.3:
            return 6, 13, 4
        elif vol > 0.015 and freq > 0.2:
            return 8, 17, 6
        elif vol > 0.01:
            return 12, 26, 9
        elif vol > 0.005:
            return 16, 34, 13
        else:
            return 21, 55, 13
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """EMA"""
        alpha = 2.0 / (period + 1.0)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1.0 - alpha) * ema[i-1]
        return ema
    
    def _calculate_macd(self, closes: np.ndarray, fast: int, slow: int,
                        signal_p: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """حساب MACD الكامل"""
        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal_p)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _histogram_direction(self, histogram: np.ndarray) -> str:
        """اتجاه الهيستوجرام"""
        if len(histogram) < 3:
            return 'flat'
        if histogram[-1] > histogram[-2] and histogram[-2] > histogram[-3]:
            return 'rising'
        elif histogram[-1] < histogram[-2] and histogram[-2] < histogram[-3]:
            return 'falling'
        else:
            return 'flat'
    
    def _calculate_slope(self, values: np.ndarray) -> float:
        """ميل"""
        if len(values) < 5:
            return 0.0
        return (values[-1] - values[-5]) / 5.0
    
    def _detect_cross(self, macd: np.ndarray, signal: np.ndarray) -> str:
        """تقاطع MACD مع Signal"""
        if len(macd) < 2 or len(signal) < 2:
            return 'none'
        if macd[-2] <= signal[-2] and macd[-1] > signal[-1]:
            return 'bullish'
        elif macd[-2] >= signal[-2] and macd[-1] < signal[-1]:
            return 'bearish'
        return 'none'
    
    def _detect_zero_cross(self, macd: np.ndarray) -> str:
        """عبور خط الصفر"""
        if len(macd) < 2:
            return 'unknown'
        if macd[-2] < 0 and macd[-1] > 0:
            return 'crossed_up'
        elif macd[-2] > 0 and macd[-1] < 0:
            return 'crossed_down'
        elif macd[-1] > 0:
            return 'above'
        else:
            return 'below'
    
    def _calculate_zero_magnetism(self, macd_line: np.ndarray) -> Tuple[float, float]:
        """
        🟡 تعديل 6: Zero Line Magnetism
        
        MACD بعيد عن خط الصفر = جاذبية للعودة
        """
        if len(macd_line) < 20:
            return 0.0, 0.0
        
        current = macd_line[-1]
        recent_std = np.std(macd_line[-20:]) if len(macd_line) >= 20 else 0.0001
        
        if recent_std == 0:
            return 0.0, 0.0
        
        # المسافة بالانحرافات المعيارية
        distance_in_std = abs(current) / recent_std
        magnetism = min(1.0, distance_in_std / 2.5)  # 2.5+ انحراف = جاذبية قوية
        
        return distance_in_std, magnetism
    
    def _calculate_macd_v(self, closes: np.ndarray, volumes: np.ndarray,
                           fast: int, slow: int, signal_p: int) -> Dict:
        """
        🔴 تعديل 2: MACD-V بصيغة صحيحة
        
        كان: vw_price = closes * volumes / np.maximum(np.mean(volumes), 1) ← خطأ
        الآن: كل شمعة موزونة بحجمها نسبة للمتوسط
        """
        if len(closes) < slow:
            return {"macd_line": np.array([]), "signal_line": np.array([]), "histogram": np.array([]), "current": 0.0}
        
        # 🔴 تعديل 2: الصيغة الصحيحة - حجم نسبي لكل شمعة
        avg_vol = np.mean(volumes[-50:]) if len(volumes) >= 50 else np.mean(volumes)
        if avg_vol == 0:
            avg_vol = 1.0
        
        # السعر الموزون بالحجم النسبي
        vol_weights = volumes / avg_vol
        vw_price = closes * (1.0 + np.tanh(vol_weights - 1.0) * 0.3)
        
        macd_v, signal_v, hist_v = self._calculate_macd(vw_price, fast, slow, signal_p)
        
        return {
            "macd_line": macd_v,
            "signal_line": signal_v,
            "histogram": hist_v,
            "current": macd_v[-1] if len(macd_v) > 0 else 0.0,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف الإشارات والتباعدات (محسن)                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MACDSignalDetector:
    """
    يكتشف كل إشارات MACD.
    
    🔴 تعديل 1: إصلاح histogram_confirm (j > 1)
    🔴 تعديل 3: Convergence Detection محسن
    🟡 تعديل 4: Trend Filter للتقاطعات
    🟡 تعديل 5: Divergence + Histogram تأكيد مضاعف
    """
    
    def analyze(self, macd: DynamicMACD, closes: np.ndarray,
                highs: np.ndarray, lows: np.ndarray,
                regime_data: Dict = None) -> Dict:
        """اكتشاف الإشارات"""
        
        # 🟡 تعديل 4: تحقق من نظام السوق
        trend_ok = self._check_trend_for_macd(regime_data)
        
        signals = []
        
        # تقاطع Signal Line
        if macd.signal_cross == 'bullish':
            hist_confirm = macd.current_histogram > 0 or macd.histogram_direction == 'rising'
            strength = 0.6 if hist_confirm else 0.4
            
            # 🟡 تعديل 4: Trend Filter
            trend_filtered = False
            if not trend_ok.get('ok_for_bullish', True):
                strength *= 0.4
                trend_filtered = True
            
            signals.append(MACDSignal(
                index=len(closes)-1, signal_type='cross',
                direction='bullish', strength=strength,
                histogram_confirm=hist_confirm,
                description="تقاطع MACD فوق Signal" + (" ✓" if hist_confirm else ""),
                trend_filtered=trend_filtered,
            ))
        elif macd.signal_cross == 'bearish':
            hist_confirm = macd.current_histogram < 0 or macd.histogram_direction == 'falling'
            strength = 0.6 if hist_confirm else 0.4
            
            trend_filtered = False
            if not trend_ok.get('ok_for_bearish', True):
                strength *= 0.4
                trend_filtered = True
            
            signals.append(MACDSignal(
                index=len(closes)-1, signal_type='cross',
                direction='bearish', strength=strength,
                histogram_confirm=hist_confirm,
                description="تقاطع MACD تحت Signal" + (" ✓" if hist_confirm else ""),
                trend_filtered=trend_filtered,
            ))
        
        # عبور الصفر
        if macd.zero_cross == 'crossed_up':
            signals.append(MACDSignal(
                index=len(closes)-1, signal_type='zero_cross',
                direction='bullish', strength=0.65, histogram_confirm=True,
                description="MACD عبر فوق الصفر - تأكيد صعود",
            ))
        elif macd.zero_cross == 'crossed_down':
            signals.append(MACDSignal(
                index=len(closes)-1, signal_type='zero_cross',
                direction='bearish', strength=0.65, histogram_confirm=True,
                description="MACD عبر تحت الصفر - تأكيد هبوط",
            ))
        
        # 🟡 تعديل 6: Zero Line Magnetism Signal
        if macd.zero_line_magnetism > 0.6:
            direction = 'bullish' if macd.current_macd < 0 else 'bearish'
            signals.append(MACDSignal(
                index=len(closes)-1, signal_type='zero_magnetism',
                direction=direction,
                strength=0.45 * macd.zero_line_magnetism,
                histogram_confirm=False,
                description=f"جاذبية خط الصفر ({macd.zero_line_distance:.1f}σ) - ارتداد متوقع",
            ))
        
        # انعكاس الهيستوجرام
        hist_signals = self._detect_histogram_reversal(macd)
        signals.extend(hist_signals)
        
        # تباعدات
        divergences = self._find_divergences(macd, closes, highs, lows)
        
        # Convergence
        convergence = self._detect_convergence(macd, closes)
        signals.extend(convergence)
        
        return {
            "signals": signals,
            "divergences": divergences[-5:],
            "latest_signal": signals[-1] if signals else None,
        }
    
    def _check_trend_for_macd(self, regime_data: Dict = None) -> Dict:
        """
        🟡 تعديل 4: Trend Filter
        
        لا تأخذ تقاطع صاعد في اتجاه هابط قوي
        """
        if regime_data is None:
            return {"ok_for_bullish": True, "ok_for_bearish": True}
        
        try:
            regime = regime_data.get('regime_data', {}).get('regime')
            if regime is None:
                return {"ok_for_bullish": True, "ok_for_bearish": True}
            
            regime_type = str(regime.regime_type) if hasattr(regime, 'regime_type') else str(regime)
            
            if 'TRENDING_BULL' in regime_type.upper():
                return {"ok_for_bullish": True, "ok_for_bearish": False}
            elif 'TRENDING_BEAR' in regime_type.upper():
                return {"ok_for_bullish": False, "ok_for_bearish": True}
            
            return {"ok_for_bullish": True, "ok_for_bearish": True}
        except:
            return {"ok_for_bullish": True, "ok_for_bearish": True}
    
    def _detect_histogram_reversal(self, macd: DynamicMACD) -> List[MACDSignal]:
        """اكتشاف انعكاس الهيستوجرام"""
        signals = []
        
        if len(macd.histogram) < 3:
            return signals
        
        if macd.histogram[-2] < 0 and macd.current_histogram > 0:
            signals.append(MACDSignal(
                index=len(macd.histogram)-1, signal_type='histogram_reversal',
                direction='bullish', strength=0.55, histogram_confirm=True,
                description="هيستوجرام تحول للأخضر - إشارة صعود مبكرة",
            ))
        
        if macd.histogram[-2] > 0 and macd.current_histogram < 0:
            signals.append(MACDSignal(
                index=len(macd.histogram)-1, signal_type='histogram_reversal',
                direction='bearish', strength=0.55, histogram_confirm=True,
                description="هيستوجرام تحول للأحمر - إشارة هبوط مبكرة",
            ))
        
        return signals
    
    def _find_divergences(self, macd: DynamicMACD, closes: np.ndarray,
                           highs: np.ndarray, lows: np.ndarray) -> List[MACDDivergence]:
        """
        اكتشاف كل أنواع التباعد.
        
        🔴 تعديل 1: إصلاح histogram_confirm (j > 1)
        🟡 تعديل 5: Divergence + Histogram تأكيد مضاعف
        """
        divergences = []
        
        if len(closes) < 20:
            return divergences
        
        # تباعد هابط
        for i in range(10, len(highs) - 3):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                for j in range(i-5, max(0, i-25), -1):
                    if highs[j] > highs[j-1] and highs[j] > highs[j+1]:
                        if highs[i] > highs[j] and macd.macd_line[i] < macd.macd_line[j]:
                            # 🔴 تعديل 1: j > 1 بدل j > 0
                            hist_confirm = macd.macd_line[i] < macd.macd_line[j-1] if j > 1 else False
                            
                            # 🟡 تعديل 5: تأكيد مضاعف (تباعد + هيستوجرام)
                            double_confirm = hist_confirm and macd.histogram[i] < macd.histogram[i-1]
                            
                            divergences.append(MACDDivergence(
                                index=i, divergence_type='bearish',
                                price_level=highs[i], macd_value=macd.macd_line[i],
                                strength=min(1.0, (macd.macd_line[j] - macd.macd_line[i]) / max(abs(macd.macd_line[j]), 0.0001) * 5),
                                bars_between=i-j,
                                histogram_confirm=hist_confirm,
                                double_confirm=double_confirm,
                            ))
                        break
        
        # تباعد صاعد
        for i in range(10, len(lows) - 3):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                for j in range(i-5, max(0, i-25), -1):
                    if lows[j] < lows[j-1] and lows[j] < lows[j+1]:
                        if lows[i] < lows[j] and macd.macd_line[i] > macd.macd_line[j]:
                            hist_confirm = macd.macd_line[i] > macd.macd_line[j-1] if j > 1 else False
                            double_confirm = hist_confirm and macd.histogram[i] > macd.histogram[i-1]
                            
                            divergences.append(MACDDivergence(
                                index=i, divergence_type='bullish',
                                price_level=lows[i], macd_value=macd.macd_line[i],
                                strength=min(1.0, (macd.macd_line[i] - macd.macd_line[j]) / max(abs(macd.macd_line[j]), 0.0001) * 5),
                                bars_between=i-j,
                                histogram_confirm=hist_confirm,
                                double_confirm=double_confirm,
                            ))
                        break
        
        return divergences
    
    def _detect_convergence(self, macd: DynamicMACD, closes: np.ndarray) -> List[MACDSignal]:
        """
        🔴 تعديل 3: Convergence Detection محسن
        
        كان: abs(recent[-1]) < 0.1 * abs(recent[0]) ← صارم جداً (90% تلاشي)
        الآن: abs(recent[-1]) < 0.35 * abs(recent[0]) ← معقول (65% تلاشي)
        """
        signals = []
        
        if len(macd.macd_line) < 10:
            return signals
        
        recent = macd.macd_line[-5:]
        
        if abs(recent[0]) < 0.0001:
            return signals
        
        # 🔴 تعديل 3: نسبة تلاشي 65% بدل 90%
        if abs(recent[-1]) < 0.35 * abs(recent[0]):
            if recent[-1] > 0:
                signals.append(MACDSignal(
                    index=len(closes)-1, signal_type='convergence',
                    direction='bearish', strength=0.5, histogram_confirm=False,
                    description="MACD يتلاشى - ضعف الزخم الصاعد",
                ))
            else:
                signals.append(MACDSignal(
                    index=len(closes)-1, signal_type='convergence',
                    direction='bullish', strength=0.5, histogram_confirm=False,
                    description="MACD يتلاشى - ضعف الزخم الهابط",
                ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║             الدرجة النهائية: استراتيجية MACD الموحدة (محسنة)              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicMACDStrategy:
    """
    استراتيجية MACD الديناميكية الكاملة - الإصدار 2.0
    
    - فترات ديناميكية
    - MACD-V بصيغة صحيحة
    - Trend Filter للتقاطعات
    - Divergence + Histogram تأكيد مضاعف
    - Zero Line Magnetism
    """
    
    def __init__(self):
        self.macd_builder = DynamicMACDBuilder()
        self.signal_detector = MACDSignalDetector()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        regime_data = chart_data.get('regime_data', None)
        
        if len(closes) < 26:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 26 شمعة على الأقل"}
        
        macd_data = self.macd_builder.analyze(closes, highs, lows, volumes)
        macd = macd_data.get('macd')
        signal_data = self.signal_detector.analyze(macd, closes, highs, lows, regime_data)
        decision = self._make_decision(macd_data, signal_data, closes)
        
        return {**decision, "macd_data": macd_data, "signal_data": signal_data}
    
    def _make_decision(self, macd_data: Dict, signal_data: Dict,
                       closes: np.ndarray) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        
        macd = macd_data.get('macd')
        macd_v = macd_data.get('macd_v', {})
        
        # ---- من MACD مباشرة ----
        if macd:
            if macd.signal_cross == 'bullish':
                buy_signals.append(("MACD تقاطع صاعد", 0.55))
            elif macd.signal_cross == 'bearish':
                sell_signals.append(("MACD تقاطع هابط", 0.55))
            
            if macd.zero_cross == 'crossed_up':
                buy_signals.append(("MACD عبر فوق الصفر", 0.6))
            elif macd.zero_cross == 'crossed_down':
                sell_signals.append(("MACD عبر تحت الصفر", 0.6))
            elif macd.zero_cross == 'above':
                buy_signals.append(("MACD فوق الصفر", 0.25))
            elif macd.zero_cross == 'below':
                sell_signals.append(("MACD تحت الصفر", 0.25))
            
            # 🟡 تعديل 6: Zero Line Magnetism
            if macd.zero_line_magnetism > 0.5:
                if macd.current_macd < 0:
                    buy_signals.append((f"جاذبية خط الصفر ({macd.zero_line_distance:.1f}σ) - ارتداد صاعد", 0.45))
                else:
                    sell_signals.append((f"جاذبية خط الصفر ({macd.zero_line_distance:.1f}σ) - ارتداد هابط", 0.45))
            
            if macd.histogram_direction == 'rising' and macd.current_histogram > 0:
                buy_signals.append(("هيستوجرام أخضر يصعد", 0.45))
            elif macd.histogram_direction == 'falling' and macd.current_histogram < 0:
                sell_signals.append(("هيستوجرام أحمر يهبط", 0.45))
            elif macd.histogram_direction == 'rising' and macd.current_histogram < 0:
                buy_signals.append(("هيستوجرام أحمر يتقلص - تحسن", 0.4))
            elif macd.histogram_direction == 'falling' and macd.current_histogram > 0:
                sell_signals.append(("هيستوجرام أخضر يتقلص - تدهور", 0.4))
        
        # ---- من MACD-V ----
        if macd_v.get('current', 0) > 0:
            buy_signals.append(("MACD-V إيجابي", 0.25))
        else:
            sell_signals.append(("MACD-V سلبي", 0.25))
        
        # ---- من الإشارات ----
        signals = signal_data.get('signals', [])
        for sig in signals[-5:]:
            weight = sig.strength * 0.6
            
            # 🟡 تعديل 4: Trend Filter penalty
            if sig.trend_filtered:
                weight *= 0.5
            
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, weight))
            else:
                sell_signals.append((sig.description, weight))
        
        # ---- من التباعدات ----
        for div in signal_data.get('divergences', [])[-3:]:
            weight = div.strength * 0.75
            
            # 🟡 تعديل 5: تأكيد مضاعف
            if div.double_confirm:
                weight *= 1.4
                desc_suffix = " (تأكيد مضاعف)"
            elif div.histogram_confirm:
                desc_suffix = " (✓)"
            else:
                desc_suffix = ""
            
            if div.divergence_type == 'bullish':
                buy_signals.append((f"تباعد MACD صاعد{desc_suffix}", weight))
            else:
                sell_signals.append((f"تباعد MACD هابط{desc_suffix}", weight))
        
        # ---- القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            confidence = min(90, int(total_buy / max(total_buy + total_sell, 1) * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            confidence = min(90, int(total_sell / max(total_buy + total_sell, 1) * 100))
        elif total_buy > total_sell:
            recommendation = "شراء ضعيف"
            confidence = 35
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 35
        else:
            recommendation = "محايد"
            confidence = 20
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        
        if macd:
            reason += f" | MACD:{macd.current_macd:.4f} Hist:{macd.current_histogram:.4f}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_macd_strategy():
    """إنشاء استراتيجية MACD الديناميكية الجاهزة (الإصدار 2.0)"""
    return DynamicMACDStrategy()