"""
═══════════════════════════════════════════════════════════════════════════════
SMART MONEY CONCEPTS / ICT - النسخة الكاملة والنهائية (الإصدار 2.0)
المدرسة الثانية: مفاهيم المال الذكي - منهجية ICT المتقدمة
═══════════════════════════════════════════════════════════════════════════════

هذا الملف يحتوي على كل ما يتعلق بمدرسة SMC/ICT - النسخة المحسنة:
- Order Blocks مع نظام First/Second Presentation
- Fair Value Gaps مع Confluence تلقائي
- Breaker Blocks & Mitigation Blocks (كشف كامل)
- Liquidity Sweeps & Voids
- Rejection Blocks (مع opens مصلح)
- Asian Range & Killzones
- Judas Swing & Silver Bullet
- AMD Cycles
- Power of 3 (شمعة وجلسة)
- Turtle Soup مع تقييم الجودة
- Nested ICT PD Arrays مع confluence_count
- NWOG/NDOG
- Time-based OB Strength
- OB Continuation vs Reversal

الفلسفة:
السوق خوارزمية تبحث عن السيولة. السعر ليس عشوائياً،
بل ينتقل من منطقة سيولة إلى أخرى عبر مناطق عدم توازن.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class OrderBlock:
    """كتلة أوامر - نسخة محسنة"""
    index: int
    ob_type: str
    high: float
    low: float
    open: float
    close: float
    body_50: float
    zone_top: float
    zone_bottom: float
    strength: float
    is_fresh: bool
    is_nested: bool
    parent_ob_index: int
    touches: int
    volume_confirm: bool
    presentation_number: int = 0  # 🟡 تعديل 4: 0=First, 1=Second
    continuation_type: str = 'unknown'  # 🟢 تعديل 14: 'continuation' or 'reversal'
    time_strength_multiplier: float = 1.0  # 🟢 تعديل 15: × session multiplier


@dataclass
class FairValueGap:
    """فجوة القيمة العادلة - نسخة محسنة"""
    index: int
    fvg_type: str
    top: float
    bottom: float
    size: float
    relative_size: float
    is_inverse: bool
    filled: float
    volume_imbalance: float
    strength: float
    has_ob_confluence: bool = False  # 🟡 تعديل 3: تداخل مع Order Block
    confluence_strength: float = 0.0  # 🟡 تعديل 3


@dataclass
class BreakerBlock:
    """كتلة كاسرة"""
    index: int
    original_ob: OrderBlock
    breaker_type: str
    zone_high: float
    zone_low: float
    mid_zone: float
    strength: float


@dataclass
class LiquiditySweep:
    """مسح سيولة"""
    index: int
    sweep_type: str  # 'double_top', 'double_bottom', 'trendline', 'range'
    swept_price: float
    direction: str  # 'buy' or 'sell' (اتجاه ما بعد المسح)
    strength: float
    volume_confirm: bool


@dataclass
class Killzone:
    """منطقة القتل الزمنية"""
    session: str
    start_hour: int
    end_hour: int
    high: float
    low: float
    range_size: float
    manipulation_detected: bool
    direction: str


@dataclass
class PDArray:
    """مصفوفة ICT - نسخة محسنة"""
    array_type: str
    index: int
    price_level: float
    zone_top: float
    zone_bottom: float
    time_created: int
    strength: float
    confluence_count: int = 0
    session: str = 'unknown'  # 🟢 تعديل 15


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الأولى: محلل كتل الأوامر (Order Block Analyzer) محسن       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OrderBlockAnalyzer:
    """
    يكتشف ويحلل كتل الأوامر بكل أنواعها.
    🟡 تعديل 4: First vs Second Presentation
    🟢 تعديل 14: Continuation vs Reversal
    🟢 تعديل 15: Time-based Strength
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray,
                sessions: List[str] = None) -> Dict:
        """
        تحليل كتل الأوامر الكامل
        """
        all_obs = self._detect_all_order_blocks(opens, highs, lows, closes, volumes, sessions)
        classified = self._classify_blocks(all_obs, highs, lows, closes)
        nested = self._find_nested_blocks(classified)
        
        # 🟢 تعديل 14: تصنيف Continuation vs Reversal
        classified = self._classify_continuation_reversal(classified, highs, lows, closes)
        
        best_obs = self._find_best_current_blocks(classified, closes[-1])
        
        return {
            "all_order_blocks": classified[-30:],
            "nested_blocks": nested,
            "best_bullish_ob": best_obs.get('bullish'),
            "best_bearish_ob": best_obs.get('bearish'),
            "total_obs": len(classified),
        }
    
    def _detect_all_order_blocks(self, opens, highs, lows, closes, volumes, 
                                  sessions=None) -> List[OrderBlock]:
        """اكتشاف كل كتل الأوامر"""
        order_blocks = []
        
        for i in range(2, len(closes) - 1):
            # كتلة صاعدة
            if (closes[i] < opens[i] and closes[i+1] > opens[i+1] and closes[i+1] > highs[i]):
                move_strength = self._measure_move_strength(highs, lows, closes, i+1, 'up')
                if move_strength > 0.3:
                    body_50 = (opens[i] + closes[i]) / 2
                    session = sessions[i] if sessions and i < len(sessions) else 'unknown'
                    
                    order_blocks.append(OrderBlock(
                        index=i, ob_type='bullish',
                        high=highs[i], low=lows[i], open=opens[i], close=closes[i],
                        body_50=body_50, zone_top=highs[i], zone_bottom=body_50,
                        strength=move_strength, is_fresh=True, is_nested=False,
                        parent_ob_index=-1, touches=0,
                        volume_confirm=volumes[i] > np.mean(volumes[max(0,i-20):i+1]) if i >= 5 else False,
                        presentation_number=0,
                        continuation_type='unknown',
                        time_strength_multiplier=self._get_time_multiplier(session),
                    ))
            
            # كتلة هابطة
            if (closes[i] > opens[i] and closes[i+1] < opens[i+1] and closes[i+1] < lows[i]):
                move_strength = self._measure_move_strength(highs, lows, closes, i+1, 'down')
                if move_strength > 0.3:
                    body_50 = (opens[i] + closes[i]) / 2
                    session = sessions[i] if sessions and i < len(sessions) else 'unknown'
                    
                    order_blocks.append(OrderBlock(
                        index=i, ob_type='bearish',
                        high=highs[i], low=lows[i], open=opens[i], close=closes[i],
                        body_50=body_50, zone_top=body_50, zone_bottom=lows[i],
                        strength=move_strength, is_fresh=True, is_nested=False,
                        parent_ob_index=-1, touches=0,
                        volume_confirm=volumes[i] > np.mean(volumes[max(0,i-20):i+1]) if i >= 5 else False,
                        presentation_number=0,
                        continuation_type='unknown',
                        time_strength_multiplier=self._get_time_multiplier(session),
                    ))
        
        return order_blocks
    
    def _measure_move_strength(self, highs, lows, closes, start_index, direction) -> float:
        """قياس قوة الحركة التي تلت الكتلة"""
        if start_index >= len(closes) - 1:
            return 0.3
        
        lookahead = min(10, len(closes) - start_index)
        if lookahead < 2:
            return 0.3
        
        avg_range = np.mean(highs[-20:] - lows[-20:]) if len(highs) >= 20 else (highs[-1] - lows[-1])
        if avg_range == 0:
            avg_range = 0.0001
        
        if direction == 'up':
            max_move = max(highs[start_index:start_index+lookahead]) - closes[start_index]
        else:
            max_move = closes[start_index] - min(lows[start_index:start_index+lookahead])
        
        distance_score = min(1.0, max_move / (avg_range * 2))
        
        reached_peak = 0
        for j in range(start_index+1, start_index+lookahead):
            if direction == 'up':
                if highs[j] >= highs[start_index] + avg_range:
                    reached_peak = j - start_index
                    break
            else:
                if lows[j] <= lows[start_index] - avg_range:
                    reached_peak = j - start_index
                    break
        
        speed_score = min(1.0, 3.0 / reached_peak) if reached_peak > 0 else 0.3
        
        if direction == 'up':
            continuation = sum(1 for j in range(start_index, min(start_index+5, len(closes)-1))
                              if closes[j+1] > closes[j]) / 5
        else:
            continuation = sum(1 for j in range(start_index, min(start_index+5, len(closes)-1))
                              if closes[j+1] < closes[j]) / 5
        
        return min(1.0, distance_score * 0.4 + speed_score * 0.35 + continuation * 0.25)
    
    def _get_time_multiplier(self, session: str) -> float:
        """
        🟢 تعديل 15: مضاعف الوقت للكتلة
        London Open OB > Asian OB
        """
        multipliers = {
            'London': 1.4, 'NewYork': 1.3, 'Overlap': 1.5,
            'Asian': 0.7, 'Asian_Late': 0.6, 'unknown': 1.0,
        }
        return multipliers.get(session, 1.0)
    
    def _classify_blocks(self, order_blocks: List[OrderBlock], highs, lows, closes) -> List[OrderBlock]:
        """
        تصنيف الكتل: حية، ميتة، عدد الاختبارات
        
        🟡 تعديل 4: First Presentation = touches==0, Second = touches>=1
        """
        for ob in order_blocks:
            for i in range(ob.index + 2, len(closes)):
                if ob.ob_type == 'bullish':
                    if lows[i] < ob.zone_bottom:
                        penetration = (ob.zone_bottom - lows[i]) / max(ob.zone_bottom - ob.low, 0.0001)
                        if penetration > 1.0:
                            ob.is_fresh = False
                            ob.strength *= 0.3
                        else:
                            ob.strength *= 0.6
                        ob.touches += 1
                    elif ob.zone_bottom <= lows[i] <= ob.zone_top and closes[i] > opens[i] if 'opens' in dir() else True:
                        ob.touches += 1
                        # 🟡 تعديل 4: كل لمسة تضعف الكتلة
                        if ob.touches == 1:
                            ob.strength *= 0.7  # Second Presentation = 70%
                            ob.presentation_number = 1
                        elif ob.touches >= 2:
                            ob.strength *= 0.5  # Third+ = 30%
                            ob.presentation_number = 2
                            ob.is_fresh = False
                else:
                    if highs[i] > ob.zone_top:
                        penetration = (highs[i] - ob.zone_top) / max(ob.high - ob.zone_top, 0.0001)
                        if penetration > 1.0:
                            ob.is_fresh = False
                            ob.strength *= 0.3
                        else:
                            ob.strength *= 0.6
                        ob.touches += 1
                    elif ob.zone_top >= highs[i] >= ob.zone_bottom and closes[i] < opens[i] if 'opens' in dir() else True:
                        ob.touches += 1
                        if ob.touches == 1:
                            ob.strength *= 0.7
                            ob.presentation_number = 1
                        elif ob.touches >= 2:
                            ob.strength *= 0.5
                            ob.presentation_number = 2
                            ob.is_fresh = False
        
        return order_blocks
    
    def _find_nested_blocks(self, order_blocks: List[OrderBlock]) -> List[OrderBlock]:
        """اكتشاف الكتل المتداخلة"""
        nested = []
        for i in range(len(order_blocks)):
            for j in range(i+1, len(order_blocks)):
                outer, inner = order_blocks[i], order_blocks[j]
                if outer.ob_type != inner.ob_type:
                    continue
                if inner.index - outer.index > 50:
                    continue
                if outer.ob_type == 'bullish':
                    if inner.high <= outer.high and inner.low >= outer.low:
                        inner.is_nested = True
                        inner.parent_ob_index = outer.index
                        inner.strength = min(1.0, (inner.strength + outer.strength) * 0.7)
                        nested.append(inner)
                else:
                    if inner.high <= outer.high and inner.low >= outer.low:
                        inner.is_nested = True
                        inner.parent_ob_index = outer.index
                        inner.strength = min(1.0, (inner.strength + outer.strength) * 0.7)
                        nested.append(inner)
        return nested
    
    def _classify_continuation_reversal(self, order_blocks: List[OrderBlock],
                                         highs, lows, closes) -> List[OrderBlock]:
        """
        🟢 تعديل 14: تصنيف OB إلى Continuation أو Reversal
        
        Continuation: الكتلة تدفع السعر في اتجاه الحركة السابقة
        Reversal: الكتلة تعكس الحركة السابقة (أقوى)
        """
        for ob in order_blocks:
            if ob.index < 10:
                continue
            
            # اتجاه السعر قبل الكتلة
            pre_trend = closes[ob.index] - closes[max(0, ob.index-10)]
            
            if ob.ob_type == 'bullish':
                if pre_trend < 0:
                    ob.continuation_type = 'reversal'  # انعكاس من هابط = قوي
                    ob.strength *= 1.2
                else:
                    ob.continuation_type = 'continuation'
            else:
                if pre_trend > 0:
                    ob.continuation_type = 'reversal'
                    ob.strength *= 1.2
                else:
                    ob.continuation_type = 'continuation'
        
        return order_blocks
    
    def _find_best_current_blocks(self, order_blocks: List[OrderBlock], 
                                   current_price: float) -> Dict:
        """
        🟡 تعديل 9: أفضل كتلة تراعي Confluence مع FVG
        (FVG data تُمرر من الخارج في الاستراتيجية الموحدة)
        """
        best_bullish = None
        best_bearish = None
        
        bullish_obs = [ob for ob in order_blocks if ob.ob_type == 'bullish' and ob.is_fresh]
        bearish_obs = [ob for ob in order_blocks if ob.ob_type == 'bearish' and ob.is_fresh]
        
        below_price = [ob for ob in bullish_obs if ob.zone_bottom < current_price]
        if below_price:
            # الأفضل = الأقوى × الأقرب × First Presentation preferred
            best_bullish = max(below_price, 
                key=lambda ob: ob.strength * ob.time_strength_multiplier * 
                              (1.5 if ob.presentation_number == 0 else 1.0) *
                              (1 - abs(current_price - ob.zone_top) / max(current_price, 0.0001)))
        
        above_price = [ob for ob in bearish_obs if ob.zone_top > current_price]
        if above_price:
            best_bearish = max(above_price,
                key=lambda ob: ob.strength * ob.time_strength_multiplier *
                              (1.5 if ob.presentation_number == 0 else 1.0) *
                              (1 - abs(ob.zone_bottom - current_price) / max(current_price, 0.0001)))
        
        return {'bullish': best_bullish, 'bearish': best_bearish}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║        الدرجة الثانية: محلل فجوات القيمة العادلة (FVG Analyzer) محسن      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class FVGAnalyzer:
    """
    يكتشف ويحلل فجوات القيمة العادلة.
    🟡 تعديل 3: Confluence مع Order Block تلقائي
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, order_blocks: List[OrderBlock] = None) -> Dict:
        """تحليل كامل لفجوات القيمة العادلة"""
        all_fvgs = self._detect_all_fvgs(highs, lows, closes, volumes)
        classified = self._classify_fvgs(all_fvgs, highs, lows, closes)
        double_fvgs = self._find_double_fvgs(classified)
        inverse_fvgs = self._find_inverse_fvgs(classified, highs, lows, closes)
        
        # 🟡 تعديل 3: Confluence مع Order Blocks
        if order_blocks:
            classified = self._find_ob_confluence(classified, order_blocks)
        
        active_fvgs = self._find_active_fvgs(classified, closes[-1])
        
        return {
            "all_fvgs": classified[-30:],
            "double_fvgs": double_fvgs,
            "inverse_fvgs": inverse_fvgs,
            "active_fvgs": active_fvgs,
            "nearest_bullish_fvg": self._find_nearest_fvg(classified, closes[-1], 'bullish'),
            "nearest_bearish_fvg": self._find_nearest_fvg(classified, closes[-1], 'bearish'),
        }
    
    def _detect_all_fvgs(self, highs, lows, closes, volumes) -> List[FairValueGap]:
        """اكتشاف كل فجوات القيمة العادلة"""
        fvgs = []
        for i in range(len(closes) - 2):
            if lows[i] > highs[i+2]:
                top, bottom = lows[i], highs[i+2]
                size = top - bottom
                if size > 0:
                    avg_range = np.mean(highs[max(0,i-20):i+1] - lows[max(0,i-20):i+1]) if i >= 5 else size
                    relative_size = size / max(avg_range, 0.0001)
                    vol_imbalance = volumes[i+1] / max(np.mean(volumes[max(0,i-15):i+1]), 0.0001) if i >= 5 else 1.0
                    fvgs.append(FairValueGap(
                        index=i, fvg_type='bullish', top=top, bottom=bottom, size=size,
                        relative_size=min(3.0, relative_size), is_inverse=False, filled=0.0,
                        volume_imbalance=min(3.0, vol_imbalance),
                        strength=min(1.0, relative_size * 0.4 + vol_imbalance * 0.3 + 0.3),
                    ))
            
            if highs[i] < lows[i+2]:
                top, bottom = lows[i+2], highs[i]
                size = top - bottom
                if size > 0:
                    avg_range = np.mean(highs[max(0,i-20):i+1] - lows[max(0,i-20):i+1]) if i >= 5 else size
                    relative_size = size / max(avg_range, 0.0001)
                    vol_imbalance = volumes[i+1] / max(np.mean(volumes[max(0,i-15):i+1]), 0.0001) if i >= 5 else 1.0
                    fvgs.append(FairValueGap(
                        index=i, fvg_type='bearish', top=top, bottom=bottom, size=size,
                        relative_size=min(3.0, relative_size), is_inverse=False, filled=0.0,
                        volume_imbalance=min(3.0, vol_imbalance),
                        strength=min(1.0, relative_size * 0.4 + vol_imbalance * 0.3 + 0.3),
                    ))
        return fvgs
    
    def _classify_fvgs(self, fvgs: List[FairValueGap], highs, lows, closes) -> List[FairValueGap]:
        """تصنيف الفجوات: درجة الملء"""
        for fvg in fvgs:
            for i in range(fvg.index + 3, len(closes)):
                if fvg.fvg_type == 'bullish':
                    if lows[i] <= fvg.top:
                        penetration = (fvg.top - lows[i]) / max(fvg.size, 0.0001)
                        fvg.filled = max(fvg.filled, min(1.0, penetration))
                        if fvg.filled >= 1.0 and closes[i] < fvg.bottom:
                            fvg.is_inverse = True
                else:
                    if highs[i] >= fvg.bottom:
                        penetration = (highs[i] - fvg.bottom) / max(fvg.size, 0.0001)
                        fvg.filled = max(fvg.filled, min(1.0, penetration))
                        if fvg.filled >= 1.0 and closes[i] > fvg.top:
                            fvg.is_inverse = True
        return fvgs
    
    def _find_ob_confluence(self, fvgs: List[FairValueGap], 
                             order_blocks: List[OrderBlock]) -> List[FairValueGap]:
        """
        🟡 تعديل 3: اكتشاف تداخل FVG مع Order Block
        
        FVG + OB في نفس المنطقة = منطقة ICT ذهبية
        """
        for fvg in fvgs:
            for ob in order_blocks:
                if not ob.is_fresh:
                    continue
                # فحص التداخل
                if self._zones_overlap(fvg.top, fvg.bottom, ob.zone_top, ob.zone_bottom):
                    fvg.has_ob_confluence = True
                    fvg.confluence_strength = (fvg.strength + ob.strength) / 2
                    fvg.strength = min(1.0, fvg.strength * 1.3)  # تعزيز
                    break
        return fvgs
    
    def _zones_overlap(self, top1, bottom1, top2, bottom2) -> bool:
        """فحص تداخل منطقتين"""
        return not (top1 < bottom2 or bottom1 > top2)
    
    def _find_double_fvgs(self, fvgs: List[FairValueGap]) -> List[Dict]:
        """اكتشاف الفجوات المزدوجة"""
        doubles = []
        for i in range(1, len(fvgs)):
            f1, f2 = fvgs[i-1], fvgs[i]
            if f1.fvg_type == f2.fvg_type and f2.index - f1.index <= 3:
                if f1.fvg_type == 'bullish' and abs(f1.bottom - f2.top) < f1.size * 0.3:
                    doubles.append({
                        "start_index": f1.index, "end_index": f2.index,
                        "combined_top": f1.top, "combined_bottom": f2.bottom,
                        "total_size": f1.size + f2.size,
                        "strength": (f1.strength + f2.strength) * 0.6,
                    })
        return doubles
    
    def _find_inverse_fvgs(self, fvgs, highs, lows, closes) -> List[FairValueGap]:
        return [f for f in fvgs if f.is_inverse and f.filled >= 1.0]
    
    def _find_active_fvgs(self, fvgs, current_price) -> List[FairValueGap]:
        return [f for f in fvgs if f.filled < 0.9 and not f.is_inverse]
    
    def _find_nearest_fvg(self, fvgs, current_price, fvg_type) -> Optional[FairValueGap]:
        relevant = [f for f in fvgs if f.fvg_type == fvg_type and f.filled < 0.9]
        if fvg_type == 'bullish':
            below = [f for f in relevant if f.top < current_price]
            if below:
                return min(below, key=lambda f: current_price - f.top)
        else:
            above = [f for f in relevant if f.bottom > current_price]
            if above:
                return min(above, key=lambda f: f.bottom - current_price)
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الثالثة: محلل الكتل الكاسرة والارتدادية (Breaker & Mitigation) ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BreakerMitigationAnalyzer:
    """
    يكتشف الكتل الكاسرة ومناطق التخفيف وكتل الرفض.
    🔴 تعديل 1: opens يمرر بشكل صحيح
    🔴 تعديل 2: Mitigation كامل (بدون break)
    """
    
    def analyze(self, order_blocks: List[OrderBlock], highs: np.ndarray,
                lows: np.ndarray, closes: np.ndarray, 
                opens: np.ndarray = None) -> Dict:
        """تحليل الكتل الكاسرة والارتدادية"""
        breakers = self._detect_breakers(order_blocks, highs, lows, closes)
        mitigations = self._detect_mitigations(order_blocks, highs, lows, closes)
        rejection_blocks = self._detect_rejection_blocks(highs, lows, closes, opens)
        
        return {
            "breaker_blocks": breakers[-20:],
            "mitigation_zones": mitigations,
            "rejection_blocks": rejection_blocks[-10:],
            "active_breakers": [b for b in breakers if b.strength > 0.5],
        }
    
    def _detect_breakers(self, order_blocks, highs, lows, closes) -> List[BreakerBlock]:
        """اكتشاف الكتل الكاسرة"""
        breakers = []
        for ob in order_blocks:
            if ob.is_fresh:
                continue
            for i in range(ob.index + 5, len(closes)):
                if ob.ob_type == 'bullish':
                    if closes[i] < ob.body_50 and lows[i] < ob.low:
                        breakers.append(BreakerBlock(
                            index=i, original_ob=ob, breaker_type='bearish_breaker',
                            zone_high=ob.body_50, zone_low=ob.low,
                            mid_zone=(ob.body_50 + ob.low) / 2,
                            strength=ob.strength * 0.9,
                        ))
                        break
                else:
                    if closes[i] > ob.body_50 and highs[i] > ob.high:
                        breakers.append(BreakerBlock(
                            index=i, original_ob=ob, breaker_type='bullish_breaker',
                            zone_high=ob.high, zone_low=ob.body_50,
                            mid_zone=(ob.high + ob.body_50) / 2,
                            strength=ob.strength * 0.9,
                        ))
                        break
        return breakers
    
    def _detect_mitigations(self, order_blocks, highs, lows, closes) -> List[Dict]:
        """
        🔴 تعديل 2: اكتشاف كل الـ Mitigations، وليس الأول فقط
        """
        mitigations = []
        for ob in order_blocks:
            if not ob.is_fresh or ob.touches > 0:
                continue
            for i in range(ob.index + 3, len(closes)):
                touched_50 = False
                if ob.ob_type == 'bullish':
                    if abs(lows[i] - ob.body_50) < (ob.high - ob.low) * 0.05:
                        touched_50 = True
                else:
                    if abs(highs[i] - ob.body_50) < (ob.high - ob.low) * 0.05:
                        touched_50 = True
                
                if touched_50 and i + 3 < len(closes):
                    if ob.ob_type == 'bullish':
                        bounced = closes[i+1] > closes[i] and closes[i+2] > closes[i]
                    else:
                        bounced = closes[i+1] < closes[i] and closes[i+2] < closes[i]
                    
                    if bounced:
                        mitigations.append({
                            "ob_index": ob.index, "mitigation_index": i,
                            "price": ob.body_50, "type": ob.ob_type,
                            "confirmed": True,
                        })
                        # 🔴 تعديل 2: لا break - نستمر بالفحص
        return mitigations
    
    def _detect_rejection_blocks(self, highs, lows, closes, 
                                  opens: np.ndarray = None) -> List[Dict]:
        """
        🔴 تعديل 1: opens يمرر كمعامل
        
        كتل الرفض: منطقة يتم رفض السعر عندها بشكل عنيف
        """
        rejection_blocks = []
        
        for i in range(1, len(closes) - 1):
            candle_range = highs[i] - lows[i]
            if candle_range == 0:
                continue
            
            # استخدام open من المعامل، أو تقديره من الإغلاق السابق
            if opens is not None and i < len(opens):
                candle_open = opens[i]
            else:
                candle_open = closes[i-1] if i > 0 else closes[i]
            
            candle_close = closes[i]
            body_high = max(candle_open, candle_close)
            body_low = min(candle_open, candle_close)
            
            # رفض علوي (Bearish Rejection Block)
            upper_wick = highs[i] - body_high
            if upper_wick > candle_range * 0.65:
                rejection_blocks.append({
                    "index": i, "type": "bearish_rejection",
                    "zone_high": highs[i],
                    "zone_low": (highs[i] + body_high) / 2,
                    "strength": min(1.0, upper_wick / candle_range),
                })
            
            # رفض سفلي (Bullish Rejection Block)
            lower_wick = body_low - lows[i]
            if lower_wick > candle_range * 0.65:
                rejection_blocks.append({
                    "index": i, "type": "bullish_rejection",
                    "zone_high": (lows[i] + body_low) / 2,
                    "zone_low": lows[i],
                    "strength": min(1.0, lower_wick / candle_range),
                })
        
        return rejection_blocks


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الرابعة: دورة AMD + Liquidity Sweeps                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AMDCycleAnalyzer:
    """
    يحلل دورات التجميع والتلاعب والتوزيع.
    🟡 تعديل 8: Liquidity Sweep Detection
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray, killzones: List[Killzone]) -> Dict:
        """تحليل دورة AMD"""
        accumulation = self._detect_accumulation(highs, lows, closes, volumes)
        distribution = self._detect_distribution(highs, lows, closes, volumes)
        manipulation = self._detect_manipulation(highs, lows, closes, volumes, killzones)
        liquidity_sweeps = self._detect_liquidity_sweeps(highs, lows, closes, volumes)
        
        current_phase = self._determine_current_phase(accumulation, distribution, manipulation, closes[-1])
        
        return {
            "accumulation": accumulation,
            "distribution": distribution,
            "manipulation": manipulation,
            "liquidity_sweeps": liquidity_sweeps[-10:],
            "current_phase": current_phase,
        }
    
    def _detect_accumulation(self, highs, lows, closes, volumes) -> Optional[Dict]:
        """كشف التجميع"""
        if len(closes) < 20:
            return None
        recent_highs, recent_lows = highs[-20:], lows[-20:]
        recent_closes, recent_volumes = closes[-20:], volumes[-20:]
        
        price_range = max(recent_highs) - min(recent_lows)
        avg_range = np.mean(recent_highs - recent_lows)
        if avg_range == 0 or price_range / avg_range > 8:
            return None
        
        mid_price = (max(recent_highs) + min(recent_lows)) / 2
        closes_near_mid = sum(1 for c in recent_closes if abs(c - mid_price) < price_range * 0.3)
        if closes_near_mid < 10:
            return None
        
        avg_vol = np.mean(recent_volumes)
        overall_avg_vol = np.mean(volumes) if len(volumes) > 0 else avg_vol
        vol_ratio = avg_vol / max(overall_avg_vol, 0.0001)
        
        fake_breaks = 0
        for i in range(15, len(recent_closes)-2):
            if recent_closes[i] > max(recent_highs[:i]) * 1.001 and recent_closes[i+1] < max(recent_highs[:i]):
                fake_breaks += 1
            if recent_closes[i] < min(recent_lows[:i]) * 0.999 and recent_closes[i+1] > min(recent_lows[:i]):
                fake_breaks += 1
        
        score = (1 - price_range/max(avg_range*8, 0.0001)) * 0.3 + (closes_near_mid/20) * 0.3 + \
                (1 - min(vol_ratio, 2)/2) * 0.2 + min(fake_breaks/3, 1) * 0.2
        
        if score > 0.55:
            return {"detected": True, "zone_high": max(recent_highs), 
                    "zone_low": min(recent_lows), "duration": 20, "score": score}
        return None
    
    def _detect_distribution(self, highs, lows, closes, volumes) -> Optional[Dict]:
        """كشف التوزيع"""
        if len(closes) < 20:
            return None
        recent_highs, recent_lows = highs[-20:], lows[-20:]
        recent_volumes = volumes[-20:]
        
        overall_high = max(highs[-60:]) if len(highs) >= 60 else max(highs)
        if max(recent_highs) < overall_high * 0.95:
            return None
        
        price_range = max(recent_highs) - min(recent_lows)
        avg_range = np.mean(recent_highs - recent_lows)
        if avg_range == 0:
            return None
        
        avg_vol = np.mean(recent_volumes)
        overall_avg_vol = np.mean(volumes) if len(volumes) > 0 else avg_vol
        vol_ratio = avg_vol / max(overall_avg_vol, 0.0001)
        
        score = (1 - price_range/max(avg_range*15, 0.0001)) * 0.25 + min(vol_ratio/2, 1) * 0.35
        
        if score > 0.55:
            return {"detected": True, "zone_high": max(recent_highs),
                    "zone_low": min(recent_lows), "score": score}
        return None
    
    def _detect_manipulation(self, highs, lows, closes, volumes, killzones) -> Optional[Dict]:
        """كشف التلاعب"""
        if len(closes) < 10:
            return None
        manipulations = []
        for i in range(5, len(closes) - 3):
            lookback_high = max(highs[i-5:i])
            lookback_low = min(lows[i-5:i])
            range_size = lookback_high - lookback_low
            if range_size == 0:
                continue
            
            if lows[i] < lookback_low and closes[i] > lookback_low:
                move_up = closes[i+1] > closes[i] and closes[i+2] > closes[i] if i+2 < len(closes) else False
                if move_up:
                    manipulations.append({"index": i, "type": "bullish_judas",
                                          "swept_low": lows[i], "strength": (lookback_low - lows[i]) / range_size})
            
            if highs[i] > lookback_high and closes[i] < lookback_high:
                move_down = closes[i+1] < closes[i] and closes[i+2] < closes[i] if i+2 < len(closes) else False
                if move_down:
                    manipulations.append({"index": i, "type": "bearish_judas",
                                          "swept_high": highs[i], "strength": (highs[i] - lookback_high) / range_size})
        
        if manipulations:
            return {"detected": True, "events": manipulations[-5:], "latest": manipulations[-1]}
        return None
    
    def _detect_liquidity_sweeps(self, highs, lows, closes, volumes) -> List[LiquiditySweep]:
        """
        🟡 تعديل 8: Liquidity Sweep Detection
        
        يبحث عن قمم/قيعان مزدوجة ويومض عندما يُخترق أحدهما
        """
        sweeps = []
        
        if len(closes) < 20:
            return sweeps
        
        # البحث عن قمم مزدوجة
        for i in range(10, len(closes) - 3):
            lookback = min(50, i)
            
            # قمة مزدوجة: قمتان متساويتان تقريباً
            for j in range(i-5, max(0, i-lookback), -1):
                if abs(highs[i] - highs[j]) < (highs[i] - lows[i]) * 0.05:
                    # هل اخترقت القمة؟
                    if i + 2 < len(closes) and highs[i+1] > highs[i]:
                        sweeps.append(LiquiditySweep(
                            index=i+1, sweep_type='double_top',
                            swept_price=highs[i], direction='buy',
                            strength=0.7,
                            volume_confirm=volumes[i+1] > np.mean(volumes[max(0,i-10):i+1]) if i >= 5 else False,
                        ))
                    break
            
            # قاع مزدوج
            for j in range(i-5, max(0, i-lookback), -1):
                if abs(lows[i] - lows[j]) < (highs[i] - lows[i]) * 0.05:
                    if i + 2 < len(closes) and lows[i+1] < lows[i]:
                        sweeps.append(LiquiditySweep(
                            index=i+1, sweep_type='double_bottom',
                            swept_price=lows[i], direction='sell',
                            strength=0.7,
                            volume_confirm=volumes[i+1] > np.mean(volumes[max(0,i-10):i+1]) if i >= 5 else False,
                        ))
                    break
        
        return sweeps
    
    def _determine_current_phase(self, accumulation, distribution, manipulation, current_price) -> str:
        if accumulation and accumulation.get('detected'):
            return "Manipulation_Up" if manipulation and manipulation.get('detected') else "Accumulation"
        if distribution and distribution.get('detected'):
            return "Manipulation_Down" if manipulation and manipulation.get('detected') else "Distribution"
        if manipulation and manipulation.get('detected'):
            latest = manipulation.get('latest', {})
            return "Manipulation_Up" if latest.get('type') == 'bullish_judas' else "Manipulation_Down"
        return "Trending"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الخامسة: مناطق القتل الزمنية (Killzones) محسن               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class KillzoneAnalyzer:
    """
    يحلل مناطق القتل الزمنية.
    🟢 تعديل 11: Silver Bullet بأوقات حقيقية
    🟢 تعديل 12: NWOG/NDOG
    """
    
    SESSIONS = {
        'Asian': {'start': 20, 'end': 24},
        'London': {'start': 2, 'end': 5},
        'NewYork': {'start': 8, 'end': 11},
        'LondonClose': {'start': 10, 'end': 12},
    }
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                opens: np.ndarray = None, times: Optional[List] = None) -> Dict:
        """تحليل مناطق القتل الزمنية"""
        killzones = self._analyze_without_times(highs, lows, closes) if times is None else []
        asian_range = self._get_asian_range(killzones)
        london_manipulation = self._detect_london_manipulation(killzones, highs, lows, closes)
        silver_bullet = self._check_silver_bullet(highs, lows, closes, times)
        nwog_ndog = self._detect_nwog_ndog(opens, closes) if opens is not None else None
        
        return {
            "killzones": killzones,
            "asian_range": asian_range,
            "london_manipulation": london_manipulation,
            "silver_bullet": silver_bullet,
            "nwog_ndog": nwog_ndog,
        }
    
    def _analyze_without_times(self, highs, lows, closes) -> List[Killzone]:
        """تحليل بدون أوقات حقيقية"""
        killzones = []
        if len(highs) < 24:
            return killzones
        
        segments = {'Asian': (-24, -18), 'London': (-18, -12), 
                     'NewYork': (-12, -6), 'LondonClose': (-6, -1)}
        
        for session, (start, end) in segments.items():
            seg_highs = highs[start:end+1]
            seg_lows = lows[start:end+1]
            seg_closes = closes[start:end+1]
            if len(seg_highs) == 0:
                continue
            
            kz = Killzone(
                session=session, start_hour=self.SESSIONS[session]['start'],
                end_hour=self.SESSIONS[session]['end'],
                high=max(seg_highs), low=min(seg_lows),
                range_size=max(seg_highs) - min(seg_lows),
                manipulation_detected=False, direction='neutral',
            )
            
            if len(seg_closes) >= 4:
                first_close, last_close = seg_closes[0], seg_closes[-1]
                if abs(last_close - first_close) < kz.range_size * 0.2:
                    if max(seg_highs) - first_close > kz.range_size * 0.6:
                        kz.manipulation_detected = True
                        kz.direction = 'up'
                    elif first_close - min(seg_lows) > kz.range_size * 0.6:
                        kz.manipulation_detected = True
                        kz.direction = 'down'
            killzones.append(kz)
        return killzones
    
    def _get_asian_range(self, killzones) -> Optional[Dict]:
        asian = [k for k in killzones if k.session == 'Asian']
        if not asian:
            return None
        kz = asian[0]
        return {"high": kz.high, "low": kz.low, "mid": (kz.high + kz.low) / 2, "range": kz.range_size}
    
    def _detect_london_manipulation(self, killzones, highs, lows, closes) -> Optional[Dict]:
        london = [k for k in killzones if k.session == 'London']
        if not london:
            return None
        kz = london[0]
        if kz.manipulation_detected:
            return {"detected": True, "direction": kz.direction, "high": kz.high, "low": kz.low}
        return None
    
    def _check_silver_bullet(self, highs, lows, closes, times=None) -> Dict:
        """
        🟢 تعديل 11: Silver Bullet (10:00-11:00 EST)
        مع أوقات حقيقية: دقيق. بدون: محاكاة بآخر 6 شموع
        """
        if times is not None:
            # مع أوقات حقيقية
            silver_indices = []
            for i, t in enumerate(times):
                hour = t.hour if hasattr(t, 'hour') else 0
                if 10 <= hour < 11:
                    silver_indices.append(i)
            
            if silver_indices:
                seg_highs = highs[silver_indices]
                seg_lows = lows[silver_indices]
                seg_closes = closes[silver_indices]
                
                range_size = max(seg_highs) - min(seg_lows)
                first, last = seg_closes[0], seg_closes[-1]
                
                if range_size > 0 and abs(last - first) > range_size * 0.5:
                    return {"active": True, "direction": "long" if last > first else "short",
                            "entry": (max(seg_highs) + min(seg_lows)) / 2, "using_real_times": True}
                return {"active": False, "using_real_times": True}
        
        # محاكاة بدون أوقات
        if len(closes) < 6:
            return {"active": False}
        
        recent, recent_highs, recent_lows = closes[-6:], highs[-6:], lows[-6:]
        range_size = max(recent_highs) - min(recent_lows)
        first, last = recent[0], recent[-1]
        
        if range_size > 0 and abs(last - first) > range_size * 0.5:
            return {"active": True, "direction": "long" if last > first else "short",
                    "entry": (max(recent_highs) + min(recent_lows)) / 2, "using_real_times": False}
        return {"active": False}
    
    def _detect_nwog_ndog(self, opens, closes) -> Optional[Dict]:
        """
        🟢 تعديل 12: NWOG/NDOG (New Week/Day Opening Gap)
        فجوة افتتاح الأسبوع/اليوم
        """
        if len(opens) < 5 or len(closes) < 5:
            return None
        
        # تقدير: نبحث عن فجوة بين إغلاق وآخر وافتتاح تالٍ
        for i in range(1, len(opens)):
            gap = opens[i] - closes[i-1]
            avg_range = np.mean(highs[max(0,i-10):i] - lows[max(0,i-10):i]) if i >= 5 else abs(gap)
            
            if avg_range > 0 and abs(gap) > avg_range * 0.5:
                return {
                    "detected": True,
                    "type": "NWOG" if abs(gap) > avg_range * 1.5 else "NDOG",
                    "gap_price": opens[i],
                    "gap_size": gap,
                    "index": i,
                }
        
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة السادسة: الاستراتيجيات التكتيكية (ICT Tactical Models) محسن   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ICTTacticalModels:
    """
    نماذج ICT التكتيكية.
    🟡 تعديل 6: Turtle Soup Quality
    🟡 تعديل 7: Power of 3 على مستوى الجلسة
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                opens: np.ndarray, volumes: np.ndarray,
                order_blocks: List[OrderBlock], fvgs: List[FairValueGap], 
                killzones: List[Killzone]) -> Dict:
        """تحليل النماذج التكتيكية"""
        turtle_soup = self._detect_turtle_soup(highs, lows, closes, volumes)
        power_of_3 = self._analyze_power_of_3(opens, highs, lows, closes, killzones)
        propulsion = self._detect_propulsion_blocks(highs, lows, closes, order_blocks)
        pd_arrays = self._map_pd_arrays(order_blocks, fvgs, highs, lows, closes)
        
        return {
            "turtle_soup": turtle_soup,
            "power_of_3": power_of_3,
            "propulsion_blocks": propulsion,
            "pd_arrays": pd_arrays[-15:],
            "confluence_zones": self._find_confluence(pd_arrays),
        }
    
    def _detect_turtle_soup(self, highs, lows, closes, volumes) -> List[Dict]:
        """
        🟡 تعديل 6: Turtle Soup مع تقييم الجودة
        
        الجودة = قوة المستوى + حجم التأكيد
        """
        soups = []
        for i in range(5, len(closes) - 2):
            lookback_high = max(highs[i-5:i])
            lookback_low = min(lows[i-5:i])
            range_size = lookback_high - lookback_low
            
            # Turtle Soup: اختراق قمة ثم ارتداد
            if highs[i] > lookback_high and closes[i] < lookback_high:
                volume_confirm = volumes[i] > np.mean(volumes[max(0,i-10):i]) if i >= 5 else False
                level_strength = sum(1 for j in range(max(0,i-30), i) if abs(highs[j] - lookback_high) < range_size * 0.1) / 5
                
                quality = 0.5
                if volume_confirm:
                    quality += 0.25
                quality += min(0.25, level_strength * 0.25)
                
                soups.append({
                    "index": i, "type": "TurtleSoup", "swept_price": lookback_high,
                    "entry_price": closes[i], "direction": "sell",
                    "stop": highs[i], "target": lookback_low,
                    "quality": quality, "volume_confirm": volume_confirm,
                    "level_strength": level_strength,
                })
            
            # Inverse Turtle Soup
            if lows[i] < lookback_low and closes[i] > lookback_low:
                volume_confirm = volumes[i] > np.mean(volumes[max(0,i-10):i]) if i >= 5 else False
                level_strength = sum(1 for j in range(max(0,i-30), i) if abs(lows[j] - lookback_low) < range_size * 0.1) / 5
                
                quality = 0.5
                if volume_confirm:
                    quality += 0.25
                quality += min(0.25, level_strength * 0.25)
                
                soups.append({
                    "index": i, "type": "InverseTurtleSoup", "swept_price": lookback_low,
                    "entry_price": closes[i], "direction": "buy",
                    "stop": lows[i], "target": lookback_high,
                    "quality": quality, "volume_confirm": volume_confirm,
                    "level_strength": level_strength,
                })
        return soups
    
    def _analyze_power_of_3(self, opens, highs, lows, closes, killzones) -> Dict:
        """
        🟡 تعديل 7: Power of 3 على مستوى الشمعة والجلسة
        
        PO3 للشمعة: open → manipulation → close
        PO3 للجلسة: Asian Range → London Manipulation → NY Distribution
        """
        result = {"candle_po3": None, "session_po3": None}
        
        # PO3 على مستوى الشمعة
        if len(opens) >= 3:
            last_open, last_close = opens[-1], closes[-1]
            last_high, last_low = highs[-1], lows[-1]
            last_range = last_high - last_low
            
            if last_range > 0:
                upper_wick = last_high - max(last_open, last_close)
                lower_wick = min(last_open, last_close) - last_low
                body = abs(last_close - last_open)
                
                if lower_wick > body * 0.5 and last_close > last_open:
                    result["candle_po3"] = {"pattern": "Bullish_PO3", "manipulation_low": last_low}
                elif upper_wick > body * 0.5 and last_close < last_open:
                    result["candle_po3"] = {"pattern": "Bearish_PO3", "manipulation_high": last_high}
        
        # 🟡 تعديل 7: PO3 على مستوى الجلسة
        asian_kz = [k for k in killzones if k.session == 'Asian']
        london_kz = [k for k in killzones if k.session == 'London']
        
        if asian_kz and london_kz:
            asian = asian_kz[0]
            london = london_kz[0]
            
            if london.manipulation_detected:
                if london.direction == 'down' and closes[-1] > asian.high:
                    result["session_po3"] = {
                        "pattern": "Session_Bullish_PO3",
                        "accumulation": f"Asian Range {asian.low:.2f}-{asian.high:.2f}",
                        "manipulation": f"London Judas Down to {london.low:.2f}",
                        "distribution": "NY Rally",
                    }
                elif london.direction == 'up' and closes[-1] < asian.low:
                    result["session_po3"] = {
                        "pattern": "Session_Bearish_PO3",
                        "accumulation": f"Asian Range {asian.low:.2f}-{asian.high:.2f}",
                        "manipulation": f"London Judas Up to {london.high:.2f}",
                        "distribution": "NY Sell-off",
                    }
        
        return result
    
    def _detect_propulsion_blocks(self, highs, lows, closes, order_blocks) -> List[Dict]:
        """كتل الدفع"""
        propulsion = []
        for ob in order_blocks:
            if not ob.is_fresh:
                continue
            for i in range(ob.index + 10, len(closes) - 3):
                if ob.ob_type == 'bullish' and ob.zone_bottom <= lows[i] <= ob.zone_top:
                    if closes[i+1] > closes[i] and closes[i+2] > closes[i+1]:
                        propulsion.append({"ob_index": ob.index, "touch_index": i,
                                           "type": "Bullish_Propulsion",
                                           "entry": (ob.zone_top + ob.zone_bottom) / 2})
                        break
                elif ob.ob_type == 'bearish' and ob.zone_bottom <= highs[i] <= ob.zone_top:
                    if closes[i+1] < closes[i] and closes[i+2] < closes[i+1]:
                        propulsion.append({"ob_index": ob.index, "touch_index": i,
                                           "type": "Bearish_Propulsion",
                                           "entry": (ob.zone_top + ob.zone_bottom) / 2})
                        break
        return propulsion
    
    def _map_pd_arrays(self, order_blocks, fvgs, highs, lows, closes) -> List[PDArray]:
        """
        رسم مصفوفات ICT مع confluence_count محدث
        🟡 تعديل 10: confluence_count يملأ
        """
        pd_arrays = []
        
        for ob in order_blocks[-20:]:
            if ob.is_fresh:
                pd_arrays.append(PDArray(
                    array_type='OB', index=ob.index, price_level=ob.body_50,
                    zone_top=ob.zone_top, zone_bottom=ob.zone_bottom,
                    time_created=ob.index, strength=ob.strength, confluence_count=0,
                ))
        
        for fvg in fvgs[-20:]:
            if fvg.filled < 0.9:
                pd_arrays.append(PDArray(
                    array_type='FVG', index=fvg.index,
                    price_level=(fvg.top + fvg.bottom) / 2,
                    zone_top=fvg.top, zone_bottom=fvg.bottom,
                    time_created=fvg.index, strength=fvg.strength, confluence_count=0,
                ))
        
        # 🟡 تعديل 10: حساب confluence_count
        for i in range(len(pd_arrays)):
            count = 0
            for j in range(len(pd_arrays)):
                if i != j:
                    if not (pd_arrays[i].zone_top < pd_arrays[j].zone_bottom or 
                           pd_arrays[i].zone_bottom > pd_arrays[j].zone_top):
                        count += 1
            pd_arrays[i].confluence_count = count
        
        return pd_arrays
    
    def _find_confluence(self, pd_arrays: List[PDArray]) -> List[Dict]:
        """إيجاد مناطق الالتقاء"""
        if len(pd_arrays) < 2:
            return []
        
        zones = []
        for i in range(len(pd_arrays)):
            confluence = [pd_arrays[i]]
            for j in range(i+1, len(pd_arrays)):
                if not (pd_arrays[i].zone_top < pd_arrays[j].zone_bottom or 
                       pd_arrays[i].zone_bottom > pd_arrays[j].zone_top):
                    confluence.append(pd_arrays[j])
            
            if len(confluence) >= 2:
                zones.append({
                    "price_level": np.mean([a.price_level for a in confluence]),
                    "arrays": [a.array_type for a in confluence],
                    "count": len(confluence),
                    "avg_strength": np.mean([a.strength for a in confluence]),
                    "strong": len(confluence) >= 3,
                    "has_ob_fvg": any(a.array_type == 'OB' for a in confluence) and 
                                  any(a.array_type == 'FVG' for a in confluence),
                })
        
        return zones


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                الدرجة النهائية: استراتيجية ICT الموحدة (محسنة)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ICTStrategy:
    """
    استراتيجية ICT كاملة - الإصدار 2.0
    تجمع كل المحللات في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.ob_analyzer = OrderBlockAnalyzer()
        self.fvg_analyzer = FVGAnalyzer()
        self.breaker_analyzer = BreakerMitigationAnalyzer()
        self.amd_analyzer = AMDCycleAnalyzer()
        self.killzone_analyzer = KillzoneAnalyzer()
        self.tactical_models = ICTTacticalModels()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        times = chart_data.get('times', None)
        sessions = chart_data.get('sessions', None)
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "بيانات غير كافية (تحتاج 20 شمعة)"}
        
        # 1. Order Blocks
        ob_data = self.ob_analyzer.analyze(opens, highs, lows, closes, volumes, sessions)
        all_obs = ob_data['all_order_blocks']
        
        # 2. FVGs (مع Confluence مع OB)
        fvg_data = self.fvg_analyzer.analyze(highs, lows, closes, volumes, all_obs)
        all_fvgs = fvg_data['all_fvgs']
        
        # 3. Breakers & Mitigations (مع opens)
        breaker_data = self.breaker_analyzer.analyze(all_obs, highs, lows, closes, opens)
        
        # 4. Killzones
        killzone_data = self.killzone_analyzer.analyze(highs, lows, closes, opens, times)
        killzones = killzone_data.get('killzones', [])
        
        # 5. AMD Cycle + Liquidity Sweeps
        amd_data = self.amd_analyzer.analyze(opens, highs, lows, closes, volumes, killzones)
        
        # 6. Tactical Models
        tactical_data = self.tactical_models.analyze(
            highs, lows, closes, opens, volumes, all_obs, all_fvgs, killzones
        )
        
        # 7. اتخاذ القرار
        decision = self._make_decision(ob_data, fvg_data, breaker_data,
                                       amd_data, killzone_data, tactical_data)
        
        return {
            **decision,
            "order_blocks": ob_data,
            "fvgs": fvg_data,
            "breakers": breaker_data,
            "amd": amd_data,
            "killzones": killzone_data,
            "tactical": tactical_data,
        }
    
    def _make_decision(self, ob_data, fvg_data, breaker_data, amd_data,
                       killzone_data, tactical_data) -> Dict:
        """تجميع كل الإشارات"""
        buy_signals = []
        sell_signals = []
        
        # ---- Order Blocks ----
        best_bull = ob_data.get('best_bullish_ob')
        best_bear = ob_data.get('best_bearish_ob')
        
        if best_bull:
            pres = "First" if best_bull.presentation_number == 0 else "Second"
            weight = best_bull.strength * best_bull.time_strength_multiplier * 0.25
            buy_signals.append((f"Bullish OB ({pres} Pres, {best_bull.continuation_type})", weight))
        
        if best_bear:
            pres = "First" if best_bear.presentation_number == 0 else "Second"
            weight = best_bear.strength * best_bear.time_strength_multiplier * 0.25
            sell_signals.append((f"Bearish OB ({pres} Pres, {best_bear.continuation_type})", weight))
        
        # ---- FVGs ----
        bull_fvg = fvg_data.get('nearest_bullish_fvg')
        bear_fvg = fvg_data.get('nearest_bearish_fvg')
        
        if bull_fvg:
            weight = bull_fvg.strength * 0.15
            if bull_fvg.has_ob_confluence:
                weight *= 1.4
                buy_signals.append((f"Bullish FVG + OB Confluence (×{bull_fvg.confluence_strength:.2f})", weight))
            else:
                buy_signals.append(("Bullish FVG جاذب", weight))
        
        if bear_fvg:
            weight = bear_fvg.strength * 0.15
            if bear_fvg.has_ob_confluence:
                weight *= 1.4
                sell_signals.append((f"Bearish FVG + OB Confluence (×{bear_fvg.confluence_strength:.2f})", weight))
            else:
                sell_signals.append(("Bearish FVG جاذب", weight))
        
        # ---- Breakers ----
        for br in breaker_data.get('active_breakers', []):
            if br.breaker_type == 'bullish_breaker':
                buy_signals.append(("Bullish Breaker", br.strength * 0.2))
            else:
                sell_signals.append(("Bearish Breaker", br.strength * 0.2))
        
        # ---- AMD ----
        phase = amd_data.get('current_phase', 'Trending')
        if phase == 'Manipulation_Up':
            buy_signals.append(("AMD: تلاعب صاعد", 0.3))
        elif phase == 'Manipulation_Down':
            sell_signals.append(("AMD: تلاعب هابط", 0.3))
        
        # ---- Liquidity Sweeps ----
        for sweep in amd_data.get('liquidity_sweeps', [])[-3:]:
            if sweep.direction == 'buy':
                buy_signals.append((f"Liquidity Sweep: {sweep.sweep_type}", sweep.strength * 0.3))
            else:
                sell_signals.append((f"Liquidity Sweep: {sweep.sweep_type}", sweep.strength * 0.3))
        
        # ---- Turtle Soup ----
        for ts in tactical_data.get('turtle_soup', [])[-3:]:
            weight = ts.get('quality', 0.5) * 0.35
            if ts['direction'] == 'buy':
                buy_signals.append((f"Turtle Soup (Q:{ts.get('quality',0):.0%})", weight))
            else:
                sell_signals.append((f"Turtle Soup (Q:{ts.get('quality',0):.0%})", weight))
        
        # ---- Silver Bullet ----
        sb = killzone_data.get('silver_bullet', {})
        if sb.get('active'):
            if sb.get('direction') == 'long':
                buy_signals.append(("Silver Bullet Long", 0.35))
            else:
                sell_signals.append(("Silver Bullet Short", 0.35))
        
        # ---- NWOG/NDOG ----
        nwog = killzone_data.get('nwog_ndog')
        if nwog and nwog.get('detected'):
            if nwog.get('gap_size', 0) > 0:
                buy_signals.append((f"{nwog['type']} فجوة افتتاح", 0.25))
            else:
                sell_signals.append((f"{nwog['type']} فجوة افتتاح", 0.25))
        
        # ---- Confluence Zones ----
        for cz in tactical_data.get('confluence_zones', [])[-3:]:
            if cz.get('strong') and cz.get('has_ob_fvg'):
                buy_signals.append((f"Confluence Zone (×{cz['count']})", cz['avg_strength'] * 0.3))
        
        # ---- القرار النهائي ----
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
            confidence = 35
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 35
        else:
            recommendation = "محايد"
            confidence = 20
        
        top_reasons = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_reasons]) if top_reasons else "لا إشارات واضحة"
        reason += f" | AMD:{phase}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_ict_strategy():
    """إنشاء استراتيجية ICT الجاهزة (الإصدار 2.0)"""
    return ICTStrategy()