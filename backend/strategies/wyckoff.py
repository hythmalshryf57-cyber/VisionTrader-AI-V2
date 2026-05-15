"""
═══════════════════════════════════════════════════════════════════════════════
WYCKOFF METHOD - النسخة الديناميكية المتكاملة (الإصدار 2.0 - المعدل)
المدرسة الثالثة: منهجية وايكوف - لغة المؤسسات الخفية
═══════════════════════════════════════════════════════════════════════════════

ريتشارد وايكوف (1873-1934) كان أول من كشف كيف تتلاعب المؤسسات الكبرى بالأسواق.
هو من اخترع مفاهيم: التجميع، التوزيع، السبب والنتيجة، والجهد مقابل النتيجة.

هذه النسخة ديناميكية بالكامل - معدلة بـ 15 تحسيناً تداولياً:
- لا أرقام ثابتة
- لا نسب جامدة
- كل مرحلة تتحدد من سلوك السعر والحجم والزمن معاً
- السوق يخبرك بمرحلته، لا أنت من تفرضها عليه
- الذكاء التداولي: السياق يحكم كل شيء

التعديلات الجوهرية:
🔴 5 أخطاء تداولية تم إصلاحها
🟡 7 تحسينات ذكاء تداولي
🟢 3 فرص قوية غير مستغلة تم تفعيلها

الفلسفة:
السوق يتحرك في دورات. كل دورة = تجميع ← اتجاه صاعد ← توزيع ← اتجاه هابط.
الرجل الذكي (Composite Operator) يترك بصماته على الشارت.
اقرأ البصمات، ترى الحقيقة.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class WyckoffPhase(Enum):
    """مراحل دورة وايكوف"""
    ACCUMULATION_PHASE_A = "تجميع - مرحلة أ (توقف الهبوط)"
    ACCUMULATION_PHASE_B = "تجميع - مرحلة ب (بناء السبب)"
    ACCUMULATION_PHASE_C = "تجميع - مرحلة ج (الاختبار الربيعي)"
    ACCUMULATION_PHASE_D = "تجميع - مرحلة د (تأكيد القوة)"
    ACCUMULATION_PHASE_E = "تجميع - مرحلة هـ (الانطلاق)"
    
    DISTRIBUTION_PHASE_A = "توزيع - مرحلة أ (توقف الصعود)"
    DISTRIBUTION_PHASE_B = "توزيع - مرحلة ب (بناء السبب)"
    DISTRIBUTION_PHASE_C = "توزيع - مرحلة ج (الاختبار الخريفي)"
    DISTRIBUTION_PHASE_D = "توزيع - مرحلة د (تأكيد الضعف)"
    DISTRIBUTION_PHASE_E = "توزيع - مرحلة هـ (الانهيار)"
    
    MARKUP = "اتجاه صاعد"
    MARKDOWN = "اتجاه هابط"
    UNKNOWN = "غير محدد"


@dataclass
class WyckoffPoint:
    """نقطة مهمة في تحليل وايكوف"""
    index: int
    price: float
    volume: float
    point_type: str  # PS, SC, AR, ST, SOS, SOW, LPS, LPSY, UT, UTAD, etc.
    significance: float  # 0-1 أهمية النقطة
    description: str


@dataclass
class Wave:
    """موجة سعرية"""
    start_idx: int
    end_idx: int
    direction: str
    price_change: float
    duration: int
    volume_profile: str  # 'increasing', 'decreasing', 'climax', 'divergence'


@dataclass  
class TradingRange:
    """نطاق تداول (منطقة تجميع أو توزيع)"""
    start_idx: int
    end_idx: int
    high: float
    low: float
    mid: float
    range_type: str  # 'accumulation', 'distribution', 'unknown'
    phase: WyckoffPhase
    duration: int
    volume_trend: str  # 'drying_up', 'expanding', 'stable'
    confirmed: bool
    range_magnitude: float = 0.0  # 🟢 تعديل 14: حجم النطاق (مدى × مدة)
    breakout_quality: float = 0.0  # 🟡 تعديل 12: جودة شمعة الخروج
    support_resistance_age: int = 0  # 🟡 تعديل 8: عمر الدعم/المقاومة
    range_size_percentile: float = 0.5  # 🟡 تعديل 10: مقارنة بالنطاقات السابقة


@dataclass
class EffortResult:
    """علاقة الجهد مقابل النتيجة"""
    index: int
    effort_type: str  # 'high_effort', 'low_effort', 'normal'
    result_type: str  # 'big_result', 'small_result', 'no_result', 'reverse_result'
    interpretation: str  # التفسير المباشر
    significance: float  # 0-1
    consecutive_count: int = 0  # 🟡 تعديل 11: عدد الإشارات المتتالية من نفس النوع
    context_type: str = 'normal'  # 🟡 تعديل 6: سياق الشمعة (exhaustion/normal)


@dataclass
class SpringUpthrust:
    """اختبار ربيعي أو دفع علوي"""
    index: int
    event_type: str  # 'spring', 'upthrust', 'spring_test', 'upthrust_after_distribution', 'test_spring'
    penetration_price: float  # السعر الذي اخترق
    recovery_price: float  # سعر العودة
    volume_on_event: float
    relative_volume: float  # مقارنة بالمتوسط
    confirmed: bool
    quality: str  # 'high', 'medium', 'low'
    target_zone: Tuple[float, float]  # المنطقة المستهدفة
    support_age: int = 0  # 🟡 تعديل 8: عمر الدعم/المقاومة
    support_touches: int = 0  # 🟡 تعديل 8: عدد لمسات الدعم/المقاومة
    is_test_spring: bool = False  # 🟡 تعديل 9: هل هو Spring اختبار؟


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الأولى: محلل مراحل السوق الديناميكي                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicPhaseAnalyzer:
    """
    يحدد مرحلة السوق الحالية بطريقة ديناميكية.
    لا يعتمد على أرقام ثابتة، بل يقرأ سلوك السعر والحجم والزمن.
    
    المبدأ: السوق ينتقل بين المراحل بشكل طبيعي.
    كل مرحلة لها بصمة سلوكية فريدة، وليس نسبة رقمية محددة.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray) -> Dict:
        """
        تحديد المرحلة الديناميكي
        """
        # أولاً: هل نحن في نطاق أم اتجاه؟
        market_condition = self._assess_market_condition(highs, lows, closes)
        
        # تحديد النطاقات
        ranges = self._find_ranges(highs, lows, closes, volumes)
        
        # تحليل الاتجاهات بين النطاقات
        trends = self._analyze_trends_between_ranges(highs, lows, closes, volumes, ranges)
        
        # المرحلة الحالية
        current_phase = self._determine_current_phase(market_condition, ranges, trends, 
                                                       highs, lows, closes, volumes)
        
        return {
            "market_condition": market_condition,
            "ranges": ranges[-5:],  # آخر 5 نطاقات
            "trends": trends[-3:],   # آخر 3 اتجاهات
            "current_phase": current_phase,
            "phase_confidence": self._phase_confidence(current_phase, market_condition),
            "cycle_position": self._estimate_cycle_position(current_phase, highs, lows, closes, ranges),
        }
    
    def _assess_market_condition(self, highs: np.ndarray, lows: np.ndarray, 
                                  closes: np.ndarray) -> Dict:
        """
        تقييم حالة السوق: هل هو في نطاق أم في اتجاه؟
        ديناميكي 100%
        """
        if len(closes) < 30:
            return {"state": "غير كافٍ", "type": "unknown"}
        
        # 1. قياس التذبذب النسبي
        recent_range = max(highs[-20:]) - min(lows[-20:])
        older_range = max(highs[-40:-20]) - min(lows[-40:-20]) if len(closes) >= 40 else recent_range
        
        if older_range > 0:
            expansion_ratio = recent_range / older_range
        else:
            expansion_ratio = 1.0
        
        # 2. قياس الانضغاط (النطاق يضيق = تماسك)
        short_range = max(highs[-5:]) - min(lows[-5:])
        mid_range = max(highs[-15:]) - min(lows[-15:])
        
        if mid_range > 0:
            compression = short_range / mid_range
        else:
            compression = 1.0
        
        # 3. حركة السعر الصافية
        net_move = abs(closes[-1] - closes[-20])
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        if avg_range > 0:
            efficiency = net_move / avg_range
        else:
            efficiency = 0
        
        # 4. تقاطع السعر مع متوسطه
        sma = np.mean(closes[-20:])
        current_vs_sma = closes[-1] / sma - 1
        
        # 5. تحليل التداخل
        overlap = self._measure_price_overlap(highs[-20:], lows[-20:])
        
        # القرار الديناميكي
        if compression < 0.35 and abs(current_vs_sma) < 0.02:
            # نطاق ضيق جداً حول متوسطه = تماسك قوي
            state_type = "tight_range"
            state = "نطاق ضيق - بناء سبب"
        elif efficiency > 3.5 and overlap < 0.2:
            # حركة صافية كبيرة مع تداخل قليل = اتجاه قوي
            state_type = "strong_trend"
            state = "اتجاه قوي"
        elif efficiency > 2.0 and overlap < 0.4:
            state_type = "trend"
            state = "اتجاه"
        elif overlap > 0.6:
            state_type = "range"
            state = "نطاق تداول"
        else:
            state_type = "mixed"
            state = "مختلط"
        
        # تحديد النوع الفرعي
        if state_type in ["tight_range", "range"]:
            # هل هو تجميع أم توزيع؟
            # ننظر للموقع النسبي
            long_term_high = max(highs[-100:]) if len(highs) >= 100 else max(highs)
            long_term_low = min(lows[-100:]) if len(lows) >= 100 else min(lows)
            long_term_range = long_term_high - long_term_low
            
            if long_term_range > 0:
                position = (closes[-1] - long_term_low) / long_term_range
            else:
                position = 0.5
            
            if position < 0.35:
                range_type = "accumulation_probable"
            elif position > 0.65:
                range_type = "distribution_probable"
            else:
                range_type = "mid_range"
        else:
            range_type = "trending"
            position = 0.5
        
        return {
            "state": state,
            "type": state_type,
            "range_type": range_type,
            "compression": compression,
            "efficiency": efficiency,
            "overlap": overlap,
            "position_in_long_term": position,
        }
    
    def _measure_price_overlap(self, highs: np.ndarray, lows: np.ndarray) -> float:
        """
        قياس تداخل الأسعار بطريقة ديناميكية.
        تداخل عالي = نطاق. تداخل منخفض = اتجاه.
        """
        if len(highs) < 5:
            return 0.5
        
        overlaps = 0
        for i in range(1, len(highs)):
            # الشمعة الحالية تتداخل مع السابقة؟
            if min(highs[i], highs[i-1]) > max(lows[i], lows[i-1]):
                overlap_range = min(highs[i], highs[i-1]) - max(lows[i], lows[i-1])
                total_range = max(highs[i], highs[i-1]) - min(lows[i], lows[i-1])
                if total_range > 0:
                    overlaps += overlap_range / total_range
        
        return overlaps / max(len(highs) - 1, 1)
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """
        🔴 تعديل 1: حساب متوسط المدى الحقيقي (ATR) للاستخدام الديناميكي
        """
        if len(closes) < period:
            return np.mean(highs - lows)
        
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
        
        return np.mean(tr[-period:])
    
    def _find_ranges(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                     volumes: np.ndarray) -> List[TradingRange]:
        """
        اكتشاف نطاقات التداول ديناميكياً.
        النطاق: فترة تتماسك فيها الأسعار مع حجم متناقص.
        
        🟡 تعديل 10: مقارنة حجم النطاق بالنطاقات السابقة
        🟡 تعديل 12: تحليل جودة شمعة الخروج
        """
        ranges = []
        
        if len(closes) < 30:
            return ranges
        
        # حساب ATR للاستخدام الديناميكي
        atr = self._calculate_atr(highs, lows, closes)
        
        i = 0
        while i < len(closes) - 20:
            # البحث عن بداية نطاق
            segment = closes[i:i+15]
            segment_highs = highs[i:i+15]
            segment_lows = lows[i:i+15]
            
            price_range = max(segment_highs) - min(segment_lows)
            avg_segment_range = np.mean(segment_highs - segment_lows)
            
            if avg_segment_range == 0:
                i += 1
                continue
            
            # النطاق: حركة السعر محدودة نسبة لمدى الشموع
            range_ratio = price_range / avg_segment_range
            
            if range_ratio < 5.0:  # السعر محصور
                # وجدنا بداية نطاق
                range_start = i
                
                # تحديد نهاية النطاق (حتى يتسع السعر)
                range_high = max(segment_highs)
                range_low = min(segment_lows)
                
                j = i + 15
                while j < len(closes) - 5:
                    current_high = max(highs[i:j+1])
                    current_low = min(lows[i:j+1])
                    current_range = current_high - current_low
                    
                    # النطاق يتسع ببطء
                    if current_range > max(segment_highs) - min(segment_lows) * 1.5:
                        # اتسع - قد يكون خرج من النطاق
                        if j - range_start >= 10:
                            # 🟡 تعديل 12: تحليل جودة شمعة الخروج
                            breakout_quality = self._analyze_breakout_quality(
                                highs, lows, closes, volumes, j, atr, current_high if closes[j] > closes[range_start] else current_low
                            )
                            
                            # تحليل الحجم داخل النطاق
                            range_volumes = volumes[range_start:j]
                            vol_trend = self._analyze_volume_trend(range_volumes)
                            
                            # تحديد النوع
                            position = (closes[j-1] - min(lows[max(0,range_start-50):range_start])) / \
                                      max(highs[max(0,range_start-50):range_start] - 
                                          lows[max(0,range_start-50):range_start], 0.0001) \
                                      if range_start >= 50 else 0.5
                            
                            if position < 0.4:
                                range_type = 'accumulation'
                            elif position > 0.6:
                                range_type = 'distribution'
                            else:
                                range_type = 'unknown'
                            
                            # 🟡 تعديل 10: حساب حجم النطاق مقارنة بالسابق
                            range_magnitude = current_range * np.log1p(j - range_start)
                            size_percentile = self._calculate_range_size_percentile(
                                range_magnitude, ranges, highs, lows, closes, range_start
                            )
                            
                            # 🟡 تعديل 7: تحديد موقع النطاق (قاع تاريخي أم قريب)
                            support_age = self._calculate_support_resistance_age(
                                highs, lows, closes, current_low, range_start, 'support'
                            )
                            
                            ranges.append(TradingRange(
                                start_idx=range_start,
                                end_idx=j,
                                high=current_high,
                                low=current_low,
                                mid=(current_high + current_low) / 2,
                                range_type=range_type,
                                phase=self._identify_phase_in_range(highs[i:j], lows[i:j], 
                                                                     closes[i:j], volumes[i:j], 
                                                                     range_type),
                                duration=j - range_start,
                                volume_trend=vol_trend,
                                confirmed=True,
                                range_magnitude=range_magnitude,
                                breakout_quality=breakout_quality,
                                support_resistance_age=support_age,
                                range_size_percentile=size_percentile,
                            ))
                        i = j
                        break
                    j += 1
                else:
                    # وصلنا لنهاية البيانات والنطاق مستمر
                    if len(closes) - range_start >= 10:
                        range_volumes = volumes[range_start:]
                        vol_trend = self._analyze_volume_trend(range_volumes)
                        
                        range_magnitude = (max(highs[range_start:]) - min(lows[range_start:])) * \
                                         np.log1p(len(closes) - 1 - range_start)
                        
                        ranges.append(TradingRange(
                            start_idx=range_start,
                            end_idx=len(closes)-1,
                            high=max(highs[range_start:]),
                            low=min(lows[range_start:]),
                            mid=(max(highs[range_start:]) + min(lows[range_start:])) / 2,
                            range_type='unknown',
                            phase=WyckoffPhase.UNKNOWN,
                            duration=len(closes)-1 - range_start,
                            volume_trend=vol_trend,
                            confirmed=False,
                            range_magnitude=range_magnitude,
                            breakout_quality=0.0,
                            support_resistance_age=0,
                            range_size_percentile=0.5,
                        ))
                    i = len(closes)
            else:
                i += 1
        
        return ranges
    
    def _analyze_volume_trend(self, volumes: np.ndarray) -> str:
        """
        🔴 تعديل 2: تحليل اتجاه الحجم بمقارنة الربع الأول بالربع الأخير
        بدلاً من مقارنة نصفين. هذا يظهر جفاف/توسع الحجم بشكل أنقى.
        """
        if len(volumes) < 12:
            return 'stable'
        
        # تقسيم لأرباع
        quarter = len(volumes) // 4
        if quarter < 3:
            return 'stable'
        
        first_quarter = np.mean(volumes[:quarter])
        last_quarter = np.mean(volumes[-quarter:])
        
        if first_quarter == 0:
            return 'stable'
        
        ratio = last_quarter / first_quarter
        
        if ratio < 0.65:
            return 'drying_up'  # الحجم يجف = تجميع
        elif ratio > 1.5:
            return 'expanding'  # الحجم يتوسع = توزيع
        else:
            return 'stable'
    
    def _identify_phase_in_range(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray,
                                  range_type: str) -> WyckoffPhase:
        """
        تحديد المرحلة الفرعية داخل النطاق.
        ديناميكي بالكامل.
        
        🔴 تعديل 1: استخدام ATR بدلاً من نسبة ثابتة لاكتشاف الاختراقات الوهمية
        """
        if len(closes) < 10:
            return WyckoffPhase.UNKNOWN
        
        range_high = max(highs)
        range_low = min(lows)
        range_mid = (range_high + range_low) / 2
        total_range = range_high - range_low
        
        if total_range == 0:
            return WyckoffPhase.UNKNOWN
        
        current = closes[-1]
        position_in_range = (current - range_low) / total_range
        
        # تحليل الحجم في النصف الأخير
        half = len(volumes) // 2
        recent_vol = np.mean(volumes[half:])
        older_vol = np.mean(volumes[:half])
        
        if older_vol == 0:
            vol_ratio = 1.0
        else:
            vol_ratio = recent_vol / older_vol
        
        # 🔴 تعديل 1: استخدام ATR لتحديد نسبة الاختراق الوهمي ديناميكياً
        # في سوق هادئ (ATR صغير)، النسبة أكبر. في سوق متقلب (ATR كبير)، النسبة أصغر
        avg_range = np.mean(highs - lows)
        atr_ratio = avg_range / range_high if range_high > 0 else 0.005
        
        # نسبة الاختراق الوهمي تتكيف مع التقلب
        # كلما كان ATR أكبر (سوق متقلب)، كلما احتجنا لاختراق أعمق
        fake_break_threshold = max(0.001, min(0.01, atr_ratio * 0.5))
        
        # تحليل الاختراقات الوهمية
        fake_breaks_high = 0
        fake_breaks_low = 0
        
        for i in range(5, len(closes) - 2):
            if highs[i] > range_high * (1 + fake_break_threshold) and closes[i] < range_high:
                fake_breaks_high += 1
            if lows[i] < range_low * (1 - fake_break_threshold) and closes[i] > range_low:
                fake_breaks_low += 1
        
        if range_type == 'accumulation':
            if fake_breaks_low >= 2 and vol_ratio > 1.3:
                return WyckoffPhase.ACCUMULATION_PHASE_C  # Spring
            elif fake_breaks_low >= 1 and current > range_mid:
                return WyckoffPhase.ACCUMULATION_PHASE_D  # تأكيد
            elif position_in_range < 0.3 and vol_ratio < 0.7:
                return WyckoffPhase.ACCUMULATION_PHASE_B  # بناء السبب
            elif current > range_mid * 1.05 and vol_ratio > 1.2:
                return WyckoffPhase.ACCUMULATION_PHASE_E  # انطلاق
            else:
                return WyckoffPhase.ACCUMULATION_PHASE_A  # توقف الهبوط
        
        elif range_type == 'distribution':
            if fake_breaks_high >= 2 and vol_ratio > 1.3:
                return WyckoffPhase.DISTRIBUTION_PHASE_C  # Upthrust
            elif fake_breaks_high >= 1 and current < range_mid:
                return WyckoffPhase.DISTRIBUTION_PHASE_D  # تأكيد
            elif position_in_range > 0.7 and vol_ratio < 0.7:
                return WyckoffPhase.DISTRIBUTION_PHASE_B  # بناء السبب
            elif current < range_mid * 0.95 and vol_ratio > 1.2:
                return WyckoffPhase.DISTRIBUTION_PHASE_E  # انهيار
            else:
                return WyckoffPhase.DISTRIBUTION_PHASE_A  # توقف الصعود
        
        return WyckoffPhase.UNKNOWN
    
    def _analyze_trends_between_ranges(self, highs: np.ndarray, lows: np.ndarray,
                                        closes: np.ndarray, volumes: np.ndarray,
                                        ranges: List[TradingRange]) -> List[Dict]:
        """تحليل الاتجاهات بين النطاقات"""
        trends = []
        
        if len(ranges) < 1:
            return trends
        
        # الاتجاه قبل آخر نطاق
        last_range = ranges[-1]
        if last_range.start_idx > 20:
            pre_range_start = max(0, last_range.start_idx - 30)
            pre_range = closes[pre_range_start:last_range.start_idx]
            
            if len(pre_range) >= 5:
                direction = 'up' if closes[last_range.start_idx-1] > pre_range[0] else 'down'
                strength = abs(closes[last_range.start_idx-1] - pre_range[0]) / \
                          np.mean(highs[pre_range_start:last_range.start_idx] - 
                                 lows[pre_range_start:last_range.start_idx])
                
                trends.append({
                    "direction": direction,
                    "strength": strength,
                    "leads_to_range": True,
                    "range_type": last_range.range_type,
                })
        
        # اتجاه ما بعد آخر نطاق (إذا كان النطاق قد انتهى)
        if last_range.end_idx < len(closes) - 5:
            post_range = closes[last_range.end_idx:]
            if len(post_range) >= 5:
                direction = 'up' if post_range[-1] > post_range[0] else 'down'
                strength = abs(post_range[-1] - post_range[0]) / \
                          np.mean(highs[last_range.end_idx:] - lows[last_range.end_idx:])
                
                trends.append({
                    "direction": direction,
                    "strength": strength,
                    "leads_to_range": False,
                    "is_post_range": True,
                })
        
        return trends
    
    def _determine_current_phase(self, market_condition: Dict, ranges: List[TradingRange],
                                  trends: List[Dict], highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray) -> WyckoffPhase:
        """تحديد المرحلة الحالية"""
        
        if market_condition.get('state') in ['نطاق ضيق - بناء سبب', 'نطاق تداول']:
            # نحن داخل نطاق
            if ranges:
                return ranges[-1].phase
        
        if market_condition.get('state') == 'اتجاه قوي':
            # نحن في اتجاه
            if trends:
                last_trend = trends[-1]
                if last_trend.get('direction') == 'up':
                    return WyckoffPhase.MARKUP
                else:
                    return WyckoffPhase.MARKDOWN
        
        if market_condition.get('state') == 'اتجاه':
            if trends:
                last_trend = trends[-1]
                if last_trend.get('direction') == 'up':
                    return WyckoffPhase.MARKUP
                else:
                    return WyckoffPhase.MARKDOWN
        
        return WyckoffPhase.UNKNOWN
    
    def _phase_confidence(self, phase: WyckoffPhase, market_condition: Dict) -> float:
        """حساب الثقة في تحديد المرحلة"""
        if phase in [WyckoffPhase.UNKNOWN]:
            return 0.3
        
        if phase in [WyckoffPhase.MARKUP, WyckoffPhase.MARKDOWN]:
            efficiency = market_condition.get('efficiency', 1)
            return min(0.9, 0.5 + efficiency * 0.1)
        
        # داخل نطاق
        compression = market_condition.get('compression', 0.5)
        return min(0.85, 0.4 + (1 - compression) * 0.5)
    
    def _estimate_cycle_position(self, phase: WyckoffPhase, highs: np.ndarray,
                                  lows: np.ndarray, closes: np.ndarray, 
                                  ranges: List[TradingRange]) -> float:
        """
        تقدير الموقع في الدورة (0 = بداية, 1 = نهاية)
        
        🔴 تعديل 3: حساب الوقت من بداية الموجة الحالية فقط
        """
        if phase == WyckoffPhase.ACCUMULATION_PHASE_A:
            return 0.05
        elif phase == WyckoffPhase.ACCUMULATION_PHASE_B:
            return 0.2
        elif phase == WyckoffPhase.ACCUMULATION_PHASE_C:
            return 0.35
        elif phase == WyckoffPhase.ACCUMULATION_PHASE_D:
            return 0.5
        elif phase == WyckoffPhase.ACCUMULATION_PHASE_E:
            return 0.6
        elif phase == WyckoffPhase.MARKUP:
            # 🔴 تعديل 3: حساب تقدم الموجة من بدايتها (نهاية آخر نطاق)
            if ranges:
                wave_start = ranges[-1].end_idx
            else:
                wave_start = max(0, len(closes) - 20)
            return self._estimate_trend_progress(closes[wave_start:], 'up')
        elif phase == WyckoffPhase.DISTRIBUTION_PHASE_A:
            return 0.65
        elif phase == WyckoffPhase.DISTRIBUTION_PHASE_B:
            return 0.75
        elif phase == WyckoffPhase.DISTRIBUTION_PHASE_C:
            return 0.85
        elif phase == WyckoffPhase.DISTRIBUTION_PHASE_D:
            return 0.92
        elif phase == WyckoffPhase.DISTRIBUTION_PHASE_E:
            return 0.97
        elif phase == WyckoffPhase.MARKDOWN:
            if ranges:
                wave_start = ranges[-1].end_idx
            else:
                wave_start = max(0, len(closes) - 20)
            return self._estimate_trend_progress(closes[wave_start:], 'down')
        
        return 0.5
    
    def _estimate_trend_progress(self, wave_closes: np.ndarray, direction: str) -> float:
        """
        🔴 تعديل 3: تقدير مدى تقدم الموجة من بيانات الموجة فقط
        
        time_factor يُحسب من طول الموجة الحالية، وليس من كل البيانات
        """
        if len(wave_closes) < 5:
            return 0.5
        
        high = max(wave_closes)
        low = min(wave_closes)
        
        if direction == 'up':
            if high == low:
                return 0.5
            progress = (wave_closes[-1] - low) / (high - low)
        else:
            if high == low:
                return 0.5
            progress = (high - wave_closes[-1]) / (high - low)
        
        # 🔴 تعديل 3: عامل الزمن من طول الموجة الحالية فقط
        # موجة قصيرة (أقل من 20 شمعة) = في البداية
        # موجة طويلة (أكثر من 50 شمعة) = في النهاية
        if len(wave_closes) < 20:
            time_factor = 0.2
        elif len(wave_closes) < 35:
            time_factor = 0.5
        elif len(wave_closes) < 50:
            time_factor = 0.7
        else:
            time_factor = 0.9
        
        return (progress * 0.6 + time_factor * 0.4)
    
    def _analyze_breakout_quality(self, highs: np.ndarray, lows: np.ndarray, 
                                   closes: np.ndarray, volumes: np.ndarray,
                                   breakout_idx: int, atr: float, range_border: float) -> float:
        """
        🟡 تعديل 12: تحليل جودة شمعة الخروج من النطاق
        
        خروج بشمعة قاتلة (3 أضعاف متوسط المدى) = حركة حقيقية
        خروج بطيء ومتردد = اختراق وهمي محتمل
        """
        if breakout_idx >= len(closes):
            return 0.5
        
        # حجم شمعة الاختراق
        bar_range = highs[breakout_idx] - lows[breakout_idx]
        
        if atr == 0:
            return 0.5
        
        # قوة الاختراق
        range_ratio = bar_range / atr
        
        # موقع الإغلاق
        if closes[breakout_idx] > closes[breakout_idx - 1] if breakout_idx > 0 else True:
            close_position = (closes[breakout_idx] - lows[breakout_idx]) / bar_range if bar_range > 0 else 0.5
        else:
            close_position = (highs[breakout_idx] - closes[breakout_idx]) / bar_range if bar_range > 0 else 0.5
        
        # حجم التداول على الاختراق
        avg_vol = np.mean(volumes[max(0, breakout_idx-10):breakout_idx]) if breakout_idx >= 5 else volumes[breakout_idx]
        vol_ratio = volumes[breakout_idx] / avg_vol if avg_vol > 0 else 1.0
        
        # التقييم
        quality = 0.0
        
        # شمعة كبيرة
        if range_ratio > 3.0:
            quality += 0.4
        elif range_ratio > 2.0:
            quality += 0.3
        elif range_ratio > 1.5:
            quality += 0.2
        else:
            quality += 0.1
        
        # إغلاق قوي
        if close_position > 0.8:
            quality += 0.3
        elif close_position > 0.6:
            quality += 0.2
        else:
            quality += 0.05
        
        # حجم مرتفع
        if vol_ratio > 2.0:
            quality += 0.3
        elif vol_ratio > 1.5:
            quality += 0.2
        elif vol_ratio > 1.0:
            quality += 0.1
        
        return min(1.0, quality)
    
    def _calculate_range_size_percentile(self, current_magnitude: float, 
                                          existing_ranges: List[TradingRange],
                                          highs: np.ndarray, lows: np.ndarray,
                                          closes: np.ndarray, current_idx: int) -> float:
        """
        🟡 تعديل 10: مقارنة حجم النطاق الحالي بالنطاقات السابقة
        
        النطاق الصغير جداً (مقارنة بالنطاقات السابقة) غالباً ليس تجميعاً حقيقياً بل استراحة
        """
        if not existing_ranges:
            return 0.5
        
        magnitudes = [r.range_magnitude for r in existing_ranges if r.range_magnitude > 0]
        
        if not magnitudes:
            return 0.5
        
        magnitudes.append(current_magnitude)
        magnitudes.sort()
        
        # موقع النطاق الحالي في التوزيع
        rank = magnitudes.index(current_magnitude)
        percentile = rank / max(len(magnitudes) - 1, 1)
        
        return percentile
    
    def _calculate_support_resistance_age(self, highs: np.ndarray, lows: np.ndarray,
                                           closes: np.ndarray, level: float, 
                                           current_idx: int, level_type: str) -> int:
        """
        🟡 تعديل 7: حساب عمر الدعم/المقاومة
        
        نطاق في قاع تاريخي (لم يُرَ منذ 200 شمعة) = تجميع قوي جداً
        نطاق في قاع قريب (شوهد قبل 20 شمعة) = تجميع ضعيف أو استراحة
        """
        if current_idx < 20:
            return 0
        
        # البحث عن آخر مرة كان السعر عند هذا المستوى
        lookback_start = max(0, current_idx - 200)
        
        last_touch = None
        for i in range(current_idx - 5, lookback_start, -1):
            if level_type == 'support':
                if abs(lows[i] - level) / level < 0.01:
                    last_touch = i
                    break
            else:
                if abs(highs[i] - level) / level < 0.01:
                    last_touch = i
                    break
        
        if last_touch is None:
            return 200  # لم يُلمس في آخر 200 شمعة
        
        return current_idx - last_touch


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الثانية: محلل الجهد مقابل النتيجة (Effort vs Result)       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class EffortResultAnalyzer:
    """
    يحلل علاقة الجهد (الحجم) مقابل النتيجة (حركة السعر).
    
    هذه هي بوصلتك في السوق:
    - جهد كبير + نتيجة كبيرة = استمرار (توافق)
    - جهد كبير + نتيجة صغيرة = انعكاس قريب (انحراف)
    - جهد صغير + نتيجة كبيرة = استمرار سهل (قلة مقاومة)
    - جهد صغير + نتيجة صغيرة = لا اهتمام = لا شيء
    
    🟡 تعديل 6: تفسير الإغلاق الوسط حسب سياق الشموع السابقة
    🟡 تعديل 11: مضاعفة وزن الإشارات المتتالية
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray) -> Dict:
        """
        تحليل الجهد مقابل النتيجة
        """
        # تحليل كل شمعة
        efforts = []
        
        for i in range(1, len(closes)):
            effort_result = self._analyze_single_bar(highs[i], lows[i], opens[i], 
                                                      closes[i], volumes[i],
                                                      highs[i-1], lows[i-1], closes[i-1],
                                                      volumes, i, highs, lows, closes)
            if effort_result:
                efforts.append(effort_result)
        
        # 🟡 تعديل 11: تراكم الإشارات المتتالية
        efforts = self._apply_consecutive_weighting(efforts)
        
        # تجميع الإشارات الحديثة
        recent_efforts = efforts[-20:] if len(efforts) >= 20 else efforts
        
        # إشارات التباعد
        divergences = self._detect_effort_divergences(recent_efforts)
        
        # الإشارة الحالية
        current_signal = self._interpret_current_efforts(recent_efforts[-5:])
        
        return {
            "recent_efforts": recent_efforts[-10:],
            "divergences": divergences,
            "current_signal": current_signal,
            "effort_balance": self._calculate_effort_balance(recent_efforts),
        }
    
    def _analyze_single_bar(self, high: float, low: float, open_p: float,
                             close: float, volume: float, prev_high: float,
                             prev_low: float, prev_close: float,
                             all_volumes: np.ndarray, index: int,
                             all_highs: np.ndarray, all_lows: np.ndarray,
                             all_closes: np.ndarray) -> Optional[EffortResult]:
        """
        تحليل شمعة واحدة: الجهد (الحجم) مقابل النتيجة (حركة السعر)
        ديناميكي بالكامل
        
        🟡 تعديل 6: تفسير "الإغلاق الوسط" حسب سياق الشموع الخمس السابقة
        """
        # حساب الجهد النسبي (مقارنة بالمتوسط المتحرك للحجم)
        if len(all_volumes) >= 10 and index >= 10:
            avg_vol = np.mean(all_volumes[max(0,index-10):index])
        else:
            avg_vol = volume
        
        if avg_vol == 0:
            return None
        
        relative_vol = volume / avg_vol
        
        # تصنيف الجهد
        if relative_vol > 2.0:
            effort = 'high_effort'
        elif relative_vol > 1.3:
            effort = 'above_normal'
        elif relative_vol < 0.4:
            effort = 'low_effort'
        else:
            effort = 'normal'
        
        # حساب النتيجة (حركة السعر نسبة للمدى النموذجي)
        price_move = abs(close - open_p)
        bar_range = high - low
        
        if bar_range == 0:
            return None
        
        # النتيجة الحقيقية: هل أغلقت الشمعة في اتجاهها؟
        if close > open_p:  # شمعة صاعدة
            close_position = (close - low) / bar_range  # 1 = عند القمة
        else:
            close_position = (high - close) / bar_range  # 1 = عند القاع
        
        # هل الحركة كانت "نتيجة كبيرة"؟
        recent_moves = []
        for j in range(max(0, index-10), index):
            recent_moves.append(abs(all_closes[j] - all_closes[j-1]) if j > 0 else 0)
        
        avg_move = np.mean(recent_moves) if recent_moves else price_move
        
        if avg_move > 0:
            result = price_move / avg_move
        else:
            result = 1.0
        
        # 🟡 تعديل 6: تحليل سياق الشموع الخمس السابقة
        context_type = self._analyze_bar_context(all_highs, all_lows, all_closes, index)
        
        # التفسير الديناميكي
        if effort in ['high_effort', 'above_normal'] and result < 0.6:
            interpretation = "انحراف هبوطي - جهد كبير بلا نتيجة"
            significance = 0.8
        elif effort in ['high_effort', 'above_normal'] and result > 2.0:
            interpretation = "توافق - استمرار قوي"
            significance = 0.7
        elif effort == 'low_effort' and result > 1.5:
            interpretation = "حركة سهلة - قلة مقاومة"
            significance = 0.5
        elif effort == 'low_effort' and result < 0.5:
            interpretation = "لا اهتمام - انتظار"
            significance = 0.2
        elif effort in ['high_effort'] and close_position > 0.85 and close > open_p:
            interpretation = "جهد كبير + إغلاق عند القمة = قوة شرائية"
            significance = 0.75
        elif effort in ['high_effort'] and close_position > 0.85 and close < open_p:
            interpretation = "جهد كبير + إغلاق عند القاع = قوة بيعية"
            significance = 0.75
        elif effort in ['high_effort'] and 0.4 < close_position < 0.6:
            # 🟡 تعديل 6: تفسير الإغلاق الوسط حسب السياق
            if context_type == 'exhaustion':
                interpretation = "جهد كبير + إغلاق وسط + سياق إنهاك = انعكاس محتمل"
                significance = 0.9
            elif context_type == 'normal_range':
                interpretation = "جهد كبير + إغلاق وسط + سياق عرضي = طبيعي"
                significance = 0.4
            else:
                interpretation = "جهد كبير + إغلاق وسط = تردد"
                significance = 0.6
        else:
            interpretation = "طبيعي"
            significance = 0.3
        
        return EffortResult(
            index=index,
            effort_type=effort,
            result_type='big_result' if result > 1.5 else 'small_result' if result < 0.5 else 'normal',
            interpretation=interpretation,
            significance=significance,
            context_type=context_type,
        )
    
    def _analyze_bar_context(self, highs: np.ndarray, lows: np.ndarray, 
                              closes: np.ndarray, index: int) -> str:
        """
        🟡 تعديل 6: تحليل سياق الشمعة بالنظر للشموع الخمس السابقة
        
        إغلاق وسط بعد 10 شموع قوية في اتجاه واحد = إنهاك
        إغلاق وسط بعد 10 شموع عرضية = طبيعي
        """
        if index < 5:
            return 'normal'
        
        # فحص آخر 5 شموع
        prev_closes = closes[index-5:index]
        
        # هل هناك اتجاه واضح؟
        first_to_last = prev_closes[-1] - prev_closes[0]
        total_range = max(highs[index-5:index]) - min(lows[index-5:index])
        
        if total_range == 0:
            return 'normal'
        
        directionality = abs(first_to_last) / total_range
        
        if directionality > 0.7:
            # اتجاه قوي في آخر 5 شموع
            return 'exhaustion'  # احتمال إنهاك
        elif directionality < 0.3:
            return 'normal_range'  # عرضي
        else:
            return 'normal'
    
    def _apply_consecutive_weighting(self, efforts: List[EffortResult]) -> List[EffortResult]:
        """
        🟡 تعديل 11: مضاعفة وزن الإشارات المتتالية من نفس النوع
        
        3 إشارات "انحراف جهد" متتالية أقوى من 3 إشارات متفرقة
        """
        if len(efforts) < 2:
            return efforts
        
        for i in range(1, len(efforts)):
            # فحص هل الإشارة الحالية مشابهة للسابقة
            if efforts[i].interpretation == efforts[i-1].interpretation:
                efforts[i].consecutive_count = efforts[i-1].consecutive_count + 1
                
                # مضاعفة الأهمية حسب التكرار
                if efforts[i].consecutive_count >= 3:
                    efforts[i].significance = min(1.0, efforts[i].significance * 3.0)
                elif efforts[i].consecutive_count >= 2:
                    efforts[i].significance = min(1.0, efforts[i].significance * 2.0)
            else:
                efforts[i].consecutive_count = 0
        
        return efforts
    
    def _detect_effort_divergences(self, efforts: List[EffortResult]) -> List[Dict]:
        """
        اكتشاف تباعدات الجهد عن النتيجة عبر الزمن
        """
        divergences = []
        
        if len(efforts) < 5:
            return divergences
        
        # البحث عن نمط: جهد يتزايد والنتيجة تتناقص (أو العكس)
        for i in range(4, len(efforts)):
            window = efforts[i-4:i+1]
            
            # هل الجهود تتزايد؟
            high_efforts = sum(1 for e in window if e.effort_type in ['high_effort', 'above_normal'])
            
            if high_efforts >= 3:
                # الجهود عالية لكن النتائج؟
                small_results = sum(1 for e in window if e.result_type == 'small_result')
                
                if small_results >= 3:
                    # 🟡 تعديل 11: إذا كانت متتالية، قوة أكبر
                    consecutive = sum(1 for e in window if e.consecutive_count > 0)
                    strength = 0.85 + (consecutive * 0.05)
                    
                    divergences.append({
                        "start_index": window[0].index,
                        "end_index": window[-1].index,
                        "type": "effort_increasing_result_decreasing",
                        "meaning": "انحراف كبير - انعكاس وشيك",
                        "strength": min(0.95, strength),
                        "consecutive_count": consecutive,
                    })
            
            # هل الجهود تتناقص والنتائج تتزايد؟
            low_efforts = sum(1 for e in window if e.effort_type == 'low_effort')
            big_results = sum(1 for e in window if e.result_type == 'big_result')
            
            if low_efforts >= 3 and big_results >= 2:
                divergences.append({
                    "start_index": window[0].index,
                    "end_index": window[-1].index,
                    "type": "effort_decreasing_result_increasing",
                    "meaning": "حركة سهلة - استمرار بدون مقاومة",
                    "strength": 0.6,
                })
        
        return divergences
    
    def _interpret_current_efforts(self, recent: List[EffortResult]) -> Dict:
        """تفسير آخر إشارات الجهد"""
        if not recent:
            return {"signal": "لا إشارات", "bias": "محايد"}
        
        # الإشارة الأقوى في آخر 5
        strongest = max(recent, key=lambda e: e.significance)
        
        # إمالة عامة
        high_effort_count = sum(1 for e in recent if e.effort_type in ['high_effort', 'above_normal'])
        small_result_count = sum(1 for e in recent if e.result_type == 'small_result')
        
        if high_effort_count >= 3 and small_result_count >= 2:
            bias = "انعكاس محتمل - الجهد لا ينتج نتيجة"
        elif high_effort_count >= 2 and small_result_count <= 1:
            bias = "استمرار محتمل - الجهد ينتج نتيجة"
        else:
            bias = "محايد"
        
        # 🟡 تعديل 11: إذا كانت الإشارة متتالية، رفع القوة
        strength = strongest.significance
        if strongest.consecutive_count >= 2:
            strength = min(1.0, strength * 1.5)
        
        return {
            "signal": strongest.interpretation,
            "bias": bias,
            "strength": strength,
            "context_type": strongest.context_type,
        }
    
    def _calculate_effort_balance(self, efforts: List[EffortResult]) -> float:
        """حساب ميزان الجهد (موجب = جهد منتج، سالب = جهد ضائع)"""
        if not efforts:
            return 0.0
        
        balance = 0.0
        for e in efforts:
            if e.effort_type in ['high_effort', 'above_normal'] and e.result_type == 'big_result':
                balance += 1.0
            elif e.effort_type in ['high_effort', 'above_normal'] and e.result_type == 'small_result':
                balance -= 1.5
            elif e.effort_type == 'low_effort' and e.result_type == 'big_result':
                balance += 0.5
        
        return balance / max(len(efforts), 1)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثالثة: الاختبارات الربيعية والدفع العلوي (Springs/Upthrusts)║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SpringUpthrustAnalyzer:
    """
    يكتشف الاختبارات الربيعية (Springs) والدفع العلوي (Upthrusts).
    
    هذه هي أخطر وأهم لحظات وايكوف:
    - Spring: اختراق تحت دعم مع ارتداد عنيف = شراء
    - Upthrust: اختراق فوق مقاومة مع ارتداد عنيف = بيع
    
    ديناميكي: لا نعتمد على نسبة ارتداد ثابتة،
    بل على قوة الارتداد مقارنة بقوة الاختراق.
    
    🟡 تعديل 8: تقييم قوة الدعم من عمره وعدد لمساته
    🟡 تعديل 9: كشف Spring الاختبار (Test Spring)
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, ranges: List[TradingRange]) -> Dict:
        """
        اكتشاف Springs و Upthrusts
        """
        springs = self._detect_springs(highs, lows, closes, volumes, ranges)
        upthrusts = self._detect_upthrusts(highs, lows, closes, volumes, ranges)
        
        # 🟡 تعديل 9: كشف Springs الاختبارية بعد Spring ناجح
        test_springs = self._detect_test_springs(highs, lows, closes, volumes, springs, ranges)
        springs.extend(test_springs)
        
        # أفضل الإشارات الحالية
        recent_spring = springs[-1] if springs else None
        recent_upthrust = upthrusts[-1] if upthrusts else None
        
        return {
            "springs": springs[-10:],
            "upthrusts": upthrusts[-10:],
            "recent_spring": recent_spring,
            "recent_upthrust": recent_upthrust,
            "spring_active": self._is_spring_active(recent_spring, closes[-1]),
            "upthrust_active": self._is_upthrust_active(recent_upthrust, closes[-1]),
        }
    
    def _detect_springs(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                        volumes: np.ndarray, ranges: List[TradingRange]) -> List[SpringUpthrust]:
        """
        اكتشاف الاختبارات الربيعية.
        
        🟡 تعديل 8: تقييم قوة الدعم من عمره وعدد لمساته
        """
        springs = []
        
        if len(lows) < 20:
            return springs
        
        for i in range(10, len(lows) - 3):
            # إيجاد مستوى الدعم (قاع واضح سابق)
            support_level, support_age, support_touches = self._find_nearest_support_with_metadata(
                lows[:i], closes[:i], highs[:i], i
            )
            
            if support_level is None:
                continue
            
            # هل السعر اخترق هذا الدعم؟
            if lows[i] < support_level:
                # الاختراق يجب أن يكون "وهمياً" (يعود السعر بسرعة)
                # 1. الإغلاق يعود فوق الدعم
                if closes[i] > support_level:
                    # 2. قوة الارتداد
                    recovery_strength = self._measure_recovery_strength(
                        closes[i-1] if i > 0 else closes[i], 
                        highs[i], lows[i], closes[i], support_level, 'spring')
                    
                    if recovery_strength > 0.4:
                        # 3. تحليل الحجم
                        vol_ratio = volumes[i] / np.mean(volumes[max(0,i-15):i]) if i >= 5 else 1.0
                        
                        # 🟡 تعديل 8: الجودة تتأثر بعمر الدعم وعدد لمساته
                        base_quality = recovery_strength
                        
                        # دعم قديم (أكثر من 50 شمعة) = أقوى
                        if support_age > 50:
                            base_quality += 0.2
                        elif support_age > 25:
                            base_quality += 0.1
                        
                        # دعم مُختبر (لمس أكثر من 3 مرات) = أقوى
                        if support_touches >= 3:
                            base_quality += 0.15
                        elif support_touches >= 2:
                            base_quality += 0.07
                        
                        # تحديد الجودة
                        if base_quality > 0.7 and vol_ratio > 1.3:
                            quality = 'high'
                        elif base_quality > 0.5:
                            quality = 'medium'
                        else:
                            quality = 'low'
                        
                        springs.append(SpringUpthrust(
                            index=i,
                            event_type='spring',
                            penetration_price=lows[i],
                            recovery_price=closes[i],
                            volume_on_event=volumes[i],
                            relative_volume=vol_ratio,
                            confirmed=quality in ['high', 'medium'],
                            quality=quality,
                            target_zone=(support_level, support_level * 1.02),
                            support_age=support_age,
                            support_touches=support_touches,
                        ))
        
        return springs
    
    def _detect_upthrusts(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                          volumes: np.ndarray, ranges: List[TradingRange]) -> List[SpringUpthrust]:
        """
        اكتشاف الدفع العلوي (Upthrust).
        عكس Spring تماماً.
        """
        upthrusts = []
        
        if len(highs) < 20:
            return upthrusts
        
        for i in range(10, len(highs) - 3):
            resistance_level, resistance_age, resistance_touches = self._find_nearest_resistance_with_metadata(
                highs[:i], closes[:i], lows[:i], i
            )
            
            if resistance_level is None:
                continue
            
            if highs[i] > resistance_level:
                if closes[i] < resistance_level:
                    recovery_strength = self._measure_recovery_strength(
                        closes[i-1] if i > 0 else closes[i],
                        highs[i], lows[i], closes[i], resistance_level, 'upthrust')
                    
                    if recovery_strength > 0.4:
                        vol_ratio = volumes[i] / np.mean(volumes[max(0,i-15):i]) if i >= 5 else 1.0
                        
                        base_quality = recovery_strength
                        
                        if resistance_age > 50:
                            base_quality += 0.2
                        elif resistance_age > 25:
                            base_quality += 0.1
                        
                        if resistance_touches >= 3:
                            base_quality += 0.15
                        elif resistance_touches >= 2:
                            base_quality += 0.07
                        
                        if base_quality > 0.7 and vol_ratio > 1.3:
                            quality = 'high'
                        elif base_quality > 0.5:
                            quality = 'medium'
                        else:
                            quality = 'low'
                        
                        upthrusts.append(SpringUpthrust(
                            index=i,
                            event_type='upthrust',
                            penetration_price=highs[i],
                            recovery_price=closes[i],
                            volume_on_event=volumes[i],
                            relative_volume=vol_ratio,
                            confirmed=quality in ['high', 'medium'],
                            quality=quality,
                            target_zone=(resistance_level * 0.98, resistance_level),
                            support_age=resistance_age,
                            support_touches=resistance_touches,
                        ))
        
        return upthrusts
    
    def _detect_test_springs(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                              volumes: np.ndarray, springs: List[SpringUpthrust],
                              ranges: List[TradingRange]) -> List[SpringUpthrust]:
        """
        🟡 تعديل 9: كشف Spring الاختبار (Test Spring)
        
        بعد Spring ناجح، السعر يعود لمنطقة الـ Spring التي أصبحت دعماً.
        إذا ارتد منها مرة أخرى = تأكيد مزدوج (أقوى إشارات وايكوف)
        """
        test_springs = []
        
        if not springs:
            return test_springs
        
        # آخر Spring ناجح
        last_spring = springs[-1]
        
        # نبحث عن عودة السعر لمنطقة الـ Spring
        spring_zone_low = last_spring.recovery_price * 0.995
        spring_zone_high = last_spring.recovery_price * 1.005
        
        for i in range(last_spring.index + 3, len(lows) - 2):
            # السعر يعود لمنطقة الـ Spring
            if spring_zone_low <= lows[i] <= spring_zone_high:
                # هل ارتد السعر لأعلى؟
                if closes[i] > lows[i] and closes[i] > closes[i-1]:
                    # هذا Test Spring
                    vol_ratio = volumes[i] / np.mean(volumes[max(0,i-15):i]) if i >= 5 else 1.0
                    
                    test_springs.append(SpringUpthrust(
                        index=i,
                        event_type='test_spring',
                        penetration_price=lows[i],
                        recovery_price=closes[i],
                        volume_on_event=volumes[i],
                        relative_volume=vol_ratio,
                        confirmed=True,
                        quality='high',  # Test Spring دائماً عالي الجودة
                        target_zone=(last_spring.target_zone[0], last_spring.target_zone[1] * 1.02),
                        support_age=last_spring.support_age,
                        support_touches=last_spring.support_touches + 1,
                        is_test_spring=True,
                    ))
                    break
        
        return test_springs
    
    def _find_nearest_support_with_metadata(self, lows: np.ndarray, closes: np.ndarray,
                                             highs: np.ndarray, current_idx: int) -> Tuple[Optional[float], int, int]:
        """
        🟡 تعديل 8: إيجاد أقرب دعم مع عمره وعدد لمساته
        """
        if len(lows) < 5:
            return None, 0, 0
        
        # البحث عن قيعان محلية
        valleys = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
                valleys.append((lows[i], i))
        
        if not valleys:
            return None, 0, 0
        
        # الدعم هو متوسط القيعان القريبة
        recent_valleys = valleys[-5:] if len(valleys) >= 5 else valleys
        support_levels = [v[0] for v in recent_valleys]
        support = np.median(support_levels)
        
        # تعديل: الدعم يكون تحت السعر الحالي
        current = closes[-1] if len(closes) > 0 else support
        if support > current:
            support = min(support_levels)
        
        # 🟡 تعديل 8: حساب عمر الدعم (آخر مرة لُمس فيها)
        last_touch_idx = 0
        for v in reversed(valleys):
            if abs(v[0] - support) / support < 0.02:
                last_touch_idx = v[1]
                break
        
        support_age = current_idx - last_touch_idx if last_touch_idx > 0 else current_idx
        
        # 🟡 تعديل 8: حساب عدد اللمسات
        touches = 0
        for v in valleys:
            if abs(v[0] - support) / support < 0.02:
                touches += 1
        
        return support, support_age, touches
    
    def _find_nearest_resistance_with_metadata(self, highs: np.ndarray, closes: np.ndarray,
                                                lows: np.ndarray, current_idx: int) -> Tuple[Optional[float], int, int]:
        """
        🟡 تعديل 8: إيجاد أقرب مقاومة مع عمرها وعدد لمساتها
        """
        if len(highs) < 5:
            return None, 0, 0
        
        peaks = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
                peaks.append((highs[i], i))
        
        if not peaks:
            return None, 0, 0
        
        recent_peaks = peaks[-5:] if len(peaks) >= 5 else peaks
        resistance_levels = [p[0] for p in recent_peaks]
        resistance = np.median(resistance_levels)
        
        current = closes[-1] if len(closes) > 0 else resistance
        if resistance < current:
            resistance = max(resistance_levels)
        
        last_touch_idx = 0
        for p in reversed(peaks):
            if abs(p[0] - resistance) / resistance < 0.02:
                last_touch_idx = p[1]
                break
        
        resistance_age = current_idx - last_touch_idx if last_touch_idx > 0 else current_idx
        
        touches = 0
        for p in peaks:
            if abs(p[0] - resistance) / resistance < 0.02:
                touches += 1
        
        return resistance, resistance_age, touches
    
    def _find_nearest_support(self, lows: np.ndarray, closes: np.ndarray, current_idx: int) -> Optional[float]:
        """إيجاد أقرب مستوى دعم ديناميكي (للتوافق مع الإصدار السابق)"""
        support, _, _ = self._find_nearest_support_with_metadata(lows, closes, np.array([]), current_idx)
        return support
    
    def _find_nearest_resistance(self, highs: np.ndarray, closes: np.ndarray, current_idx: int) -> Optional[float]:
        """إيجاد أقرب مستوى مقاومة ديناميكي (للتوافق مع الإصدار السابق)"""
        resistance, _, _ = self._find_nearest_resistance_with_metadata(highs, closes, np.array([]), current_idx)
        return resistance
    
    def _measure_recovery_strength(self, open_p: float, high: float, low: float,
                                    close: float, level: float, event_type: str) -> float:
        """
        قياس قوة الارتداد بعد الاختراق.
        ديناميكي بالكامل: يقارن قوة الاختراق بقوة الارتداد.
        """
        bar_range = high - low
        if bar_range == 0:
            return 0.0
        
        if event_type == 'spring':
            penetration = level - low
            recovery = close - level
            
            if penetration <= 0:
                return 0.0
            
            recovery_ratio = recovery / penetration
            close_position = (close - low) / bar_range
            
            strength = (min(recovery_ratio / 3, 1.0) * 0.5 + close_position * 0.5)
            
        else:  # upthrust
            penetration = high - level
            recovery = level - close
            
            if penetration <= 0:
                return 0.0
            
            recovery_ratio = recovery / penetration
            close_position = (high - close) / bar_range
            
            strength = (min(recovery_ratio / 3, 1.0) * 0.5 + close_position * 0.5)
        
        return min(1.0, max(0.0, strength))
    
    def _is_spring_active(self, spring: Optional[SpringUpthrust], current_price: float) -> Dict:
        """هل Spring ما زال نشطاً (يمكن التداول عليه)"""
        if not spring:
            return {"active": False}
        
        target_hit = current_price >= spring.target_zone[1] if spring.target_zone else False
        
        return {
            "active": not target_hit,
            "entry": spring.recovery_price,
            "stop": spring.penetration_price,
            "target": spring.target_zone[1] if spring.target_zone else None,
            "is_test_spring": spring.is_test_spring,
        }
    
    def _is_upthrust_active(self, upthrust: Optional[SpringUpthrust], current_price: float) -> Dict:
        """هل Upthrust ما زال نشطاً"""
        if not upthrust:
            return {"active": False}
        
        target_hit = current_price <= upthrust.target_zone[0] if upthrust.target_zone else False
        
        return {
            "active": not target_hit,
            "entry": upthrust.recovery_price,
            "stop": upthrust.penetration_price,
            "target": upthrust.target_zone[0] if upthrust.target_zone else None,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الرابعة: محلل السبب والنتيجة (Cause & Effect)               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CauseEffectAnalyzer:
    """
    يحلل علاقة السبب (النطاق) بالنتيجة (الاتجاه).
    
    مبدأ وايكوف: كل حركة تحتاج سبباً يسبقها.
    حجم السبب (النطاق) يتناسب مع حجم النتيجة (الاتجاه).
    
    ديناميكي: العلاقة تحدد من السوق نفسه، لا من نسبة ثابتة.
    
    🔴 تعديل 5: دمج التقلب الحالي مع المتوسط التاريخي للمضاعف
    🟡 تعديل 7: تمييز القاع التاريخي عن القاع القريب في جودة السبب
    🟢 تعديل 14: تحليل موقع النطاق في الدورة الكبرى
    🟢 تعديل 15: تناظر النطاقات (صورة مرآة للدورة السابقة)
    """
    
    def analyze(self, ranges: List[TradingRange], highs: np.ndarray, 
                lows: np.ndarray, closes: np.ndarray) -> Dict:
        """
        تحليل السبب والنتيجة
        """
        # قياس السبب الحالي
        current_cause = self._measure_current_cause(ranges)
        
        # 🟢 تعديل 14: تحليل موقع النطاق في الدورة الكبرى
        cycle_position = self._analyze_cycle_position(ranges, highs, lows, closes)
        current_cause['cycle_position'] = cycle_position
        
        # 🟢 تعديل 15: تحليل تناظر النطاقات
        symmetry = self._analyze_range_symmetry(ranges)
        current_cause['symmetry'] = symmetry
        
        # تقدير النتيجة المتوقعة
        expected_effect = self._estimate_effect(current_cause, highs, lows, closes)
        
        # مقارنة النتيجة الفعلية بالمتوقعة
        actual_vs_expected = self._compare_actual_vs_expected(current_cause, 
                                                                expected_effect, closes)
        
        return {
            "current_cause": current_cause,
            "expected_effect": expected_effect,
            "actual_vs_expected": actual_vs_expected,
            "cause_quality": self._assess_cause_quality(current_cause),
        }
    
    def _measure_current_cause(self, ranges: List[TradingRange]) -> Dict:
        """
        قياس السبب الحالي (النطاق الذي يسبق الحركة)
        """
        if not ranges:
            return {"exists": False, "size": 0}
        
        last_range = ranges[-1]
        
        # حجم السبب = مدة النطاق × اتساعه × حجم التداول فيه
        range_size = last_range.high - last_range.low
        duration = last_range.duration
        
        # نقيس الحجم النسبي
        cause_magnitude = range_size * np.log1p(duration)
        
        return {
            "exists": True,
            "range_high": last_range.high,
            "range_low": last_range.low,
            "range_mid": last_range.mid,
            "size": range_size,
            "duration": duration,
            "magnitude": cause_magnitude,
            "type": last_range.range_type,
            "volume_trend": last_range.volume_trend,
            "range_magnitude": last_range.range_magnitude,
            "breakout_quality": last_range.breakout_quality,
            "support_resistance_age": last_range.support_resistance_age,
            "range_size_percentile": last_range.range_size_percentile,
        }
    
    def _estimate_effect(self, cause: Dict, highs: np.ndarray, lows: np.ndarray,
                         closes: np.ndarray) -> Dict:
        """
        تقدير النتيجة المتوقعة من السبب.
        
        🔴 تعديل 5: دمج التقلب الحالي مع المتوسط التاريخي للمضاعف
        """
        if not cause.get('exists'):
            return {"direction": "none", "magnitude": 0}
        
        # 🔴 تعديل 5: حساب مضاعف ديناميكي يدمج التاريخي مع التقلب الحالي
        historical_multiplier = self._calculate_dynamic_multiplier(highs, lows, closes)
        recent_volatility = self._calculate_recent_volatility(highs, lows, closes)
        
        # مزج المضاعف التاريخي مع التقلب الحالي
        # في سوق هادئ: المضاعف أقل. في سوق متقلب: المضاعف أعلى
        avg_volatility = self._calculate_average_volatility(highs, lows, closes)
        
        if avg_volatility > 0:
            volatility_ratio = recent_volatility / avg_volatility
        else:
            volatility_ratio = 1.0
        
        # التقلب الأعلى من المتوسط = مضاعف أكبر
        # التقلب الأقل من المتوسط = مضاعف أصغر
        adjusted_multiplier = historical_multiplier * (0.7 + 0.3 * volatility_ratio)
        
        expected_magnitude = cause['magnitude'] * adjusted_multiplier
        
        if cause['type'] == 'accumulation':
            direction = 'up'
            target = cause['range_high'] + expected_magnitude
        elif cause['type'] == 'distribution':
            direction = 'down'
            target = cause['range_low'] - expected_magnitude
        else:
            direction = 'unknown'
            target = None
        
        return {
            "direction": direction,
            "magnitude": expected_magnitude,
            "target": target,
            "multiplier_used": adjusted_multiplier,
            "historical_multiplier": historical_multiplier,
            "volatility_ratio": volatility_ratio,
        }
    
    def _calculate_dynamic_multiplier(self, highs: np.ndarray, lows: np.ndarray,
                                       closes: np.ndarray) -> float:
        """
        حساب المضاعف الديناميكي من تاريخ السوق.
        كم مرة تحرك السعر مقارنة بحجم النطاق السابق؟
        """
        if len(closes) < 50:
            return 1.5  # افتراضي معقول
        
        multipliers = []
        third = len(closes) // 3
        
        for i in range(2):
            start = i * third
            mid = start + third // 2
            end = (i + 1) * third
            
            if end > len(closes):
                break
            
            pre_range = max(highs[start:mid]) - min(lows[start:mid])
            post_move = max(highs[mid:end]) - min(lows[mid:end])
            
            if pre_range > 0:
                multipliers.append(post_move / pre_range)
        
        if multipliers:
            return np.median(multipliers)
        
        return 1.5
    
    def _calculate_recent_volatility(self, highs: np.ndarray, lows: np.ndarray, 
                                      closes: np.ndarray, period: int = 20) -> float:
        """
        🔴 تعديل 5: حساب التقلب الحالي
        """
        if len(closes) < period:
            period = len(closes)
        
        tr = np.zeros(period)
        for i in range(1, period):
            idx = len(closes) - period + i
            tr[i] = max(
                highs[idx] - lows[idx],
                abs(highs[idx] - closes[idx-1]),
                abs(lows[idx] - closes[idx-1])
            )
        
        return np.mean(tr) if len(tr) > 0 else 0
    
    def _calculate_average_volatility(self, highs: np.ndarray, lows: np.ndarray,
                                       closes: np.ndarray, period: int = 100) -> float:
        """
        🔴 تعديل 5: حساب متوسط التقلب طويل المدى
        """
        if len(closes) < period:
            period = len(closes)
        
        tr = np.zeros(period)
        for i in range(1, period):
            idx = len(closes) - period + i
            tr[i] = max(
                highs[idx] - lows[idx],
                abs(highs[idx] - closes[idx-1]),
                abs(lows[idx] - closes[idx-1])
            )
        
        return np.mean(tr) if len(tr) > 0 else 0
    
    def _compare_actual_vs_expected(self, cause: Dict, expected: Dict,
                                     closes: np.ndarray) -> Dict:
        """مقارنة النتيجة الفعلية بالمتوقعة"""
        if not cause.get('exists') or expected.get('direction') == 'none':
            return {"status": "no_cause"}
        
        current = closes[-1]
        
        if expected['direction'] == 'up':
            achieved = max(0, current - cause['range_high']) / max(expected['magnitude'], 0.0001)
        else:
            achieved = max(0, cause['range_low'] - current) / max(expected['magnitude'], 0.0001)
        
        achieved = min(1.0, achieved)
        
        if achieved < 0.2:
            status = "الحركة في بدايتها"
        elif achieved < 0.6:
            status = "في منتصف الحركة"
        elif achieved < 0.9:
            status = "الحركة تقترب من هدفها"
        else:
            status = "الهدف تحقق - انتظار سبب جديد"
        
        return {
            "status": status,
            "achieved_ratio": achieved,
            "remaining_potential": 1 - achieved,
        }
    
    def _assess_cause_quality(self, cause: Dict) -> Dict:
        """
        تقييم جودة السبب
        
        🟡 تعديل 7: تمييز القاع التاريخي عن القاع القريب
        🟢 تعديل 14: موقع النطاق في الدورة الكبرى
        🟢 تعديل 15: تناظر النطاقات
        """
        if not cause.get('exists'):
            return {"quality": "no_cause", "score": 0}
        
        score = 0.5
        
        # المدة (كلما كانت أطول = أفضل)
        if cause['duration'] > 30:
            score += 0.2
        elif cause['duration'] > 15:
            score += 0.1
        
        # اتجاه الحجم (جفاف = أفضل للتجميع، توسع = أفضل للتوزيع)
        if cause['type'] == 'accumulation' and cause['volume_trend'] == 'drying_up':
            score += 0.15
        elif cause['type'] == 'distribution' and cause['volume_trend'] == 'expanding':
            score += 0.15
        
        # وضوح الحدود
        if cause['size'] > 0 and cause['range_high'] / cause['range_low'] > 1.02:
            score += 0.1
        
        # 🟡 تعديل 7: عمر الدعم/المقاومة
        if cause.get('support_resistance_age', 0) > 100:
            score += 0.15  # قاع/قمة تاريخي
        elif cause.get('support_resistance_age', 0) > 50:
            score += 0.1
        
        # 🟡 تعديل 10: حجم النطاق مقارنة بالسابق
        if cause.get('range_size_percentile', 0.5) > 0.7:
            score += 0.1  # نطاق كبير نسبياً
        elif cause.get('range_size_percentile', 0.5) < 0.3:
            score -= 0.1  # نطاق صغير = مشبوه
        
        # 🟡 تعديل 12: جودة شمعة الخروج
        if cause.get('breakout_quality', 0) > 0.7:
            score += 0.1
        elif cause.get('breakout_quality', 0) < 0.3:
            score -= 0.05
        
        # 🟢 تعديل 14: موقع النطاق في الدورة الكبرى
        cycle_pos = cause.get('cycle_position', {})
        if cycle_pos.get('is_major_bottom') and cause['type'] == 'accumulation':
            score += 0.15  # قاع تاريخي = تجميع قوي
        elif cycle_pos.get('is_major_top') and cause['type'] == 'distribution':
            score += 0.15  # قمة تاريخية = توزيع قوي
        
        # 🟢 تعديل 15: تناظر النطاقات
        symmetry = cause.get('symmetry', {})
        if symmetry.get('is_mirror', False):
            score += 0.12  # تناظر مع نطاق سابق = دورة مكتملة
        
        score = min(1.0, max(0.1, score))
        
        if score > 0.7:
            quality = "ممتاز"
        elif score > 0.5:
            quality = "جيد"
        elif score > 0.3:
            quality = "مقبول"
        else:
            quality = "ضعيف"
        
        return {"quality": quality, "score": score}
    
    def _analyze_cycle_position(self, ranges: List[TradingRange], highs: np.ndarray,
                                 lows: np.ndarray, closes: np.ndarray) -> Dict:
        """
        🟢 تعديل 14: تحليل موقع النطاق في الدورة الكبرى
        
        التجميع الحقيقي يحدث بعد هبوط. التجميع في منتصف الصعود = استراحة وليس انعكاساً
        """
        if not ranges:
            return {"position": "unknown"}
        
        if len(closes) < 100:
            return {"position": "unknown", "is_major_bottom": False, "is_major_top": False}
        
        last_range = ranges[-1]
        range_mid = last_range.mid
        
        # أعلى وأدنى سعر في آخر 100-200 شمعة
        lookback = min(200, len(closes))
        all_time_high = max(highs[-lookback:])
        all_time_low = min(lows[-lookback:])
        
        if all_time_high == all_time_low:
            return {"position": "unknown"}
        
        # موقع النطاق بالنسبة للمدى الكامل
        position_in_range = (range_mid - all_time_low) / (all_time_high - all_time_low)
        
        # هل هو قاع رئيسي؟ (في أدنى 20% من المدى طويل الأجل)
        is_major_bottom = position_in_range < 0.2
        
        # هل هو قمة رئيسية؟ (في أعلى 20% من المدى طويل الأجل)
        is_major_top = position_in_range > 0.8
        
        # هل سبقه هبوط؟ (للتجميع الحقيقي)
        if last_range.range_type == 'accumulation':
            pre_range_data = closes[max(0, last_range.start_idx-50):last_range.start_idx]
            if len(pre_range_data) > 10:
                was_downtrend = pre_range_data[-1] < pre_range_data[0] * 0.95
            else:
                was_downtrend = False
        else:
            was_downtrend = False
        
        # هل سبقه صعود؟ (للتوزيع الحقيقي)
        if last_range.range_type == 'distribution':
            pre_range_data = closes[max(0, last_range.start_idx-50):last_range.start_idx]
            if len(pre_range_data) > 10:
                was_uptrend = pre_range_data[-1] > pre_range_data[0] * 1.05
            else:
                was_uptrend = False
        else:
            was_uptrend = False
        
        return {
            "position": "bottom" if is_major_bottom else "top" if is_major_top else "middle",
            "position_percentile": position_in_range,
            "is_major_bottom": is_major_bottom,
            "is_major_top": is_major_top,
            "was_preceded_by_downtrend": was_downtrend,
            "was_preceded_by_uptrend": was_uptrend,
        }
    
    def _analyze_range_symmetry(self, ranges: List[TradingRange]) -> Dict:
        """
        🟢 تعديل 15: تحليل تناظر النطاقات (صورة مرآة للدورة السابقة)
        
        نطاق التوزيع غالباً ما يكون "صورة مرآة" لنطاق التجميع السابق له
        """
        if len(ranges) < 2:
            return {"is_mirror": False, "symmetry_score": 0}
        
        last_range = ranges[-1]
        prev_range = ranges[-2]
        
        # نقارن خصائص النطاقين
        symmetry_score = 0
        
        # تشابه الحجم
        if last_range.range_magnitude > 0 and prev_range.range_magnitude > 0:
            size_ratio = min(last_range.range_magnitude, prev_range.range_magnitude) / \
                        max(last_range.range_magnitude, prev_range.range_magnitude)
            if size_ratio > 0.7:
                symmetry_score += 0.3
            elif size_ratio > 0.5:
                symmetry_score += 0.15
        
        # تشابه المدة
        if last_range.duration > 0 and prev_range.duration > 0:
            duration_ratio = min(last_range.duration, prev_range.duration) / \
                           max(last_range.duration, prev_range.duration)
            if duration_ratio > 0.7:
                symmetry_score += 0.25
            elif duration_ratio > 0.5:
                symmetry_score += 0.12
        
        # عكس النوع (تجميع ثم توزيع أو العكس)
        if (last_range.range_type == 'distribution' and prev_range.range_type == 'accumulation') or \
           (last_range.range_type == 'accumulation' and prev_range.range_type == 'distribution'):
            symmetry_score += 0.25
        
        # تشابه نمط الحجم (كلاهما جفاف أو كلاهما توسع)
        if last_range.volume_trend == prev_range.volume_trend:
            symmetry_score += 0.1
        
        # تشابه في الموقع النسبي
        if last_range.range_size_percentile > 0 and prev_range.range_size_percentile > 0:
            percentile_diff = abs(last_range.range_size_percentile - prev_range.range_size_percentile)
            if percentile_diff < 0.2:
                symmetry_score += 0.1
        
        is_mirror = symmetry_score > 0.5
        
        return {
            "is_mirror": is_mirror,
            "symmetry_score": symmetry_score,
            "mirrored_range_type": prev_range.range_type if is_mirror else None,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية وايكوف الموحدة                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class WyckoffStrategy:
    """
    الاستراتيجية الكاملة لمنهجية وايكوف الديناميكية (الإصدار 2.0)
    
    تجمع:
    - تحليل المراحل
    - الجهد مقابل النتيجة
    - Springs / Upthrusts
    - السبب والنتيجة
    
    في قرار تداولي واحد.
    
    الإضافات الجديدة:
    🔴 5 أخطاء تداولية تم إصلاحها
    🟡 7 تحسينات ذكاء تداولي
    🟢 3 فرص قوية غير مستغلة تم تفعيلها
    """
    
    def __init__(self):
        self.phase_analyzer = DynamicPhaseAnalyzer()
        self.effort_analyzer = EffortResultAnalyzer()
        self.spring_analyzer = SpringUpthrustAnalyzer()
        self.cause_effect_analyzer = CauseEffectAnalyzer()
    
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
                    "reason": "تحتاج 30 شمعة على الأقل لتحليل وايكوف"}
        
        # 1. المراحل
        phase_data = self.phase_analyzer.analyze(highs, lows, closes, volumes, opens)
        
        # 2. الجهد مقابل النتيجة
        effort_data = self.effort_analyzer.analyze(highs, lows, closes, volumes, opens)
        
        # 3. Springs & Upthrusts
        ranges = phase_data.get('ranges', [])
        spring_data = self.spring_analyzer.analyze(highs, lows, closes, volumes, ranges)
        
        # 4. السبب والنتيجة
        cause_data = self.cause_effect_analyzer.analyze(ranges, highs, lows, closes)
        
        # 5. القرار
        decision = self._make_decision(phase_data, effort_data, spring_data, cause_data, ranges)
        
        return {
            **decision,
            "phase_data": phase_data,
            "effort_data": effort_data,
            "spring_data": spring_data,
            "cause_data": cause_data,
        }
    
    def _make_decision(self, phase_data: Dict, effort_data: Dict,
                       spring_data: Dict, cause_data: Dict,
                       ranges: List[TradingRange]) -> Dict:
        """
        تجميع كل إشارات وايكوف في قرار واحد
        
        🔴 تعديل 4: Spring/Upthrust الضعيف يُقوى في Phase C
        🟢 تعديل 13: تآزر Spring مع انحراف الجهد = تأكيد مزدوج
        """
        buy_signals = []
        sell_signals = []
        
        current_phase = phase_data.get('current_phase')
        
        # ---- من المرحلة ----
        if current_phase in [WyckoffPhase.ACCUMULATION_PHASE_D,
                              WyckoffPhase.ACCUMULATION_PHASE_E]:
            buy_signals.append(("تجميع متقدم - جاهز للصعود", 0.8))
        elif current_phase == WyckoffPhase.ACCUMULATION_PHASE_C:
            buy_signals.append(("Spring Phase - فرصة شراء", 0.7))
        elif current_phase == WyckoffPhase.ACCUMULATION_PHASE_B:
            buy_signals.append(("بناء سبب صاعد", 0.4))
        elif current_phase in [WyckoffPhase.DISTRIBUTION_PHASE_D,
                                WyckoffPhase.DISTRIBUTION_PHASE_E]:
            sell_signals.append(("توزيع متقدم - جاهز للهبوط", 0.8))
        elif current_phase == WyckoffPhase.DISTRIBUTION_PHASE_C:
            sell_signals.append(("Upthrust Phase - فرصة بيع", 0.7))
        elif current_phase == WyckoffPhase.DISTRIBUTION_PHASE_B:
            sell_signals.append(("بناء سبب هابط", 0.4))
        elif current_phase == WyckoffPhase.MARKUP:
            buy_signals.append(("في موجة صاعدة", 0.6))
        elif current_phase == WyckoffPhase.MARKDOWN:
            sell_signals.append(("في موجة هابطة", 0.6))
        
        # ---- من الجهد مقابل النتيجة ----
        effort_balance = effort_data.get('effort_balance', 0)
        if effort_balance > 1.5:
            buy_signals.append(("جهد منتج للصعود", 0.5))
        elif effort_balance < -1.5:
            sell_signals.append(("جهد ضائع - هبوط محتمل", 0.5))
        
        current_signal = effort_data.get('current_signal', {})
        if current_signal.get('bias') == 'انعكاس محتمل - الجهد لا ينتج نتيجة':
            if current_phase in [WyckoffPhase.MARKUP]:
                sell_signals.append(("انحراف جهد في موجة صاعدة", 0.7))
            elif current_phase in [WyckoffPhase.MARKDOWN]:
                buy_signals.append(("انحراف جهد في موجة هابطة", 0.7))
        
        # ---- من Springs / Upthrusts ----
        recent_spring = spring_data.get('recent_spring')
        if recent_spring:
            # 🔴 تعديل 4: Spring الضعيف يُقوى في Phase C، ويُضعف في الاتجاه
            adjusted_quality = self._adjust_spring_quality_for_phase(
                recent_spring, current_phase
            )
            
            if adjusted_quality in ['high', 'medium']:
                weight = 0.8 if adjusted_quality == 'high' else 0.6
                buy_signals.append((f"Spring {adjusted_quality} (معدل حسب المرحلة)", weight))
                
                # 🟢 تعديل 13: تآزر Spring مع انحراف الجهد
                if self._check_spring_effort_synergy(recent_spring, effort_data, 'spring'):
                    buy_signals.append(("تآزر Spring + انحراف جهد (تأكيد مزدوج)", 0.9))
        
        recent_upthrust = spring_data.get('recent_upthrust')
        if recent_upthrust:
            adjusted_quality = self._adjust_spring_quality_for_phase(
                recent_upthrust, current_phase
            )
            
            if adjusted_quality in ['high', 'medium']:
                weight = 0.8 if adjusted_quality == 'high' else 0.6
                sell_signals.append((f"Upthrust {adjusted_quality} (معدل حسب المرحلة)", weight))
                
                # 🟢 تعديل 13: تآزر Upthrust مع انحراف الجهد
                if self._check_spring_effort_synergy(recent_upthrust, effort_data, 'upthrust'):
                    sell_signals.append(("تآزر Upthrust + انحراف جهد (تأكيد مزدوج)", 0.9))
        
        # ---- من السبب والنتيجة ----
        cause_quality = cause_data.get('cause_quality', {})
        actual_vs = cause_data.get('actual_vs_expected', {})
        expected = cause_data.get('expected_effect', {})
        
        if cause_quality.get('quality') in ['ممتاز', 'جيد']:
            if expected.get('direction') == 'up':
                buy_signals.append(("سبب صاعد قوي", 0.5))
            elif expected.get('direction') == 'down':
                sell_signals.append(("سبب هابط قوي", 0.5))
        
        if actual_vs.get('status') == "الحركة في بدايتها":
            if expected.get('direction') == 'up':
                buy_signals.append(("بداية حركة - فرصة دخول", 0.6))
            elif expected.get('direction') == 'down':
                sell_signals.append(("بداية حركة - فرصة دخول", 0.6))
        
        # 🟢 تعديل 14: إشارات موقع الدورة الكبرى
        cycle_pos = cause_data.get('current_cause', {}).get('cycle_position', {})
        if cycle_pos.get('is_major_bottom') and current_phase in [WyckoffPhase.ACCUMULATION_PHASE_B,
                                                                    WyckoffPhase.ACCUMULATION_PHASE_C]:
            buy_signals.append(("قاع تاريخي + تجميع = فرصة كبرى", 0.85))
        if cycle_pos.get('is_major_top') and current_phase in [WyckoffPhase.DISTRIBUTION_PHASE_B,
                                                                 WyckoffPhase.DISTRIBUTION_PHASE_C]:
            sell_signals.append(("قمة تاريخية + توزيع = فرصة كبرى", 0.85))
        
        # 🟢 تعديل 15: إشارات تناظر النطاقات
        symmetry = cause_data.get('current_cause', {}).get('symmetry', {})
        if symmetry.get('is_mirror', False):
            if ranges and ranges[-1].range_type == 'distribution':
                sell_signals.append(("تناظر مع نطاق تجميع سابق - دورة مكتملة", 0.7))
            elif ranges and ranges[-1].range_type == 'accumulation':
                buy_signals.append(("تناظر مع نطاق توزيع سابق - دورة مكتملة", 0.7))
        
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
            confidence = 40 + int(total_buy - total_sell) * 15
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 40 + int(total_sell - total_buy) * 15
        else:
            recommendation = "محايد"
            confidence = 25
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        
        # تحذيرات
        warnings = []
        if effort_data.get('divergences'):
            warnings.append("انحراف جهد عن النتيجة")
        if spring_data.get('spring_active', {}).get('active') and recommendation == "بيع":
            warnings.append("Spring نشط - تحذير من البيع")
        if spring_data.get('upthrust_active', {}).get('active') and recommendation == "شراء":
            warnings.append("Upthrust نشط - تحذير من الشراء")
        if spring_data.get('spring_active', {}).get('is_test_spring'):
            warnings.append("Test Spring نشط - تأكيد مضاعف")
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings)
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "phase": str(current_phase) if current_phase else "غير محدد",
        }
    
    def _adjust_spring_quality_for_phase(self, event: SpringUpthrust, 
                                          current_phase: WyckoffPhase) -> str:
        """
        🔴 تعديل 4: تعديل جودة Spring/Upthrust حسب المرحلة الحالية
        
        في Phase C من التجميع، حتى Spring ضعيف يعتبر تأكيداً قوياً
        في اتجاه قوي، نفس الـ Spring ينخفض تقييمه
        """
        base_quality = event.quality
        
        # في Phase C: رفع الجودة
        if event.event_type == 'spring' and current_phase == WyckoffPhase.ACCUMULATION_PHASE_C:
            if base_quality == 'low':
                return 'medium'
            elif base_quality == 'medium':
                return 'high'
        
        if event.event_type == 'upthrust' and current_phase == WyckoffPhase.DISTRIBUTION_PHASE_C:
            if base_quality == 'low':
                return 'medium'
            elif base_quality == 'medium':
                return 'high'
        
        # في اتجاه قوي: خفض الجودة (Spring في موجة صاعدة = مشبوه)
        if event.event_type == 'spring' and current_phase == WyckoffPhase.MARKUP:
            if base_quality == 'high':
                return 'medium'
            elif base_quality == 'medium':
                return 'low'
        
        if event.event_type == 'upthrust' and current_phase == WyckoffPhase.MARKDOWN:
            if base_quality == 'high':
                return 'medium'
            elif base_quality == 'medium':
                return 'low'
        
        # Test Spring دائماً عالي
        if event.is_test_spring:
            return 'high'
        
        return base_quality
    
    def _check_spring_effort_synergy(self, event: SpringUpthrust, 
                                      effort_data: Dict, event_type: str) -> bool:
        """
        🟢 تعديل 13: كشف تآزر Spring مع انحراف الجهد
        
        Spring + انحراف جهد (حجم عالي + نتيجة صغيرة) = تأكيد مزدوج نادر
        """
        recent_efforts = effort_data.get('recent_efforts', [])
        
        if not recent_efforts:
            return False
        
        # فحص آخر 3 إشارات جهد
        for effort in recent_efforts[-3:]:
            if effort.interpretation in ["انحراف هبوطي - جهد كبير بلا نتيجة",
                                          "جهد كبير + إغلاق وسط = تردد"]:
                if event_type == 'spring' and effort.significance > 0.7:
                    return True
                if event_type == 'upthrust' and effort.significance > 0.7:
                    return True
        
        # فحص التباعدات
        divergences = effort_data.get('divergences', [])
        for div in divergences[-2:]:
            if div.get('type') == 'effort_increasing_result_decreasing' and div.get('strength', 0) > 0.7:
                return True
        
        return False


def create_wyckoff_strategy():
    """إنشاء استراتيجية وايكوف الجاهزة (الإصدار 2.0 المعدل)"""
    return WyckoffStrategy()