"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC MOVING AVERAGES STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثالثة عشرة: المتوسطات المتحركة الديناميكية
═══════════════════════════════════════════════════════════════════════════════

المتوسطات المتحركة هي أقدم وأشهر مؤشر في التاريخ.
لكن النسخة الكلاسيكية (SMA 50, EMA 200) ثابتة وغبية.

هذه النسخة ديناميكية بالكامل:
- لا فترات ثابتة (50, 100, 200)
- الفترة تتكيف مع تقلب السوق
- نوع المتوسط يتغير حسب نظام السوق
- المتوسطات "تتنفس" مع السوق
- كروس أوفر ديناميكي (ليس تقاطع ثابت)

الأنواع المستخدمة ديناميكياً:
1. EMA - Exponential Moving Average
2. HMA - Hull Moving Average (الأسرع)
3. KAMA - Kaufman Adaptive Moving Average
4. McGinley Dynamic (يتكيف تلقائياً مع السرعة)
5. Adaptive Envelope (نطاقات متكيفة)
6. MA Rainbow (قوس قزح المتوسطات)
7. Displaced MA (متوسطات مزاحة)

مفاهيم متقدمة:
- Ribbon (شريط المتوسطات)
- Cloud (سحابة المتوسطات)
- Adaptive Bands (نطاقات متكيفة)
- Rainbow (قوس قزح المتوسطات)
- Displaced MA (متوسطات مزاحة)
- Envelope ديناميكي
- Slope Analysis (تحليل الميل)
- Acceleration/Deceleration
- Mean Reversion Distance
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
class AdaptiveMA:
    """متوسط متحرك متكيف"""
    name: str
    ma_type: str
    period: int
    values: np.ndarray
    slope: float
    acceleration: float
    direction: str
    strength: float
    # 🟡 تعديل 6: Displaced MA
    displaced_forward: Optional[np.ndarray] = None
    displaced_backward: Optional[np.ndarray] = None


@dataclass
class MACrossover:
    """تقاطع متوسطات"""
    index: int
    fast_ma: str
    slow_ma: str
    direction: str
    strength: float
    angle: float
    confirmed: bool
    fake_out_risk: float


@dataclass
class MARibbon:
    """شريط المتوسطات"""
    mas: List[AdaptiveMA]
    alignment: str
    spread: float
    expansion: str
    strength: float
    # 🟡 تعديل 5: Rainbow
    rainbow_alignment: str = 'mixed'  # 'perfect_bullish', 'bullish', 'mixed', 'bearish', 'perfect_bearish'


@dataclass
class AdaptiveEnvelope:
    """نطاق متكيف حول المتوسط"""
    ma_name: str
    upper_band: np.ndarray
    lower_band: np.ndarray
    current_upper: float
    current_lower: float
    bandwidth: float  # اتساع النطاق
    price_position: float  # -1 (تحت) إلى 1 (فوق)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: مهندس المتوسطات الديناميكية (محسن)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicMovingAverageEngineer:
    """
    يبني المتوسطات المتحركة بفترات ديناميكية.
    لا 50 ولا 200 ثابتين. الفترة الأفضل = ما يناسب السوق الآن.
    """
    
    def __init__(self):
        self.base_periods = [3, 5, 8, 13, 21, 34, 55, 89, 144]
        self.adaptive_scaler = 1.0
        
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """بناء المتوسطات الديناميكية"""
        market_speed = self._measure_market_speed(closes, highs, lows)
        adapted_periods = self._adapt_periods(market_speed, closes)
        mas = self._build_multiple_mas(closes, highs, lows, adapted_periods)
        ribbon = self._build_ribbon(mas)
        cloud = self._build_cloud(mas, closes)
        slope_analysis = self._analyze_slopes(mas)
        
        # 🟡 تعديل 4: Adaptive Envelope
        envelopes = self._build_envelopes(mas, closes, highs, lows)
        
        # 🟡 تعديل 5: MA Rainbow
        rainbow = self._build_rainbow(mas, closes)
        
        return {
            "mas": mas,
            "ribbon": ribbon,
            "cloud": cloud,
            "slope_analysis": slope_analysis,
            "market_speed": market_speed,
            "adapted_periods": adapted_periods,
            "envelopes": envelopes,
            "rainbow": rainbow,
        }
    
    def _measure_market_speed(self, closes: np.ndarray, highs: np.ndarray,
                               lows: np.ndarray) -> Dict:
        """قياس سرعة السوق"""
        if len(closes) < 20:
            return {"speed": "normal", "factor": 1.0}
        
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-20:])
        
        if avg_price > 0:
            volatility = avg_range / avg_price
        else:
            volatility = 0.01
        
        net_change = abs(closes[-1] - closes[-20])
        total_path = sum(abs(closes[i] - closes[i-1]) for i in range(-19, 0)) if len(closes) >= 20 else 1
        efficiency = net_change / total_path if total_path > 0 else 0.5
        
        direction_changes = sum(1 for i in range(-18, 0) 
                               if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                                  (closes[i] < closes[i-1] and closes[i-1] > closes[i-2])) if len(closes) >= 20 else 0
        change_freq = direction_changes / 18 if len(closes) >= 20 else 0.5
        
        if volatility > 0.02 and efficiency > 0.6:
            speed = "fast_trending"
            factor = 0.5
        elif volatility > 0.02 and efficiency < 0.4:
            speed = "fast_choppy"
            factor = 0.7
        elif volatility < 0.005:
            speed = "slow"
            factor = 1.5
        elif change_freq > 0.5:
            speed = "choppy"
            factor = 1.2
        else:
            speed = "normal"
            factor = 1.0
        
        return {"speed": speed, "factor": factor, "volatility": volatility}
    
    def _adapt_periods(self, market_speed: Dict, closes: np.ndarray) -> List[int]:
        """تكييف الفترات مع سرعة السوق"""
        factor = market_speed.get('factor', 1.0)
        adapted = []
        for base in self.base_periods:
            new_period = max(2, int(base * factor))
            adapted.append(new_period)
        return adapted
    
    def _build_multiple_mas(self, closes: np.ndarray, highs: np.ndarray,
                             lows: np.ndarray, periods: List[int]) -> List[AdaptiveMA]:
        """بناء عدة أنواع من المتوسطات"""
        mas = []
        
        for period in periods[:6]:
            if len(closes) < period:
                continue
            
            # EMA
            ema = self._calculate_ema(closes, period)
            mas.append(self._create_ma_obj('EMA', period, ema, closes))
            
            # HMA (Hull)
            if period >= 4:
                hma = self._calculate_hma(closes, period)
                mas.append(self._create_ma_obj('HMA', period, hma, closes))
            
            # KAMA (Kaufman Adaptive)
            if period >= 5:
                kama = self._calculate_kama(closes, period)
                mas.append(self._create_ma_obj('KAMA', period, kama, closes))
            
            # McGinley Dynamic
            mcginley = self._calculate_mcginley(closes, period)
            mas.append(self._create_ma_obj('McGinley', period, mcginley, closes))
        
        return mas
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """EMA ديناميكي"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def _calculate_hma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Hull Moving Average - أسرع وأدق"""
        half_period = max(1, int(period / 2))
        sqrt_period = max(1, int(np.sqrt(period)))
        
        wma_half = self._calculate_wma_safe(data, half_period)
        wma_full = self._calculate_wma_safe(data, period)
        
        raw_hma = 2 * wma_half - wma_full
        hma = self._calculate_wma_safe(raw_hma, sqrt_period)
        
        return hma
    
    def _calculate_wma_safe(self, data: np.ndarray, period: int) -> np.ndarray:
        """
        🔴 تعديل 2: WMA آمن مع قيم أولية (SMA لأول period)
        """
        weights = np.arange(1, period + 1)
        weights = weights / weights.sum()
        
        wma = np.zeros_like(data)
        
        # أول period-1: استخدم SMA
        for i in range(min(period - 1, len(data))):
            if i > 0:
                wma[i] = np.mean(data[:i+1])
            else:
                wma[i] = data[i]
        
        # بعد ذلك: WMA كامل
        for i in range(period - 1, len(data)):
            wma[i] = np.sum(data[i-period+1:i+1] * weights[::-1])
        
        return wma
    
    def _calculate_kama(self, data: np.ndarray, period: int) -> np.ndarray:
        """Kaufman Adaptive Moving Average"""
        kama = np.zeros_like(data)
        kama[period-1] = data[period-1]
        
        fastest = 2 / (2 + 1)
        slowest = 2 / (30 + 1)
        
        for i in range(period, len(data)):
            direction = abs(data[i] - data[i-period])
            volatility = sum(abs(data[j] - data[j-1]) for j in range(i-period+1, i+1))
            
            if volatility > 0:
                er = direction / volatility
            else:
                er = 0
            
            sc = (er * (fastest - slowest) + slowest) ** 2
            kama[i] = kama[i-1] + sc * (data[i] - kama[i-1])
        
        return kama
    
    def _calculate_mcginley(self, data: np.ndarray, period: int) -> np.ndarray:
        """McGinley Dynamic - يتكيف تلقائياً مع السرعة"""
        mg = np.zeros_like(data)
        mg[0] = data[0]
        
        for i in range(1, len(data)):
            if mg[i-1] != 0:
                mg[i] = mg[i-1] + (data[i] - mg[i-1]) / (period * (data[i] / mg[i-1]) ** 4)
            else:
                mg[i] = data[i]
        
        return mg
    
    def _create_ma_obj(self, ma_type: str, period: int, values: np.ndarray,
                        closes: np.ndarray) -> AdaptiveMA:
        """بناء كائن المتوسط - آمن"""
        if len(values) < 2:
            return AdaptiveMA(ma_type, ma_type, period, values, 0, 0, 'flat', 0)
        
        # 🔴 تعديل 1: تأكد من وجود قيم كافية
        safe_idx_1 = min(1, len(values)-1)
        safe_idx_3 = min(3, len(values)-1)
        safe_idx_5 = min(5, len(values)-1)
        
        # الميل
        if values[safe_idx_3] != 0:
            slope = (values[-1] - values[safe_idx_3]) / abs(values[safe_idx_3]) * 100
        else:
            slope = 0
        
        # التسارع
        if len(values) >= 5 and values[safe_idx_5] != 0:
            slope_prev = (values[safe_idx_3] - values[safe_idx_5]) / abs(values[safe_idx_5]) * 100
            acceleration = slope - slope_prev
        else:
            acceleration = 0
        
        # الاتجاه
        if slope > 0.02:
            direction = 'rising'
        elif slope < -0.02:
            direction = 'falling'
        else:
            direction = 'flat'
        
        # القوة
        if len(closes) > 0 and closes[-1] != 0:
            distance = abs(closes[-1] - values[-1]) / abs(closes[-1])
            strength = min(1.0, distance * 50)
        else:
            strength = 0.5
        
        # 🟡 تعديل 6: Displaced MA
        displacement = max(1, period // 4)
        displaced_forward = np.roll(values, -displacement) if len(values) > displacement else None
        displaced_backward = np.roll(values, displacement) if len(values) > displacement else None
        
        return AdaptiveMA(
            name=f"{ma_type}_{period}",
            ma_type=ma_type,
            period=period,
            values=values,
            slope=slope,
            acceleration=acceleration,
            direction=direction,
            strength=strength,
            displaced_forward=displaced_forward,
            displaced_backward=displaced_backward,
        )
    
    def _build_ribbon(self, mas: List[AdaptiveMA]) -> MARibbon:
        """بناء شريط المتوسطات - آمن"""
        if not mas:
            return MARibbon([], 'flat', 0, 'stable', 0, 'mixed')
        
        sorted_mas = sorted(mas, key=lambda m: m.values[-1] if len(m.values) > 0 else 0)
        
        fast_mas = [m for m in mas if m.period <= 13]
        slow_mas = [m for m in mas if m.period >= 55]
        
        fast_rising = sum(1 for m in fast_mas if m.direction == 'rising')
        slow_rising = sum(1 for m in slow_mas if m.direction == 'rising')
        
        if len(fast_mas) > 0 and fast_rising > len(fast_mas) * 0.7:
            if len(slow_mas) > 0 and slow_rising > len(slow_mas) * 0.7:
                alignment = 'bullish'
            else:
                alignment = 'mixed'
        elif len(fast_mas) > 0 and fast_rising < len(fast_mas) * 0.3:
            if len(slow_mas) > 0 and slow_rising < len(slow_mas) * 0.3:
                alignment = 'bearish'
            else:
                alignment = 'mixed'
        else:
            alignment = 'flat'
        
        # 🔴 تعديل 3: حساب spread بشكل آمن
        if len(sorted_mas) >= 2 and len(sorted_mas[0].values) >= 2 and len(sorted_mas[-1].values) >= 2:
            spread = sorted_mas[-1].values[-1] - sorted_mas[0].values[-1]
            spread_pct = spread / max(abs(sorted_mas[-1].values[-1]), 0.0001)
            
            prev_spread = sorted_mas[-1].values[-2] - sorted_mas[0].values[-2]
            if spread > prev_spread * 1.1:
                expansion = 'expanding'
            elif spread < prev_spread * 0.9:
                expansion = 'contracting'
            else:
                expansion = 'stable'
        else:
            spread = 0
            spread_pct = 0
            expansion = 'stable'
        
        # 🟡 تعديل 5: Rainbow Alignment
        rainbow = self._calculate_rainbow_alignment(sorted_mas)
        
        return MARibbon(
            mas=mas,
            alignment=alignment,
            spread=spread,
            expansion=expansion,
            strength=min(1.0, abs(spread_pct) * 20),
            rainbow_alignment=rainbow,
        )
    
    def _calculate_rainbow_alignment(self, sorted_mas: List[AdaptiveMA]) -> str:
        """
        🟡 تعديل 5: Rainbow Alignment
        
        إذا كانت المتوسطات مرتبة من الأصغر (فوق) إلى الأكبر (تحت) = Perfect Bullish
        إذا كانت معكوسة = Perfect Bearish
        """
        if len(sorted_mas) < 3:
            return 'mixed'
        
        # المتوسطات مرتبة حسب الفترة (الأصغر يفترض أن يكون أعلى في الصعود)
        periods = [m.period for m in sorted_mas]
        values = [m.values[-1] if len(m.values) > 0 else 0 for m in sorted_mas]
        
        # هل القيم مرتبة تنازلياً مع الفترة تصاعدياً؟
        # (المتوسط الأسرع أعلى من الأبطأ = صاعد مثالي)
        correct_order = 0
        for i in range(len(values)-1):
            if values[i] > values[i+1]:  # الأسرع فوق الأبطأ
                correct_order += 1
        
        ratio = correct_order / max(len(values)-1, 1)
        
        if ratio > 0.9:
            return 'perfect_bullish'
        elif ratio > 0.6:
            return 'bullish'
        elif ratio < 0.1:
            return 'perfect_bearish'
        elif ratio < 0.4:
            return 'bearish'
        else:
            return 'mixed'
    
    def _build_cloud(self, mas: List[AdaptiveMA], closes: np.ndarray) -> Dict:
        """بناء سحابة المتوسطات"""
        if len(mas) < 2:
            return {"exists": False}
        
        fast_mas = sorted(mas, key=lambda m: m.period)[:2]
        slow_mas = sorted(mas, key=lambda m: m.period, reverse=True)[:2]
        
        if len(fast_mas) >= 2 and len(slow_mas) >= 2:
            cloud_top = max(fast_mas[0].values[-1], fast_mas[1].values[-1])
            cloud_bottom = min(fast_mas[0].values[-1], fast_mas[1].values[-1])
            
            cloud_top_future = max(slow_mas[0].values[-1], slow_mas[1].values[-1])
            cloud_bottom_future = min(slow_mas[0].values[-1], slow_mas[1].values[-1])
            
            if cloud_top > cloud_top_future:
                cloud_color = 'bullish'
            else:
                cloud_color = 'bearish'
            
            current_price = closes[-1] if len(closes) > 0 else 0
            price_above_cloud = current_price > cloud_top
            price_below_cloud = current_price < cloud_bottom
            
            return {
                "exists": True,
                "cloud_top": cloud_top,
                "cloud_bottom": cloud_bottom,
                "cloud_color": cloud_color,
                "price_position": 'above' if price_above_cloud else 'below' if price_below_cloud else 'inside',
            }
        
        return {"exists": False}
    
    def _build_envelopes(self, mas: List[AdaptiveMA], closes: np.ndarray,
                          highs: np.ndarray, lows: np.ndarray) -> List[AdaptiveEnvelope]:
        """
        🟡 تعديل 4: Adaptive Envelope
        
        نطاقات حول المتوسط تتسع وتضيق مع التقلب (ATR)
        """
        envelopes = []
        
        if len(closes) < 14:
            return envelopes
        
        # حساب ATR
        atr = self._calculate_atr(highs, lows, closes, 14)
        
        for ma in mas[:4]:  # أول 4 متوسطات
            if len(ma.values) < 2:
                continue
            
            # النطاق = MA ± ATR * multiplier
            multiplier = 1.5 + (ma.period / 50)  # متوسطات أبطأ = نطاق أوسع
            
            upper = ma.values[-1] + atr * multiplier
            lower = ma.values[-1] - atr * multiplier
            
            # موقع السعر في النطاق
            if upper != lower:
                price_pos = (closes[-1] - lower) / (upper - lower) * 2 - 1
            else:
                price_pos = 0
            
            envelopes.append(AdaptiveEnvelope(
                ma_name=ma.name,
                upper_band=np.array([upper]),
                lower_band=np.array([lower]),
                current_upper=upper,
                current_lower=lower,
                bandwidth=(upper - lower) / max(abs(ma.values[-1]), 0.0001),
                price_position=price_pos,
            ))
        
        return envelopes
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, 
                        closes: np.ndarray, period: int = 14) -> float:
        """حساب ATR"""
        if len(closes) < period:
            return np.mean(highs - lows)
        
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        
        return np.mean(tr[-period:])
    
    def _build_rainbow(self, mas: List[AdaptiveMA], closes: np.ndarray) -> Dict:
        """
        🟡 تعديل 5: MA Rainbow
        
        تقييم كامل لقوس قزح المتوسطات
        """
        if len(mas) < 3:
            return {"exists": False}
        
        sorted_by_period = sorted(mas, key=lambda m: m.period)
        
        values = [m.values[-1] if len(m.values) > 0 else 0 for m in sorted_by_period]
        
        # هل المتوسطات في ترتيب صاعد (الأسرع فوق الأبطأ)؟
        bullish_aligned = all(values[i] > values[i+1] for i in range(len(values)-1))
        bearish_aligned = all(values[i] < values[i+1] for i in range(len(values)-1))
        
        if bullish_aligned:
            alignment = "قوس قزح صاعد مثالي"
            strength = 0.9
        elif bearish_aligned:
            alignment = "قوس قزح هابط مثالي"
            strength = 0.9
        else:
            # تحقق جزئي
            correct = sum(1 for i in range(len(values)-1) if values[i] > values[i+1])
            if correct > len(values) / 2:
                alignment = "قوس قزح صاعد جزئي"
                strength = 0.5
            else:
                alignment = "قوس قزح مختلط"
                strength = 0.3
        
        return {
            "exists": True,
            "alignment": alignment,
            "strength": strength,
            "bullish_aligned": bullish_aligned,
            "bearish_aligned": bearish_aligned,
            "price_vs_ma": "above_all" if closes[-1] > max(values) else "below_all" if closes[-1] < min(values) else "inside",
        }
    
    def _analyze_slopes(self, mas: List[AdaptiveMA]) -> Dict:
        """تحليل ميل المتوسطات"""
        if not mas:
            return {"trend": "none", "strength": 0}
        
        slopes = [m.slope for m in mas]
        avg_slope = np.mean(slopes)
        
        rising = sum(1 for s in slopes if s > 0.01)
        falling = sum(1 for s in slopes if s < -0.01)
        
        if rising > len(slopes) * 0.7:
            trend = "إجماع صاعد"
            strength = min(1.0, avg_slope * 20)
        elif falling > len(slopes) * 0.7:
            trend = "إجماع هابط"
            strength = min(1.0, abs(avg_slope) * 20)
        elif avg_slope > 0:
            trend = "ميل صاعد ضعيف"
            strength = 0.3
        elif avg_slope < 0:
            trend = "ميل هابط ضعيف"
            strength = 0.3
        else:
            trend = "مسطح"
            strength = 0.1
        
        return {"trend": trend, "avg_slope": avg_slope, "strength": strength}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الثانية: كاشف التقاطعات الديناميكية                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicCrossoverDetector:
    """
    يكتشف تقاطعات المتوسطات.
    ليس أي تقاطع - بل التقاطعات "ذات المعنى".
    """
    
    def analyze(self, mas: List[AdaptiveMA], closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """اكتشاف التقاطعات"""
        crossovers = self._detect_all_crossovers(mas, closes, volumes)
        golden_death = self._detect_golden_death(crossovers)
        
        return {
            "recent_crossovers": crossovers[-10:],
            "golden_cross": golden_death.get('golden'),
            "death_cross": golden_death.get('death'),
            "pending_crossovers": self._detect_pending_crossovers(mas),
        }
    
    def _detect_all_crossovers(self, mas: List[AdaptiveMA], closes: np.ndarray,
                                volumes: np.ndarray) -> List[MACrossover]:
        """اكتشاف كل التقاطعات المهمة"""
        crossovers = []
        
        if len(mas) < 2:
            return crossovers
        
        for i in range(len(mas)):
            for j in range(i+1, len(mas)):
                fast = mas[i] if mas[i].period < mas[j].period else mas[j]
                slow = mas[j] if mas[i].period < mas[j].period else mas[i]
                
                if len(fast.values) < 3 or len(slow.values) < 3:
                    continue
                
                for k in range(max(0, len(closes)-5), len(closes)-1):
                    if k+1 >= len(fast.values) or k+1 >= len(slow.values):
                        continue
                    
                    fast_above = fast.values[k] > slow.values[k]
                    fast_above_next = fast.values[k+1] > slow.values[k+1]
                    
                    if fast_above != fast_above_next:
                        direction = 'bullish' if fast_above_next else 'bearish'
                        angle = abs(fast.slope - slow.slope)
                        strength = min(1.0, angle * 10)
                        
                        avg_vol = np.mean(volumes[max(0,k-5):k+1]) if k >= 5 else volumes[k]
                        vol_confirm = volumes[k+1] > avg_vol * 1.2 if k+1 < len(volumes) else False
                        
                        fake_out_risk = 0.7 if (strength < 0.3 and not vol_confirm) else 0.2 if vol_confirm else 0.4
                        
                        crossovers.append(MACrossover(
                            index=k+1, fast_ma=fast.name, slow_ma=slow.name,
                            direction=direction, strength=strength, angle=angle,
                            confirmed=vol_confirm, fake_out_risk=fake_out_risk,
                        ))
        
        return crossovers
    
    def _detect_golden_death(self, crossovers: List[MACrossover]) -> Dict:
        """اكتشاف الصليب الذهبي وصليب الموت"""
        result = {'golden': None, 'death': None}
        
        for c in crossovers:
            fast_period = int(c.fast_ma.split('_')[-1]) if '_' in c.fast_ma else 0
            slow_period = int(c.slow_ma.split('_')[-1]) if '_' in c.slow_ma else 0
            
            if c.direction == 'bullish' and c.strength > 0.5 and fast_period <= 21 and slow_period >= 34:
                if result['golden'] is None or c.strength > result['golden'].strength:
                    result['golden'] = c
            
            if c.direction == 'bearish' and c.strength > 0.5 and fast_period <= 21 and slow_period >= 34:
                if result['death'] is None or c.strength > result['death'].strength:
                    result['death'] = c
        
        return result
    
    def _detect_pending_crossovers(self, mas: List[AdaptiveMA]) -> List[Dict]:
        """اكتشاف تقاطعات وشيكة"""
        pending = []
        
        for i in range(len(mas)):
            for j in range(i+1, len(mas)):
                fast = mas[i] if mas[i].period < mas[j].period else mas[j]
                slow = mas[j] if mas[i].period < mas[j].period else mas[i]
                
                if len(fast.values) < 2 or len(slow.values) < 2:
                    continue
                
                current_diff = fast.values[-1] - slow.values[-1]
                prev_diff = fast.values[-2] - slow.values[-2]
                
                if abs(current_diff) < abs(prev_diff) and current_diff * prev_diff > 0:
                    if abs(current_diff - prev_diff) > 0:
                        bars_to_cross = abs(current_diff) / abs(current_diff - prev_diff)
                    else:
                        bars_to_cross = 99
                    
                    if bars_to_cross < 5:
                        pending.append({
                            "fast_ma": fast.name,
                            "slow_ma": slow.name,
                            "direction": 'bullish' if current_diff < 0 else 'bearish',
                            "bars_estimated": int(bars_to_cross),
                            "current_distance": current_diff,
                        })
        
        return pending[:5]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثالثة: محلل المسافة والارتداد (Mean Reversion Analyzer)    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MeanReversionAnalyzer:
    """
    يحلل مسافة السعر عن متوسطاته.
    """
    
    def analyze(self, closes: np.ndarray, mas: List[AdaptiveMA]) -> Dict:
        """تحليل المسافة عن المتوسطات"""
        distances = self._calculate_distances(closes, mas)
        extremes = self._detect_extremes(distances, closes)
        
        return {
            "distances": distances,
            "extremes": extremes,
            "mean_reversion_pressure": self._calculate_pressure(distances),
        }
    
    def _calculate_distances(self, closes: np.ndarray, mas: List[AdaptiveMA]) -> List[Dict]:
        """حساب مسافة السعر عن كل متوسط"""
        distances = []
        
        if len(closes) == 0:
            return distances
        
        current = closes[-1]
        
        for ma in mas:
            if len(ma.values) == 0:
                continue
            
            ma_value = ma.values[-1]
            if ma_value != 0:
                distance_pct = (current - ma_value) / ma_value * 100
            else:
                distance_pct = 0
            
            if len(closes) >= 20:
                std = np.std(closes[-20:])
                distance_std = (current - ma_value) / std if std > 0 else 0
            else:
                distance_std = distance_pct
            
            distances.append({
                "ma_name": ma.name,
                "ma_value": ma_value,
                "distance_pct": distance_pct,
                "distance_std": distance_std,
                "extreme": abs(distance_std) > 2.0,
            })
        
        return distances
    
    def _detect_extremes(self, distances: List[Dict], closes: np.ndarray) -> Dict:
        """اكتشاف الانحرافات المتطرفة"""
        if not distances:
            return {"detected": False}
        
        extremes = [d for d in distances if d.get('extreme')]
        
        if extremes:
            avg_distance = np.mean([d['distance_std'] for d in extremes])
            
            if avg_distance > 0:
                signal = "هبوط متوقع"
            else:
                signal = "صعود متوقع"
            
            return {
                "detected": True,
                "extremes_count": len(extremes),
                "signal": signal,
                "avg_distance_std": avg_distance,
            }
        
        return {"detected": False}
    
    def _calculate_pressure(self, distances: List[Dict]) -> Dict:
        """حساب ضغط العودة للمتوسط"""
        if not distances:
            return {"direction": "none", "strength": 0}
        
        avg_distance = np.mean([d['distance_std'] for d in distances])
        
        if avg_distance > 1.5:
            pressure = "ضغط هبوطي قوي"
            strength = min(1.0, avg_distance / 4)
        elif avg_distance > 0.5:
            pressure = "ضغط هبوطي"
            strength = 0.4
        elif avg_distance < -1.5:
            pressure = "ضغط صعودي قوي"
            strength = min(1.0, abs(avg_distance) / 4)
        elif avg_distance < -0.5:
            pressure = "ضغط صعودي"
            strength = 0.4
        else:
            pressure = "متوازن"
            strength = 0.1
        
        return {"direction": pressure, "strength": strength, "avg_distance_std": avg_distance}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية المتوسطات الموحدة (محسنة)           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicMovingAverageStrategy:
    """
    استراتيجية المتوسطات المتحركة الديناميكية الكاملة - الإصدار 2.0
    
    لا تستخدم 50 و 200 ثابتين.
    كل شيء يتكيف مع السوق.
    """
    
    def __init__(self):
        self.ma_engineer = DynamicMovingAverageEngineer()
        self.crossover_detector = DynamicCrossoverDetector()
        self.mean_reversion = MeanReversionAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        ma_data = self.ma_engineer.analyze(closes, highs, lows, volumes)
        mas = ma_data.get('mas', [])
        crossover_data = self.crossover_detector.analyze(mas, closes, volumes)
        mr_data = self.mean_reversion.analyze(closes, mas)
        decision = self._make_decision(ma_data, crossover_data, mr_data, closes)
        
        return {**decision, "ma_data": ma_data, "crossover_data": crossover_data, "mr_data": mr_data}
    
    def _make_decision(self, ma_data: Dict, crossover_data: Dict,
                       mr_data: Dict, closes: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        
        # ---- من الشريط ----
        ribbon = ma_data.get('ribbon')
        if ribbon:
            if ribbon.alignment == 'bullish' and ribbon.strength > 0.3:
                buy_signals.append(("شريط متوسطات صاعد", ribbon.strength * 0.6))
            elif ribbon.alignment == 'bearish' and ribbon.strength > 0.3:
                sell_signals.append(("شريط متوسطات هابط", ribbon.strength * 0.6))
            
            if ribbon.expansion == 'expanding':
                if ribbon.alignment == 'bullish':
                    buy_signals.append(("اتساع الشريط - قوة الصعود", 0.5))
                elif ribbon.alignment == 'bearish':
                    sell_signals.append(("اتساع الشريط - قوة الهبوط", 0.5))
            
            # 🟡 تعديل 5: Rainbow
            if ribbon.rainbow_alignment == 'perfect_bullish':
                buy_signals.append(("قوس قزح صاعد مثالي", 0.65))
            elif ribbon.rainbow_alignment == 'perfect_bearish':
                sell_signals.append(("قوس قزح هابط مثالي", 0.65))
            elif ribbon.rainbow_alignment == 'bullish':
                buy_signals.append(("قوس قزح صاعد", 0.4))
            elif ribbon.rainbow_alignment == 'bearish':
                sell_signals.append(("قوس قزح هابط", 0.4))
        
        # ---- من السحابة ----
        cloud = ma_data.get('cloud', {})
        if cloud.get('exists'):
            if cloud.get('cloud_color') == 'bullish' and cloud.get('price_position') == 'above':
                buy_signals.append(("سحابة صاعدة + السعر فوقها", 0.55))
            elif cloud.get('cloud_color') == 'bearish' and cloud.get('price_position') == 'below':
                sell_signals.append(("سحابة هابطة + السعر تحتها", 0.55))
        
        # ---- من التقاطعات ----
        golden = crossover_data.get('golden_cross')
        death = crossover_data.get('death_cross')
        
        if golden:
            buy_signals.append((f"صليب ذهبي ({golden.fast_ma} × {golden.slow_ma})", 0.7))
        if death:
            sell_signals.append((f"صليب موت ({death.fast_ma} × {death.slow_ma})", 0.7))
        
        # ---- من Envelopes ----
        envelopes = ma_data.get('envelopes', [])
        for env in envelopes:
            if env.price_position > 0.8:
                sell_signals.append((f"سعر عند أعلى نطاق {env.ma_name}", 0.4))
            elif env.price_position < -0.8:
                buy_signals.append((f"سعر عند أسفل نطاق {env.ma_name}", 0.4))
        
        # ---- من Rainbow ----
        rainbow = ma_data.get('rainbow', {})
        if rainbow.get('exists'):
            if rainbow.get('price_vs_ma') == 'above_all':
                buy_signals.append(("السعر فوق كل المتوسطات - قوة", 0.45))
            elif rainbow.get('price_vs_ma') == 'below_all':
                sell_signals.append(("السعر تحت كل المتوسطات - ضعف", 0.45))
        
        # ---- من المتوسطات والميل ----
        slope = ma_data.get('slope_analysis', {})
        if slope.get('trend') == 'إجماع صاعد':
            buy_signals.append(("إجماع متوسطات صاعد", 0.5))
        elif slope.get('trend') == 'إجماع هابط':
            sell_signals.append(("إجماع متوسطات هابط", 0.5))
        
        # ---- من المسافة ----
        pressure = mr_data.get('mean_reversion_pressure', {})
        if pressure.get('strength', 0) > 0.6:
            if 'هبوطي' in pressure.get('direction', ''):
                sell_signals.append((pressure['direction'], pressure['strength'] * 0.5))
            elif 'صعودي' in pressure.get('direction', ''):
                buy_signals.append((pressure['direction'], pressure['strength'] * 0.5))
        
        extremes = mr_data.get('extremes', {})
        if extremes.get('detected'):
            if 'صعود' in extremes.get('signal', ''):
                buy_signals.append(("انحراف متطرف - ارتداد متوقع", 0.6))
            elif 'هبوط' in extremes.get('signal', ''):
                sell_signals.append(("انحراف متطرف - ارتداد متوقع", 0.6))
        
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
        reason += f" | سرعة: {ma_data.get('market_speed', {}).get('speed', '?')}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_moving_averages_strategy():
    """إنشاء استراتيجية المتوسطات الديناميكية الجاهزة (الإصدار 2.0)"""
    return DynamicMovingAverageStrategy()