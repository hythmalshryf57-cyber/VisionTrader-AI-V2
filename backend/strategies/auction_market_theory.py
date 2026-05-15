"""
═══════════════════════════════════════════════════════════════════════════════
AUCTION MARKET THEORY - النسخة الديناميكية المتكاملة
المدرسة التاسعة: نظرية سوق المزاد - فلسفة السوق المفتوح
═══════════════════════════════════════════════════════════════════════════════

نظرية سوق المزاد (Auction Market Theory - AMT) تفسر كل حركة سعرية
على أنها نتيجة مزاد مستمر بين المشترين والبائعين.

طورها J. Peter Steidlmayer (مبتكر Market Profile) و Donald Jones.
الفكرة: السوق يتحرك بين ثلاث حالات ديناميكية:
1. التوازن (Balance/Equilibrium) - السعر العادل
2. عدم التوازن (Imbalance/Disequilibrium) - البحث عن سعر عادل جديد
3. الانتقال (Transition) - الحركة بين مناطق التوازن

هذه النسخة ديناميكية بالكامل:
- لا حدود ثابتة للتوازن
- السعر العادل يكتشف من المزاد نفسه
- المراحل تتداخل وتتحول بشكل طبيعي
- كل سوق له إيقاعه الخاص في الانتقال بين المراحل

المفاهيم الأساسية:
1. Fair Value (القيمة العادلة) - حيث يتساوى المشترين والبائعين
2. Value Area - منطقة القيمة (امتداد للقيمة العادلة)
3. Responsive Activity - نشاط مستجيب (العودة للقيمة)
4. Initiative Activity - نشاط مبادر (البحث عن قيمة جديدة)
5. Excess - الرفض السعري (نهاية البحث)
6. Bracketing - التأطير (التداول بين حدود)
7. Range Extension - تمديد النطاق
8. Volume at Price - الحجم عند السعر
9. Time at Price - الزمن عند السعر
10. Auction Failures - فشل المزاد
11. Auction Continuation - استمرار المزاد
12. Price Discovery - اكتشاف السعر
13. Acceptance vs Rejection - القبول والرفض

الأنماط السلوكية:
- Bracketed Market (سوق مؤطر)
- Trending Market (سوق متجه)
- Side-by-Side Value Areas (مناطق قيمة متجاورة)
- Overlapping Value Areas (مناطق قيمة متداخلة)
- Stepping Value Areas (مناطق قيمة متدرجة)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class AuctionPhase:
    """مرحلة مزاد"""
    start_idx: int
    end_idx: int
    phase_type: str  # 'balance', 'imbalance_up', 'imbalance_down', 'transition', 'discovery'
    fair_value: float
    value_high: float
    value_low: float
    total_volume: float
    duration: int
    excess_high: Optional[float]
    excess_low: Optional[float]
    responsive_ratio: float  # نسبة النشاط المستجيب
    initiative_ratio: float  # نسبة النشاط المبادر
    acceptance_level: float  # 0-1 درجة قبول السعر


@dataclass
class ValueZone:
    """منطقة قيمة (منطقة توازن)"""
    high: float
    low: float
    fair_value: float
    volume_inside: float
    time_spent: int  # عدد الشموع
    overlaps_with_next: bool
    overlaps_with_prev: bool
    gap_from_prev: Optional[float]


@dataclass
class AuctionEvent:
    """حدث مزادي"""
    index: int
    event_type: str  # 'rejection', 'acceptance', 'breakout', 'failed_breakout', 'excess', 'gap', 'auction_failure'
    price_level: float
    direction: str  # 'up', 'down', 'neutral'
    strength: float  # 0-1
    volume_confirmed: bool
    description: str


@dataclass
class AuctionProfile:
    """بروفايل المزاد الكامل"""
    phases: List[AuctionPhase]
    value_zones: List[ValueZone]
    events: List[AuctionEvent]
    current_phase: str
    current_fair_value: float
    market_condition: str  # 'bracketed', 'trending', 'discovery', 'transitional'
    auction_health: float  # 0-1 صحة المزاد
    next_expected_phase: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الأولى: محلل المزاد الديناميكي (Dynamic Auction Analyzer)      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicAuctionAnalyzer:
    """
    يحلل السوق كمزاد حي.
    يكتشف التوازن وعدمه من سلوك السعر والحجم والزمن.
    
    ديناميكي: القيمة العادلة تتغير مع كل صفقة.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray) -> Dict:
        """
        تحليل المزاد الكامل
        """
        # اكتشاف مراحل المزاد
        phases = self._detect_auction_phases(highs, lows, closes, volumes)
        
        # بناء مناطق القيمة
        value_zones = self._build_value_zones(phases, closes, volumes)
        
        # اكتشاف أحداث المزاد
        events = self._detect_auction_events(highs, lows, closes, volumes, phases)
        
        # المرحلة الحالية
        current_phase = self._determine_current_phase(phases, events, closes)
        current_fv = self._estimate_fair_value(closes, volumes, phases)
        
        # صحة المزاد
        auction_health = self._assess_auction_health(phases, events)
        
        profile = AuctionProfile(
            phases=phases,
            value_zones=value_zones,
            events=events,
            current_phase=current_phase,
            current_fair_value=current_fv,
            market_condition=self._determine_market_condition(phases, value_zones),
            auction_health=auction_health,
            next_expected_phase=self._predict_next_phase(phases, events),
        )
        
        return {
            "profile": profile,
            "phases": phases[-5:],
            "value_zones": value_zones[-5:],
            "events": events[-20:],
            "current_phase": current_phase,
            "fair_value": current_fv,
            "auction_health": auction_health,
        }
    
    def _detect_auction_phases(self, highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray, volumes: np.ndarray) -> List[AuctionPhase]:
        """
        اكتشاف مراحل المزاد.
        السوق ينتقل بين توازن وعدم توازن بشكل طبيعي.
        """
        phases = []
        
        if len(closes) < 20:
            return phases
        
        i = 0
        phase_id = 0
        
        while i < len(closes) - 10:
            # البحث عن منطقة توازن
            segment = closes[i:i+10]
            segment_highs = highs[i:i+10]
            segment_lows = lows[i:i+10]
            segment_volumes = volumes[i:i+10]
            
            price_range = max(segment_highs) - min(segment_lows)
            avg_range = np.mean(segment_highs - segment_lows)
            
            if avg_range == 0:
                i += 1
                continue
            
            # التوازن: السعر محصور في نطاق
            range_ratio = price_range / avg_range
            
            if range_ratio < 4.0:
                # وجدنا توازن
                balance_start = i
                balance_high = max(segment_highs)
                balance_low = min(segment_lows)
                balance_vol = sum(segment_volumes)
                
                # تمديد منطقة التوازن
                j = i + 10
                while j < len(closes) - 3:
                    current_high = max(highs[balance_start:j+1])
                    current_low = min(lows[balance_start:j+1])
                    current_range = current_high - current_low
                    
                    # متى ينتهي التوازن؟
                    extension = current_range / (balance_high - balance_low) if balance_high != balance_low else 1
                    
                    if extension > 2.0:
                        # كسر التوازن
                        break
                    elif extension > 1.5 and np.mean(volumes[max(j-2,balance_start):j+1]) > np.mean(volumes[balance_start:j]) * 1.5:
                        # حجم مرتفع = خروج من التوازن
                        break
                    
                    balance_high = current_high
                    balance_low = current_low
                    balance_vol += volumes[j]
                    j += 1
                
                # حساب القيمة العادلة
                fv = self._calculate_fair_value_in_range(highs[balance_start:j], 
                                                          lows[balance_start:j],
                                                          closes[balance_start:j],
                                                          volumes[balance_start:j])
                
                # حساب الرفض (Excess)
                excess_high = self._detect_excess_in_range(highs[balance_start:j], 
                                                            lows[balance_start:j],
                                                            closes[balance_start:j], 'high')
                excess_low = self._detect_excess_in_range(highs[balance_start:j],
                                                           lows[balance_start:j],
                                                           closes[balance_start:j], 'low')
                
                # النشاط المستجيب والمبادر
                responsive, initiative = self._measure_activity_types(
                    highs[balance_start:j], lows[balance_start:j], closes[balance_start:j],
                    volumes[balance_start:j], fv)
                
                # درجة القبول
                acceptance = self._measure_acceptance(closes[balance_start:j], fv, 
                                                       balance_high, balance_low)
                
                phases.append(AuctionPhase(
                    start_idx=balance_start,
                    end_idx=j,
                    phase_type='balance',
                    fair_value=fv,
                    value_high=balance_high,
                    value_low=balance_low,
                    total_volume=balance_vol,
                    duration=j - balance_start,
                    excess_high=excess_high,
                    excess_low=excess_low,
                    responsive_ratio=responsive,
                    initiative_ratio=initiative,
                    acceptance_level=acceptance,
                ))
                
                i = j
                phase_id += 1
            else:
                # منطقة عدم توازن (اتجاه)
                imbalance_start = i
                imbalance_direction = 'up' if closes[i+5] > closes[i] else 'down'
                
                j = i + 10
                while j < len(closes) - 3:
                    # متى ينتهي عدم التوازن؟
                    recent_range = max(highs[j-5:j+1]) - min(lows[j-5:j+1])
                    earlier_range = max(highs[imbalance_start:j-3]) - min(lows[imbalance_start:j-3])
                    
                    if earlier_range > 0 and recent_range / earlier_range < 0.3:
                        # التراجع = نهاية عدم التوازن
                        break
                    
                    # تباطؤ = نهاية
                    if j - imbalance_start > 15 and abs(closes[j] - closes[j-5]) < abs(closes[imbalance_start+5] - closes[imbalance_start]) * 0.3:
                        break
                    
                    j += 1
                
                phases.append(AuctionPhase(
                    start_idx=imbalance_start,
                    end_idx=j,
                    phase_type=f'imbalance_{imbalance_direction}',
                    fair_value=closes[j-1],
                    value_high=max(highs[imbalance_start:j]),
                    value_low=min(lows[imbalance_start:j]),
                    total_volume=sum(volumes[imbalance_start:j]),
                    duration=j - imbalance_start,
                    excess_high=None,
                    excess_low=None,
                    responsive_ratio=0.3,
                    initiative_ratio=0.7,
                    acceptance_level=0.5,
                ))
                
                i = j
                phase_id += 1
            
            # حماية من التكرار اللانهائي
            if i >= len(closes) - 10:
                break
        
        return phases
    
    def _calculate_fair_value_in_range(self, highs: np.ndarray, lows: np.ndarray,
                                        closes: np.ndarray, volumes: np.ndarray) -> float:
        """
        حساب القيمة العادلة داخل نطاق.
        ديناميكي: أعلى كثافة للحجم والزمن.
        """
        if len(closes) == 0:
            return 0
        
        # VWAP داخل النطاق
        if sum(volumes) > 0:
            vwap = np.average(closes, weights=volumes)
        else:
            vwap = np.mean(closes)
        
        # TPO POC (أعلى زمن)
        price_range = max(highs) - min(lows)
        if price_range == 0:
            return vwap
        
        # تقسيم النطاق إلى مستويات
        num_levels = min(50, max(10, int(price_range / (np.mean(highs - lows) * 0.5))))
        level_size = price_range / num_levels if num_levels > 0 else 1
        
        level_time = defaultdict(int)
        for i in range(len(closes)):
            bar_low = lows[i]
            bar_high = highs[i]
            for level in np.arange(min(lows), max(highs), level_size):
                if bar_low <= level <= bar_high:
                    level_time[round(level, 4)] += 1
        
        # POC = أعلى زمن
        if level_time:
            poc = max(level_time, key=level_time.get)
            return poc
        
        return vwap
    
    def _detect_excess_in_range(self, highs: np.ndarray, lows: np.ndarray,
                                 closes: np.ndarray, side: str) -> Optional[float]:
        """
        اكتشاف الرفض (Excess) عند أطراف النطاق.
        """
        if len(closes) < 5:
            return None
        
        if side == 'high':
            # قمة بظل طويل أو جسم صغير يعقبه هبوط
            top_idx = np.argmax(highs)
            if top_idx < len(highs) - 1:
                if closes[top_idx] < highs[top_idx] * 0.995 and closes[top_idx] < closes[min(top_idx+1, len(closes)-1)]:
                    return highs[top_idx]
        else:
            bottom_idx = np.argmin(lows)
            if bottom_idx < len(lows) - 1:
                if closes[bottom_idx] > lows[bottom_idx] * 1.005 and closes[bottom_idx] > closes[min(bottom_idx+1, len(closes)-1)]:
                    return lows[bottom_idx]
        
        return None
    
    def _measure_activity_types(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray,
                                  fair_value: float) -> Tuple[float, float]:
        """
        قياس النشاط المستجيب والمبادر.
        """
        if len(closes) < 5:
            return (0.5, 0.5)
        
        responsive = 0
        initiative = 0
        
        range_high = max(highs)
        range_low = min(lows)
        mid = (range_high + range_low) / 2
        
        for i in range(1, len(closes)):
            # حركة من خارج المنطقة إلى الداخل = مستجيب
            if closes[i-1] > range_high and closes[i] <= range_high:
                responsive += 1
            elif closes[i-1] < range_low and closes[i] >= range_low:
                responsive += 1
            # حركة من الداخل للخارج = مبادر
            elif closes[i-1] <= range_high and closes[i] > range_high:
                initiative += 1
            elif closes[i-1] >= range_low and closes[i] < range_low:
                initiative += 1
        
        total = responsive + initiative
        if total == 0:
            return (0.5, 0.5)
        
        return (responsive / total, initiative / total)
    
    def _measure_acceptance(self, closes: np.ndarray, fair_value: float,
                            range_high: float, range_low: float) -> float:
        """
        قياس درجة قبول السعر.
        """
        if len(closes) < 3:
            return 0.5
        
        range_size = range_high - range_low
        if range_size == 0:
            return 1.0
        
        # عدد الإغلاقات قرب القيمة العادلة
        acceptance_zone = range_size * 0.3
        close_to_fv = sum(1 for c in closes if abs(c - fair_value) < acceptance_zone)
        
        return close_to_fv / len(closes)
    
    def _build_value_zones(self, phases: List[AuctionPhase], closes: np.ndarray,
                            volumes: np.ndarray) -> List[ValueZone]:
        """
        بناء مناطق القيمة من مراحل المزاد.
        """
        value_zones = []
        
        for i, phase in enumerate(phases):
            if phase.phase_type == 'balance':
                overlap_next = False
                overlap_prev = False
                gap_prev = None
                
                if i < len(phases) - 1:
                    next_phase = phases[i+1]
                    overlap_next = not (phase.value_high < next_phase.value_low or 
                                       phase.value_low > next_phase.value_high)
                
                if i > 0:
                    prev_phase = phases[i-1]
                    overlap_prev = not (phase.value_high < prev_phase.value_low or 
                                       phase.value_low > prev_phase.value_high)
                    if not overlap_prev:
                        gap_prev = min(abs(phase.value_low - prev_phase.value_high),
                                      abs(phase.value_high - prev_phase.value_low))
                
                value_zones.append(ValueZone(
                    high=phase.value_high,
                    low=phase.value_low,
                    fair_value=phase.fair_value,
                    volume_inside=phase.total_volume,
                    time_spent=phase.duration,
                    overlaps_with_next=overlap_next,
                    overlaps_with_prev=overlap_prev,
                    gap_from_prev=gap_prev,
                ))
        
        return value_zones
    
    def _detect_auction_events(self, highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray, volumes: np.ndarray,
                                phases: List[AuctionPhase]) -> List[AuctionEvent]:
        """
        اكتشاف أحداث المزاد.
        """
        events = []
        
        if len(phases) < 2:
            return events
        
        for i in range(1, len(phases)):
            prev = phases[i-1]
            curr = phases[i]
            
            # انتقال من توازن لعدم توازن = اختراق
            if prev.phase_type == 'balance' and 'imbalance' in curr.phase_type:
                direction = 'up' if 'up' in curr.phase_type else 'down'
                breakout_price = curr.value_high if direction == 'up' else curr.value_low
                
                events.append(AuctionEvent(
                    index=curr.start_idx,
                    event_type='breakout',
                    price_level=breakout_price,
                    direction=direction,
                    strength=0.7,
                    volume_confirmed=curr.total_volume > prev.total_volume * 1.3,
                    description=f"اختراق {'صاعد' if direction == 'up' else 'هابط'} من منطقة توازن",
                ))
            
            # فشل اختراق = رفض
            if prev.phase_type == 'imbalance_up' and curr.phase_type == 'balance':
                if curr.value_high < prev.value_high:
                    events.append(AuctionEvent(
                        index=curr.start_idx,
                        event_type='failed_breakout',
                        price_level=prev.value_high,
                        direction='down',
                        strength=0.75,
                        volume_confirmed=True,
                        description="فشل اختراق صاعد - رفض السعر الأعلى",
                    ))
            
            if prev.phase_type == 'imbalance_down' and curr.phase_type == 'balance':
                if curr.value_low > prev.value_low:
                    events.append(AuctionEvent(
                        index=curr.start_idx,
                        event_type='failed_breakout',
                        price_level=prev.value_low,
                        direction='up',
                        strength=0.75,
                        volume_confirmed=True,
                        description="فشل اختراق هابط - رفض السعر الأدنى",
                    ))
            
            # فجوة بين مناطق القيمة
            if prev.phase_type == 'balance' and curr.phase_type == 'balance':
                if prev.value_high < curr.value_low:
                    events.append(AuctionEvent(
                        index=curr.start_idx,
                        event_type='gap',
                        price_level=(prev.value_high + curr.value_low) / 2,
                        direction='up',
                        strength=0.6,
                        volume_confirmed=True,
                        description="فجوة صاعدة بين مناطق قيمة",
                    ))
                elif prev.value_low > curr.value_high:
                    events.append(AuctionEvent(
                        index=curr.start_idx,
                        event_type='gap',
                        price_level=(prev.value_low + curr.value_high) / 2,
                        direction='down',
                        strength=0.6,
                        volume_confirmed=True,
                        description="فجوة هابطة بين مناطق قيمة",
                    ))
        
        return events
    
    def _determine_current_phase(self, phases: List[AuctionPhase],
                                   events: List[AuctionEvent],
                                   closes: np.ndarray) -> str:
        """تحديد المرحلة الحالية"""
        if not phases:
            return 'unknown'
        
        last_phase = phases[-1]
        
        # إذا انتهت آخر مرحلة، نحن في انتقال
        if last_phase.end_idx < len(closes) - 5:
            return 'transition'
        
        return last_phase.phase_type
    
    def _estimate_fair_value(self, closes: np.ndarray, volumes: np.ndarray,
                              phases: List[AuctionPhase]) -> float:
        """تقدير القيمة العادلة الحالية"""
        if len(closes) < 5:
            return closes[-1] if len(closes) > 0 else 0
        
        # آخر منطقة توازن
        balance_phases = [p for p in phases if p.phase_type == 'balance']
        if balance_phases:
            return balance_phases[-1].fair_value
        
        # VWAP للفترة الأخيرة
        recent_vol = volumes[-20:] if len(volumes) >= 20 else volumes
        recent_closes = closes[-20:] if len(closes) >= 20 else closes
        
        if sum(recent_vol) > 0:
            return np.average(recent_closes, weights=recent_vol)
        
        return np.mean(recent_closes)
    
    def _assess_auction_health(self, phases: List[AuctionPhase],
                                events: List[AuctionEvent]) -> float:
        """تقييم صحة المزاد"""
        if not phases:
            return 0.5
        
        # مزاد صحي = توازن مستقر + حركة منظمة
        balance_phases = [p for p in phases if p.phase_type == 'balance']
        
        if not balance_phases:
            return 0.4
        
        avg_acceptance = np.mean([p.acceptance_level for p in balance_phases])
        failed_breakouts = sum(1 for e in events if e.event_type == 'failed_breakout')
        
        health = avg_acceptance * 0.7 + (1 - min(failed_breakouts * 0.2, 1)) * 0.3
        
        return health
    
    def _determine_market_condition(self, phases: List[AuctionPhase],
                                     value_zones: List[ValueZone]) -> str:
        """تحديد حالة السوق"""
        if not phases:
            return 'unknown'
        
        last_phase = phases[-1]
        
        if last_phase.phase_type == 'balance':
            if len(value_zones) >= 3:
                recent = value_zones[-3:]
                if all(z.overlaps_with_prev for z in recent[1:]):
                    return 'bracketed'
                elif all(not z.overlaps_with_prev for z in recent[1:]):
                    return 'discovery'
            return 'bracketed'
        
        if 'imbalance' in last_phase.phase_type:
            return 'trending'
        
        return 'transitional'
    
    def _predict_next_phase(self, phases: List[AuctionPhase],
                             events: List[AuctionEvent]) -> str:
        """توقع المرحلة التالية"""
        if not phases:
            return 'unknown'
        
        last = phases[-1]
        
        if last.phase_type == 'balance':
            # توازن → إما اختراق أو استمرار
            if last.initiative_ratio > 0.6:
                return 'imbalance'
            else:
                return 'balance'
        
        if 'imbalance' in last.phase_type:
            # عدم توازن → إما توازن جديد أو استمرار
            if last.responsive_ratio > 0.5:
                return 'balance'
            else:
                return last.phase_type
        
        return 'transition'


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الثانية: محلل القبول والرفض (Acceptance & Rejection Analyzer)   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AcceptanceRejectionAnalyzer:
    """
    يحلل القبول والرفض السعري.
    
    القبول = السعر يقضي وقتاً عند مستوى معين بحجم تداول
    الرفض = حركة سريعة بعيداً عن مستوى (Excess)
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, fair_value: float) -> Dict:
        """
        تحليل القبول والرفض
        """
        acceptance = self._measure_acceptance_current(highs, lows, closes, volumes, fair_value)
        rejection = self._detect_rejection_zones(highs, lows, closes, volumes)
        price_discovery = self._analyze_price_discovery(highs, lows, closes, volumes)
        
        return {
            "acceptance": acceptance,
            "rejection_zones": rejection,
            "price_discovery": price_discovery,
            "current_state": "acceptance" if acceptance['score'] > rejection['score'] else "rejection",
        }
    
    def _measure_acceptance_current(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, volumes: np.ndarray,
                                     fair_value: float) -> Dict:
        """
        قياس درجة القبول الحالية للسعر.
        """
        if len(closes) < 10:
            return {"score": 0.5, "state": "غير كافٍ"}
        
        recent_closes = closes[-10:]
        
        # 1. القرب من القيمة العادلة
        avg_distance = np.mean([abs(c - fair_value) for c in recent_closes])
        avg_range = np.mean(highs[-10:] - lows[-10:])
        
        if avg_range > 0:
            proximity_score = 1 - min(1.0, avg_distance / (avg_range * 2))
        else:
            proximity_score = 0.5
        
        # 2. استقرار الإغلاقات
        close_std = np.std(recent_closes)
        close_mean = np.mean(recent_closes)
        if close_mean > 0:
            stability_score = 1 - min(1.0, close_std / close_mean * 10)
        else:
            stability_score = 0.5
        
        # 3. حجم ثابت (لا طفرات)
        recent_vol = volumes[-10:]
        vol_std = np.std(recent_vol)
        vol_mean = np.mean(recent_vol) if np.mean(recent_vol) > 0 else 1
        vol_stability = 1 - min(1.0, vol_std / vol_mean * 0.5)
        
        score = (proximity_score * 0.4 + stability_score * 0.35 + vol_stability * 0.25)
        
        return {
            "score": score,
            "state": "قبول عالي" if score > 0.7 else "قبول متوسط" if score > 0.4 else "قبول منخفض",
            "proximity": proximity_score,
            "stability": stability_score,
            "volume_stability": vol_stability,
        }
    
    def _detect_rejection_zones(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray) -> List[Dict]:
        """
        اكتشاف مناطق الرفض.
        """
        rejection_zones = []
        
        if len(highs) < 10:
            return rejection_zones
        
        for i in range(5, len(highs) - 3):
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                continue
            
            # رفض علوي: ظل علوي طويل مع إغلاق منخفض
            upper_wick = highs[i] - max(closes[i], closes[i-1] if i > 0 else closes[i])
            if upper_wick > bar_range * 0.5 and closes[i] < (highs[i] + lows[i]) / 2:
                rejection_zones.append({
                    "index": i,
                    "level": highs[i],
                    "direction": "down",
                    "type": "upper_rejection",
                    "wick_ratio": upper_wick / bar_range,
                    "strength": min(1.0, upper_wick / bar_range),
                })
            
            # رفض سفلي: ظل سفلي طويل مع إغلاق مرتفع
            lower_wick = min(closes[i], closes[i-1] if i > 0 else closes[i]) - lows[i]
            if lower_wick > bar_range * 0.5 and closes[i] > (highs[i] + lows[i]) / 2:
                rejection_zones.append({
                    "index": i,
                    "level": lows[i],
                    "direction": "up",
                    "type": "lower_rejection",
                    "wick_ratio": lower_wick / bar_range,
                    "strength": min(1.0, lower_wick / bar_range),
                })
        
        # تجميع مناطق الرفض المتقاربة
        return rejection_zones[-10:]
    
    def _analyze_price_discovery(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        تحليل اكتشاف السعر.
        """
        if len(closes) < 20:
            return {"active": False}
        
        # مقارنة النطاق الأخير بالأقدم
        recent_range = max(highs[-10:]) - min(lows[-10:])
        older_range = max(highs[-20:-10]) - min(lows[-20:-10])
        
        if older_range > 0:
            expansion = recent_range / older_range
        else:
            expansion = 1.0
        
        # حجم في الاتجاه الجديد
        if closes[-1] > max(highs[-20:-10]):
            discovery_direction = 'up'
            discovery_active = volumes[-1] > np.mean(volumes[-20:]) * 1.5
        elif closes[-1] < min(lows[-20:-10]):
            discovery_direction = 'down'
            discovery_active = volumes[-1] > np.mean(volumes[-20:]) * 1.5
        else:
            discovery_direction = 'none'
            discovery_active = False
        
        return {
            "active": discovery_active,
            "direction": discovery_direction,
            "expansion_ratio": expansion,
            "state": "اكتشاف سعر جديد" if discovery_active else "ضمن النطاق المعروف",
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║            الدرجة النهائية: استراتيجية المزاد الموحدة                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AuctionMarketStrategy:
    """
    استراتيجية نظرية سوق المزاد الكاملة.
    
    تجمع:
    - مراحل المزاد والتوازن
    - القبول والرفض
    - اكتشاف السعر
    - مناطق القيمة
    
    في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.auction_analyzer = DynamicAuctionAnalyzer()
        self.acceptance_analyzer = AcceptanceRejectionAnalyzer()
    
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
        
        # 1. تحليل المزاد
        auction_data = self.auction_analyzer.analyze(highs, lows, closes, volumes, opens)
        
        # 2. تحليل القبول والرفض
        fair_value = auction_data.get('fair_value', closes[-1])
        acceptance_data = self.acceptance_analyzer.analyze(highs, lows, closes, volumes, fair_value)
        
        # 3. القرار
        decision = self._make_decision(auction_data, acceptance_data)
        
        return {
            **decision,
            "auction_data": auction_data,
            "acceptance_data": acceptance_data,
        }
    
    def _make_decision(self, auction_data: Dict, acceptance_data: Dict) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        current_phase = auction_data.get('current_phase', 'unknown')
        fair_value = auction_data.get('fair_value', 0)
        events = auction_data.get('events', [])
        profile = auction_data.get('profile')
        
        current_price = 0
        if profile and profile.phases:
            current_price = profile.phases[-1].value_high
        
        # ---- من المرحلة الحالية ----
        if current_phase == 'balance':
            # في توازن: شراء عند القاع، بيع عند القمة
            if profile and profile.phases:
                last = profile.phases[-1]
                if current_price <= last.value_low * 1.01:
                    buy_signals.append(("قاع منطقة توازن - شراء مستجيب", 0.6))
                elif current_price >= last.value_high * 0.99:
                    sell_signals.append(("قمة منطقة توازن - بيع مستجيب", 0.6))
                elif current_price < last.fair_value:
                    buy_signals.append(("تحت القيمة العادلة في توازن", 0.4))
                elif current_price > last.fair_value:
                    sell_signals.append(("فوق القيمة العادلة في توازن", 0.4))
        
        elif current_phase == 'imbalance_up':
            buy_signals.append(("عدم توازن صاعد - استمر مع الاتجاه", 0.65))
            if acceptance_data.get('price_discovery', {}).get('active'):
                buy_signals.append(("اكتشاف سعر صاعد نشط", 0.55))
        
        elif current_phase == 'imbalance_down':
            sell_signals.append(("عدم توازن هابط - استمر مع الاتجاه", 0.65))
            if acceptance_data.get('price_discovery', {}).get('active'):
                sell_signals.append(("اكتشاف سعر هابط نشط", 0.55))
        
        elif current_phase == 'transition':
            # انتقال: انتظار وضوح
            if profile and profile.next_expected_phase == 'imbalance':
                buy_signals.append(("انتقال - توقع اختراق", 0.3))
            elif profile and profile.next_expected_phase == 'balance':
                sell_signals.append(("انتقال - توقع عودة للتوازن", 0.3))
        
        # ---- من أحداث المزاد ----
        for event in events[-5:]:
            if event.event_type == 'failed_breakout':
                if event.direction == 'up':
                    buy_signals.append(("فشل اختراق هابط - إشارة صعود", 0.7))
                else:
                    sell_signals.append(("فشل اختراق صاعد - إشارة هبوط", 0.7))
            
            if event.event_type == 'gap':
                if event.direction == 'up':
                    buy_signals.append(("فجوة صاعدة بين مناطق قيمة", 0.5))
                else:
                    sell_signals.append(("فجوة هابطة بين مناطق قيمة", 0.5))
        
        # ---- من القبول والرفض ----
        current_state = acceptance_data.get('current_state', 'unknown')
        rejection_zones = acceptance_data.get('rejection_zones', [])
        
        if current_state == 'rejection':
            if rejection_zones:
                last_rejection = rejection_zones[-1]
                if last_rejection['direction'] == 'up':
                    buy_signals.append(("رفض سفلي - إشارة شراء", 0.65))
                else:
                    sell_signals.append(("رفض علوي - إشارة بيع", 0.65))
        
        if acceptance_data.get('acceptance', {}).get('score', 0) > 0.7:
            # قبول عالي = تداول في النطاق
            if current_price > fair_value:
                sell_signals.append(("قبول عالي فوق القيمة - بيع", 0.5))
            else:
                buy_signals.append(("قبول عالي تحت القيمة - شراء", 0.5))
        
        # ---- من صحة المزاد ----
        auction_health = auction_data.get('auction_health', 0.5)
        if auction_health < 0.3:
            buy_signals.append(("مزاد ضعيف - انتظار", 0.1))
            sell_signals.append(("مزاد ضعيف - انتظار", 0.1))
        
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
        reason += f" | المرحلة: {current_phase} | القيمة العادلة: {fair_value:.4f}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "phase": current_phase,
        }


def create_auction_market_strategy():
    """إنشاء استراتيجية سوق المزاد الجاهزة"""
    return AuctionMarketStrategy()