"""
═══════════════════════════════════════════════════════════════════════════════
ELLIOTT WAVE THEORY - النسخة الديناميكية المتكاملة
المدرسة الرابعة: نظرية موجات إليوت - علم النفس الجماعي
═══════════════════════════════════════════════════════════════════════════════

رالف نيلسون إليوت (1871-1948) اكتشف أن الأسواق تتحرك في موجات متكررة
تعكس سيكولوجية الجماهير: التفاؤل ← النشوة ← القلق ← الإنكار ← الذعر.

هذه النسخة ديناميكية بالكامل:
- لا نعتمد على نسب فيبوناتشي ثابتة (61.8%, 38.2%...)
- النسب تُستنتج من السوق نفسه في كل موجة
- كل سوق له "شخصيته الموجية" الخاصة
- الموجات تُكتشف من سلوك السعر والزخم والزمن
- درجة الموجة (Degree) تحدد بشكل نسبي وليس مطلق

الفلسفة:
السوق يتحرك في 5 موجات مع الاتجاه + 3 موجات تصحيحية.
لكن ليست كل 5 موجات متشابهة. كل موجة تحمل بصمتها الخاصة.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class WaveDegree(Enum):
    """درجة الموجة (نسبي وليس مطلق)"""
    GRAND_SUPERCYCLE = "دورة عظمى كبرى"
    SUPERCYCLE = "دورة عظمى"
    CYCLE = "دورة"
    PRIMARY = "رئيسية"
    INTERMEDIATE = "متوسطة"
    MINOR = "صغرى"
    MINUTE = "دقيقة"
    MINUETTE = "صغيرة جداً"
    SUBMINUETTE = "تحت الصغيرة"


class WaveType(Enum):
    """نوع الموجة"""
    IMPULSE = "دافعة"
    DIAGONAL_LEADING = "قطرية قائدة"
    DIAGONAL_ENDING = "قطرية ختامية"
    ZIGZAG = "زيجزاج"
    FLAT = "فلات"
    TRIANGLE = "مثلث"
    COMBINATION = "مركبة"
    UNKNOWN = "غير معروفة"


@dataclass
class WavePoint:
    """نقطة تحول موجية"""
    index: int
    price: float
    point_type: str  # 'start', 'peak_1', 'trough_2', 'peak_3', 'trough_4', 'peak_5', 'A', 'B', 'C'
    degree: WaveDegree
    confidence: float  # 0-1


@dataclass
class ElliottWave:
    """موجة إليوت كاملة"""
    start_idx: int
    end_idx: int
    wave_number: int  # 1, 2, 3, 4, 5, A, B, C
    wave_type: WaveType
    degree: WaveDegree
    price_start: float
    price_end: float
    price_change: float
    duration: int  # عدد الشموع
    sub_waves: List[int]  # قائمة الموجات الفرعية
    strength: float  # 0-1 قوة الموجة
    personality: str  # وصف شخصية الموجة


@dataclass
class WaveSequence:
    """تسلسل موجي كامل (5 موجات دافعة أو 3 تصحيحية)"""
    waves: List[ElliottWave]
    sequence_type: str  # 'impulse', 'corrective'
    degree: WaveDegree
    start_idx: int
    end_idx: int
    complete: bool
    extended_wave: Optional[int]  # أي موجة امتدت؟
    truncation_detected: bool  # هل هناك بتر؟
    channel_lines: Tuple[float, float, float, float]  # خطوط القناة


@dataclass
class FibonacciCluster:
    """مجموعة نسب ديناميكية (وليست ثابتة)"""
    price_level: float
    ratios_present: List[float]  # النسب الموجودة عند هذا المستوى
    cluster_strength: float  # 0-1 قوة التجمع
    wave_relations: List[str]  # أي موجات تكون هذه النسبة


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: محلل الموجات الديناميكي (Dynamic Wave Detector)      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicWaveDetector:
    """
    يكتشف الموجات بطريقة ديناميكية من سلوك السعر والزخم.
    لا يعتمد على نسب فيبوناتشي ثابتة، بل يقرأ "قصة" الموجة.
    
    المبادئ الديناميكية:
    1. الموجة 3 ليست دائماً 161.8% من الموجة 1، بل هي "أقوى موجة"
    2. الموجة 4 لا تتداخل مع الموجة 1 لأنهما من درجتين مختلفتين
    3. شخصية كل موقة تحددها سرعتها وعلاقتها بأخواتها
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """
        اكتشاف الموجات الكامل
        """
        # استخراج نقاط التحول
        pivot_points = self._extract_pivot_points(highs, lows, closes, volumes)
        
        # بناء الموجات من نقاط التحول
        waves = self._build_waves(pivot_points, highs, lows, closes, volumes)
        
        # تجميع الموجات في تسلسلات
        sequences = self._build_sequences(waves)
        
        # الموجات الحالية
        current_wave = self._identify_current_wave(sequences, waves)
        
        return {
            "pivot_points": pivot_points[-30:],
            "waves": waves[-20:],
            "sequences": sequences[-5:],
            "current_wave": current_wave,
            "wave_count": self._get_wave_count(sequences),
        }
    
    def _extract_pivot_points(self, highs: np.ndarray, lows: np.ndarray, 
                               closes: np.ndarray, volumes: np.ndarray) -> List[WavePoint]:
        """
        استخراج نقاط التحول الموجية.
        ديناميكي: يبحث عن "نقاط القرار" حيث يتغير الزخم.
        """
        pivot_points = []
        
        if len(closes) < 5:
            return pivot_points
        
        # حساب الزخم (معدل التغير)
        momentum = np.zeros(len(closes))
        for i in range(3, len(closes)):
            momentum[i] = (closes[i] - closes[i-3]) / max(abs(closes[i-3]), 0.0001)
        
        # البحث عن القمم والقيعان
        for i in range(2, len(closes) - 2):
            is_peak = self._is_dynamic_peak(highs, lows, closes, momentum, volumes, i)
            is_trough = self._is_dynamic_trough(highs, lows, closes, momentum, volumes, i)
            
            if is_peak or is_trough:
                price = highs[i] if is_peak else lows[i]
                point_type = self._classify_pivot_point(pivot_points, price, i, is_peak)
                
                # تحديد الدرجة النسبية
                degree = self._estimate_degree(highs, lows, i, is_peak)
                
                pivot_points.append(WavePoint(
                    index=i,
                    price=price,
                    point_type=point_type,
                    degree=degree,
                    confidence=self._pivot_confidence(highs, lows, closes, volumes, i, is_peak),
                ))
        
        return pivot_points
    
    def _is_dynamic_peak(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                          momentum: np.ndarray, volumes: np.ndarray, i: int) -> bool:
        """
        كشف القمة الديناميكي.
        القمة = نقطة يتحول عندها الزخم من إيجابي إلى سلبي.
        """
        # 1. السعر أعلى من جيرانه
        if not (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and 
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
            return False
        
        # 2. الزخم يتحول (من صاعد إلى هابط أو يتباطأ)
        if i >= 3:
            mom_before = momentum[i-1] - momentum[i-3] if i >= 4 else 0
            mom_after = momentum[i+1] - momentum[i] if i+2 < len(momentum) else -0.001
            
            if mom_before > 0 and mom_after < 0:
                return True
        
        # 3. ظل علوي (رفض)
        candle_range = highs[i] - lows[i]
        if candle_range > 0:
            upper_wick = highs[i] - max(closes[i], closes[i-1] if i > 0 else closes[i])
            if upper_wick > candle_range * 0.3:
                return True
        
        return False
    
    def _is_dynamic_trough(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                            momentum: np.ndarray, volumes: np.ndarray, i: int) -> bool:
        """
        كشف القاع الديناميكي.
        القاع = نقطة يتحول عندها الزخم من سلبي إلى إيجابي.
        """
        if not (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
            return False
        
        if i >= 3:
            mom_before = momentum[i-1] - momentum[i-3] if i >= 4 else 0
            mom_after = momentum[i+1] - momentum[i] if i+2 < len(momentum) else 0.001
            
            if mom_before < 0 and mom_after > 0:
                return True
        
        candle_range = highs[i] - lows[i]
        if candle_range > 0:
            lower_wick = min(closes[i], closes[i-1] if i > 0 else closes[i]) - lows[i]
            if lower_wick > candle_range * 0.3:
                return True
        
        return False
    
    def _classify_pivot_point(self, existing_points: List[WavePoint], price: float,
                               index: int, is_peak: bool) -> str:
        """
        تصنيف نقطة التحول كجزء من تركيب موجي.
        هذا هو قلب الترقيم الموجي الديناميكي.
        """
        if len(existing_points) < 2:
            return 'start' if not is_peak else 'peak_1'
        
        # تحليل آخر 7 نقاط لتحديد السياق الموجي
        recent = existing_points[-7:] if len(existing_points) >= 7 else existing_points
        
        # هل نحن في موجة دافعة أم تصحيحية؟
        last_peaks = [p for p in recent if 'peak' in p.point_type]
        last_troughs = [p for p in recent if 'trough' in p.point_type]
        
        if is_peak:
            if len(last_peaks) == 0:
                return 'peak_1'
            elif len(last_peaks) == 1:
                if len(last_troughs) >= 1 and price > last_peaks[-1].price:
                    return 'peak_3'  # قمة أعلى = الموجة 3
                elif price < last_peaks[-1].price:
                    return 'peak_B'  # قمة أقل = تصحيح B
                else:
                    return 'peak_3'
            elif len(last_peaks) == 2:
                if price > last_peaks[-1].price:
                    return 'peak_5'  # قمة أعلى = الموجة 5
                else:
                    return 'peak_B'
            else:
                # نميز بين بداية موجة جديدة أو استمرار تصحيح
                if price > last_peaks[-1].price:
                    return 'peak_1'  # بداية موجة جديدة من درجة أعلى
                else:
                    return 'peak_B'
        else:  # trough
            if len(last_troughs) == 0:
                return 'trough_2'
            elif len(last_troughs) == 1:
                if price > last_troughs[-1].price:
                    return 'trough_4'  # قاع أعلى = الموجة 4
                elif price < last_troughs[-1].price:
                    return 'trough_A'  # قاع أقل = تصحيح A
                else:
                    return 'trough_4'
            elif len(last_troughs) == 2:
                if price < last_troughs[-1].price:
                    return 'trough_C'
                else:
                    return 'trough_A'
            else:
                if price < last_troughs[-1].price:
                    return 'trough_1'  # بداية موجة هابطة
                else:
                    return 'trough_C'
    
    def _estimate_degree(self, highs: np.ndarray, lows: np.ndarray, 
                          index: int, is_peak: bool) -> WaveDegree:
        """
        تقدير الدرجة النسبية للموجة.
        ديناميكي: يقارن حجم الحركة بالحركات السابقة.
        """
        if index < 50:
            return WaveDegree.MINOR
        
        # حجم الحركة الحالية
        local_range = max(highs[max(0,index-20):index+1]) - min(lows[max(0,index-20):index+1])
        
        # حجم الحركات السابقة
        if index >= 100:
            larger_range = max(highs[index-100:index]) - min(lows[index-100:index])
        else:
            larger_range = max(highs[:index]) - min(lows[:index])
        
        if larger_range == 0:
            return WaveDegree.MINOR
        
        ratio = local_range / larger_range
        
        if ratio > 0.5:
            return WaveDegree.PRIMARY
        elif ratio > 0.2:
            return WaveDegree.INTERMEDIATE
        elif ratio > 0.08:
            return WaveDegree.MINOR
        elif ratio > 0.03:
            return WaveDegree.MINUTE
        else:
            return WaveDegree.MINUETTE
    
    def _pivot_confidence(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                           volumes: np.ndarray, i: int, is_peak: bool) -> float:
        """حساب ثقة نقطة التحول"""
        confidence = 0.5
        
        # 1. قوة الحركة السابقة
        if i >= 5:
            prev_move = abs(closes[i] - closes[i-5])
            avg_move = np.mean([abs(closes[j] - closes[j-1]) for j in range(max(0,i-15), i)])
            if avg_move > 0:
                confidence += min(0.2, prev_move / avg_move * 0.05)
        
        # 2. حجم التداول (ذروة بيع/شراء)
        if i >= 10:
            avg_vol = np.mean(volumes[i-10:i])
            if avg_vol > 0 and volumes[i] > avg_vol * 1.5:
                confidence += 0.15
        
        # 3. وضوح النقطة (كم هي أعلى/أقل من جيرانها)
        if is_peak:
            neighbors_high = max(highs[max(0,i-3):i].tolist() + highs[i+1:min(len(highs),i+4)].tolist())
            if neighbors_high > 0:
                clarity = (highs[i] - neighbors_high) / highs[i]
                confidence += min(0.15, clarity * 15)
        else:
            neighbors_low = min(lows[max(0,i-3):i].tolist() + lows[i+1:min(len(lows),i+4)].tolist())
            if lows[i] > 0:
                clarity = (neighbors_low - lows[i]) / lows[i]
                confidence += min(0.15, clarity * 15)
        
        return min(1.0, confidence)
    
    def _build_waves(self, pivot_points: List[WavePoint], highs: np.ndarray,
                     lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> List[ElliottWave]:
        """
        بناء الموجات من نقاط التحول.
        كل موجتين متتاليتين من نقاط التحول = موجة إليوت.
        """
        waves = []
        
        for i in range(1, len(pivot_points)):
            start_pt = pivot_points[i-1]
            end_pt = pivot_points[i]
            
            # تحديد رقم الموجة
            wave_number = self._determine_wave_number(start_pt, end_pt)
            
            # تحديد نوع الموجة
            wave_type = self._determine_wave_type(start_pt, end_pt, highs, lows, closes)
            
            # قياس قوة الموجة
            strength = self._measure_wave_strength(highs, lows, closes, volumes,
                                                    start_pt.index, end_pt.index)
            
            # تحليل شخصية الموجة
            personality = self._analyze_wave_personality(wave_number, wave_type, 
                                                          start_pt, end_pt, strength)
            
            waves.append(ElliottWave(
                start_idx=start_pt.index,
                end_idx=end_pt.index,
                wave_number=wave_number,
                wave_type=wave_type,
                degree=end_pt.degree,
                price_start=start_pt.price,
                price_end=end_pt.price,
                price_change=end_pt.price - start_pt.price,
                duration=end_pt.index - start_pt.index,
                sub_waves=[],
                strength=strength,
                personality=personality,
            ))
        
        return waves
    
    def _determine_wave_number(self, start_pt: WavePoint, end_pt: WavePoint) -> int:
        """
        تحديد رقم الموجة من نوع نقاط البداية والنهاية.
        """
        pt_map = {
            ('start', 'peak_1'): 1, ('peak_1', 'trough_2'): 2,
            ('trough_2', 'peak_3'): 3, ('peak_3', 'trough_4'): 4,
            ('trough_4', 'peak_5'): 5,
            ('peak_5', 'trough_A'): -1, ('trough_A', 'peak_B'): -2,
            ('peak_B', 'trough_C'): -3,
        }
        
        key = (start_pt.point_type, end_pt.point_type)
        return pt_map.get(key, 0)
    
    def _determine_wave_type(self, start_pt: WavePoint, end_pt: WavePoint,
                              highs: np.ndarray, lows: np.ndarray, 
                              closes: np.ndarray) -> WaveType:
        """
        تحديد نوع الموجة (دافعة، قطرية، تصحيحية...).
        ديناميكي: يحلل شكل الموجة وليس نسبها.
        """
        wave_num = self._determine_wave_number(start_pt, end_pt)
        
        if wave_num in [1, 2, 3, 4, 5]:
            # موجة دافعة أو قطرية
            if wave_num == 5:
                # هل هي قطرية ختامية؟
                is_ending_diagonal = self._check_ending_diagonal(start_pt, end_pt, 
                                                                  highs, lows, closes)
                if is_ending_diagonal:
                    return WaveType.DIAGONAL_ENDING
            if wave_num == 1:
                is_leading_diagonal = self._check_leading_diagonal(start_pt, end_pt,
                                                                    highs, lows, closes)
                if is_leading_diagonal:
                    return WaveType.DIAGONAL_LEADING
            return WaveType.IMPULSE
        elif wave_num in [-1, -2, -3]:
            # موجة تصحيحية
            return self._identify_corrective_type(start_pt, end_pt, highs, lows, closes)
        
        return WaveType.UNKNOWN
    
    def _check_ending_diagonal(self, start_pt: WavePoint, end_pt: WavePoint,
                                highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray) -> bool:
        """
        كشف القطرية الختامية.
        خصائصها: تتداخل الموجات، تتحرك في وتد، الزخم يتباطأ.
        """
        seg_highs = highs[start_pt.index:end_pt.index+1]
        seg_lows = lows[start_pt.index:end_pt.index+1]
        
        if len(seg_highs) < 10:
            return False
        
        # القطرية تتشكل على شكل وتد متضيق
        highs_trend = np.polyfit(range(len(seg_highs)), seg_highs, 1)[0]
        lows_trend = np.polyfit(range(len(seg_lows)), seg_lows, 1)[0]
        
        # في القطرية: القمم والقيعان تتقارب (الوتد يضيق)
        highs_range_start = max(seg_highs[:3]) - min(seg_highs[:3])
        highs_range_end = max(seg_highs[-3:]) - min(seg_highs[-3:])
        
        # الخطوط تتقارب
        if highs_trend > 0 and lows_trend > 0 and highs_trend > lows_trend * 1.2:
            return True
        
        return False
    
    def _check_leading_diagonal(self, start_pt: WavePoint, end_pt: WavePoint,
                                 highs: np.ndarray, lows: np.ndarray,
                                 closes: np.ndarray) -> bool:
        """
        كشف القطرية القائدة.
        تشبه القطرية الختامية لكنها في بداية الاتجاه.
        """
        # نفس منطق القطرية الختامية لكن في بداية اتجاه جديد
        return self._check_ending_diagonal(start_pt, end_pt, highs, lows, closes)
    
    def _identify_corrective_type(self, start_pt: WavePoint, end_pt: WavePoint,
                                   highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray) -> WaveType:
        """
        تحديد نوع الموجة التصحيحية: زيجزاج، فلات، مثلث، أو مركبة.
        ديناميكي من شكل الموجة.
        """
        seg_highs = highs[start_pt.index:end_pt.index+1]
        seg_lows = lows[start_pt.index:end_pt.index+1]
        seg_closes = closes[start_pt.index:end_pt.index+1]
        
        if len(seg_closes) < 8:
            return WaveType.ZIGZAG  # افتراضي
        
        # قياس التداخل (للتفريق بين فلات وزيجزاج)
        mid = (max(seg_highs) + min(seg_lows)) / 2
        total_range = max(seg_highs) - min(seg_lows)
        
        if total_range == 0:
            return WaveType.FLAT
        
        # كم من الوقت قضى السعر في النصف العلوي من النطاق؟
        time_in_upper = sum(1 for c in seg_closes if c > mid)
        upper_ratio = time_in_upper / len(seg_closes)
        
        # قياس التذبذب
        oscillation = np.std(seg_closes) / np.mean(seg_closes) if np.mean(seg_closes) > 0 else 0
        
        if upper_ratio > 0.55 and upper_ratio < 0.65 and oscillation < 0.02:
            return WaveType.FLAT  # فلات: حركة أفقية
        elif oscillation < 0.01:
            return WaveType.TRIANGLE  # مثلث: نطاق يضيق
        elif start_pt.price > end_pt.price:
            return WaveType.ZIGZAG  # زيجزاج: موجة حادة
        else:
            return WaveType.COMBINATION
    
    def _measure_wave_strength(self, highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray, volumes: np.ndarray,
                                start_idx: int, end_idx: int) -> float:
        """
        قياس قوة الموجة.
        ديناميكي: سرعة الموجة + استمراريتها + حجم التداول.
        """
        if end_idx <= start_idx:
            return 0.5
        
        segment_closes = closes[start_idx:end_idx+1]
        
        # 1. السرعة (السعر/الزمن)
        price_change = abs(segment_closes[-1] - segment_closes[0])
        duration = end_idx - start_idx
        speed = price_change / max(duration, 1)
        
        # السرعة النسبية
        if start_idx >= 20:
            prev_speed = abs(closes[start_idx] - closes[max(0,start_idx-20)]) / 20
            speed_ratio = speed / max(prev_speed, 0.0001)
        else:
            speed_ratio = 1.0
        
        # 2. الاستمرارية
        same_direction = 0
        for i in range(start_idx+1, end_idx+1):
            if segment_closes[-1] > segment_closes[0]:
                if closes[i] > closes[i-1]:
                    same_direction += 1
            else:
                if closes[i] < closes[i-1]:
                    same_direction += 1
        
        continuity = same_direction / max(duration, 1)
        
        # 3. حجم التداول (تأكيد)
        if start_idx >= 10:
            avg_vol_segment = np.mean(volumes[start_idx:end_idx+1])
            avg_vol_overall = np.mean(volumes[max(0,start_idx-30):start_idx])
            if avg_vol_overall > 0:
                vol_ratio = avg_vol_segment / avg_vol_overall
            else:
                vol_ratio = 1.0
        else:
            vol_ratio = 1.0
        
        # الدرجة النهائية
        strength = (min(speed_ratio/3, 1.0) * 0.35 + 
                   continuity * 0.35 + 
                   min(vol_ratio/2, 1.0) * 0.3)
        
        return min(1.0, max(0.1, strength))
    
    def _analyze_wave_personality(self, wave_number: int, wave_type: WaveType,
                                   start_pt: WavePoint, end_pt: WavePoint,
                                   strength: float) -> str:
        """
        تحليل "شخصية" الموجة.
        كل موجة في إليوت لها شخصية نفسية مميزة.
        """
        if wave_number == 1:
            if strength > 0.7:
                return "موجة 1 قوية - السوق يستيقظ بقوة، القطيع لا يزال نائماً"
            else:
                return "موجة 1 ضعيفة - بداية مترددة، السوق يختبر المياه"
        
        elif wave_number == 2:
            return "موجة 2 - خوف وتشكك، الجميع يعتقد أن الاتجاه القديم عاد"
        
        elif wave_number == 3:
            if strength > 0.8:
                return "موجة 3 العظيمة - الأقوى والأطول، القطيع يبدأ بالدخول"
            else:
                return "موجة 3 - حركة قوية، الأخبار تتحسن، التفاؤل يزداد"
        
        elif wave_number == 4:
            return "موجة 4 - تردد وجني أرباح، تصحيح ممل لكنه صحي"
        
        elif wave_number == 5:
            if strength < 0.5:
                return "موجة 5 ضعيفة - الزخم ينفد، النشوة في ذروتها، النهاية تقترب"
            else:
                return "موجة 5 - اندفاع أخير، القطيع كله هنا، كن حذراً"
        
        elif wave_number == -1:  # A
            return "موجة A - القطيع ينكر الانعكاس، يعتقد أنه تصحيح عادي"
        
        elif wave_number == -2:  # B
            return "موجة B - فخ الثيران/الدببة، أمل كاذب، السوق يخدع الجميع"
        
        elif wave_number == -3:  # C
            return "موجة C - الذعر يسيطر، الأسوأ لم يأت بعد، لكن النهاية تقترب"
        
        return "موجة غير معروفة"
    
    def _build_sequences(self, waves: List[ElliottWave]) -> List[WaveSequence]:
        """
        بناء تسلسلات موجية من الموجات الفردية.
        تسلسل دافع = 5 موجات. تسلسل تصحيحي = 3 موجات.
        """
        sequences = []
        
        if len(waves) < 3:
            return sequences
        
        i = 0
        while i <= len(waves) - 3:
            # البحث عن تسلسل دافع (5 موجات)
            if i + 4 < len(waves):
                impulse_candidates = waves[i:i+5]
                impulse_numbers = [w.wave_number for w in impulse_candidates]
                
                if impulse_numbers == [1, 2, 3, 4, 5]:
                    # تحقق ديناميكي
                    if self._validate_impulse_sequence(impulse_candidates):
                        extended = self._find_extended_wave(impulse_candidates)
                        truncated = self._detect_truncation(impulse_candidates)
                        
                        sequences.append(WaveSequence(
                            waves=impulse_candidates,
                            sequence_type='impulse',
                            degree=impulse_candidates[-1].degree,
                            start_idx=impulse_candidates[0].start_idx,
                            end_idx=impulse_candidates[-1].end_idx,
                            complete=True,
                            extended_wave=extended,
                            truncation_detected=truncated,
                            channel_lines=self._calculate_channel_lines(impulse_candidates),
                        ))
                        i += 5
                        continue
            
            # البحث عن تسلسل تصحيحي (3 موجات)
            corrective_candidates = waves[i:i+3]
            corrective_numbers = [w.wave_number for w in corrective_candidates]
            
            if corrective_numbers in [[-1, -2, -3], [2, 3, 4]]:
                if self._validate_corrective_sequence(corrective_candidates):
                    sequences.append(WaveSequence(
                        waves=corrective_candidates,
                        sequence_type='corrective',
                        degree=corrective_candidates[-1].degree,
                        start_idx=corrective_candidates[0].start_idx,
                        end_idx=corrective_candidates[-1].end_idx,
                        complete=True,
                        extended_wave=None,
                        truncation_detected=False,
                        channel_lines=(0,0,0,0),
                    ))
                    i += 3
                    continue
            
            i += 1
        
        return sequences
    
    def _validate_impulse_sequence(self, waves: List[ElliottWave]) -> bool:
        """
        التحقق الديناميكي من صحة التسلسل الدافع.
        
        القواعد الديناميكية (وليس النسب الثابتة):
        1. الموجة 2 لا ترتد عن كامل الموجة 1 (وإلا فهو ليس اتجاهاً جديداً)
        2. الموجة 3 هي الأقوى (وليس بالضرورة 161.8%)
        3. الموجة 4 لا تتداخل مع الموجة 1 (سعرياً وليس نسبياً)
        """
        if len(waves) != 5:
            return False
        
        w1, w2, w3, w4, w5 = waves
        
        # القاعدة 1: الموجة 2 لا تلغي الموجة 1 بالكامل
        if abs(w2.price_change) > abs(w1.price_change) * 1.0:
            return False
        
        # القاعدة 2: الموجة 3 هي الأقوى (أكبر حركة سعرية)
        wave_changes = [abs(w.price_change) for w in waves]
        if wave_changes[2] < max(wave_changes[0], wave_changes[4]):
            # الموجة 3 ليست الأكبر - لكن قد تكون هناك بتر أو امتداد
            if not (wave_changes[0] > wave_changes[2] * 1.5 or wave_changes[4] > wave_changes[2] * 1.5):
                # الفارق مقبول
                pass
            else:
                return False
        
        # القاعدة 3: الموجة 4 لا تتداخل مع نطاق الموجة 1
        w1_range = (min(w1.price_start, w1.price_end), max(w1.price_start, w1.price_end))
        w4_range = (min(w4.price_start, w4.price_end), max(w4.price_start, w4.price_end))
        
        if w3.price_change > 0:  # اتجاه صاعد
            if w4_range[1] < w1_range[1]:
                return False  # تداخل
        else:  # اتجاه هابط
            if w4_range[0] > w1_range[0]:
                return False
        
        return True
    
    def _validate_corrective_sequence(self, waves: List[ElliottWave]) -> bool:
        """التحقق من التسلسل التصحيحي"""
        if len(waves) != 3:
            return False
        
        # التصحيح يجب أن يكون أصغر من الموجة الدافعة السابقة
        # لكن هذه القاعدة نسبية وتعتمد على السياق
        return True
    
    def _find_extended_wave(self, waves: List[ElliottWave]) -> Optional[int]:
        """
        اكتشاف الموجة الممتدة.
        الموجة الممتدة = موجة تحتوي موجات فرعية واضحة.
        """
        wave_changes = [abs(w.price_change) for w in waves]
        avg_change = np.mean(wave_changes)
        
        if avg_change == 0:
            return None
        
        for i, change in enumerate(wave_changes):
            if change > avg_change * 2.0:
                return i + 1  # رقم الموجة
        
        return None
    
    def _detect_truncation(self, waves: List[ElliottWave]) -> bool:
        """
        كشف البتر (Truncation): الموجة 5 أقصر من الموجة 3.
        """
        if len(waves) < 5:
            return False
        
        w3 = abs(waves[2].price_change)
        w5 = abs(waves[4].price_change)
        
        return w5 < w3 * 0.4
    
    def _calculate_channel_lines(self, waves: List[ElliottWave]) -> Tuple[float, float, float, float]:
        """
        حساب خطوط القناة.
        القناة تربط القمم والقيعان لتحديد مسار الموجات.
        """
        if len(waves) < 3:
            return (0, 0, 0, 0)
        
        # خط القاع: يربط نهاية الموجة 2 بنهاية الموجة 4
        w2_end_price = waves[1].price_end
        w4_end_price = waves[3].price_end
        w2_end_idx = waves[1].end_idx
        w4_end_idx = waves[3].end_idx
        
        # خط القمة: يربط نهاية الموجة 1 بنهاية الموجة 3 (ثم يمتد للموجة 5)
        w1_end_price = waves[0].price_end
        w3_end_price = waves[2].price_end
        w1_end_idx = waves[0].end_idx
        w3_end_idx = waves[2].end_idx
        
        return (w2_end_price, w4_end_price, w1_end_price, w3_end_price)
    
    def _identify_current_wave(self, sequences: List[WaveSequence],
                                waves: List[ElliottWave]) -> Dict:
        """
        تحديد الموجة الحالية.
        """
        if sequences:
            last_seq = sequences[-1]
            if not last_seq.complete:
                return {
                    "sequence_type": last_seq.sequence_type,
                    "current_wave_in_sequence": len(last_seq.waves),
                    "waves_remaining": (5 if last_seq.sequence_type == 'impulse' else 3) - len(last_seq.waves),
                }
            else:
                # التسلسل مكتمل - ما التالي؟
                if last_seq.sequence_type == 'impulse':
                    return {"next_expected": "corrective", "status": "اكتمل الدافع - نتوقع تصحيح"}
                else:
                    return {"next_expected": "impulse", "status": "اكتمل التصحيح - نتوقع دافع"}
        
        if waves:
            return {"current_wave": waves[-1].wave_number, "personality": waves[-1].personality}
        
        return {"status": "غير محدد"}
    
    def _get_wave_count(self, sequences: List[WaveSequence]) -> Dict:
        """إحصاء الموجات"""
        total_impulses = sum(1 for s in sequences if s.sequence_type == 'impulse')
        total_correctives = sum(1 for s in sequences if s.sequence_type == 'corrective')
        
        return {
            "total_sequences": len(sequences),
            "impulses": total_impulses,
            "correctives": total_correctives,
            "current_cycle_position": self._estimate_cycle_position(total_impulses, total_correctives),
        }
    
    def _estimate_cycle_position(self, impulses: int, correctives: int) -> str:
        """تقدير موقع الدورة"""
        if impulses == 0 and correctives == 0:
            return "بداية"
        if impulses > correctives:
            return "في موجة دافعة"
        elif correctives > impulses:
            return "في موجة تصحيحية"
        else:
            return "نهاية دورة"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الثانية: محلل النسب الديناميكي (Dynamic Ratio Analyzer)       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicRatioAnalyzer:
    """
    يحلل النسب بين الموجات بطريقة ديناميكية.
    
    بدلاً من استخدام نسب فيبوناتشي الثابتة، يستنتج هذا المحلل
    النسب "الشخصية" للسوق من تاريخه الموجي.
    
    كل سوق له نسبه المفضلة. هذا المحلل يكتشفها.
    """
    
    def analyze(self, sequences: List[WaveSequence]) -> Dict:
        """
        تحليل النسب الديناميكية بين الموجات
        """
        # استخراج النسب التاريخية
        historical_ratios = self._extract_historical_ratios(sequences)
        
        # النسب المفضلة لهذا السوق
        preferred_ratios = self._find_preferred_ratios(historical_ratios)
        
        # النسب الحالية
        current_ratios = self._analyze_current_ratios(sequences)
        
        # مستويات فيبوناتشي الديناميكية
        fib_clusters = self._find_fibonacci_clusters(current_ratios, preferred_ratios)
        
        return {
            "historical_ratios": historical_ratios,
            "preferred_ratios": preferred_ratios,
            "current_ratios": current_ratios,
            "fib_clusters": fib_clusters[-5:],
        }
    
    def _extract_historical_ratios(self, sequences: List[WaveSequence]) -> Dict:
        """
        استخراج النسب التاريخية من كل التسلسلات.
        بدلاً من 61.8% ثابتة، نجد ما استخدمه السوق فعلاً.
        """
        ratios = {
            "wave2_to_wave1": [],
            "wave3_to_wave1": [],
            "wave4_to_wave3": [],
            "wave5_to_wave1": [],
            "waveA_to_wave5": [],
            "waveB_to_waveA": [],
            "waveC_to_waveA": [],
        }
        
        for seq in sequences:
            if seq.sequence_type == 'impulse' and len(seq.waves) == 5:
                w1 = abs(seq.waves[0].price_change)
                w2 = abs(seq.waves[1].price_change)
                w3 = abs(seq.waves[2].price_change)
                w4 = abs(seq.waves[3].price_change)
                w5 = abs(seq.waves[4].price_change)
                
                if w1 > 0:
                    ratios["wave2_to_wave1"].append(w2 / w1)
                    ratios["wave3_to_wave1"].append(w3 / w1)
                    ratios["wave5_to_wave1"].append(w5 / w1)
                
                if w3 > 0:
                    ratios["wave4_to_wave3"].append(w4 / w3)
            
            elif seq.sequence_type == 'corrective' and len(seq.waves) == 3:
                wA = abs(seq.waves[0].price_change)
                wB = abs(seq.waves[1].price_change)
                wC = abs(seq.waves[2].price_change)
                
                if wA > 0:
                    ratios["waveB_to_waveA"].append(wB / wA)
                    ratios["waveC_to_waveA"].append(wC / wA)
        
        return ratios
    
    def _find_preferred_ratios(self, historical: Dict) -> Dict:
        """
        اكتشاف النسب المفضلة للسوق من تاريخه.
        السوق "يتذكر" نسبه ويميل لتكرارها.
        """
        preferred = {}
        
        for key, values in historical.items():
            if len(values) < 3:
                preferred[key] = None
                continue
            
            # تجميع النسب المتشابهة
            clusters = self._cluster_ratios(values)
            
            if clusters:
                preferred[key] = {
                    "clusters": clusters[:3],
                    "median": np.median(values),
                    "std": np.std(values) if len(values) > 1 else 0,
                }
            else:
                preferred[key] = None
        
        return preferred
    
    def _cluster_ratios(self, values: List[float]) -> List[float]:
        """
        تجميع النسب المتشابهة لاكتشاف "النسب المفضلة".
        """
        if not values:
            return []
        
        sorted_vals = sorted(values)
        clusters = []
        current_cluster = [sorted_vals[0]]
        
        for i in range(1, len(sorted_vals)):
            if sorted_vals[i] - current_cluster[-1] < 0.05:
                current_cluster.append(sorted_vals[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append(np.mean(current_cluster))
                current_cluster = [sorted_vals[i]]
        
        if len(current_cluster) >= 2:
            clusters.append(np.mean(current_cluster))
        
        return sorted(clusters, reverse=True)
    
    def _analyze_current_ratios(self, sequences: List[WaveSequence]) -> Dict:
        """
        تحليل النسب الحالية في آخر تسلسل.
        """
        current = {}
        
        if sequences:
            last_seq = sequences[-1]
            if last_seq.sequence_type == 'impulse' and len(last_seq.waves) >= 3:
                w1 = abs(last_seq.waves[0].price_change)
                w2 = abs(last_seq.waves[1].price_change)
                w3 = abs(last_seq.waves[2].price_change)
                
                if w1 > 0:
                    current["w2/w1"] = w2 / w1
                    current["w3/w1"] = w3 / w1
                    
                    # المقارنة مع المتوقع ديناميكياً
                    current["w2_expected"] = w1 * 0.5  # سيتم تعديله ديناميكياً
                    current["w3_expected"] = w1 * 1.5
        
        return current
    
    def _find_fibonacci_clusters(self, current_ratios: Dict, 
                                  preferred_ratios: Dict) -> List[FibonacciCluster]:
        """
        إيجاد مناطق تجمع النسب (مستويات مهمة).
        """
        clusters = []
        
        # دمج النسب الحالية مع النسب المفضلة
        all_levels = {}
        
        for key, ratio in current_ratios.items():
            if isinstance(ratio, (int, float)):
                # البحث عن النسبة في النسب المفضلة
                for pref_key, pref_data in preferred_ratios.items():
                    if pref_data and pref_data.get('clusters'):
                        for cluster in pref_data['clusters']:
                            if abs(ratio - cluster) < 0.1:
                                level = round(ratio * 100)
                                if level not in all_levels:
                                    all_levels[level] = {"ratios": [], "relations": []}
                                all_levels[level]["ratios"].append(ratio)
                                all_levels[level]["relations"].append(f"{key} ≈ {pref_key}")
        
        # تحويل إلى FibonacciCluster
        for level, data in all_levels.items():
            clusters.append(FibonacciCluster(
                price_level=level / 100,
                ratios_present=data["ratios"],
                cluster_strength=min(1.0, len(data["ratios"]) * 0.3),
                wave_relations=data["relations"],
            ))
        
        return sorted(clusters, key=lambda c: c.cluster_strength, reverse=True)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية موجات إليوت الموحدة                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ElliottWaveStrategy:
    """
    استراتيجية موجات إليوت الديناميكية الكاملة.
    
    تجمع:
    - اكتشاف الموجات الديناميكي
    - تحليل النسب الديناميكي
    - شخصية كل موجة
    - علاقات الزمن والزخم
    
    في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.wave_detector = DynamicWaveDetector()
        self.ratio_analyzer = DynamicRatioAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 50:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 50 شمعة على الأقل لتحليل موجات إليوت"}
        
        # 1. اكتشاف الموجات
        wave_data = self.wave_detector.analyze(highs, lows, closes, volumes)
        
        # 2. تحليل النسب
        sequences = wave_data.get('sequences', [])
        ratio_data = self.ratio_analyzer.analyze(sequences)
        
        # 3. القرار
        decision = self._make_decision(wave_data, ratio_data)
        
        return {
            **decision,
            "wave_data": wave_data,
            "ratio_data": ratio_data,
        }
    
    def _make_decision(self, wave_data: Dict, ratio_data: Dict) -> Dict:
        """
        اتخاذ القرار بناءً على الموجات والنسب
        """
        buy_signals = []
        sell_signals = []
        
        current_wave = wave_data.get('current_wave', {})
        sequences = wave_data.get('sequences', [])
        
        # ---- من الموجة الحالية ----
        if current_wave:
            wave_num = current_wave.get('current_wave_in_sequence')
            wave_personality = current_wave.get('personality', '')
            
            if isinstance(wave_num, int):
                if wave_num == 2:
                    buy_signals.append(("نهاية الموجة 2 - أفضل فرصة شراء", 0.8))
                elif wave_num == 4:
                    buy_signals.append(("تصحيح الموجة 4 - فرصة شراء", 0.6))
                elif wave_num == 3:
                    buy_signals.append(("في الموجة 3 - استمر بالشراء", 0.7))
                elif wave_num == 5:
                    buy_signals.append(("الموجة 5 - كن حذراً، الأفضل جني أرباح", 0.4))
                    sell_signals.append(("نهاية الموجة 5 تقترب - استعد للبيع", 0.5))
        
        # ---- من التسلسلات الكاملة ----
        if sequences:
            last_seq = sequences[-1]
            if last_seq.sequence_type == 'impulse' and last_seq.complete:
                sell_signals.append(("اكتمل الدافع - تصحيح قادم", 0.65))
            elif last_seq.sequence_type == 'corrective' and last_seq.complete:
                buy_signals.append(("اكتمل التصحيح - دافع قادم", 0.65))
            
            # الامتداد
            if last_seq.extended_wave:
                if last_seq.extended_wave == 3:
                    buy_signals.append(("موجة 3 ممتدة - مزيد من الصعود", 0.7))
                elif last_seq.extended_wave == 5:
                    sell_signals.append(("موجة 5 ممتدة - سئمت من الصعود، قرب النهاية", 0.7))
            
            # البتر
            if last_seq.truncation_detected:
                sell_signals.append(("بتر في الموجة 5 - انعكاس حاد قادم", 0.75))
        
        # ---- من النسب ----
        current_ratios = ratio_data.get('current_ratios', {})
        preferred = ratio_data.get('preferred_ratios', {})
        
        if current_ratios and preferred:
            # مقارنة النسب الحالية بالمفضلة
            for key, ratio_value in current_ratios.items():
                if isinstance(ratio_value, (int, float)):
                    pref_key = key.replace('/', '_to_')
                    pref_data = preferred.get(pref_key)
                    
                    if pref_data and pref_data.get('clusters'):
                        # هل النسبة الحالية قريبة من إحدى النسب المفضلة؟
                        nearest_cluster = min(pref_data['clusters'], 
                                             key=lambda c: abs(c - ratio_value))
                        
                        if abs(ratio_value - nearest_cluster) < 0.05:
                            if ratio_value > 1.0:
                                buy_signals.append((f"نسبة {key} عند القيمة المفضلة {nearest_cluster:.2f}", 0.5))
        
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
        
        # إضافة شخصية الموجة الحالية للسبب
        if current_wave.get('personality'):
            reason += f" | {current_wave['personality']}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "wave_position": current_wave,
        }


def create_elliott_wave_strategy():
    """إنشاء استراتيجية موجات إليوت الجاهزة"""
    return ElliottWaveStrategy()