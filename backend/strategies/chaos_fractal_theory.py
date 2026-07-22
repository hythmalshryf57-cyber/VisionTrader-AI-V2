"""
═══════════════════════════════════════════════════════════════════════════════
CHAOS & FRACTAL STRATEGY - النسخة الديناميكية المتكاملة
المدرسة التاسعة والعشرون: نظرية الفوضى والفركتلات
═══════════════════════════════════════════════════════════════════════════════

بينوا ماندلبروت (1924-2010) أثبت أن الأسواق "فركتلية" وليست عشوائية.
الأسواق لها "ذاكرة" وتتشابه في كل الأطر الزمنية.

هذه المدرسة تجمع:
1. Chaos Theory في الأسواق
2. Fractal Geometry
3. Butterfly Effect
4. Strange Attractors
5. Fractal Dimension
6. Hurst Exponent
7. Lyapunov Exponent
8. Correlation Dimension
9. Phase Space Reconstruction
10. Self-Similarity

ديناميكي بالكامل:
- البعد الفركتلي يتغير مع السوق
- أنماط الفركتلات تتكيف
- لا حدود ثابتة
- السوق يخبرك بدرجة "فوضويته"

المفاهيم المتقدمة:
1. Williams Fractals (Bill Williams)
2. Alligator Indicator
3. Awesome Oscillator
4. Acceleration Oscillator
5. Fractal Break
6. Fractal Dimension Index
7. Chaos Stability Index
8. Attractor Zones
9. Phase Transitions
10. Critical Points
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
class Fractal:
    """فركتل (نقطة تحول)"""
    index: int
    price: float
    fractal_type: str      # 'up' (قمة), 'down' (قاع)
    strength: float        # 0-1
    break_level: float
    confirmed: bool
    dimension_around: float


@dataclass
class ChaosMetrics:
    """مقاييس الفوضى"""
    fractal_dimension: float       # البعد الفركتلي (1.0-2.0)
    hurst_exponent: float           # 0-1
    lyapunov_exponent: float        # موجب = فوضوي
    correlation_dimension: float
    entropy: float                  # درجة العشوائية
    chaos_level: str                # 'stable', 'mild_chaos', 'chaotic', 'turbulent'
    predictability: float           # 0-1 قابلية التوقع
    strange_attractor_detected: bool
    phase_transition_risk: float


@dataclass
class FractalSignal:
    """إشارة فركتلية"""
    index: int
    signal_type: str
    direction: str
    price: float
    strength: float
    description: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: كاشف الفركتلات (Fractal Detector)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class FractalDetector:
    """
    يكتشف فركتلات ويليامز والأنماط الفركتلية.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """
        اكتشاف الفركتلات
        """
        # فركتلات ويليامز
        up_fractals = self._detect_up_fractals(highs)
        down_fractals = self._detect_down_fractals(lows)
        
        # تجميع الفركتلات
        all_fractals = self._combine_fractals(up_fractals, down_fractals)
        
        # البعد الفركتلي
        dimension = self._calculate_fractal_dimension(highs, lows)
        
        # أنماط Alligator
        alligator = self._calculate_alligator(closes)
        
        # Awesome Oscillator
        ao = self._calculate_awesome_oscillator(highs, lows)
        
        # Acceleration Oscillator
        ac = self._calculate_acceleration_oscillator(ao)
        
        # فركتلات نشطة
        active_fractals = self._find_active_fractals(all_fractals, closes[-1])
        
        return {
            "up_fractals": up_fractals[-5:],
            "down_fractals": down_fractals[-5:],
            "all_fractals": all_fractals[-10:],
            "dimension": dimension,
            "alligator": alligator,
            "ao": ao,
            "ac": ac,
            "active_fractals": active_fractals,
        }
    
    def _detect_up_fractals(self, highs: np.ndarray) -> List[Fractal]:
        """
        اكتشاف فركتلات علوية (قمم).
        القمة = أعلى من الشمعتين قبلها وبعدها.
        """
        fractals = []
        
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                
                # قوة الفركتل
                surrounding_high = max(
                    highs[i-2], highs[i-1], highs[i+1], highs[i+2]
                )
                strength = (highs[i] - surrounding_high) / max(highs[i], 0.0001) * 100
                strength = min(1.0, strength)
                
                fractals.append(Fractal(
                    index=i,
                    price=highs[i],
                    fractal_type='up',
                    strength=strength,
                    break_level=highs[i],
                    confirmed=True,
                    dimension_around=0,
                ))
        
        return fractals
    
    def _detect_down_fractals(self, lows: np.ndarray) -> List[Fractal]:
        """
        اكتشاف فركتلات سفلية (قيعان).
        """
        fractals = []
        
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                
                surrounding_low = min(
                    lows[i-2], lows[i-1], lows[i+1], lows[i+2]
                )
                strength = (surrounding_low - lows[i]) / max(lows[i], 0.0001) * 100
                strength = min(1.0, abs(strength))
                
                fractals.append(Fractal(
                    index=i,
                    price=lows[i],
                    fractal_type='down',
                    strength=strength,
                    break_level=lows[i],
                    confirmed=True,
                    dimension_around=0,
                ))
        
        return fractals
    
    def _combine_fractals(self, up_fractals: List[Fractal],
                           down_fractals: List[Fractal]) -> List[Fractal]:
        """
        دمج الفركتلات وترتيبها.
        """
        combined = up_fractals + down_fractals
        combined.sort(key=lambda f: f.index)
        return combined
    
    def _calculate_fractal_dimension(self, highs: np.ndarray, lows: np.ndarray) -> Dict:
        """
        حساب البعد الفركتلي.
        البعد الفركتلي = مقياس "لخشونة" السوق.
        1.0 = خط مستقيم، 2.0 = فوضى كاملة.
        """
        if len(highs) < 30:
            return {"value": 1.5, "interpretation": "غير كافٍ"}
        
        # طريقة مبسطة: نسبة التغير في النطاق
        ranges = highs[-30:] - lows[-30:]
        
        if len(ranges) < 10:
            return {"value": 1.5, "interpretation": "غير كافٍ"}
        
        # البعد الفركتلي = log(N) / log(1/ε)
        total_range = max(highs[-30:]) - min(lows[-30:])
        avg_range = np.mean(ranges)
        
        if avg_range > 0:
            dimension = np.log(len(ranges)) / np.log(total_range / avg_range)
            dimension = max(1.0, min(2.0, dimension))
        else:
            dimension = 1.5
        
        # التفسير
        if dimension < 1.2:
            interpretation = "سوق سلس - اتجاه قوي"
        elif dimension < 1.4:
            interpretation = "سوق شبه منتظم"
        elif dimension < 1.6:
            interpretation = "سوق طبيعي"
        elif dimension < 1.8:
            interpretation = "سوق خشن - فوضى متوسطة"
        else:
            interpretation = "سوق شديد الفوضى"
        
        return {"value": dimension, "interpretation": interpretation}
    
    def _calculate_alligator(self, closes: np.ndarray) -> Dict:
        """
        حساب مؤشر Alligator (بيل ويليامز).
        """
        if len(closes) < 13:
            return {"jaw": 0, "teeth": 0, "lips": 0, "state": "غير كافٍ"}
        
        # Jaw (الأزرق) - 13 فترة
        jaw = self._sma(closes, 13)
        jaw_shifted = np.roll(jaw, 8)
        
        # Teeth (الأحمر) - 8 فترة
        teeth = self._sma(closes, 8)
        teeth_shifted = np.roll(teeth, 5)
        
        # Lips (الأخضر) - 5 فترة
        lips = self._sma(closes, 5)
        lips_shifted = np.roll(lips, 3)
        
        current_jaw = jaw_shifted[-1] if len(jaw_shifted) > 0 else 0
        current_teeth = teeth_shifted[-1] if len(teeth_shifted) > 0 else 0
        current_lips = lips_shifted[-1] if len(lips_shifted) > 0 else 0
        
        # حالة Alligator
        if current_lips > current_teeth > current_jaw:
            state = "مستيقظ صاعد"
        elif current_lips < current_teeth < current_jaw:
            state = "مستيقظ هابط"
        elif abs(current_lips - current_teeth) < abs(current_jaw - current_teeth) * 0.3:
            state = "نائم"
        else:
            state = "يستيقظ"
        
        return {
            "jaw": current_jaw,
            "teeth": current_teeth,
            "lips": current_lips,
            "state": state,
        }
    
    def _calculate_awesome_oscillator(self, highs: np.ndarray, lows: np.ndarray) -> Dict:
        """
        Awesome Oscillator (AO).
        """
        if len(highs) < 34:
            return {"current": 0, "signal": "غير كافٍ"}
        
        median = (highs + lows) / 2
        ao = self._sma(median, 5) - self._sma(median, 34)
        
        current_ao = ao[-1] if len(ao) > 0 else 0
        
        if len(ao) >= 3:
            if ao[-1] > ao[-2] and ao[-2] < ao[-3]:
                signal = "صاعد"
            elif ao[-1] < ao[-2] and ao[-2] > ao[-3]:
                signal = "هابط"
            elif ao[-1] > 0 and ao[-2] > 0:
                signal = "إيجابي"
            elif ao[-1] < 0 and ao[-2] < 0:
                signal = "سلبي"
            else:
                signal = "محايد"
        else:
            signal = "غير كافٍ"
        
        return {"current": current_ao, "signal": signal, "values": ao[-5:] if len(ao) >= 5 else []}
    
    def _calculate_acceleration_oscillator(self, ao_data: Dict) -> Dict:
        """
        Acceleration Oscillator (AC).
        """
        ao_values = ao_data.get('values', [])
        
        if len(ao_values) < 5:
            return {"current": 0, "signal": "غير كافٍ"}
        
        ao_array = np.array(ao_values)
        if len(ao_array) >= 5:
            ac = ao_array - self._sma(ao_array, 5)
            current_ac = ac[-1] if len(ac) > 0 else 0
            
            if len(ac) >= 2:
                if ac[-1] > ac[-2]:
                    signal = "تسارع إيجابي"
                else:
                    signal = "تسارع سلبي"
            else:
                signal = "محايد"
        else:
            current_ac = 0
            signal = "غير كافٍ"
        
        return {"current": current_ac, "signal": signal}
    
    def _find_active_fractals(self, fractals: List[Fractal], current_price: float) -> List[Fractal]:
        """
        الفركتلات النشطة (القريبة من السعر).
        """
        active = []
        
        for f in fractals[-10:]:
            if abs(f.price - current_price) < current_price * 0.02:
                active.append(f)
        
        return active
    
    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """متوسط بسيط"""
        result = np.full_like(data, np.nan)
        for i in range(period-1, len(data)):
            result[i] = np.mean(data[i-period+1:i+1])
        return result


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: محلل الفوضى (Chaos Analyzer)                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ChaosAnalyzer:
    """
    يحلل درجة الفوضى في السوق.
    """
    
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> ChaosMetrics:
        """
        تحليل الفوضى
        """
        if len(closes) < 30:
            return ChaosMetrics(1.5, 0.5, 0, 0, 0.5, 'stable', 0.5, False, 0)
        
        # البعد الفركتلي
        fd = self._fractal_dimension(highs, lows)
        
        # أس هيرست
        hurst = self._hurst_exponent(closes)
        
        # أس ليابونوف
        lyapunov = self._lyapunov_exponent(closes)
        
        # الإنتروبي
        entropy = self._sample_entropy(closes)
        
        # قابلية التوقع
        predictability = 1 - entropy
        
        # درجة الفوضى
        if entropy < 0.3 and hurst > 0.6:
            chaos_level = 'stable'
        elif entropy < 0.5 and hurst > 0.5:
            chaos_level = 'mild_chaos'
        elif entropy > 0.7 or lyapunov > 0.1:
            chaos_level = 'chaotic'
        else:
            chaos_level = 'turbulent'
        
        # خطر انتقال الطور
        phase_risk = entropy * (1 - abs(hurst - 0.5) * 2)
        
        return ChaosMetrics(
            fractal_dimension=fd,
            hurst_exponent=hurst,
            lyapunov_exponent=lyapunov,
            correlation_dimension=fd * 0.8,
            entropy=entropy,
            chaos_level=chaos_level,
            predictability=predictability,
            strange_attractor_detected=lyapunov > 0.05,
            phase_transition_risk=phase_risk,
        )
    
    def _fractal_dimension(self, highs: np.ndarray, lows: np.ndarray) -> float:
        """البعد الفركتلي"""
        if len(highs) < 20:
            return 1.5
        
        ranges = highs[-20:] - lows[-20:]
        if len(ranges) < 5:
            return 1.5
        
        total = max(highs[-20:]) - min(lows[-20:])
        avg = np.mean(ranges)
        
        if avg > 0:
            dim = np.log(len(ranges)) / np.log(total / avg)
            return max(1.0, min(2.0, dim))
        
        return 1.5
    
    def _hurst_exponent(self, closes: np.ndarray) -> float:
        """أس هيرست"""
        if len(closes) < 30:
            return 0.5
        
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) < 10:
            return 0.5
        
        lags = [2, 4, 8, 16, 32]
        variances = []
        
        for lag in lags:
            if lag < len(returns):
                lagged = returns[lag:] - returns[:-lag]
                variances.append(np.var(lagged))
        
        if len(variances) < 3:
            return 0.5
        
        log_lags = np.log(lags[:len(variances)])
        log_vars = np.log(variances)
        
        slope = np.polyfit(log_lags, log_vars, 1)[0]
        hurst = slope / 2
        
        return max(0.1, min(0.9, hurst))
    
    def _lyapunov_exponent(self, closes: np.ndarray) -> float:
        """
        أس ليابونوف (حساسية الظروف الابتدائية).
        موجب = فوضوي.
        """
        if len(closes) < 20:
            return 0
        
        # تبسيط: متوسط التغير اللوغاريتمي
        log_returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        
        if len(log_returns) < 5:
            return 0
        
        # التقلب المتغير
        rolling_std = np.zeros(len(log_returns))
        for i in range(5, len(log_returns)):
            rolling_std[i] = np.std(log_returns[i-5:i+1])
        
        # ليابونوف = معدل تغير التقلب
        if len(rolling_std) > 10 and np.mean(rolling_std[-10:]) > 0:
            lyap = np.mean(np.abs(np.diff(rolling_std[-10:]))) / np.mean(rolling_std[-10:])
        else:
            lyap = 0
        
        return min(1.0, lyap)
    
    def _sample_entropy(self, data: np.ndarray) -> float:
        """
        Sample Entropy (درجة العشوائية).
        """
        if len(data) < 20:
            return 0.5
        
        # تبسيط: معامل الاختلاف
        returns = np.diff(data)
        if len(returns) < 5:
            return 0.5
        
        # عدد تغيرات الاتجاه
        changes = sum(1 for i in range(2, len(returns))
                     if (returns[i] > 0 and returns[i-1] < 0) or
                        (returns[i] < 0 and returns[i-1] > 0))
        
        change_rate = changes / max(len(returns), 1)
        
        # الانحراف المعياري الطبيعي
        std_normalized = np.std(returns) / max(np.mean(np.abs(data)), 0.0001)
        
        entropy = change_rate * 0.6 + min(std_normalized * 5, 1) * 0.4
        
        return max(0.1, min(1.0, entropy))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الفوضى والفركتلات الموحدة            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ChaosFractalStrategy:
    """
    استراتيجية نظرية الفوضى والفركتلات الكاملة.
    """
    
    def __init__(self):
        self.fractal_detector = FractalDetector()
        self.chaos_analyzer = ChaosAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        # 1. اكتشاف الفركتلات
        fractal_data = self.fractal_detector.analyze(highs, lows, closes, volumes)
        
        # 2. تحليل الفوضى
        chaos_metrics = self.chaos_analyzer.analyze(closes, highs, lows)
        
        # 3. القرار
        decision = self._make_decision(fractal_data, chaos_metrics, closes)
        
        from dataclasses import asdict, is_dataclass
        import numpy as _np
        
        def _clean_data(obj):
            if is_dataclass(obj) and not isinstance(obj, type):
                return _clean_data(asdict(obj))
            elif isinstance(obj, dict):
                return {k: _clean_data(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_clean_data(v) for v in obj]
            elif isinstance(obj, tuple):
                return tuple(_clean_data(v) for v in obj)
            elif isinstance(obj, _np.generic):
                return obj.item()
            elif isinstance(obj, _np.ndarray):
                return _clean_data(obj.tolist())
            elif hasattr(obj, '__dict__') and not isinstance(obj, type):
                try:
                    return {k: _clean_data(v) for k, v in obj.__dict__.items()}
                except Exception:
                    return str(obj)
            return obj

        raw_result = {
            **decision,
            "fractal_data": fractal_data,
            "chaos_metrics": chaos_metrics,
        }
        return _clean_data(raw_result)
    
    def _make_decision(self, fractal_data: Dict, chaos: ChaosMetrics,
                       closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        current_price = closes[-1]
        
        # ---- من الفركتلات النشطة ----
        active = fractal_data.get('active_fractals', [])
        for f in active:
            if f.fractal_type == 'up':
                sell_signals.append((f"فركتل علوي عند {f.price:.4f}", 0.45))
            else:
                buy_signals.append((f"فركتل سفلي عند {f.price:.4f}", 0.45))
        
        # ---- من Alligator ----
        alligator = fractal_data.get('alligator', {})
        if alligator.get('state') == 'مستيقظ صاعد':
            buy_signals.append(("Alligator مستيقظ صاعد", 0.5))
        elif alligator.get('state') == 'مستيقظ هابط':
            sell_signals.append(("Alligator مستيقظ هابط", 0.5))
        elif alligator.get('state') == 'نائم':
            buy_signals.append(("Alligator نائم - انتظار", 0.15))
            sell_signals.append(("Alligator نائم - انتظار", 0.15))
        
        # ---- من AO/AC ----
        ao = fractal_data.get('ao', {})
        ac = fractal_data.get('ac', {})
        
        if ao.get('signal') == 'صاعد' and ac.get('signal') == 'تسارع إيجابي':
            buy_signals.append(("AO + AC صاعدين", 0.6))
        elif ao.get('signal') == 'هابط' and ac.get('signal') == 'تسارع سلبي':
            sell_signals.append(("AO + AC هابطين", 0.6))
        
        # ---- من الفوضى ----
        if chaos.chaos_level == 'stable':
            buy_signals.append(("سوق مستقر - قابل للتوقع", 0.4))
        elif chaos.chaos_level == 'chaotic':
            buy_signals.append(("سوق فوضوي - حذر", 0.1))
            sell_signals.append(("سوق فوضوي - حذر", 0.1))
        
        if chaos.phase_transition_risk > 0.7:
            buy_signals.append(("خطر انتقال طور - تقلب قادم", 0.2))
            sell_signals.append(("خطر انتقال طور - تقلب قادم", 0.2))
        
        if chaos.predictability > 0.6:
            if closes[-1] > np.mean(closes[-10:]):
                buy_signals.append(("قابلية توقع عالية + صعود", 0.45))
            else:
                sell_signals.append(("قابلية توقع عالية + هبوط", 0.45))
        
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
        reason += f" | {chaos.chaos_level}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_chaos_fractal_strategy():
    """إنشاء استراتيجية الفوضى والفركتلات الجاهزة"""
    return ChaosFractalStrategy()