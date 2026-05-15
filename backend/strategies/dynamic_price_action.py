"""
═══════════════════════════════════════════════════════════════════════════════
PRICE ACTION DYNAMIC ADVANCED - النسخة الكاملة والنهائية
المدرسة الأولى: حركة السعر الديناميكية المتقدمة
═══════════════════════════════════════════════════════════════════════════════

هذا الملف يحتوي على كل ما يتعلق بمدرسة البرايس أكشن:
- الأساسيات الكلاسيكية
- التقنيات المتقدمة
- الأسرار المخفية
- ما يتداوله المحترفون فقط
- كل شيء تم ذكره في الموسوعة

الفلسفة:
السعر كائن حي. لا أرقام ثابتة. لا نسب جامدة.
كل شيء يقرأ من سلوك السعر نفسه في لحظته.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات الأساسية                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class SwingPoint:
    """نقطة تأرجح في هيكل السوق"""
    index: int
    price: float
    swing_type: str  # 'HH', 'HL', 'LH', 'LL'
    strength: float  # 0.0 إلى 1.0 (قوة النقطة)
    volume_at_point: float
    time_at_point: int


@dataclass
class CandleAnalysis:
    """تحليل متقدم لشمعة واحدة"""
    index: int
    open: float
    high: float
    low: float
    close: float
    body: float           # حجم الجسم
    upper_wick: float     # الظل العلوي
    lower_wick: float     # الظل السفلي
    total_range: float    # المدى الكلي
    body_position: float  # موقع الجسم داخل النطاق (0=أسفل, 0.5=وسط, 1=أعلى)
    is_bullish: bool
    is_doji: bool         # شمعة مترددة (جسم صغير جداً)
    is_marubozu: bool     # شمعة بدون ظلال (قوة)
    path_type: str        # مسار الشمعة (RisingBear, FallingBull, Neutral, Rejection)
    relative_size: float  # حجم الشمعة نسبة لمتوسط الشموع
    killer_candle: bool   # شمعة قاتلة (أكبر بـ 3 أضعاف من المتوسط)


@dataclass
class Wave:
    """موجة سعرية كاملة"""
    start_index: int
    end_index: int
    direction: str        # 'up' or 'down'
    price_distance: float # المسافة السعرية
    candle_count: int     # عدد الشموع
    average_speed: float  # السرعة المتوسطة (مسافة/زمن)
    max_speed: float      # أقصى سرعة
    health: float         # صحة الموجة (0=مريضة, 1=قوية جداً)
    phase: str            # Birth, Growth, Maturity, Decay
    time_age: float       # العمر الزمني النسبي (0-1)
    exhaustion_score: float # درجة الإنهاك


@dataclass
class LiquidityEvent:
    """حدث سيولة مكتشف"""
    index: int
    event_type: str       # 'sweep', 'drain', 'grab', 'hunt'
    direction: str        # 'above' or 'below'
    level_price: float
    wick_length: float
    return_speed: float   # سرعة العودة (كلما أسرع = سيولة حقيقية)
    consumed: float       # نسبة السيولة المستهلكة (0-1)


@dataclass
class SupportResistanceZone:
    """منطقة دعم/مقاومة ديناميكية"""
    price_high: float
    price_low: float
    zone_type: str        # 'support', 'resistance'
    origin_index: int
    touches: int          # عدد مرات اللمس
    freshness: float      # 1.0 = لم تختبر, 0.0 = ماتت
    strength_score: float # القوة الكلية
    is_live: bool         # هل ما زالت حية؟


@dataclass
class Pattern:
    """نمط سعري مكتشف"""
    pattern_type: str     # Engulfing, PinBar, InsideBar, ThreeDrives, Diamond, Megaphone, WolfWave, etc.
    index: int
    direction: str        # 'bullish', 'bearish', 'neutral'
    quality: float        # جودة النمط (0-1)
    confidence: float     # ثقة التوقع
    hidden: bool          # نمط مخفي/نادر


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الأولى: تحليل هيكل السوق الحي (Living Structure)          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LivingStructureAnalyzer:
    """
    يحلل هيكل السوق ككائن حي.
    لا يبحث عن قمم وقيعان ثابتة، بل يقرأ قصة السعر.
    """
    
    def __init__(self):
        self.swing_threshold_ratio = 0.0  # سيتحدد ديناميكياً
        self.internal_structure = []
        self.external_structure = []
        self.micro_structure = []
        
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                volumes: np.ndarray) -> Dict:
        """
        التحليل الكامل لهيكل السوق بطبقاته الثلاث
        """
        # تحديد العتبة الديناميكية بناءً على تقلب السوق
        avg_range = np.mean(highs[-20:] - lows[-20:])
        self.swing_threshold_ratio = avg_range * 0.3  # عتبة متكيفة
        
        # استخراج نقاط التأرجح
        all_swings = self._extract_swing_points(highs, lows, closes, volumes)
        
        # تصنيف الهيكل
        external = self._build_external_structure(all_swings)
        internal = self._build_internal_structure(all_swings)
        micro = self._build_micro_structure(highs, lows, closes, volumes)
        
        # تحليل حالة الهيكل الحالية
        structure_state = self._analyze_structure_state(all_swings[-30:])
        
        return {
            "swings": all_swings,
            "external": external,
            "internal": internal,
            "micro": micro,
            "state": structure_state,
            "trend": self._determine_trend(all_swings),
            "structure_health": self._assess_structure_health(all_swings, volumes),
        }
    
    def _extract_swing_points(self, highs, lows, closes, volumes) -> List[SwingPoint]:
        """
        استخراج نقاط التأرجح بطريقة ديناميكية.
        لا نبحث عن عدد ثابت من الشموع، بل نبحث عن "نقاط القرار".
        """
        swings = []
        
        for i in range(2, len(highs) - 2):
            # اكتشاف القمم
            if self._is_swing_high(highs, lows, closes, i):
                strength = self._calculate_swing_strength(highs, lows, closes, volumes, i, 'high')
                swing_type = self._classify_swing(swings, highs[i], 'high')
                swings.append(SwingPoint(
                    index=i, price=highs[i], swing_type=swing_type,
                    strength=strength, volume_at_point=volumes[i], time_at_point=i
                ))
            
            # اكتشاف القيعان
            if self._is_swing_low(highs, lows, closes, i):
                strength = self._calculate_swing_strength(highs, lows, closes, volumes, i, 'low')
                swing_type = self._classify_swing(swings, lows[i], 'low')
                swings.append(SwingPoint(
                    index=i, price=lows[i], swing_type=swing_type,
                    strength=strength, volume_at_point=volumes[i], time_at_point=i
                ))
        
        return swings
    
    def _is_swing_high(self, highs, lows, closes, i) -> bool:
        """اكتشاف القمة الديناميكي - ليس مجرد مقارنة بالجيران"""
        window = min(5, max(2, int(len(highs) * 0.02)))
        
        # الشرط الأساسي: أعلى من الجيران
        is_higher = all(highs[i] >= highs[i-j] for j in range(1, min(window+1, i+1))) and \
                    all(highs[i] >= highs[i+j] for j in range(1, min(window+1, len(highs)-i)))
        
        if not is_higher:
            return False
        
        # تحقق إضافي: هل هذه القمة ذات معنى؟
        left_bars = highs[max(0, i-window):i]
        right_bars = highs[i+1:min(len(highs), i+window+1)]
        
        if len(left_bars) < 2 or len(right_bars) < 2:
            return False
        
        avg_left = np.mean(left_bars)
        avg_right = np.mean(right_bars)
        
        # القمة الحقيقية تكون أعلى من المتوسط المحيط بها بشكل ملحوظ
        avg_range = np.mean(highs[-20:] - lows[-20:])
        return (highs[i] - max(avg_left, avg_right)) > avg_range * 0.15
    
    def _is_swing_low(self, highs, lows, closes, i) -> bool:
        """اكتشاف القاع الديناميكي"""
        window = min(5, max(2, int(len(lows) * 0.02)))
        
        is_lower = all(lows[i] <= lows[i-j] for j in range(1, min(window+1, i+1))) and \
                   all(lows[i] <= lows[i+j] for j in range(1, min(window+1, len(lows)-i)))
        
        if not is_lower:
            return False
        
        left_bars = lows[max(0, i-window):i]
        right_bars = lows[i+1:min(len(lows), i+window+1)]
        
        if len(left_bars) < 2 or len(right_bars) < 2:
            return False
        
        avg_left = np.mean(left_bars)
        avg_right = np.mean(right_bars)
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        return (min(avg_left, avg_right) - lows[i]) > avg_range * 0.15
    
    def _calculate_swing_strength(self, highs, lows, closes, volumes, i, swing_side) -> float:
        """حساب قوة نقطة التأرجح ديناميكياً"""
        strength = 0.5
        
        # 1. حجم التداول عند النقطة (كلما زاد = نقطة أقوى)
        avg_vol = np.mean(volumes[max(0,i-20):i])
        if avg_vol > 0 and volumes[i] > avg_vol:
            strength += min(0.2, (volumes[i] / avg_vol - 1) * 0.1)
        
        # 2. سرعة الوصول للنقطة (حركة سريعة = قمة/قاع قوي)
        if i >= 5:
            speed = abs(closes[i] - closes[i-5]) / 5
            avg_speed = np.mean(np.abs(np.diff(closes[max(0,i-30):i])))
            if avg_speed > 0 and speed > avg_speed:
                strength += 0.15
        
        # 3. شكل الشمعة (ظل طويل في اتجاه النقطة = رفض = قوة)
        candle_range = highs[i] - lows[i]
        if candle_range > 0:
            if swing_side == 'high':
                wick_ratio = (highs[i] - max(opens[i] if 'opens' in dir() else closes[i], 
                         closes[i])) / candle_range if i < len(closes) else 0
            else:
                wick_ratio = (min(opens[i] if 'opens' in dir() else closes[i], 
                         closes[i]) - lows[i]) / candle_range if i < len(closes) else 0
            strength += min(0.15, wick_ratio * 0.2)
        
        # 4. هل النقطة عند منطقة نفسية؟
        rounded = round(highs[i] if swing_side == 'high' else lows[i], 2)
        if str(rounded).endswith('00') or str(rounded).endswith('50'):
            strength += 0.1
        
        return min(1.0, strength)
    
    def _classify_swing(self, existing_swings: List[SwingPoint], price: float, 
                        side: str) -> str:
        """تصنيف نقطة التأرجح ضمن هيكل السوق"""
        if len(existing_swings) < 2:
            return 'HH' if side == 'high' else 'LL'
        
        # الحصول على آخر نقطتين من نفس النوع
        same_side = [s for s in existing_swings if 
                    (s.swing_type in ['HH', 'LH'] and side == 'high') or 
                    (s.swing_type in ['LL', 'HL'] and side == 'low')]
        
        if len(same_side) < 1:
            return 'HH' if side == 'high' else 'LL'
        
        last_same = same_side[-1]
        
        if side == 'high':
            if price > last_same.price:
                # كسر القمة السابقة = BOS
                return 'HH'  # Higher High - استمرار صعود
            else:
                # قمة أقل = CHoCH محتمل
                return 'LH'  # Lower High - ضعف الصعود
        else:
            if price < last_same.price:
                return 'LL'  # Lower Low - استمرار هبوط
            else:
                return 'HL'  # Higher Low - ضعف الهبوط
    
    def _build_external_structure(self, swings: List[SwingPoint]) -> Dict:
        """بناء الهيكل الخارجي (الإطار الأكبر)"""
        if len(swings) < 4:
            return {"trend": "غير محدد", "state": "غير مكتمل"}
        
        # تحليل آخر 4 نقاط
        last4 = swings[-4:]
        highs_points = [s for s in last4 if s.swing_type in ['HH', 'LH']]
        lows_points = [s for s in last4 if s.swing_type in ['HL', 'LL']]
        
        trend = "متعادل"
        if len(highs_points) >= 2 and len(lows_points) >= 2:
            if highs_points[-1].swing_type == 'HH' and lows_points[-1].swing_type == 'HL':
                trend = "صاعد"
            elif highs_points[-1].swing_type == 'LH' and lows_points[-1].swing_type == 'LL':
                trend = "هابط"
        
        return {
            "trend": trend,
            "last_significant_high": highs_points[-1].price if highs_points else None,
            "last_significant_low": lows_points[-1].price if lows_points else None,
            "structure_sequence": [s.swing_type for s in swings[-10:]],
        }
    
    def _build_internal_structure(self, swings: List[SwingPoint]) -> Dict:
        """بناء الهيكل الداخلي (الإطار المتوسط) - ساحة المعركة"""
        if len(swings) < 3:
            return {"state": "غير مكتمل"}
        
        recent = swings[-10:]
        
        # كشف BOS و CHoCH
        events = []
        for i in range(2, len(recent)):
            prev = recent[i-2]
            curr = recent[i]
            
            if prev.swing_type in ['HH', 'LH'] and curr.swing_type in ['HH', 'LH']:
                if prev.swing_type == 'LH' and curr.swing_type == 'HH':
                    events.append({"type": "BOS_UP", "index": curr.index, 
                                   "meaning": "كسر هيكل للأعلى - استمرار صعود"})
                elif prev.swing_type == 'HH' and curr.swing_type == 'LH':
                    events.append({"type": "CHoCH_DOWN", "index": curr.index,
                                   "meaning": "تغير شخصية هابط - تحذير انعكاس"})
            else:
                if prev.swing_type == 'HL' and curr.swing_type == 'LL':
                    events.append({"type": "BOS_DOWN", "index": curr.index,
                                   "meaning": "كسر هيكل للأسفل - استمرار هبوط"})
                elif prev.swing_type == 'LL' and curr.swing_type == 'HL':
                    events.append({"type": "CHoCH_UP", "index": curr.index,
                                   "meaning": "تغير شخصية صاعد - تحذير انعكاس"})
        
        # كشف MSS (Market Structure Shift)
        mss = None
        if len(events) >= 2:
            last_two = events[-2:]
            if last_two[0]["type"] == "CHoCH_DOWN" and last_two[1]["type"] == "BOS_DOWN":
                mss = {"direction": "bearish", "confirmed": True}
            elif last_two[0]["type"] == "CHoCH_UP" and last_two[1]["type"] == "BOS_UP":
                mss = {"direction": "bullish", "confirmed": True}
        
        return {
            "events": events,
            "mss": mss,
            "battle_zone": self._find_battle_zone(swings[-20:]),
        }
    
    def _build_micro_structure(self, highs, lows, closes, volumes) -> Dict:
        """بناء الهيكل الصغري - تنفس السوق"""
        if len(closes) < 10:
            return {"state": "بيانات غير كافية"}
        
        # تحليل آخر 10 شموع
        last_10 = closes[-10:]
        
        # هل الحركة ذات اتجاه واحد؟ (One-Way)
        diffs = np.diff(last_10)
        up_moves = sum(d > 0 for d in diffs)
        
        one_way_score = abs(up_moves - 5) / 5  # 1.0 = كلها في اتجاه واحد
        
        # سرعة الحركة الصغرية
        micro_speed = abs(closes[-1] - closes[-10]) / 10
        
        # التداخل (Consolidation)
        consolidation = self._measure_consolidation(highs[-10:], lows[-10:])
        
        return {
            "one_way_score": one_way_score,
            "one_way_detected": one_way_score > 0.7,
            "micro_speed": micro_speed,
            "consolidation": consolidation,
            "state": "اندفاع" if one_way_score > 0.7 and micro_speed > np.mean(np.abs(diffs)) 
                     else "تماسك" if consolidation > 0.6 else "متوازن",
        }
    
    def _measure_consolidation(self, highs, lows) -> float:
        """قياس درجة التماسك - كلما كانت أعلى كان الانفجار أقوى"""
        ranges = np.array(highs) - np.array(lows)
        avg_range = np.mean(ranges)
        
        if avg_range == 0:
            return 1.0
        
        # التماسك الحقيقي = نطاقات ضيقة باستمرار
        tight_bars = sum(1 for r in ranges if r < avg_range * 0.7)
        return tight_bars / len(ranges)
    
    def _analyze_structure_state(self, swings: List[SwingPoint]) -> Dict:
        """تحليل حالة الهيكل الحالية"""
        if len(swings) < 4:
            return {"state": "غير محدد", "confidence": 0.3}
        
        recent = swings[-8:]
        
        # هل الهيكل واضح أم فوضوي؟
        types = [s.swing_type for s in recent]
        alternating = 0
        for i in range(1, len(types)):
            if (types[i] in ['HH', 'LH'] and types[i-1] in ['HL', 'LL']) or \
               (types[i] in ['HL', 'LL'] and types[i-1] in ['HH', 'LH']):
                alternating += 1
        
        clarity = 1.0 - (alternating / (len(types) - 1)) if len(types) > 1 else 0.5
        
        return {
            "clarity": clarity,
            "state": "واضح" if clarity > 0.7 else "متوسط" if clarity > 0.4 else "فوضوي",
            "confidence": clarity,
        }
    
    def _determine_trend(self, swings: List[SwingPoint]) -> Dict:
        """تحديد الاتجاه بطريقة ديناميكية"""
        if len(swings) < 6:
            return {"direction": "محايد", "strength": 0.3}
        
        last_highs = [s for s in swings[-15:] if s.swing_type in ['HH', 'LH']]
        last_lows = [s for s in swings[-15:] if s.swing_type in ['HL', 'LL']]
        
        if len(last_highs) < 2 or len(last_lows) < 2:
            return {"direction": "محايد", "strength": 0.3}
        
        # قوة الاتجاه
        trend_strength = 0.5
        
        # هل القمم تصعد والقيعان تصعد؟
        if last_highs[-1].price > last_highs[-2].price and \
           last_lows[-1].price > last_lows[-2].price:
            direction = "صاعد"
            # قياس قوة الصعود
            if len(last_highs) >= 3 and len(last_lows) >= 3:
                if last_highs[-1].price > last_highs[-3].price:
                    trend_strength += 0.2
                if last_lows[-1].price > last_lows[-3].price:
                    trend_strength += 0.2
        elif last_highs[-1].price < last_highs[-2].price and \
             last_lows[-1].price < last_lows[-2].price:
            direction = "هابط"
            if len(last_highs) >= 3 and len(last_lows) >= 3:
                if last_highs[-1].price < last_highs[-3].price:
                    trend_strength += 0.2
                if last_lows[-1].price < last_lows[-3].price:
                    trend_strength += 0.2
        else:
            direction = "محايد"
            trend_strength = 0.3
        
        return {"direction": direction, "strength": min(1.0, trend_strength)}
    
    def _assess_structure_health(self, swings, volumes) -> float:
        """تقييم صحة الهيكل"""
        if len(swings) < 10:
            return 0.5
        
        # قوة نقاط التأرجح
        avg_strength = np.mean([s.strength for s in swings[-10:]])
        
        # وضوح التسلسل
        types = [s.swing_type for s in swings[-10:]]
        alternating = sum(1 for i in range(1, len(types)) 
                        if (types[i] in ['HH','LH']) != (types[i-1] in ['HH','LH']))
        sequence_clarity = alternating / (len(types) - 1)
        
        return (avg_strength * 0.6 + sequence_clarity * 0.4)
    
    def _find_battle_zone(self, swings) -> Dict:
        """تحديد منطقة الصراع الحالية"""
        if len(swings) < 4:
            return {"exists": False}
        
        # المنطقة بين آخر قمة وقاع مهمين
        last_highs = [s for s in swings if s.swing_type in ['HH', 'LH']]
        last_lows = [s for s in swings if s.swing_type in ['HL', 'LL']]
        
        if last_highs and last_lows:
            return {
                "exists": True,
                "upper_bound": last_highs[-1].price,
                "lower_bound": last_lows[-1].price,
                "zone_width": last_highs[-1].price - last_lows[-1].price,
            }
        
        return {"exists": False}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║            الدرجة الثانية: تحليل السيولة الديناميكي                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicLiquidityAnalyzer:
    """
    يحلل السيولة كقوة دافعة خفية للسوق.
    يكتشف أين توجد الأوامر الحقيقية وكيف يتحرك السعر نحوها.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, swings: List[SwingPoint]) -> Dict:
        """
        التحليل الكامل للسيولة
        """
        # اكتشاف أحداث السيولة
        events = self._detect_liquidity_events(highs, lows, closes, volumes)
        
        # تحديد مناطق السيولة
        structural_liquidity = self._find_structural_liquidity(swings)
        psychological_liquidity = self._find_psychological_liquidity(closes[-1])
        trend_liquidity = self._find_trend_liquidity(highs, lows, closes, volumes)
        
        # قياس جاذبية السيولة
        gravity = self._measure_liquidity_gravity(events, closes[-1])
        
        return {
            "events": events,
            "structural_liquidity": structural_liquidity,
            "psychological_liquidity": psychological_liquidity,
            "trend_liquidity": trend_liquidity,
            "gravity": gravity,
            "liquidity_state": self._determine_liquidity_state(events, gravity),
        }
    
    def _detect_liquidity_events(self, highs, lows, closes, volumes) -> List[LiquidityEvent]:
        """
        اكتشاف أحداث السيولة: كنس، استنزاف، اصطياد
        """
        events = []
        
        for i in range(5, len(highs) - 1):
            # Sweep: اختراق وهمي مع ارتداد سريع
            if self._is_liquidity_sweep(highs, lows, closes, i, 'high'):
                wick = highs[i] - max(closes[i], closes[i-1] if i > 0 else closes[i])
                return_speed = abs(closes[i] - closes[i-1]) if i > 0 else 0
                events.append(LiquidityEvent(
                    index=i, event_type='sweep', direction='above',
                    level_price=self._find_nearest_level(highs, i),
                    wick_length=wick, return_speed=return_speed,
                    consumed=min(1.0, wick / (np.mean(highs[-20:] - lows[-20:]) * 2))
                ))
            
            if self._is_liquidity_sweep(highs, lows, closes, i, 'low'):
                wick = min(closes[i], closes[i-1] if i > 0 else closes[i]) - lows[i]
                return_speed = abs(closes[i] - closes[i-1]) if i > 0 else 0
                events.append(LiquidityEvent(
                    index=i, event_type='sweep', direction='below',
                    level_price=self._find_nearest_level(lows, i),
                    wick_length=wick, return_speed=return_speed,
                    consumed=min(1.0, wick / (np.mean(highs[-20:] - lows[-20:]) * 2))
                ))
            
            # Drain: استنزاف (يبقى فوق/تحت المستوى لفترة)
            if i >= 10:
                if self._is_liquidity_drain(highs, lows, closes, i, 'high'):
                    events.append(LiquidityEvent(
                        index=i, event_type='drain', direction='above',
                        level_price=self._find_nearest_level(highs, i),
                        wick_length=0, return_speed=0, consumed=0.8
                    ))
                if self._is_liquidity_drain(highs, lows, closes, i, 'low'):
                    events.append(LiquidityEvent(
                        index=i, event_type='drain', direction='below',
                        level_price=self._find_nearest_level(lows, i),
                        wick_length=0, return_speed=0, consumed=0.8
                    ))
        
        return events
    
    def _is_liquidity_sweep(self, highs, lows, closes, i, direction) -> bool:
        """
        كشف كنس السيولة: اختراق بظل طويل ثم عودة سريعة
        """
        if direction == 'high':
            # ظل علوي طويل
            body_high = max(closes[i], closes[i-1] if i > 0 else closes[i])
            wick = highs[i] - body_high
            candle_range = highs[i] - lows[i]
            
            if candle_range == 0:
                return False
            
            # الظل أكبر من 60% من الشمعة
            if wick < candle_range * 0.6:
                return False
            
            # الإغلاق أسفل الجسم السابق
            if closes[i] < (closes[i-1] if i > 0 else closes[i]):
                return True
                
        else:
            # ظل سفلي طويل
            body_low = min(closes[i], closes[i-1] if i > 0 else closes[i])
            wick = body_low - lows[i]
            candle_range = highs[i] - lows[i]
            
            if candle_range == 0:
                return False
            
            if wick < candle_range * 0.6:
                return False
            
            if closes[i] > (closes[i-1] if i > 0 else closes[i]):
                return True
        
        return False
    
    def _is_liquidity_drain(self, highs, lows, closes, i, direction) -> bool:
        """
        كشف استنزاف السيولة: السعر يخترق ويبقى فترة (مترنح)
        """
        if direction == 'high':
            # اختراق فوق مستوى والبقاء هناك
            level = np.max(highs[i-10:i-3]) if i >= 10 else highs[i]
            recent = closes[i-3:i+1]
            return all(c > level for c in recent) and np.std(recent) < np.std(closes[-20:]) * 0.5
        
        else:
            level = np.min(lows[i-10:i-3]) if i >= 10 else lows[i]
            recent = closes[i-3:i+1]
            return all(c < level for c in recent) and np.std(recent) < np.std(closes[-20:]) * 0.5
    
    def _find_nearest_level(self, prices, index) -> float:
        """إيجاد أقرب مستوى سعري لسيولة"""
        if index < 5:
            return prices[index]
        return np.max(prices[index-5:index])
    
    def _find_structural_liquidity(self, swings: List[SwingPoint]) -> Dict:
        """
        إيجاد السيولة الهيكلية: فوق القمم وتحت القيعان
        """
        if len(swings) < 4:
            return {"above": [], "below": []}
        
        highs = [s for s in swings if s.swing_type in ['HH', 'LH']]
        lows = [s for s in swings if s.swing_type in ['HL', 'LL']]
        
        # السيولة فوق القمم المزدوجة
        above_liquidity = []
        for i in range(1, len(highs)):
            if abs(highs[i].price - highs[i-1].price) < highs[i].price * 0.002:
                above_liquidity.append({
                    "price": highs[i].price,
                    "type": "double_top",
                    "strength": (highs[i].strength + highs[i-1].strength) / 2,
                })
        
        # السيولة تحت القيعان المزدوجة
        below_liquidity = []
        for i in range(1, len(lows)):
            if abs(lows[i].price - lows[i-1].price) < lows[i].price * 0.002:
                below_liquidity.append({
                    "price": lows[i].price,
                    "type": "double_bottom",
                    "strength": (lows[i].strength + lows[i-1].strength) / 2,
                })
        
        return {"above": above_liquidity, "below": below_liquidity}
    
    def _find_psychological_liquidity(self, current_price: float) -> Dict:
        """
        السيولة النفسية: الأرقام الدائرية وأنصافها
        """
        # الرقم الدائري الأقرب
        round_above = round(current_price + 1, -1)
        round_below = round(current_price - 1, -1)
        
        # المستوى النصفي
        mid_above = round(current_price + 0.5, 1)
        mid_below = round(current_price - 0.5, 1)
        
        # مستويات ربعية
        quarters = []
        base = round(current_price, 0)
        for i in range(-4, 5):
            quarters.append(base + i * 0.25)
        
        return {
            "round_numbers": [round_below, round_above],
            "mid_levels": [mid_below, mid_above],
            "quarter_levels": [q for q in quarters if abs(q - current_price) < current_price * 0.02],
        }
    
    def _find_trend_liquidity(self, highs, lows, closes, volumes) -> Dict:
        """
        سيولة الاتجاه: القطيع المتأخر
        أخطر أنواع السيولة - تظهر عند نهاية الاتجاهات
        """
        if len(closes) < 20:
            return {"detected": False}
        
        # علامات الاتجاه العمودي
        vertical_score = 0.0
        recent = closes[-10:]
        
        # 1. حركة في اتجاه واحد
        diffs = np.diff(recent)
        same_direction = sum(1 for d in diffs if d > 0)
        if same_direction >= 8 or same_direction <= 2:
            vertical_score += 0.4
        
        # 2. شموع ضخمة متتالية
        ranges = np.array(highs[-10:]) - np.array(lows[-10:])
        avg_range = np.mean(ranges[-30:]) if len(ranges) >= 30 else np.mean(ranges)
        if avg_range > 0:
            big_candles = sum(1 for r in ranges if r > avg_range * 1.5)
            if big_candles >= 5:
                vertical_score += 0.3
        
        # 3. السرعة المتزايدة
        speeds = np.abs(diffs)
        if len(speeds) >= 5 and np.mean(speeds[:5]) > 0:
            acceleration = np.mean(speeds[5:]) / np.mean(speeds[:5])
            if acceleration > 1.5:
                vertical_score += 0.3
        
        return {
            "detected": vertical_score > 0.5,
            "intensity": vertical_score,
            "danger": "سيولة الاتجاه تنفد - انعكاس وشيك" if vertical_score > 0.7 else None,
        }
    
    def _measure_liquidity_gravity(self, events, current_price) -> Dict:
        """
        قياس جاذبية السيولة: أين ينجذب السعر؟
        """
        if not events:
            return {"direction": "none", "strength": 0.0}
        
        recent = events[-5:]
        above_events = [e for e in recent if e.direction == 'above']
        below_events = [e for e in recent if e.direction == 'below']
        
        above_strength = sum(e.consumed for e in above_events)
        below_strength = sum(e.consumed for e in below_events)
        
        # السعر ينجذب نحو السيولة الأعلى
        if above_strength > below_strength * 1.5:
            direction = "up"
            strength = min(1.0, above_strength / (above_strength + below_strength))
        elif below_strength > above_strength * 1.5:
            direction = "down"
            strength = min(1.0, below_strength / (above_strength + below_strength))
        else:
            direction = "balanced"
            strength = 0.5
        
        return {"direction": direction, "strength": strength}
    
    def _determine_liquidity_state(self, events, gravity) -> str:
        """تحديد حالة السيولة العامة"""
        if not events:
            return "هادئ - لا أحداث سيولة"
        
        recent_sweeps = [e for e in events[-5:] if e.event_type == 'sweep']
        recent_drains = [e for e in events[-5:] if e.event_type == 'drain']
        
        if len(recent_sweeps) >= 2:
            return "نشط - السيولة تُجمع بنشاط"
        elif len(recent_drains) >= 2:
            return "مستنزف - السوق يهضم سيولة كبيرة"
        elif gravity['strength'] > 0.7:
            return "منجذب - السعر يبحث عن سيولة في اتجاه واضح"
        else:
            return "متوازن - لا جاذبية واضحة"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة الثالثة: تحليل الشموع اليابانية المتقدم                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AdvancedCandlestickAnalyzer:
    """
    تشريح الشموع بعمق.
    لا يكتفي بقراءة النمط، بل يقرأ قصة الشمعة.
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        تحليل متقدم لكل شمعة واكتشاف الأنماط
        """
        candles = self._analyze_all_candles(opens, highs, lows, closes, volumes)
        patterns = self._detect_all_patterns(candles)
        killer_candles = self._find_killer_candles(candles)
        wick_signals = self._analyze_wick_stories(candles)
        
        return {
            "recent_candles": candles[-10:],
            "patterns": patterns,
            "killer_candles": killer_candles,
            "wick_signals": wick_signals,
            "candle_story": self._tell_candle_story(candles[-5:]),
        }
    
    def _analyze_all_candles(self, opens, highs, lows, closes, volumes) -> List[CandleAnalysis]:
        """تحليل مفصل لكل شمعة"""
        candles = []
        
        avg_range = np.mean(highs[-20:] - lows[-20:]) if len(highs) >= 20 else np.mean(highs - lows)
        
        for i in range(len(closes)):
            body = abs(closes[i] - opens[i])
            upper_wick = highs[i] - max(opens[i], closes[i])
            lower_wick = min(opens[i], closes[i]) - lows[i]
            total_range = highs[i] - lows[i]
            
            # موقع الجسم (0=كل الجسم في الأسفل, 1=كله في الأعلى)
            if total_range > 0:
                body_center = (max(opens[i], closes[i]) + min(opens[i], closes[i])) / 2
                body_position = (body_center - lows[i]) / total_range
            else:
                body_position = 0.5
            
            # نوع الشمعة
            is_bullish = closes[i] > opens[i]
            is_doji = body < total_range * 0.1 if total_range > 0 else True
            is_marubozu = (upper_wick + lower_wick) < total_range * 0.1 if total_range > 0 else False
            
            # مسار الشمعة
            path_type = self._determine_candle_path(opens[i], highs[i], lows[i], closes[i])
            
            # الحجم النسبي
            relative_size = total_range / avg_range if avg_range > 0 else 1.0
            
            candles.append(CandleAnalysis(
                index=i,
                open=opens[i], high=highs[i], low=lows[i], close=closes[i],
                body=body, upper_wick=upper_wick, lower_wick=lower_wick,
                total_range=total_range, body_position=body_position,
                is_bullish=is_bullish, is_doji=is_doji, is_marubozu=is_marubozu,
                path_type=path_type, relative_size=relative_size,
                killer_candle=relative_size > 3.0,
            ))
        
        return candles
    
    def _determine_candle_path(self, open_p, high, low, close) -> str:
        """
        تحديد مسار الشمعة: القصة الداخلية
        """
        mid = (high + low) / 2
        
        # Rising Bear: يفتح، ينخفض، يصعد للقمة، يهبط ويغلق قرب القاع
        if close < open_p and low < open_p * 0.998 and high > close * 1.002 and close < mid:
            return "RisingBear"  # صاعد خادع - هبوط حقيقي
        
        # Falling Bull: يفتح، يصعد، ينخفض للقاع، يصعد ويغلق قرب القمة
        if close > open_p and high > close * 0.998 and low < open_p * 0.998 and close > mid:
            return "FallingBull"  # هابط خادع - صعود حقيقي
        
        # Final Rejection: حركة قوية في اتجاه ثم انهيار في النهاية
        range_size = high - low
        if range_size > 0:
            if close > open_p:
                # صاعدة لكنها أغلقت قرب القاع
                if (high - close) > range_size * 0.6:
                    return "FinalRejection"  # رفض نهائي - هبوط قادم
            else:
                # هابطة لكنها أغلقت قرب القمة
                if (close - low) > range_size * 0.6:
                    return "FinalRejection"  # رفض نهائي - صعود قادم
        
        return "Neutral"
    
    def _detect_all_patterns(self, candles: List[CandleAnalysis]) -> List[Pattern]:
        """
        اكتشاف كل الأنماط السعرية: المعروفة والنادرة والسرية
        """
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        # الأنماط الأساسية
        patterns.extend(self._detect_engulfing(candles))
        patterns.extend(self._detect_pin_bars(candles))
        patterns.extend(self._detect_inside_bars(candles))
        patterns.extend(self._detect_fakey(candles))
        
        # الأنماط المتقدمة
        patterns.extend(self._detect_three_drives(candles))
        patterns.extend(self._detect_morning_evening_star(candles))
        patterns.extend(self._detect_tweezer(candles))
        patterns.extend(self._detect_railway_tracks(candles))
        
        # الأنماط السرية والنادرة
        patterns.extend(self._detect_wolf_wave(candles))
        patterns.extend(self._detect_diamond(candles))
        patterns.extend(self._detect_megaphone(candles))
        patterns.extend(self._detect_quasimodo(candles))
        patterns.extend(self._detect_three_bar_reversal(candles))
        
        return patterns
    
    def _detect_engulfing(self, candles) -> List[Pattern]:
        """اكتشاف الابتلاع (العادي والسرّي)"""
        patterns = []
        
        for i in range(1, len(candles)):
            prev = candles[i-1]
            curr = candles[i]
            
            # ابتلاع صاعد
            if (not prev.is_bullish and curr.is_bullish and
                curr.close > prev.open and curr.open < prev.close and
                curr.body > prev.body * 1.2):
                # التحقق من الموقع (اﻷقوى عند القيعان)
                near_low = curr.low <= np.min([c.low for c in candles[max(0,i-10):i]]) * 1.002 if i >= 10 else True
                quality = 0.8 if near_low else 0.5
                
                patterns.append(Pattern(
                    pattern_type="BullishEngulfing",
                    index=i, direction="bullish",
                    quality=quality,
                    confidence=0.7 if near_low else 0.5,
                    hidden=False,
                ))
            
            # ابتلاع هابط
            if (prev.is_bullish and not curr.is_bullish and
                curr.close < prev.open and curr.open > prev.close and
                curr.body > prev.body * 1.2):
                near_high = curr.high >= np.max([c.high for c in candles[max(0,i-10):i]]) * 0.998 if i >= 10 else True
                quality = 0.8 if near_high else 0.5
                
                patterns.append(Pattern(
                    pattern_type="BearishEngulfing",
                    index=i, direction="bearish",
                    quality=quality,
                    confidence=0.7 if near_high else 0.5,
                    hidden=False,
                ))
        
        return patterns
    
    def _detect_pin_bars(self, candles) -> List[Pattern]:
        """اكتشاف البين بار (العادي والمخفي)"""
        patterns = []
        
        for i in range(len(candles)):
            c = candles[i]
            if c.total_range == 0:
                continue
            
            # بين بار صاعد: جسم صغير + ظل سفلي طويل
            if c.lower_wick > c.body * 3 and c.upper_wick < c.total_range * 0.15:
                # تحقق: الظل يجب أن يكون الأطول في المنطقة
                near_low = i >= 5 and c.low <= np.min([x.low for x in candles[i-5:i]])
                quality = 0.9 if near_low else 0.5
                
                patterns.append(Pattern(
                    pattern_type="BullishPinBar",
                    index=i, direction="bullish",
                    quality=quality,
                    confidence=0.75 if near_low else 0.4,
                    hidden=not near_low,
                ))
            
            # بين بار هابط: جسم صغير + ظل علوي طويل
            if c.upper_wick > c.body * 3 and c.lower_wick < c.total_range * 0.15:
                near_high = i >= 5 and c.high >= np.max([x.high for x in candles[i-5:i]])
                quality = 0.9 if near_high else 0.5
                
                patterns.append(Pattern(
                    pattern_type="BearishPinBar",
                    index=i, direction="bearish",
                    quality=quality,
                    confidence=0.75 if near_high else 0.4,
                    hidden=not near_high,
                ))
        
        return patterns
    
    def _detect_inside_bars(self, candles) -> List[Pattern]:
        """اكتشاف الشموع الداخلية (بما فيها الثلاثية النادرة)"""
        patterns = []
        
        for i in range(2, len(candles)):
            # Inside-Inside-Inside (ثلاثية نادرة)
            if (candles[i].high < candles[i-1].high and candles[i].low > candles[i-1].low and
                candles[i-1].high < candles[i-2].high and candles[i-1].low > candles[i-2].low):
                patterns.append(Pattern(
                    pattern_type="TripleInsideBar",
                    index=i, direction="neutral",
                    quality=0.9,
                    confidence=0.8,
                    hidden=True,  # نادر
                ))
            # Inside Bar عادي
            elif candles[i].high < candles[i-1].high and candles[i].low > candles[i-1].low:
                patterns.append(Pattern(
                    pattern_type="InsideBar",
                    index=i, direction="neutral",
                    quality=0.5,
                    confidence=0.5,
                    hidden=False,
                ))
        
        return patterns
    
    def _detect_fakey(self, candles) -> List[Pattern]:
        """اكتشاف الفيكي (الكسر الوهمي + شمعة داخلية)"""
        patterns = []
        
        for i in range(2, len(candles)):
            # Fakey صاعد: كسر وهمي للأسفل ثم شمعة داخلية
            if (candles[i-1].low < candles[i-2].low and 
                candles[i-1].close > candles[i-2].low and
                candles[i].high < candles[i-1].high and 
                candles[i].low > candles[i-1].low):
                patterns.append(Pattern(
                    pattern_type="BullishFakey",
                    index=i, direction="bullish",
                    quality=0.85,
                    confidence=0.75,
                    hidden=False,
                ))
            
            # Fakey هابط
            if (candles[i-1].high > candles[i-2].high and
                candles[i-1].close < candles[i-2].high and
                candles[i].high < candles[i-1].high and
                candles[i].low > candles[i-1].low):
                patterns.append(Pattern(
                    pattern_type="BearishFakey",
                    index=i, direction="bearish",
                    quality=0.85,
                    confidence=0.75,
                    hidden=False,
                ))
        
        return patterns
    
    def _detect_three_drives(self, candles) -> List[Pattern]:
        """اكتشاف نموذج الدوافع الثلاث (نادر وقوي)"""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # البحث عن 3 قمم أو 3 قيعان متتالية بنسب متزايدة
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        
        # ثلاث قمم صاعدة (انعكاس هبوطي)
        peaks = self._find_peaks(highs)
        if len(peaks) >= 3:
            p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
            if p3 > p2 > p1:
                ratio1 = (p2 - p1) / max(p1 * 0.001, 1)
                ratio2 = (p3 - p2) / max(p2 * 0.001, 1)
                if 0.5 < ratio2 / max(ratio1, 0.001) < 2.0:
                    patterns.append(Pattern(
                        pattern_type="ThreeDrives",
                        index=len(candles)-1, direction="bearish",
                        quality=0.8, confidence=0.75,
                        hidden=True,
                    ))
        
        # ثلاث قيعان هابطة (انعكاس صعودي)
        valleys = self._find_valleys(lows)
        if len(valleys) >= 3:
            v1, v2, v3 = valleys[-3], valleys[-2], valleys[-1]
            if v3 < v2 < v1:
                ratio1 = (v1 - v2) / max(v1 * 0.001, 1)
                ratio2 = (v2 - v3) / max(v2 * 0.001, 1)
                if 0.5 < ratio2 / max(ratio1, 0.001) < 2.0:
                    patterns.append(Pattern(
                        pattern_type="ThreeDrives",
                        index=len(candles)-1, direction="bullish",
                        quality=0.8, confidence=0.75,
                        hidden=True,
                    ))
        
        return patterns
    
    def _find_peaks(self, data) -> List[float]:
        """إيجاد القمم"""
        peaks = []
        for i in range(2, len(data)-2):
            if data[i] > data[i-1] and data[i] > data[i-2] and data[i] > data[i+1] and data[i] > data[i+2]:
                peaks.append(data[i])
        return peaks
    
    def _find_valleys(self, data) -> List[float]:
        """إيجاد القيعان"""
        valleys = []
        for i in range(2, len(data)-2):
            if data[i] < data[i-1] and data[i] < data[i-2] and data[i] < data[i+1] and data[i] < data[i+2]:
                valleys.append(data[i])
        return valleys
    
    def _detect_morning_evening_star(self, candles) -> List[Pattern]:
        """اكتشاف نجمة الصباح والمساء"""
        patterns = []
        
        for i in range(2, len(candles)):
            c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
            
            # Morning Star: هابط كبير + دوجي + صاعد كبير
            if (not c1.is_bullish and c1.body > c1.total_range * 0.5 and
                c2.is_doji and c2.total_range < c1.body * 0.5 and
                c3.is_bullish and c3.body > c3.total_range * 0.5 and
                c3.close > (c1.open + c1.close) / 2):
                patterns.append(Pattern(
                    pattern_type="MorningStar",
                    index=i, direction="bullish",
                    quality=0.9, confidence=0.8,
                    hidden=False,
                ))
            
            # Evening Star
            if (c1.is_bullish and c1.body > c1.total_range * 0.5 and
                c2.is_doji and c2.total_range < c1.body * 0.5 and
                not c3.is_bullish and c3.body > c3.total_range * 0.5 and
                c3.close < (c1.open + c1.close) / 2):
                patterns.append(Pattern(
                    pattern_type="EveningStar",
                    index=i, direction="bearish",
                    quality=0.9, confidence=0.8,
                    hidden=False,
                ))
        
        return patterns
    
    def _detect_tweezer(self, candles) -> List[Pattern]:
        """اكتشاف الملقط (قمتين/قاعين متطابقين)"""
        patterns = []
        
        for i in range(1, len(candles)):
            # قمتين متطابقتين
            if abs(candles[i].high - candles[i-1].high) < candles[i].total_range * 0.05:
                patterns.append(Pattern(
                    pattern_type="TweezerTop",
                    index=i, direction="bearish",
                    quality=0.6, confidence=0.55,
                    hidden=False,
                ))
            
            # قاعين متطابقين
            if abs(candles[i].low - candles[i-1].low) < candles[i].total_range * 0.05:
                patterns.append(Pattern(
                    pattern_type="TweezerBottom",
                    index=i, direction="bullish",
                    quality=0.6, confidence=0.55,
                    hidden=False,
                ))
        
        return patterns
    
    def _detect_railway_tracks(self, candles) -> List[Pattern]:
        """اكتشاف سكة القطار (شمعتين متعاكستين بنفس الحجم)"""
        patterns = []
        
        for i in range(1, len(candles)):
            c1, c2 = candles[i-1], candles[i]
            if (c1.is_bullish != c2.is_bullish and
                abs(c1.body - c2.body) < c1.body * 0.15 and
                abs(c1.open - c2.close) < c1.total_range * 0.1):
                patterns.append(Pattern(
                    pattern_type="RailwayTracks",
                    index=i, direction="bearish" if c1.is_bullish else "bullish",
                    quality=0.7, confidence=0.65,
                    hidden=True,
                ))
        
        return patterns
    
    def _detect_wolf_wave(self, candles) -> List[Pattern]:
        """اكتشاف موجة وولف (نموذج نادر)"""
        # نموذج معقد يحتاج 5 نقاط على الأقل
        # هذا نسخة مبسطة للكشف
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # البحث عن هيكل 5 موجات
        swings = []
        for i in range(2, len(candles)-2):
            if candles[i].high > candles[i-1].high and candles[i].high > candles[i+1].high:
                swings.append(('high', i, candles[i].high))
            if candles[i].low < candles[i-1].low and candles[i].low < candles[i+1].low:
                swings.append(('low', i, candles[i].low))
        
        if len(swings) >= 5:
            last5 = swings[-5:]
            types = [s[0] for s in last5]
            # Wolf Wave: High-Low-High-Low-High أو العكس
            if types == ['high', 'low', 'high', 'low', 'high']:
                patterns.append(Pattern(
                    pattern_type="WolfWave",
                    index=len(candles)-1, direction="bearish",
                    quality=0.7, confidence=0.7,
                    hidden=True,
                ))
            elif types == ['low', 'high', 'low', 'high', 'low']:
                patterns.append(Pattern(
                    pattern_type="WolfWave",
                    index=len(candles)-1, direction="bullish",
                    quality=0.7, confidence=0.7,
                    hidden=True,
                ))
        
        return patterns
    
    def _detect_diamond(self, candles) -> List[Pattern]:
        """اكتشاف النموذج الماسي (نادر جداً)"""
        patterns = []
        
        if len(candles) < 15:
            return patterns
        
        # النموذج الماسي: توسع ثم تضييق
        ranges = [c.total_range for c in candles[-15:]]
        
        # النصف الأول: تتسع النطاقات
        first_half = ranges[:7]
        second_half = ranges[7:]
        
        first_trend = np.polyfit(range(7), first_half, 1)[0] if len(first_half) >= 2 else 0
        second_trend = np.polyfit(range(7), second_half, 1)[0] if len(second_half) >= 2 else 0
        
        if first_trend > 0 and second_trend < 0 and abs(first_trend) > 0.01 and abs(second_trend) > 0.01:
            patterns.append(Pattern(
                pattern_type="Diamond",
                index=len(candles)-1, direction="bearish",
                quality=0.85, confidence=0.75,
                hidden=True,
            ))
        
        return patterns
    
    def _detect_megaphone(self, candles) -> List[Pattern]:
        """اكتشاف نموذج البوق المتسع"""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        highs = [c.high for c in candles[-20:]]
        lows = [c.low for c in candles[-20:]]
        
        # قمم تصعد وقيعان تنخفض = بوق متسع
        peaks = self._find_peaks(highs)
        valleys = self._find_valleys(lows)
        
        if len(peaks) >= 3 and len(valleys) >= 3:
            if peaks[-1] > peaks[-2] > peaks[-3] and valleys[-1] < valleys[-2] < valleys[-3]:
                patterns.append(Pattern(
                    pattern_type="Megaphone",
                    index=len(candles)-1, direction="bearish",
                    quality=0.75, confidence=0.7,
                    hidden=True,
                ))
        
        return patterns
    
    def _detect_quasimodo(self, candles) -> List[Pattern]:
        """اكتشاف الكوازيمودو (النموذج الأحدب)"""
        patterns = []
        
        if len(candles) < 15:
            return patterns
        
        highs = [c.high for c in candles[-15:]]
        lows = [c.low for c in candles[-15:]]
        
        # البحث عن Lower High ثم Higher High (انعكاس هبوطي)
        peaks = self._find_peaks(highs)
        if len(peaks) >= 3:
            if peaks[-3] < peaks[-2] and peaks[-2] > peaks[-1]:
                # Lower High -> Higher High -> Lower High
                if peaks[-3] < peaks[-1] < peaks[-2]:
                    patterns.append(Pattern(
                        pattern_type="Quasimodo",
                        index=len(candles)-1, direction="bearish",
                        quality=0.8, confidence=0.75,
                        hidden=True,
                    ))
        
        # البحث عن Higher Low ثم Lower Low (انعكاس صعودي)
        valleys = self._find_valleys(lows)
        if len(valleys) >= 3:
            if valleys[-3] > valleys[-2] and valleys[-2] < valleys[-1]:
                if valleys[-3] > valleys[-1] > valleys[-2]:
                    patterns.append(Pattern(
                        pattern_type="Quasimodo",
                        index=len(candles)-1, direction="bullish",
                        quality=0.8, confidence=0.75,
                        hidden=True,
                    ))
        
        return patterns
    
    def _detect_three_bar_reversal(self, candles) -> List[Pattern]:
        """اكتشاف الانعكاس الثلاثي (النادر)"""
        patterns = []
        
        for i in range(2, len(candles)):
            c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
            
            # انعكاس هبوطي: صاعد - صاعد بظل علوي - هابط
            if (c1.is_bullish and c2.is_bullish and c2.upper_wick > c2.body and
                not c3.is_bullish and c3.close < c1.close):
                patterns.append(Pattern(
                    pattern_type="ThreeBarReversal",
                    index=i, direction="bearish",
                    quality=0.7, confidence=0.65,
                    hidden=True,
                ))
            
            # انعكاس صعودي
            if (not c1.is_bullish and not c2.is_bullish and c2.lower_wick > c2.body and
                c3.is_bullish and c3.close > c1.close):
                patterns.append(Pattern(
                    pattern_type="ThreeBarReversal",
                    index=i, direction="bullish",
                    quality=0.7, confidence=0.65,
                    hidden=True,
                ))
        
        return patterns
    
    def _find_killer_candles(self, candles) -> List[Dict]:
        """اكتشاف الشموع القاتلة (أكبر بـ 3 أضعاف من المتوسط)"""
        return [
            {"index": c.index, "direction": "bullish" if c.is_bullish else "bearish",
             "size_ratio": c.relative_size}
            for c in candles if c.killer_candle
        ]
    
    def _analyze_wick_stories(self, candles) -> List[Dict]:
        """تحليل قصص الأذيال"""
        stories = []
        
        for i in range(1, len(candles)):
            c = candles[i]
            
            # ذيل اختبار
            if c.upper_wick > c.total_range * 0.7:
                stories.append({
                    "index": i, "type": "ProbeWick",
                    "direction": "up",
                    "meaning": "اختبار مقاومة - سيعود لاختبارها لاحقاً",
                })
            
            if c.lower_wick > c.total_range * 0.7:
                stories.append({
                    "index": i, "type": "ProbeWick",
                    "direction": "down",
                    "meaning": "اختبار دعم - سيعود لاختباره لاحقاً",
                })
            
            # ذيل مزدوج (إنذار أحمر)
            if i >= 3:
                prev_3 = candles[i-3:i]
                wicks_up = sum(1 for pc in prev_3 if pc.upper_wick > pc.total_range * 0.5)
                wicks_down = sum(1 for pc in prev_3 if pc.lower_wick > pc.total_range * 0.5)
                
                if wicks_up >= 2:
                    stories.append({
                        "index": i, "type": "DoubleWick",
                        "direction": "up",
                        "meaning": "إنذار أحمر - انعكاس هبوطي قريب",
                    })
                if wicks_down >= 2:
                    stories.append({
                        "index": i, "type": "DoubleWick",
                        "direction": "down",
                        "meaning": "إنذار أحمر - انعكاس صعودي قريب",
                    })
        
        return stories
    
    def _tell_candle_story(self, recent_candles) -> str:
        """سرد قصة الشموع الأخيرة بالعربية"""
        if not recent_candles:
            return "لا توجد شموع كافية"
        
        story_parts = []
        last = recent_candles[-1]
        
        if last.killer_candle:
            story_parts.append("شمعة قاتلة ظهرت - حركة عنيفة قادمة")
        
        if last.path_type == "FinalRejection":
            story_parts.append("السعر يظهر رفضاً نهائياً - انعكاس محتمل")
        elif last.path_type == "RisingBear":
            story_parts.append("صعود خادع - القوة الحقيقية للبائعين")
        elif last.path_type == "FallingBull":
            story_parts.append("هبوط خادع - القوة الحقيقية للمشترين")
        
        if last.is_doji:
            story_parts.append("السوق في حالة تردد - قرار قريب")
        
        if not story_parts:
            story_parts.append("السوق يتحرك بشكل طبيعي بدون إشارات استثنائية")
        
        return ". ".join(story_parts)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║          الدرجة الرابعة: تحليل الزمن والزخم (Time & Momentum)             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class TimeMomentumAnalyzer:
    """
    يحلل الزمن والزخم كبعدين أساسيين.
    الزمن ليس مجرد عدد شموع، بل عمر الموجة ومرحلتها.
    الزخم ليس مجرد سرعة، بل صحة الحركة.
    """
    
    def analyze(self, highs, lows, closes, volumes) -> Dict:
        """
        تحليل الزمن والزخم معاً
        """
        # تحليل الموجات
        waves = self._decompose_waves(highs, lows, closes)
        
        # تحليل الزمن
        time_analysis = self._analyze_time(waves)
        
        # تحليل الزخم
        momentum_analysis = self._analyze_momentum(highs, lows, closes, volumes)
        
        # التآزر بين الزمن والزخم
        synergy = self._time_momentum_synergy(time_analysis, momentum_analysis)
        
        return {
            "waves": waves,
            "time": time_analysis,
            "momentum": momentum_analysis,
            "synergy": synergy,
            "current_phase": self._determine_current_phase(waves),
        }
    
    def _decompose_waves(self, highs, lows, closes) -> List[Wave]:
        """تفكيك السعر إلى موجات"""
        waves = []
        
        if len(closes) < 5:
            return waves
        
        # إيجاد نقاط الانعكاس
        reversals = []
        for i in range(2, len(closes)-2):
            if self._is_reversal_point(highs, lows, closes, i):
                reversals.append(i)
        
        if len(reversals) < 2:
            return waves
        
        # بناء الموجات بين نقاط الانعكاس
        for i in range(1, len(reversals)):
            start, end = reversals[i-1], reversals[i]
            if end - start < 2:
                continue
            
            direction = 'up' if closes[end] > closes[start] else 'down'
            price_distance = abs(closes[end] - closes[start])
            candle_count = end - start
            
            # حساب السرعة
            time_in_candles = candle_count
            avg_speed = price_distance / max(time_in_candles, 1)
            
            # أقصى سرعة (أسرع شمعة في الموجة)
            max_move = max(abs(closes[j] - closes[j-1]) for j in range(start+1, end+1))
            
            # صحة الموجة
            health = self._calculate_wave_health(highs[start:end+1], lows[start:end+1], 
                                                  closes[start:end+1], direction)
            
            # العمر الزمني
            time_age = self._calculate_time_age(candle_count, waves)
            
            # مرحلة الموجة
            phase = self._determine_wave_phase(time_age, health)
            
            # درجة الإنهاك
            exhaustion = self._calculate_exhaustion(highs[start:end+1], lows[start:end+1],
                                                     closes[start:end+1], direction, time_age)
            
            waves.append(Wave(
                start_index=start, end_index=end,
                direction=direction,
                price_distance=price_distance,
                candle_count=candle_count,
                average_speed=avg_speed,
                max_speed=max_move,
                health=health,
                phase=phase,
                time_age=time_age,
                exhaustion_score=exhaustion,
            ))
        
        return waves
    
    def _is_reversal_point(self, highs, lows, closes, i) -> bool:
        """اكتشاف نقاط الانعكاس"""
        # قمة
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
            return True
        # قاع
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
            return True
        return False
    
    def _calculate_wave_health(self, highs, lows, closes, direction) -> float:
        """حساب صحة الموجة (0=مريضة, 1=قوية جداً)"""
        if len(closes) < 3:
            return 0.5
        
        # 1. الاستمرارية (نسبة الشموع في اتجاه الموجة)
        if direction == 'up':
            directional_bars = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
        else:
            directional_bars = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i-1])
        
        continuity = directional_bars / max(len(closes)-1, 1)
        
        # 2. التداخل (كلما قل = موجة أقوى)
        ranges = highs - lows
        avg_range = np.mean(ranges)
        if avg_range > 0:
            overlaps = 0
            for i in range(1, len(closes)):
                if direction == 'up':
                    if lows[i] < lows[i-1]:
                        overlaps += 1
                else:
                    if highs[i] > highs[i-1]:
                        overlaps += 1
            overlap_ratio = overlaps / max(len(closes)-1, 1)
        else:
            overlap_ratio = 0.5
        
        # 3. السرعة النسبية
        total_move = abs(closes[-1] - closes[0])
        total_path = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes)))
        efficiency = total_move / max(total_path, 1)
        
        return (continuity * 0.3 + (1-overlap_ratio) * 0.4 + efficiency * 0.3)
    
    def _calculate_time_age(self, candle_count, previous_waves) -> float:
        """حساب العمر الزمني النسبي للموجة"""
        if not previous_waves:
            # لا توجد موجات سابقة للمقارنة، نفترض عمراً متوسطاً
            base_lifespan = 10
        else:
            avg_lifespan = np.mean([w.candle_count for w in previous_waves[-5:]])
            base_lifespan = max(3, avg_lifespan)
        
        age = candle_count / base_lifespan
        return min(1.5, age)  # يمكن أن تتجاوز 1.0 (موجة أطول من المعتاد)
    
    def _determine_wave_phase(self, time_age, health) -> str:
        """تحديد مرحلة الموجة"""
        if time_age < 0.25:
            return "Birth"
        elif time_age < 0.5:
            return "Growth"
        elif time_age < 0.75:
            return "Maturity"
        else:
            return "Decay"
    
    def _calculate_exhaustion(self, highs, lows, closes, direction, time_age) -> float:
        """حساب درجة الإنهاك"""
        exhaustion = 0.0
        
        # العمر (كلما زاد = إنهاك أكثر)
        exhaustion += time_age * 0.4
        
        # التباطؤ في النهاية
        if len(closes) >= 4:
            first_half_speed = abs(closes[len(closes)//2] - closes[0]) / max(len(closes)//2, 1)
            second_half_speed = abs(closes[-1] - closes[len(closes)//2]) / max(len(closes)-len(closes)//2, 1)
            
            if first_half_speed > 0 and second_half_speed / first_half_speed < 0.5:
                exhaustion += 0.3
        
        # الشموع الصغيرة في النهاية
        if len(highs) >= 5:
            recent_ranges = (highs[-3:] - lows[-3:])
            all_ranges = (highs - lows)
            if np.mean(all_ranges) > 0 and np.mean(recent_ranges) < np.mean(all_ranges) * 0.5:
                exhaustion += 0.3
        
        return min(1.0, exhaustion)
    
    def _analyze_time(self, waves) -> Dict:
        """تحليل الزمن"""
        if not waves:
            return {"current_position": "غير معروف", "symmetry": None}
        
        current_wave = waves[-1]
        
        # التناظر الزمني
        symmetry = None
        if len(waves) >= 2:
            # مقارنة الموجة الحالية بأختها السابقة
            prev_similar = [w for w in waves[-5:-1] if w.direction == current_wave.direction]
            if prev_similar:
                avg_time = np.mean([w.candle_count for w in prev_similar])
                ratio = current_wave.candle_count / max(avg_time, 1)
                if 0.8 < ratio < 1.2:
                    symmetry = "متناظرة"
                elif ratio > 1.3:
                    symmetry = "ممتدة جداً - إنهاك"
                elif ratio < 0.7:
                    symmetry = "قصيرة جداً - قد تستمر"
        
        # نافذة الانعكاس الزمني
        reversal_window = current_wave.time_age > 0.7
        
        return {
            "current_wave_time": current_wave.candle_count,
            "time_age": current_wave.time_age,
            "phase": current_wave.phase,
            "symmetry": symmetry,
            "reversal_window": reversal_window,
            "warning": "الموجة دخلت نافذة الانعكاس" if reversal_window else None,
        }
    
    def _analyze_momentum(self, highs, lows, closes, volumes) -> Dict:
        """تحليل الزخم"""
        if len(closes) < 10:
            return {"state": "غير كافٍ"}
        
        # السرعة الحالية
        recent_speed = np.mean(np.abs(np.diff(closes[-5:])))
        overall_speed = np.mean(np.abs(np.diff(closes[-20:]))) if len(closes) >= 20 else recent_speed
        
        # التغير في السرعة (تسارع/تباطؤ)
        if overall_speed > 0:
            speed_ratio = recent_speed / overall_speed
        else:
            speed_ratio = 1.0
        
        # هل هناك تباطؤ؟
        if speed_ratio > 1.5:
            momentum_state = "متسارع"
        elif speed_ratio < 0.5:
            momentum_state = "متباطئ"
        else:
            momentum_state = "ثابت"
        
        # كشف الحركة العمودية (Parabolic)
        parabolic = self._detect_parabolic(highs[-10:], lows[-10:], closes[-10:])
        
        # الزخم الصحي vs المريض
        ranges = np.array(highs[-10:]) - np.array(lows[-10:])
        avg_range = np.mean(ranges)
        
        if avg_range > 0:
            # زخم صحي = نطاقات كبيرة + سرعة
            # زخم مريض = نطاقات صغيرة + تردد
            range_consistency = 1.0 - np.std(ranges) / max(avg_range, 1)
            health = "صحي" if range_consistency > 0.6 and momentum_state == "متسارع" else \
                     "مريض" if momentum_state == "متباطئ" else "متوسط"
        else:
            health = "غير معروف"
        
        return {
            "state": momentum_state,
            "speed_ratio": speed_ratio,
            "parabolic": parabolic,
            "health": health,
        }
    
    def _detect_parabolic(self, highs, lows, closes) -> bool:
        """كشف الحركة العمودية (Parabolic)"""
        if len(closes) < 8:
            return False
        
        # 6 من آخر 8 شموع في نفس الاتجاه
        diffs = np.diff(closes)
        up_count = sum(1 for d in diffs if d > 0)
        
        return up_count >= 7 or up_count <= 1
    
    def _time_momentum_synergy(self, time_analysis, momentum_analysis) -> Dict:
        """التآزر بين الزمن والزخم"""
        warnings = []
        
        # موجة متعبة + زخم قوي = استمرار محتمل لكنه خطير
        if time_analysis.get('reversal_window') and momentum_analysis.get('state') == 'متسارع':
            warnings.append("الموجة في نافذة انعكاس لكن الزخم قوي - إما استمرار عنيف أو انعكاس حاد")
        
        # موجة شابة + زخم ضعيف = موجة مريضة منذ البداية
        if time_analysis.get('time_age', 0) < 0.3 and momentum_analysis.get('state') == 'متباطئ':
            warnings.append("موجة شابة بزخم ضعيف - الحركة مشبوهة وقد تنهار قريباً")
        
        # حركة عمودية = سيولة الاتجاه تنفد
        if momentum_analysis.get('parabolic'):
            warnings.append("حركة عمودية - سيولة الاتجاه تنفد - استعداد لانعكاس")
        
        return {
            "warnings": warnings,
            "synergy_score": 0.5 + (0.3 if not warnings else 0),
        }
    
    def _determine_current_phase(self, waves) -> str:
        """تحديد المرحلة الحالية للسوق"""
        if not waves:
            return "غير معروف"
        
        current = waves[-1]
        return current.phase


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║          الدرجة الخامسة: مناطق الدعم والمقاومة الديناميكية                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicSupportResistanceAnalyzer:
    """
    يبني مناطق دعم ومقاومة حية.
    ليست خطوطاً ثابتة، بل مناطق تتغير قوتها مع الزمن والاختبارات.
    """
    
    def analyze(self, highs, lows, closes, volumes, swings) -> Dict:
        """
        تحليل مناطق الدعم والمقاومة
        """
        zones = self._find_zones(highs, lows, closes, volumes, swings)
        active_zones = self._find_active_zones(zones, closes[-1])
        
        return {
            "all_zones": zones[-10:],  # آخر 10 مناطق
            "active_zones": active_zones,
            "nearest_support": self._find_nearest_support(active_zones, closes[-1]),
            "nearest_resistance": self._find_nearest_resistance(active_zones, closes[-1]),
        }
    
    def _find_zones(self, highs, lows, closes, volumes, swings) -> List[SupportResistanceZone]:
        """إيجاد مناطق الدعم والمقاومة"""
        zones = []
        
        # من نقاط التأرجح
        for swing in swings:
            if swing.swing_type in ['HH', 'LH']:
                zones.append(SupportResistanceZone(
                    price_high=swing.price * 1.002,
                    price_low=swing.price * 0.998,
                    zone_type='resistance',
                    origin_index=swing.index,
                    touches=1,
                    freshness=1.0,
                    strength_score=swing.strength,
                    is_live=True,
                ))
            else:
                zones.append(SupportResistanceZone(
                    price_high=swing.price * 1.002,
                    price_low=swing.price * 0.998,
                    zone_type='support',
                    origin_index=swing.index,
                    touches=1,
                    freshness=1.0,
                    strength_score=swing.strength,
                    is_live=True,
                ))
        
        # تحديث المناطق باختباراتها
        zones = self._update_zone_touches(zones, highs, lows, closes)
        
        return zones
    
    def _update_zone_touches(self, zones, highs, lows, closes) -> List[SupportResistanceZone]:
        """تحديث عدد اللمسات ودرجة النضارة"""
        for zone in zones:
            touches = 0
            for i in range(zone.origin_index + 1, len(closes)):
                if zone.zone_type == 'support':
                    if lows[i] <= zone.price_high and lows[i] >= zone.price_low:
                        touches += 1
                else:
                    if highs[i] >= zone.price_low and highs[i] <= zone.price_high:
                        touches += 1
            
            zone.touches += touches
            # النضارة تقل مع كل لمسة
            zone.freshness = max(0.1, 1.0 - touches * 0.25)
            zone.strength_score *= zone.freshness
            zone.is_live = zone.touches <= 3 and zone.freshness > 0.3
        
        return zones
    
    def _find_active_zones(self, zones, current_price) -> List[SupportResistanceZone]:
        """المناطق النشطة القريبة من السعر"""
        return [z for z in zones if z.is_live and 
                abs(z.price_high - current_price) < current_price * 0.05]
    
    def _find_nearest_support(self, zones, current_price) -> Optional[Dict]:
        """أقرب دعم"""
        supports = [z for z in zones if z.zone_type == 'support' and z.price_high < current_price]
        if not supports:
            return None
        nearest = min(supports, key=lambda z: current_price - z.price_high)
        return {"price": nearest.price_high, "strength": nearest.strength_score}
    
    def _find_nearest_resistance(self, zones, current_price) -> Optional[Dict]:
        """أقرب مقاومة"""
        resistances = [z for z in zones if z.zone_type == 'resistance' and z.price_low > current_price]
        if not resistances:
            return None
        nearest = min(resistances, key=lambda z: z.price_low - current_price)
        return {"price": nearest.price_low, "strength": nearest.strength_score}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                الدرجة النهائية: الاستراتيجية الموحدة                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PriceActionStrategy:
    """
    الاستراتيجية الكاملة لمدرسة البرايس أكشن الديناميكي.
    تجمع كل المحللات في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.structure_analyzer = LivingStructureAnalyzer()
        self.liquidity_analyzer = DynamicLiquidityAnalyzer()
        self.candlestick_analyzer = AdvancedCandlestickAnalyzer()
        self.time_momentum_analyzer = TimeMomentumAnalyzer()
        self.sr_analyzer = DynamicSupportResistanceAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل للشارت
        يتوقع chart_data يحتوي على:
        - opens, highs, lows, closes, volumes كمصفوفات numpy
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10, 
                    "reason": "بيانات غير كافية (تحتاج 20 شمعة على الأقل)"}
        
        # 1. تحليل هيكل السوق
        structure = self.structure_analyzer.analyze(highs, lows, closes, volumes)
        
        # 2. تحليل السيولة
        liquidity = self.liquidity_analyzer.analyze(highs, lows, closes, volumes, 
                                                     structure['swings'])
        
        # 3. تحليل الشموع
        candles = self.candlestick_analyzer.analyze(opens, highs, lows, closes, volumes)
        
        # 4. تحليل الزمن والزخم
        time_momentum = self.time_momentum_analyzer.analyze(highs, lows, closes, volumes)
        
        # 5. مناطق الدعم والمقاومة
        sr = self.sr_analyzer.analyze(highs, lows, closes, volumes, structure['swings'])
        
        # 6. تجميع كل الإشارات واتخاذ القرار
        decision = self._make_decision(structure, liquidity, candles, time_momentum, sr)
        
        return {
            **decision,
            "structure": structure,
            "liquidity": liquidity,
            "candles": candles,
            "time_momentum": time_momentum,
            "support_resistance": sr,
        }
    
    def _make_decision(self, structure, liquidity, candles, time_momentum, sr) -> Dict:
        """
        تجميع كل التحليلات في قرار واحد.
        هذا يحاكي عقل المتداول المحترف وهو يوازن كل العوامل.
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من هيكل السوق ----
        trend = structure.get('trend', {})
        if trend.get('direction') == 'صاعد' and trend.get('strength', 0) > 0.5:
            buy_signals.append(("هيكل صاعد قوي", trend['strength'] * 0.25))
        elif trend.get('direction') == 'هابط' and trend.get('strength', 0) > 0.5:
            sell_signals.append(("هيكل هابط قوي", trend['strength'] * 0.25))
        
        internal = structure.get('internal', {})
        if internal.get('mss'):
            mss = internal['mss']
            if mss.get('confirmed'):
                if mss['direction'] == 'bullish':
                    buy_signals.append(("MSS - تحول هيكل صاعد", 0.3))
                elif mss['direction'] == 'bearish':
                    sell_signals.append(("MSS - تحول هيكل هابط", 0.3))
        
        # ---- من السيولة ----
        liq_gravity = liquidity.get('gravity', {})
        if liq_gravity.get('direction') == 'up' and liq_gravity.get('strength', 0) > 0.6:
            buy_signals.append(("سيولة تنجذب للأعلى", liq_gravity['strength'] * 0.15))
        elif liq_gravity.get('direction') == 'down' and liq_gravity.get('strength', 0) > 0.6:
            sell_signals.append(("سيولة تنجذب للأسفل", liq_gravity['strength'] * 0.15))
        
        trend_liq = liquidity.get('trend_liquidity', {})
        if trend_liq.get('detected'):
            # سيولة الاتجاه = خطر الانعكاس
            if structure.get('trend', {}).get('direction') == 'صاعد':
                sell_signals.append(("سيولة اتجاه صاعد تنفد", 0.25))
            else:
                buy_signals.append(("سيولة اتجاه هابط تنفد", 0.25))
        
        # ---- من أنماط الشموع ----
        patterns = candles.get('patterns', [])
        recent_patterns = patterns[-5:] if len(patterns) > 5 else patterns
        for p in recent_patterns:
            weight = p.confidence * p.quality * 0.2
            if p.direction == 'bullish':
                buy_signals.append((f"نمط {p.pattern_type}", weight))
            elif p.direction == 'bearish':
                sell_signals.append((f"نمط {p.pattern_type}", weight))
        
        # ---- من الزمن والزخم ----
        time_data = time_momentum.get('time', {})
        momentum_data = time_momentum.get('momentum', {})
        synergy = time_momentum.get('synergy', {})
        
        if synergy.get('warnings'):
            # تقليل الثقة عند وجود تحذيرات
            pass
        
        if time_data.get('reversal_window') and momentum_data.get('state') == 'متباطئ':
            if structure.get('trend', {}).get('direction') == 'صاعد':
                sell_signals.append(("نافذة انعكاس + تباطؤ", 0.2))
            else:
                buy_signals.append(("نافذة انعكاس + تباطؤ", 0.2))
        
        # ---- حساب القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            confidence = min(95, int(total_buy * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            confidence = min(95, int(total_sell * 100))
        elif total_buy > total_sell:
            recommendation = "شراء ضعيف"
            confidence = int((total_buy - total_sell) * 100) + 30
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = int((total_sell - total_buy) * 100) + 30
        else:
            recommendation = "محايد"
            confidence = 25
        
        # بناء السبب
        all_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)
        top_reasons = [s[0] for s in all_signals[:5]]
        reason = " | ".join(top_reasons) if top_reasons else "السوق في حالة توازن"
        
        # إضافة تحذيرات
        warnings = time_momentum.get('synergy', {}).get('warnings', [])
        if warnings:
            reason += " ⚠️ " + " ⚠️ ".join(warnings)
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         دالة الاستخدام الرئيسية                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def create_price_action_strategy():
    """
    إنشاء استراتيجية البرايس أكشن الجاهزة للاستخدام
    """
    return PriceActionStrategy()


# للاستخدام المباشر
if __name__ == "__main__":
    # مثال
    import pandas as pd
    
    # تحميل بيانات الشارت
    # df = pd.read_csv("chart_data.csv")
    
    strategy = create_price_action_strategy()
    # result = strategy.analyze({
    #     "opens": df['open'].values,
    #     "highs": df['high'].values,
    #     "lows": df['low'].values,
    #     "closes": df['close'].values,
    #     "volumes": df['volume'].values,
    # })
    # print(result)