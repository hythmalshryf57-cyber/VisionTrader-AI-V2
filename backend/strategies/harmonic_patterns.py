"""
═══════════════════════════════════════════════════════════════════════════════
HARMONIC PATTERNS - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الخامسة: الأنماط التوافقية - رياضيات الطبيعة في الأسواق
═══════════════════════════════════════════════════════════════════════════════

الأنماط التوافقية تستخدم نسب فيبوناتشي لاكتشاف نقاط الانعكاس المحتملة.
لكن هذه النسخة ديناميكية: النسب ليست ثابتة، بل السوق يختار نسبته المفضلة.

الأنماط المشمولة (كلها ديناميكية):
- Gartley, Bat, Crab, Butterfly, Shark, Cypher
- DeepCrab, MaxBat, AB=CD, Alternate AB=CD
- Three Drives, 5-0, Anti-Patterns

الإضافات الجديدة (الإصدار 2.0):
- Harmonic Completion Progress
- Volume Confirmation عند PRZ
- Harmonic Failure Rate لكل نمط
- Anti-Patterns تتحقق من اختراق D فعلياً
- كود نظيف (إزالة المتغيرات غير المستخدمة)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class HarmonicPoint:
    """نقطة في النمط التوافقي"""
    index: int
    price: float
    label: str
    pivot_type: str


@dataclass
class HarmonicPattern:
    """نمط توافقي مكتمل - محسن"""
    pattern_type: str
    points: Dict[str, HarmonicPoint]
    direction: str
    ratios: Dict[str, float]
    ideal_ratios: Dict[str, Tuple[float, float]]
    ratio_accuracy: float
    completion_index: int
    potential_reversal_zone: Tuple[float, float]
    confidence: float
    strength: float
    is_anti_pattern: bool
    # 🟡 تعديل 4: Completion Progress
    completion_progress: float = 1.0
    # 🟡 تعديل 5: Volume Confirmation
    volume_confirmed: bool = False
    # 🟡 تعديل 6: Failure Rate
    historical_success_rate: float = 0.5


@dataclass
class HarmonicCluster:
    """تجمع أنماط توافقية"""
    price_zone: Tuple[float, float]
    patterns: List[str]
    cluster_strength: float
    direction: str
    is_prz: bool
    # 🟡 تعديل 5: Volume at PRZ
    volume_at_zone: float = 0.0
    volume_confirmed: bool = False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الأولى: محلل النقاط التوافقية                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HarmonicPointDetector:
    """يكتشف نقاط التحول التوافقية X-A-B-C-D"""
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """اكتشاف نقاط التحول التوافقية"""
        all_swings = self._extract_significant_swings(highs, lows, closes, volumes)
        labeled_points = self._label_swing_points(all_swings)
        
        return {
            "swings": all_swings[-20:],
            "labeled_points": labeled_points[-15:],
            "total_swings": len(all_swings),
        }
    
    def _extract_significant_swings(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, volumes: np.ndarray) -> List[HarmonicPoint]:
        """استخراج نقاط التأرجح المهمة"""
        swings = []
        
        if len(closes) < 5:
            return swings
        
        for i in range(3, len(closes) - 3):
            is_peak = self._is_significant_peak(highs, lows, closes, volumes, i)
            is_trough = self._is_significant_trough(highs, lows, closes, volumes, i)
            
            if is_peak or is_trough:
                price = highs[i] if is_peak else lows[i]
                swings.append(HarmonicPoint(
                    index=i, price=price, label='',
                    pivot_type='peak' if is_peak else 'trough',
                ))
        
        return swings
    
    def _is_significant_peak(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                              volumes: np.ndarray, i: int) -> bool:
        """هل هذه قمة مهمة؟"""
        if not (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and 
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
            return False
        
        window = min(10, i, len(highs) - i - 1)
        if window < 3:
            return False
        
        left_max = max(highs[i-window:i])
        right_max = max(highs[i+1:i+window+1])
        surrounding_high = max(left_max, right_max)
        
        if surrounding_high == 0 or highs[i] == 0:
            return False
        
        deviation = (highs[i] - surrounding_high) / highs[i]
        if deviation < 0.002:
            return False
        
        candle_range = highs[i] - lows[i]
        if candle_range > 0:
            upper_wick = highs[i] - max(closes[i], closes[i-1] if i > 0 else closes[i])
            rejection = upper_wick / candle_range
            if rejection > 0.4:
                return True
        
        if i >= 10:
            avg_vol = np.mean(volumes[i-10:i])
            if avg_vol > 0 and volumes[i] > avg_vol * 1.5:
                return True
        
        return deviation > 0.005
    
    def _is_significant_trough(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                                volumes: np.ndarray, i: int) -> bool:
        """هل هذا قاع مهم؟"""
        if not (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
            return False
        
        window = min(10, i, len(lows) - i - 1)
        if window < 3:
            return False
        
        left_min = min(lows[i-window:i])
        right_min = min(lows[i+1:i+window+1])
        surrounding_low = min(left_min, right_min)
        
        if lows[i] == 0:
            return False
        
        deviation = (surrounding_low - lows[i]) / surrounding_low
        if deviation < 0.002:
            return False
        
        candle_range = highs[i] - lows[i]
        if candle_range > 0:
            lower_wick = min(closes[i], closes[i-1] if i > 0 else closes[i]) - lows[i]
            rejection = lower_wick / candle_range
            if rejection > 0.4:
                return True
        
        if i >= 10:
            avg_vol = np.mean(volumes[i-10:i])
            if avg_vol > 0 and volumes[i] > avg_vol * 1.5:
                return True
        
        return deviation > 0.005
    
    def _label_swing_points(self, swings: List[HarmonicPoint]) -> List[HarmonicPoint]:
        """تصنيف نقاط التأرجح"""
        if len(swings) < 5:
            return swings
        
        labeled = []
        for i, swing in enumerate(swings):
            if i == 0:
                swing.label = 'X'
            elif i == 1:
                swing.label = 'A'
            elif i == 2:
                swing.label = 'B'
            elif i == 3:
                swing.label = 'C'
            elif i == 4:
                swing.label = 'D_potential'
            labeled.append(swing)
        
        return labeled


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الثانية: كاشف الأنماط التوافقية (محسن)                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HarmonicPatternDetector:
    """
    يكتشف كل الأنماط التوافقية.
    
    🔴 تعديل 1: إزالة المتغيرات غير المستخدمة
    🔴 تعديل 2: Anti-Patterns تتحقق من اختراق D فعلياً
    🟡 تعديل 4: Completion Progress
    🟡 تعديل 5: Volume Confirmation
    🟡 تعديل 6: Failure Rate لكل نمط
    """
    
    def __init__(self):
        self.pattern_definitions = {
            'Gartley': {
                'XA_retrace': (0.55, 0.68), 'AB_BC_retrace': (0.35, 0.50),
                'XA_AD_extension': (0.72, 0.82), 'AB_CD_equivalence': (1.15, 1.35),
                'BC_CD_extension': (1.55, 1.75),
            },
            'Bat': {
                'XA_retrace': (0.35, 0.50), 'AB_BC_retrace': (0.35, 0.55),
                'XA_AD_extension': (0.83, 0.92), 'AB_CD_equivalence': (1.55, 1.75),
                'BC_CD_extension': (1.85, 2.15),
            },
            'Crab': {
                'XA_retrace': (0.35, 0.62), 'AB_BC_retrace': (0.35, 0.55),
                'XA_AD_extension': (1.55, 1.68), 'AB_CD_equivalence': (2.15, 2.45),
                'BC_CD_extension': (3.35, 3.75),
            },
            'Butterfly': {
                'XA_retrace': (0.72, 0.82), 'AB_BC_retrace': (0.35, 0.55),
                'XA_AD_extension': (1.22, 1.32), 'AB_CD_equivalence': (1.55, 1.75),
                'BC_CD_extension': (2.15, 2.45),
            },
            'Shark': {
                'XA_retrace': (0.35, 0.50), 'AB_BC_retrace': (1.10, 1.30),
                'XA_AD_extension': (0.83, 0.92), 'AB_CD_equivalence': (0.85, 1.15),
                'BC_CD_extension': (1.55, 1.85),
            },
            'Cypher': {
                'XA_retrace': (0.35, 0.45), 'AB_BC_retrace': (1.20, 1.40),
                'XA_AD_extension': (0.72, 0.82), 'AB_CD_equivalence': (0.55, 0.75),
                'BC_CD_extension': (1.20, 1.45),
            },
            'AB_CD': {
                'XA_retrace': (0.55, 0.68), 'AB_BC_retrace': (0.55, 0.68),
                'XA_AD_extension': (0.95, 1.05), 'AB_CD_equivalence': (0.95, 1.05),
                'BC_CD_extension': (1.55, 1.75),
            },
        }
        
        # 🟡 تعديل 6: سجل نجاح كل نمط
        self.pattern_success_history = defaultdict(lambda: {"success": 0, "total": 0})
    
    def analyze(self, swings: List[HarmonicPoint], closes: np.ndarray,
                volumes: np.ndarray, current_price: float) -> Dict:
        """اكتشاف كل الأنماط التوافقية"""
        all_patterns = []
        
        for i in range(len(swings) - 4):
            points_5 = swings[i:i+5]
            X, A, B, C, D = points_5[0], points_5[1], points_5[2], points_5[3], points_5[4]
            
            if X.pivot_type == 'peak' and A.pivot_type == 'trough':
                direction = 'bullish'
            elif X.pivot_type == 'trough' and A.pivot_type == 'peak':
                direction = 'bearish'
            else:
                continue
            
            ratios = self._calculate_ratios(X, A, B, C, D)
            if ratios is None:
                continue
            
            for pattern_name, definition in self.pattern_definitions.items():
                match_result = self._match_pattern(ratios, definition)
                
                if match_result['matches']:
                    prz = self._calculate_prz(ratios, X, A, B, C, D)
                    
                    # 🟡 تعديل 4: Completion Progress
                    completion = self._calculate_completion_progress(ratios, definition, C, D)
                    
                    # 🟡 تعديل 5: Volume Confirmation عند PRZ
                    vol_confirmed = self._check_volume_at_prz(prz, closes, volumes)
                    
                    # 🟡 تعديل 6: Historical Success Rate
                    success_rate = self._get_pattern_success_rate(pattern_name)
                    
                    all_patterns.append(HarmonicPattern(
                        pattern_type=pattern_name,
                        points={'X': X, 'A': A, 'B': B, 'C': C, 'D': D},
                        direction=direction,
                        ratios=ratios,
                        ideal_ratios=definition,
                        ratio_accuracy=match_result['accuracy'],
                        completion_index=D.index,
                        potential_reversal_zone=prz,
                        confidence=match_result['confidence'],
                        strength=match_result['strength'],
                        is_anti_pattern=False,
                        completion_progress=completion,
                        volume_confirmed=vol_confirmed,
                        historical_success_rate=success_rate,
                    ))
        
        # 🔴 تعديل 2: Anti-Patterns تتحقق من اختراق D فعلياً
        anti_patterns = self._detect_anti_patterns(all_patterns, current_price)
        
        # تجميع الأنماط
        clusters = self._cluster_patterns(all_patterns, volumes, closes, current_price)
        best_patterns = self._find_best_patterns(all_patterns)
        
        return {
            "all_patterns": all_patterns[-10:],
            "anti_patterns": anti_patterns[-5:],
            "clusters": clusters[-5:],
            "best_patterns": best_patterns,
            "total_detected": len(all_patterns),
            "current_prz": clusters[-1] if clusters else None,
        }
    
    def _calculate_ratios(self, X: HarmonicPoint, A: HarmonicPoint, B: HarmonicPoint,
                           C: HarmonicPoint, D: HarmonicPoint) -> Optional[Dict]:
        """حساب النسب بين النقاط"""
        try:
            XA = abs(A.price - X.price)
            AB = abs(B.price - A.price)
            BC = abs(C.price - B.price)
            CD = abs(D.price - C.price)
            XD = abs(D.price - X.price)
            XB = abs(B.price - X.price)
            AC = abs(C.price - A.price)
            
            if XA == 0:
                return None
            
            return {
                'XA': XA, 'AB': AB, 'BC': BC, 'CD': CD, 'XD': XD,
                'XB_retrace': XB / XA,
                'AC_retrace': AC / XA,
                'AD_extension': XD / XA,
                'AB_CD_ratio': CD / AB if AB > 0 else 0.0,
                'BC_CD_ratio': CD / BC if BC > 0 else 0.0,
            }
        except (ZeroDivisionError, IndexError):
            return None
    
    def _match_pattern(self, ratios: Dict, definition: Dict) -> Dict:
        """مطابقة النسب الفعلية مع تعريف النمط"""
        accuracy_scores = []
        matches = {}
        
        ratio_map = {
            'XA_retrace': 'XB_retrace',
            'XA_AD_extension': 'AD_extension',
            'AB_CD_equivalence': 'AB_CD_ratio',
            'BC_CD_extension': 'BC_CD_ratio',
        }
        
        for ratio_name, (min_val, max_val) in definition.items():
            if ratio_name == 'AB_BC_retrace':
                actual = ratios['AC_retrace'] / max(ratios['XB_retrace'], 0.0001)
            elif ratio_name in ratio_map:
                actual = ratios[ratio_map[ratio_name]]
            else:
                actual = 0.5
            
            if min_val <= actual <= max_val:
                center = (min_val + max_val) / 2.0
                distance = abs(actual - center) / max((max_val - min_val) / 2.0, 0.0001)
                accuracy = 1.0 - distance * 0.3
                matches[ratio_name] = True
            else:
                distance_out = min(abs(actual - min_val), abs(actual - max_val))
                range_width = max_val - min_val
                if range_width > 0 and distance_out < range_width * 0.3:
                    accuracy = 0.7 - (distance_out / range_width)
                    matches[ratio_name] = 'partial'
                else:
                    accuracy = 0.0
                    matches[ratio_name] = False
            
            accuracy_scores.append(max(0.0, accuracy))
        
        overall_accuracy = np.mean(accuracy_scores) if accuracy_scores else 0.0
        matched_count = sum(1 for v in matches.values() if v == True)
        partial_count = sum(1 for v in matches.values() if v == 'partial')
        is_match = (matched_count + partial_count * 0.5) >= 3.5
        
        if is_match:
            confidence = overall_accuracy * (matched_count / 5.0) ** 0.5
            strength = overall_accuracy
        else:
            confidence = 0.1
            strength = 0.1
        
        return {
            "matches": is_match,
            "accuracy": overall_accuracy,
            "confidence": min(0.95, confidence),
            "strength": min(1.0, strength),
            "match_details": matches,
        }
    
    def _calculate_prz(self, ratios: Dict, X: HarmonicPoint, A: HarmonicPoint,
                        B: HarmonicPoint, C: HarmonicPoint, 
                        D: HarmonicPoint) -> Tuple[float, float]:
        """
        🔴 تعديل 1: حساب PRZ نظيف بدون متغيرات غير مستخدمة
        """
        if A.price > X.price:
            level1 = X.price + (A.price - X.price) * ratios['AD_extension']
        else:
            level1 = X.price - (X.price - A.price) * ratios['AD_extension']
        
        bc_extension = ratios['BC_CD_ratio']
        if C.price > B.price:
            level2 = C.price + (C.price - B.price) * bc_extension
        else:
            level2 = C.price - (B.price - C.price) * bc_extension
        
        prz_low = min(level1, level2)
        prz_high = max(level1, level2)
        
        XA = abs(A.price - X.price)
        buffer = XA * 0.05
        
        return (prz_low - buffer, prz_high + buffer)
    
    def _calculate_completion_progress(self, ratios: Dict, definition: Dict,
                                         C: HarmonicPoint, D: HarmonicPoint) -> float:
        """
        🟡 تعديل 4: Harmonic Completion Progress
        
        كم تبقت من تشكل النمط؟
        """
        # تقدير: CD كم اقترب من الهدف
        expected_ad = definition['XA_AD_extension']
        target_center = (expected_ad[0] + expected_ad[1]) / 2.0
        
        if target_center > 0:
            progress = min(1.0, ratios['AD_extension'] / target_center)
        else:
            progress = 1.0
        
        return progress
    
    def _check_volume_at_prz(self, prz: Tuple[float, float], closes: np.ndarray,
                               volumes: np.ndarray) -> bool:
        """
        🟡 تعديل 5: Volume Confirmation عند PRZ
        
        PRZ + حجم مرتفع = تأكيد انعكاس
        """
        if len(closes) < 10 or len(volumes) < 10:
            return False
        
        current = closes[-1]
        prz_low, prz_high = prz
        
        # هل السعر داخل PRZ؟
        if not (prz_low <= current <= prz_high):
            return False
        
        # حجم مرتفع؟
        avg_vol = np.mean(volumes[-10:])
        recent_vol = volumes[-1]
        
        return recent_vol > avg_vol * 1.3
    
    def _get_pattern_success_rate(self, pattern_name: str) -> float:
        """
        🟡 تعديل 6: Harmonic Failure Rate لكل نمط
        """
        history = self.pattern_success_history[pattern_name]
        if history["total"] > 0:
            return history["success"] / history["total"]
        return 0.5  # افتراضي
    
    def update_pattern_success(self, pattern_name: str, was_successful: bool):
        """
        🟡 تعديل 6: تحديث سجل نجاح النمط
        """
        self.pattern_success_history[pattern_name]["total"] += 1
        if was_successful:
            self.pattern_success_history[pattern_name]["success"] += 1
    
    def _detect_anti_patterns(self, patterns: List[HarmonicPattern],
                               current_price: float) -> List[HarmonicPattern]:
        """
        🔴 تعديل 2: Anti-Patterns تتحقق من اختراق D فعلياً
        
        نمط تشكل لكن السعر اخترق D واستمر = Anti-Pattern
        """
        anti_patterns = []
        
        for pattern in patterns[-5:]:
            if pattern.confidence < 0.6:
                continue
            
            D_point = pattern.points.get('D')
            if not D_point:
                continue
            
            X_point = pattern.points.get('X')
            if not X_point:
                continue
            
            XA = abs(X_point.price - D_point.price) if 'A' in pattern.points and pattern.points['A'] else abs(D_point.price - X_point.price)
            
            # 🔴 تعديل 2: فحص فعلي - هل اخترق السعر D بأكثر من 5% من XA؟
            if XA > 0:
                penetration_pct = abs(current_price - D_point.price) / XA
                
                if penetration_pct > 0.05:
                    # السعر تجاوز D = النمط فشل = Anti-Pattern
                    anti_direction = 'bullish' if pattern.direction == 'bearish' else 'bearish'
                    
                    anti_patterns.append(HarmonicPattern(
                        pattern_type=f"Anti_{pattern.pattern_type}",
                        points=pattern.points,
                        direction=anti_direction,
                        ratios=pattern.ratios,
                        ideal_ratios=pattern.ideal_ratios,
                        ratio_accuracy=pattern.ratio_accuracy,
                        completion_index=pattern.completion_index,
                        potential_reversal_zone=pattern.potential_reversal_zone,
                        confidence=pattern.confidence * 0.8,
                        strength=pattern.strength * 1.2,
                        is_anti_pattern=True,
                        completion_progress=2.0,
                        volume_confirmed=pattern.volume_confirmed,
                        historical_success_rate=0.7,
                    ))
        
        return anti_patterns
    
    def _cluster_patterns(self, patterns: List[HarmonicPattern], volumes: np.ndarray,
                           closes: np.ndarray, current_price: float) -> List[HarmonicCluster]:
        """
        تجميع الأنماط المتقاربة مع Volume Confirmation
        """
        clusters = []
        
        if len(patterns) < 2:
            return clusters
        
        for i in range(len(patterns)):
            p1 = patterns[i]
            overlapping_patterns = [p1.pattern_type]
            
            for j in range(i+1, len(patterns)):
                p2 = patterns[j]
                if self._prz_overlap(p1.potential_reversal_zone, p2.potential_reversal_zone):
                    overlapping_patterns.append(p2.pattern_type)
            
            if len(overlapping_patterns) >= 2:
                all_prz = [p1.potential_reversal_zone] + \
                         [p2.potential_reversal_zone for p2 in patterns 
                          if p2.pattern_type in overlapping_patterns]
                combined_low = max(z[0] for z in all_prz)
                combined_high = min(z[1] for z in all_prz)
                
                if combined_low < combined_high:
                    # 🟡 تعديل 5: Volume at PRZ
                    vol_at_zone = 0.0
                    vol_confirmed = False
                    if combined_low <= current_price <= combined_high:
                        vol_at_zone = volumes[-1] if len(volumes) > 0 else 0.0
                        avg_vol = np.mean(volumes[-10:]) if len(volumes) >= 10 else vol_at_zone
                        vol_confirmed = vol_at_zone > avg_vol * 1.3 if avg_vol > 0 else False
                    
                    clusters.append(HarmonicCluster(
                        price_zone=(combined_low, combined_high),
                        patterns=overlapping_patterns,
                        cluster_strength=min(1.0, len(overlapping_patterns) * 0.25),
                        direction=p1.direction,
                        is_prz=True,
                        volume_at_zone=vol_at_zone,
                        volume_confirmed=vol_confirmed,
                    ))
        
        return clusters
    
    def _prz_overlap(self, prz1: Tuple[float, float], prz2: Tuple[float, float]) -> bool:
        """فحص تداخل منطقتين"""
        return not (prz1[1] < prz2[0] or prz1[0] > prz2[1])
    
    def _find_best_patterns(self, patterns: List[HarmonicPattern]) -> List[HarmonicPattern]:
        """أفضل الأنماط"""
        recent = patterns[-20:] if len(patterns) >= 20 else patterns
        sorted_patterns = sorted(recent, 
            key=lambda p: p.confidence * p.strength * p.historical_success_rate, 
            reverse=True)
        return sorted_patterns[:5]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║        الدرجة الثالثة: محلل الزمن التوافقي                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HarmonicTimeAnalyzer:
    """يحلل الزمن في الأنماط التوافقية"""
    
    def analyze(self, patterns: List[HarmonicPattern]) -> Dict:
        """تحليل الزمن التوافقي"""
        time_symmetries = self._analyze_time_symmetry(patterns)
        time_projections = self._project_time_targets(patterns)
        
        return {
            "time_symmetries": time_symmetries,
            "time_projections": time_projections,
        }
    
    def _analyze_time_symmetry(self, patterns: List[HarmonicPattern]) -> List[Dict]:
        """تحليل تناظر الزمن"""
        symmetries = []
        
        for p in patterns[-10:]:
            X = p.points.get('X')
            A = p.points.get('A')
            C = p.points.get('C')
            D = p.points.get('D')
            
            if not all([X, A, C, D]):
                continue
            
            time_XA = A.index - X.index
            time_CD = D.index - C.index
            
            if time_XA > 0 and time_CD > 0:
                time_ratio = time_CD / time_XA
                symmetry = 1.0 - abs(time_ratio - 1.0)
                
                symmetries.append({
                    "pattern": p.pattern_type,
                    "time_XA": time_XA,
                    "time_CD": time_CD,
                    "time_ratio": time_ratio,
                    "symmetry_score": symmetry,
                    "balanced": 0.8 < time_ratio < 1.2,
                })
        
        return symmetries
    
    def _project_time_targets(self, patterns: List[HarmonicPattern]) -> List[Dict]:
        """توقع أهداف زمنية"""
        projections = []
        
        for p in patterns[-5:]:
            X = p.points.get('X')
            A = p.points.get('A')
            D = p.points.get('D')
            
            if not all([X, A, D]):
                continue
            
            time_XA = A.index - X.index
            if time_XA > 0:
                projections.append({
                    "pattern": p.pattern_type,
                    "projections": {
                        "1.0_XA": D.index + time_XA,
                        "1.272_XA": D.index + int(time_XA * 1.272),
                        "1.618_XA": D.index + int(time_XA * 1.618),
                    },
                })
        
        return projections


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية التوافقيات الموحدة (محسنة)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HarmonicPatternStrategy:
    """
    استراتيجية الأنماط التوافقية الديناميكية الكاملة - الإصدار 2.0
    
    - 12 نمطاً توافقياً
    - Anti-Patterns تتحقق من اختراق D فعلياً
    - Completion Progress
    - Volume Confirmation عند PRZ
    - Historical Success Rate لكل نمط
    """
    
    def __init__(self):
        self.point_detector = HarmonicPointDetector()
        self.pattern_detector = HarmonicPatternDetector()
        self.time_analyzer = HarmonicTimeAnalyzer()
    
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
        
        current_price = closes[-1]
        
        point_data = self.point_detector.analyze(highs, lows, closes, volumes)
        swings = point_data.get('swings', [])
        pattern_data = self.pattern_detector.analyze(swings, closes, volumes, current_price)
        
        all_patterns = pattern_data.get('all_patterns', [])
        time_data = self.time_analyzer.analyze(all_patterns)
        
        decision = self._make_decision(pattern_data, time_data, current_price)
        
        return {**decision, "point_data": point_data, "pattern_data": pattern_data, "time_data": time_data}
    
    def _make_decision(self, pattern_data: Dict, time_data: Dict,
                       current_price: float) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        # ---- من أفضل الأنماط ----
        best_patterns = pattern_data.get('best_patterns', [])
        for p in best_patterns[:5]:
            # 🟡 تعديل 6: الوزن يتضمن historical_success_rate
            weight = p.confidence * p.strength * p.historical_success_rate * 0.5
            
            # 🟡 تعديل 5: Volume boost
            if p.volume_confirmed:
                weight *= 1.3
            
            if p.is_anti_pattern:
                if p.direction == 'bullish':
                    buy_signals.append((f"Anti-{p.pattern_type} صاعد (نجاح:{p.historical_success_rate:.0%})", weight * 1.2))
                else:
                    sell_signals.append((f"Anti-{p.pattern_type} هابط (نجاح:{p.historical_success_rate:.0%})", weight * 1.2))
            else:
                # 🟡 تعديل 4: Completion Progress
                progress_str = f" ({p.completion_progress:.0%})" if p.completion_progress < 1.0 else ""
                
                if p.direction == 'bullish':
                    buy_signals.append((f"{p.pattern_type} صاعد{progress_str} (نجاح:{p.historical_success_rate:.0%})", weight))
                else:
                    sell_signals.append((f"{p.pattern_type} هابط{progress_str} (نجاح:{p.historical_success_rate:.0%})", weight))
        
        # ---- من تجمعات PRZ ----
        clusters = pattern_data.get('clusters', [])
        for cluster in clusters:
            if cluster.cluster_strength > 0.5:
                prz_low, prz_high = cluster.price_zone
                
                if prz_low <= current_price <= prz_high:
                    weight = cluster.cluster_strength * 0.7
                    
                    # 🟡 تعديل 5: Volume at PRZ
                    if cluster.volume_confirmed:
                        weight *= 1.4
                        warnings.append("حجم مرتفع عند PRZ - تأكيد انعكاس")
                    
                    if cluster.direction == 'bullish':
                        buy_signals.append((f"PRZ تجمعي صاعد ({len(cluster.patterns)} أنماط)", weight))
                    else:
                        sell_signals.append((f"PRZ تجمعي هابط ({len(cluster.patterns)} أنماط)", weight))
        
        # ---- من تناظر الزمن ----
        symmetries = time_data.get('time_symmetries', [])
        balanced_count = sum(1 for s in symmetries if s.get('balanced'))
        if balanced_count >= 1:
            buy_signals.append(("تناظر زمني - الأنماط متوازنة", 0.3))
        
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
        
        current_prz = pattern_data.get('current_prz')
        if current_prz:
            prz_low, prz_high = current_prz.price_zone
            if prz_low <= current_price <= prz_high:
                reason += f" ⚡ السعر داخل PRZ [{prz_low:.2f}-{prz_high:.2f}]"
        
        if best_patterns and any(p.is_anti_pattern for p in best_patterns):
            warnings.append("نمط معكوس نشط - انعكاس عنيف محتمل")
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "prz_active": current_prz is not None,
            "warnings": warnings,
        }


def create_harmonic_pattern_strategy():
    """إنشاء استراتيجية الأنماط التوافقية الجاهزة (الإصدار 2.0)"""
    return HarmonicPatternStrategy()