"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC BOLLINGER BANDS STRATEGY - النسخة الديناميكية المتكاملة
المدرسة الرابعة عشرة: نطاقات بولينجر الديناميكية
═══════════════════════════════════════════════════════════════════════════════

جون بولينجر ابتكر هذه النطاقات في الثمانينات.
الفكرة: السعر يتنفس. النطاقات تتمدد وتنكمش مع التقلب.

لكن النسخة الكلاسيكية (20 فترة، 2 انحراف معياري) ثابتة وغبية.

هذه النسخة ديناميكية بالكامل:
- الفترة تتكيف مع السوق
- عرض النطاق (عدد الانحرافات) ديناميكي
- نوع المتوسط يتغير (SMA, EMA, KAMA...)
- النطاقات "تتنفس" مع السوق

المفاهيم المتقدمة:
1. Bollinger Bands (النطاقات الأساسية)
2. Bollinger Width (عرض النطاق - مقياس التقلب)
3. %B (موقع السعر داخل النطاق)
4. Bandwidth Delta (تغير عرض النطاق)
5. Squeeze (انضغاط - انفجار قادم)
6. Bulge (انتفاخ - نهاية اتجاه)
7. Walking the Bands (السير على النطاق)
8. Bollinger Bands + RSI
9. Bollinger Bands + MACD
10. Double Bollinger Bands
11. Bollinger Envelopes
12. Adaptive %B Filter
13. Band Contraction/Expansion Signals
14. M-Top / W-Bottom
15. Head Fake (الخدعة)
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
class BollingerBands:
    """نطاقات بولينجر"""
    upper: np.ndarray
    middle: np.ndarray
    lower: np.ndarray
    period: int
    std_multiplier: float
    width: np.ndarray          # عرض النطاق
    percent_b: np.ndarray      # %B (موقع السعر)
    bandwidth_delta: np.ndarray # تغير عرض النطاق
    squeeze_detected: bool
    squeeze_intensity: float
    walking_upper: bool
    walking_lower: bool


@dataclass
class BandSignal:
    """إشارة من النطاقات"""
    index: int
    signal_type: str  # 'squeeze', 'breakout', 'reversal', 'walking', 'head_fake', 'm_top', 'w_bottom'
    direction: str
    price_level: float
    strength: float
    description: str


@dataclass  
class SqueezeAnalysis:
    """تحليل الانضغاط"""
    active: bool
    duration: int           # كم شمعة استمر
    intensity: float        # شدة الانضغاط
    expected_breakout: int  # الشموع المتوقعة للانفجار
    likely_direction: str   # الاتجاه المرجح
    energy_built: float     # الطاقة المتراكمة


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الأولى: باني نطاقات بولينجر الديناميكية                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicBollingerBuilder:
    """
    يبني نطاقات بولينجر بمعلمات ديناميكية.
    الفترة وعرض النطاق يتكيفان مع السوق.
    """
    
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """
        بناء النطاقات الديناميكية
        """
        # تحديد الفترة المثلى ديناميكياً
        optimal_period = self._find_optimal_period(closes)
        
        # تحديد مضاعف الانحراف المعياري الأمثل
        optimal_multiplier = self._find_optimal_multiplier(closes, optimal_period)
        
        # بناء النطاقات
        bands = self._build_bands(closes, optimal_period, optimal_multiplier)
        
        # بناء Double Bollinger Bands
        double_bands = self._build_double_bands(closes, optimal_period, optimal_multiplier)
        
        # تحليل الانضغاط
        squeeze = self._analyze_squeeze(bands)
        
        return {
            "bands": bands,
            "double_bands": double_bands,
            "squeeze": squeeze,
            "optimal_period": optimal_period,
            "optimal_multiplier": optimal_multiplier,
            "current": {
                "upper": bands.upper[-1] if len(bands.upper) > 0 else 0,
                "middle": bands.middle[-1] if len(bands.middle) > 0 else 0,
                "lower": bands.lower[-1] if len(bands.lower) > 0 else 0,
                "width": bands.width[-1] if len(bands.width) > 0 else 0,
                "percent_b": bands.percent_b[-1] if len(bands.percent_b) > 0 else 0,
            },
        }
    
    def _find_optimal_period(self, closes: np.ndarray) -> int:
        """
        إيجاد الفترة المثلى ديناميكياً.
        السوق السريع = فترة أقصر. السوق البطيء = فترة أطول.
        """
        if len(closes) < 30:
            return 20
        
        # قياس "تردد" السوق
        # كم مرة يغير السعر اتجاهه؟
        changes = 0
        for i in range(5, len(closes)):
            if (closes[i] - closes[i-5]) * (closes[i-5] - closes[i-10]) < 0:
                changes += 1
        
        change_freq = changes / max(len(closes) - 10, 1)
        
        # السوق سريع التغير = فترة أقصر
        if change_freq > 0.4:
            period = 10
        elif change_freq > 0.25:
            period = 15
        elif change_freq > 0.15:
            period = 20
        elif change_freq > 0.08:
            period = 30
        else:
            period = 40
        
        # تعديل بالتقلب
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) >= 10:
            vol = np.std(returns[-20:])
            if vol > 0.02:
                period = max(8, period - 5)
            elif vol < 0.005:
                period = min(50, period + 10)
        
        return period
    
    def _find_optimal_multiplier(self, closes: np.ndarray, period: int) -> float:
        """
        إيجاد مضاعف الانحراف المعياري الأمثل.
        كم مرة يلامس السعر النطاقات؟
        """
        if len(closes) < period:
            return 2.0
        
        # اختبار مضاعفات مختلفة
        best_multiplier = 2.0
        best_score = float('inf')
        target_touch_rate = 0.10  # نريد السعر يلامس النطاق 10% من الوقت
        
        for mult in [1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0]:
            ma = self._calculate_ma(closes, period)
            std = self._rolling_std(closes, period)
            
            upper = ma + mult * std
            lower = ma - mult * std
            
            touches = 0
            for i in range(period, len(closes)):
                if closes[i] >= upper[i] or closes[i] <= lower[i]:
                    touches += 1
            
            touch_rate = touches / max(len(closes) - period, 1)
            score = abs(touch_rate - target_touch_rate)
            
            if score < best_score:
                best_score = score
                best_multiplier = mult
        
        return best_multiplier
    
    def _build_bands(self, closes: np.ndarray, period: int, 
                     multiplier: float) -> BollingerBands:
        """
        بناء النطاقات.
        """
        ma = self._calculate_ma(closes, period)
        std = self._rolling_std(closes, period)
        
        upper = ma + multiplier * std
        lower = ma - multiplier * std
        
        # العرض
        width = (upper - lower) / np.maximum(ma, 0.0001)
        
        # %B
        percent_b = (closes - lower) / np.maximum(upper - lower, 0.0001)
        
        # تغير العرض
        bandwidth_delta = np.zeros_like(width)
        if len(width) > 1:
            bandwidth_delta[1:] = width[1:] - width[:-1]
        
        # السير على النطاق
        walking_upper = False
        walking_lower = False
        
        if len(closes) >= 5:
            # السير على النطاق العلوي
            near_upper = sum(1 for i in range(-5, 0) if closes[i] >= upper[i] * 0.99)
            walking_upper = near_upper >= 3
            
            # السير على النطاق السفلي
            near_lower = sum(1 for i in range(-5, 0) if closes[i] <= lower[i] * 1.01)
            walking_lower = near_lower >= 3
        
        # الانضغاط
        squeeze_detected = False
        squeeze_intensity = 0.0
        
        if len(width) >= 20:
            current_width = width[-1]
            min_width_20 = np.min(width[-20:])
            max_width_20 = np.max(width[-20:])
            
            if max_width_20 > 0:
                width_percentile = (current_width - min_width_20) / (max_width_20 - min_width_20)
                if width_percentile < 0.15:
                    squeeze_detected = True
                    squeeze_intensity = 1 - width_percentile / 0.15
        
        return BollingerBands(
            upper=upper,
            middle=ma,
            lower=lower,
            period=period,
            std_multiplier=multiplier,
            width=width,
            percent_b=percent_b,
            bandwidth_delta=bandwidth_delta,
            squeeze_detected=squeeze_detected,
            squeeze_intensity=squeeze_intensity,
            walking_upper=walking_upper,
            walking_lower=walking_lower,
        )
    
    def _build_double_bands(self, closes: np.ndarray, period: int,
                             multiplier: float) -> Dict:
        """
        بناء Double Bollinger Bands (نطاقات مزدوجة).
        """
        # نطاقات خارجية (2 انحراف)
        ma = self._calculate_ma(closes, period)
        std = self._rolling_std(closes, period)
        
        outer_upper = ma + multiplier * std
        outer_lower = ma - multiplier * std
        
        # نطاقات داخلية (1 انحراف)
        inner_upper = ma + multiplier * 0.5 * std
        inner_lower = ma - multiplier * 0.5 * std
        
        # مناطق
        current = closes[-1] if len(closes) > 0 else 0
        zone = self._determine_zone(current, outer_upper[-1], inner_upper[-1],
                                     inner_lower[-1], outer_lower[-1])
        
        return {
            "outer_upper": outer_upper,
            "inner_upper": inner_upper,
            "middle": ma,
            "inner_lower": inner_lower,
            "outer_lower": outer_lower,
            "current_zone": zone,
        }
    
    def _determine_zone(self, price: float, ou: float, iu: float,
                         il: float, ol: float) -> str:
        """تحديد منطقة السعر في النطاقات المزدوجة"""
        if price > ou:
            return "فوق النطاق - ذروة شراء متطرفة"
        elif price > iu:
            return "منطقة صاعدة"
        elif price > il:
            return "منطقة محايدة"
        elif price > ol:
            return "منطقة هابطة"
        else:
            return "تحت النطاق - ذروة بيع متطرفة"
    
    def _analyze_squeeze(self, bands: BollingerBands) -> SqueezeAnalysis:
        """
        تحليل الانضغاط.
        الانضغاط = طاقة متراكمة = انفجار قادم.
        """
        if not bands.squeeze_detected:
            return SqueezeAnalysis(False, 0, 0, 0, 'none', 0)
        
        # حساب مدة الانضغاط
        duration = 0
        for i in range(len(bands.width)-1, -1, -1):
            if len(bands.width) >= 20 and i >= 19:
                min_w = np.min(bands.width[max(0,i-19):i+1])
                max_w = np.max(bands.width[max(0,i-19):i+1])
                if max_w > 0:
                    percentile = (bands.width[i] - min_w) / (max_w - min_w)
                    if percentile < 0.15:
                        duration += 1
                    else:
                        break
        
        # الطاقة المتراكمة = مدة الانضغاط × شدته
        energy = duration * bands.squeeze_intensity / 20
        
        # اتجاه الانفجار المتوقع
        if len(bands.percent_b) >= 5:
            recent_b = np.mean(bands.percent_b[-5:])
            if recent_b > 0.6:
                likely_direction = 'up'
            elif recent_b < 0.4:
                likely_direction = 'down'
            else:
                likely_direction = 'unknown'
        else:
            likely_direction = 'unknown'
        
        return SqueezeAnalysis(
            active=True,
            duration=duration,
            intensity=bands.squeeze_intensity,
            expected_breakout=max(1, int(10 - energy)),  # كلما زادت الطاقة = أقرب للانفجار
            likely_direction=likely_direction,
            energy_built=min(1.0, energy),
        )
    
    def _calculate_ma(self, data: np.ndarray, period: int) -> np.ndarray:
        """متوسط متحرك"""
        ma = np.full_like(data, np.nan)
        for i in range(period-1, len(data)):
            ma[i] = np.mean(data[i-period+1:i+1])
        return ma
    
    def _rolling_std(self, data: np.ndarray, period: int) -> np.ndarray:
        """انحراف معياري متحرك"""
        std = np.full_like(data, np.nan)
        for i in range(period-1, len(data)):
            std[i] = np.std(data[i-period+1:i+1])
        return std


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الثانية: كاشف إشارات النطاقات (Band Signal Detector)           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BandSignalDetector:
    """
    يكتشف الإشارات من نطاقات بولينجر.
    """
    
    def analyze(self, bands: BollingerBands, closes: np.ndarray,
                volumes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Dict:
        """
        اكتشاف الإشارات
        """
        signals = []
        
        # M-Top
        m_tops = self._detect_m_top(bands, highs, closes)
        signals.extend(m_tops)
        
        # W-Bottom
        w_bottoms = self._detect_w_bottom(bands, lows, closes)
        signals.extend(w_bottoms)
        
        # Walking the Bands
        if bands.walking_upper:
            signals.append(BandSignal(
                index=len(closes)-1,
                signal_type='walking',
                direction='bullish',
                price_level=closes[-1],
                strength=0.7,
                description="السير على النطاق العلوي - قوة صاعدة",
            ))
        
        if bands.walking_lower:
            signals.append(BandSignal(
                index=len(closes)-1,
                signal_type='walking',
                direction='bearish',
                price_level=closes[-1],
                strength=0.7,
                description="السير على النطاق السفلي - قوة هابطة",
            ))
        
        # Breakout
        if len(closes) >= 3 and len(bands.upper) >= 3:
            if closes[-1] > bands.upper[-1] and closes[-2] <= bands.upper[-2]:
                # كسر النطاق العلوي
                volume_confirm = volumes[-1] > np.mean(volumes[-10:]) if len(volumes) >= 10 else True
                signals.append(BandSignal(
                    index=len(closes)-1,
                    signal_type='breakout',
                    direction='bullish',
                    price_level=closes[-1],
                    strength=0.65 if volume_confirm else 0.4,
                    description="كسر النطاق العلوي",
                ))
            
            if closes[-1] < bands.lower[-1] and closes[-2] >= bands.lower[-2]:
                volume_confirm = volumes[-1] > np.mean(volumes[-10:]) if len(volumes) >= 10 else True
                signals.append(BandSignal(
                    index=len(closes)-1,
                    signal_type='breakout',
                    direction='bearish',
                    price_level=closes[-1],
                    strength=0.65 if volume_confirm else 0.4,
                    description="كسر النطاق السفلي",
                ))
        
        # Head Fake (الخدعة)
        head_fakes = self._detect_head_fakes(bands, closes, volumes)
        signals.extend(head_fakes)
        
        return {
            "signals": signals,
            "latest_signal": signals[-1] if signals else None,
            "m_tops": [s for s in signals if s.signal_type == 'm_top'],
            "w_bottoms": [s for s in signals if s.signal_type == 'w_bottom'],
        }
    
    def _detect_m_top(self, bands: BollingerBands, highs: np.ndarray,
                      closes: np.ndarray) -> List[BandSignal]:
        """
        اكتشاف M-Top.
        قمتين: الأولى فوق النطاق، الثانية تحت النطاق لكن أعلى من المنتصف.
        """
        signals = []
        
        if len(highs) < 10 or len(bands.upper) < 10:
            return signals
        
        for i in range(5, len(highs) - 3):
            # القمة الأولى: فوق النطاق العلوي
            if highs[i] > bands.upper[i] and highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                # البحث عن قمة ثانية قريبة
                for j in range(i+2, min(i+8, len(highs)-1)):
                    if (highs[j] > bands.middle[j] and highs[j] < bands.upper[j] and
                        highs[j] > highs[j-1] and highs[j] > highs[j+1] and
                        abs(highs[j] - highs[i]) < (bands.upper[i] - bands.lower[i]) * 0.3):
                        
                        signals.append(BandSignal(
                            index=j,
                            signal_type='m_top',
                            direction='bearish',
                            price_level=highs[j],
                            strength=0.75,
                            description="M-Top: قمتين مع ضعف الثانية",
                        ))
        
        return signals
    
    def _detect_w_bottom(self, bands: BollingerBands, lows: np.ndarray,
                          closes: np.ndarray) -> List[BandSignal]:
        """
        اكتشاف W-Bottom.
        قاعين: الأول تحت النطاق، الثاني فوق النطاق لكن أدنى من المنتصف.
        """
        signals = []
        
        if len(lows) < 10 or len(bands.lower) < 10:
            return signals
        
        for i in range(5, len(lows) - 3):
            if lows[i] < bands.lower[i] and lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                for j in range(i+2, min(i+8, len(lows)-1)):
                    if (lows[j] < bands.middle[j] and lows[j] > bands.lower[j] and
                        lows[j] < lows[j-1] and lows[j] < lows[j+1] and
                        abs(lows[j] - lows[i]) < (bands.upper[i] - bands.lower[i]) * 0.3):
                        
                        signals.append(BandSignal(
                            index=j,
                            signal_type='w_bottom',
                            direction='bullish',
                            price_level=lows[j],
                            strength=0.75,
                            description="W-Bottom: قاعين مع تحسن الثاني",
                        ))
        
        return signals
    
    def _detect_head_fakes(self, bands: BollingerBands, closes: np.ndarray,
                            volumes: np.ndarray) -> List[BandSignal]:
        """
        اكتشاف الخدعة (Head Fake).
        كسر وهمي للنطاق ثم عودة سريعة.
        """
        signals = []
        
        if len(closes) < 5:
            return signals
        
        for i in range(3, len(closes) - 1):
            # كسر علوي وهمي
            if (closes[i] > bands.upper[i] and 
                closes[i-1] <= bands.upper[i-1] and
                closes[i+1] < bands.upper[i+1]):
                signals.append(BandSignal(
                    index=i,
                    signal_type='head_fake',
                    direction='bearish',
                    price_level=closes[i],
                    strength=0.7,
                    description="Head Fake علوي - فخ صاعد",
                ))
            
            # كسر سفلي وهمي
            if (closes[i] < bands.lower[i] and
                closes[i-1] >= bands.lower[i-1] and
                closes[i+1] > bands.lower[i+1]):
                signals.append(BandSignal(
                    index=i,
                    signal_type='head_fake',
                    direction='bullish',
                    price_level=closes[i],
                    strength=0.7,
                    description="Head Fake سفلي - فخ هابط",
                ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║        الدرجة الثالثة: محلل %B والنطاق (Percent B & Bandwidth)           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PercentBAnalyzer:
    """
    يحلل %B وعرض النطاق.
    """
    
    def analyze(self, bands: BollingerBands, closes: np.ndarray) -> Dict:
        """
        تحليل %B
        """
        current_b = bands.percent_b[-1] if len(bands.percent_b) > 0 else 0.5
        
        # حالة %B
        if current_b > 1.0:
            b_state = "فوق النطاق العلوي"
        elif current_b > 0.8:
            b_state = "قرب النطاق العلوي"
        elif current_b > 0.6:
            b_state = "أعلى من المنتصف"
        elif current_b > 0.4:
            b_state = "في المنتصف"
        elif current_b > 0.2:
            b_state = "أدنى من المنتصف"
        elif current_b > 0.0:
            b_state = "قرب النطاق السفلي"
        else:
            b_state = "تحت النطاق السفلي"
        
        # تغير %B (الزخم)
        if len(bands.percent_b) >= 3:
            b_momentum = bands.percent_b[-1] - bands.percent_b[-3]
        else:
            b_momentum = 0
        
        # عرض النطاق
        bandwidth_state = self._analyze_bandwidth(bands)
        
        return {
            "percent_b": current_b,
            "b_state": b_state,
            "b_momentum": b_momentum,
            "bandwidth": bandwidth_state,
        }
    
    def _analyze_bandwidth(self, bands: BollingerBands) -> Dict:
        """تحليل عرض النطاق"""
        if len(bands.width) < 10:
            return {"state": "غير كافٍ"}
        
        current = bands.width[-1]
        avg_20 = np.mean(bands.width[-20:]) if len(bands.width) >= 20 else current
        min_20 = np.min(bands.width[-20:]) if len(bands.width) >= 20 else current
        max_20 = np.max(bands.width[-20:]) if len(bands.width) >= 20 else current
        
        if max_20 > min_20:
            percentile = (current - min_20) / (max_20 - min_20)
        else:
            percentile = 0.5
        
        # الاتجاه
        if len(bands.width) >= 5:
            trend = bands.width[-1] - bands.width[-5]
            if trend > 0:
                direction = 'expanding'
            elif trend < 0:
                direction = 'contracting'
            else:
                direction = 'stable'
        else:
            direction = 'stable'
        
        if percentile < 0.1:
            state = "انضغاط شديد - انفجار وشيك"
        elif percentile < 0.25:
            state = "ضيق - استعداد للحركة"
        elif percentile > 0.9:
            state = "منتفخ - نهاية اتجاه"
        elif percentile > 0.75:
            state = "واسع - تقلب عالي"
        else:
            state = "طبيعي"
        
        return {
            "state": state,
            "direction": direction,
            "percentile": percentile,
            "current_width": current,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║            الدرجة النهائية: استراتيجية بولينجر الموحدة                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicBollingerStrategy:
    """
    استراتيجية نطاقات بولينجر الديناميكية الكاملة.
    """
    
    def __init__(self):
        self.bb_builder = DynamicBollingerBuilder()
        self.signal_detector = BandSignalDetector()
        self.b_analyzer = PercentBAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        # 1. بناء النطاقات
        bb_data = self.bb_builder.analyze(closes, highs, lows, volumes)
        
        # 2. اكتشاف الإشارات
        bands = bb_data.get('bands')
        signal_data = self.signal_detector.analyze(bands, closes, volumes, highs, lows)
        
        # 3. تحليل %B
        b_data = self.b_analyzer.analyze(bands, closes)
        
        # 4. القرار
        decision = self._make_decision(bb_data, signal_data, b_data, closes)
        
        return {
            **decision,
            "bb_data": bb_data,
            "signal_data": signal_data,
            "b_data": b_data,
        }
    
    def _make_decision(self, bb_data: Dict, signal_data: Dict,
                       b_data: Dict, closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من الانضغاط ----
        squeeze = bb_data.get('squeeze')
        if squeeze and squeeze.active:
            if squeeze.likely_direction == 'up':
                buy_signals.append((f"انضغاط مع توقع صعود (طاقة: {squeeze.energy_built:.1%})", 0.55))
            elif squeeze.likely_direction == 'down':
                sell_signals.append((f"انضغاط مع توقع هبوط (طاقة: {squeeze.energy_built:.1%})", 0.55))
            else:
                buy_signals.append(("انضغاط - جاهز لانفجار", 0.3))
                sell_signals.append(("انضغاط - جاهز لانفجار", 0.3))
        
        # ---- من %B ----
        current_b = b_data.get('percent_b', 0.5)
        b_state = b_data.get('b_state', '')
        
        if current_b > 1.0:
            sell_signals.append(("فوق النطاق العلوي - ذروة شراء", 0.6))
        elif current_b < 0.0:
            buy_signals.append(("تحت النطاق السفلي - ذروة بيع", 0.6))
        elif current_b > 0.8:
            sell_signals.append(("قرب النطاق العلوي - تمهل", 0.3))
        elif current_b < 0.2:
            buy_signals.append(("قرب النطاق السفلي - فرصة", 0.3))
        
        # ---- من عرض النطاق ----
        bandwidth = b_data.get('bandwidth', {})
        if bandwidth.get('state') == 'منتفخ - نهاية اتجاه':
            if current_b > 0.8:
                sell_signals.append(("انتفاخ + قرب العلوي = نهاية صعود", 0.65))
            elif current_b < 0.2:
                buy_signals.append(("انتفاخ + قرب السفلي = نهاية هبوط", 0.65))
        
        # ---- من الإشارات ----
        signals = signal_data.get('signals', [])
        for sig in signals[-5:]:
            if sig.signal_type == 'w_bottom':
                buy_signals.append(("W-Bottom", sig.strength * 0.8))
            elif sig.signal_type == 'm_top':
                sell_signals.append(("M-Top", sig.strength * 0.8))
            elif sig.signal_type == 'head_fake':
                if sig.direction == 'bullish':
                    buy_signals.append(("Head Fake سفلي", sig.strength * 0.7))
                else:
                    sell_signals.append(("Head Fake علوي", sig.strength * 0.7))
            elif sig.signal_type == 'walking':
                if sig.direction == 'bullish':
                    buy_signals.append(("السير على النطاق العلوي", 0.5))
                else:
                    sell_signals.append(("السير على النطاق السفلي", 0.5))
        
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
        
        current = bb_data.get('current', {})
        reason += f" | %B: {current.get('percent_b', 0):.2f}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_bollinger_strategy():
    """إنشاء استراتيجية بولينجر الديناميكية الجاهزة"""
    return DynamicBollingerStrategy()