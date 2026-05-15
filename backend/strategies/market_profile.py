"""
═══════════════════════════════════════════════════════════════════════════════
MARKET PROFILE / VOLUME PROFILE - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السابعة: بروفايل السوق - تشريح السوق ثلاثي الأبعاد
═══════════════════════════════════════════════════════════════════════════════

جيمس دالتون وبيتر ستيدلماير طورا Market Profile في الثمانينات.
الفكرة: السوق ليس مجرد سعر، بل توزيع للحجم عبر السعر والزمن.

هذه النسخة ديناميكية بالكامل - محسنة بـ 7 تعديلات:
- Value Area تتكيف مع تقلب السوق (لا نسبة 70% ثابتة)
- Point of Control (POC) ديناميكي متحرك
- POC Migration tracking
- Value Area Overlap مع الجلسات السابقة
- Naked POC detection
- Volume Holes في القرار
- توزيع حجم VWAP-like

المفاهيم الأساسية:
1. TPO (Time Price Opportunity)
2. Value Area ديناميكية
3. POC Migration
4. Single Prints / Volume Holes
5. Poor High/Low
6. Excess
7. Balance vs Imbalance
8. Initiative vs Responsive Activity
9. Naked POC
10. Value Area Overlap
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
class PriceLevel:
    """مستوى سعري مع حجمه"""
    price: float
    total_volume: float
    tpo_count: int
    volume_share: float
    is_poc: bool
    is_value_area: bool
    vwap_component: float = 0.0  # 🔴 تعديل 1: مكون VWAP


@dataclass
class ValueArea:
    """منطقة القيمة - محسنة"""
    high: float
    low: float
    poc: float
    total_volume: float
    volume_inside: float
    volume_percentage: float
    levels_count: int
    shape: str
    # 🟡 تعديل 5: تداخل مع VA سابق
    overlap_with_previous: float = 0.0
    overlap_description: str = ""


@dataclass
class VolumeProfile:
    """بروفايل الحجم الكامل - محسن"""
    levels: List[PriceLevel]
    value_area: ValueArea
    poc: float
    total_volume: float
    total_tpos: int
    high_volume_nodes: List[float]
    low_volume_nodes: List[float]
    single_prints: List[float]
    poor_high: bool
    poor_low: bool
    excess_points: List[float]
    distribution_type: str
    balance_state: str
    # 🟡 تعديل 4: POC Migration
    poc_migration: str = 'stable'
    poc_migration_distance: float = 0.0
    # 🟡 تعديل 6: Naked POC
    naked_poc: bool = False
    bars_since_poc_touched: int = 0


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الأولى: باني بروفايل الحجم الديناميكي (محسن)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicVolumeProfileBuilder:
    """
    يبني بروفايل الحجم بطريقة ديناميكية.
    
    🔴 تعديل 1: توزيع حجم VWAP-like
    🟡 تعديل 4: POC Migration
    🟡 تعديل 5: Value Area Overlap
    🟡 تعديل 6: Naked POC
    🟡 تعديل 7: Volume Holes في القرار
    """
    
    def __init__(self):
        self.previous_value_areas = deque(maxlen=5)
        self.previous_pocs = deque(maxlen=10)
        self.poc_touch_history = deque(maxlen=50)
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray, 
                price_precision: int = 4) -> Dict:
        """بناء بروفايل الحجم الكامل"""
        
        current_price = closes[-1] if len(closes) > 0 else 0.0
        
        # بناء المستويات السعرية
        levels = self._build_price_levels(highs, lows, closes, volumes, opens, price_precision)
        
        # إيجاد POC
        poc = self._find_poc(levels)
        
        # 🟡 تعديل 4: POC Migration
        poc_migration, poc_migration_distance = self._track_poc_migration(poc)
        
        # بناء Value Area ديناميكي
        value_area = self._build_dynamic_value_area(levels, poc)
        
        # 🟡 تعديل 5: Value Area Overlap
        self._calculate_va_overlap(value_area)
        
        # تحليل التوزيع
        distribution_type = self._analyze_distribution(levels)
        
        # اكتشاف العقد
        high_vol_nodes, low_vol_nodes = self._find_volume_nodes(levels)
        
        # اكتشاف الفراغات
        single_prints = self._find_single_prints(levels)
        
        # Poor High / Poor Low
        poor_high = self._is_poor_boundary(levels, 'high')
        poor_low = self._is_poor_boundary(levels, 'low')
        
        # Excess
        excess = self._find_excess(levels, highs, lows)
        
        # حالة التوازن
        balance = self._assess_balance(levels, value_area)
        
        # 🟡 تعديل 6: Naked POC
        naked_poc, bars_since = self._detect_naked_poc(poc, closes, highs, lows)
        
        # تحديث التاريخ
        self.previous_value_areas.append(value_area)
        self.previous_pocs.append(poc)
        
        profile = VolumeProfile(
            levels=levels, value_area=value_area, poc=poc,
            total_volume=sum(l.total_volume for l in levels),
            total_tpos=sum(l.tpo_count for l in levels),
            high_volume_nodes=high_vol_nodes, low_volume_nodes=low_vol_nodes,
            single_prints=single_prints, poor_high=poor_high, poor_low=poor_low,
            excess_points=excess, distribution_type=distribution_type,
            balance_state=balance,
            poc_migration=poc_migration, poc_migration_distance=poc_migration_distance,
            naked_poc=naked_poc, bars_since_poc_touched=bars_since,
        )
        
        return {
            "profile": profile, "levels": levels, "value_area": value_area,
            "poc": poc, "distribution_type": distribution_type, "balance_state": balance,
        }
    
    def _build_price_levels(self, highs: np.ndarray, lows: np.ndarray,
                            closes: np.ndarray, volumes: np.ndarray, 
                            opens: np.ndarray, precision: int) -> List[PriceLevel]:
        """
        🔴 تعديل 1: بناء المستويات السعرية بتوزيع VWAP-like
        
        بدل التوزيع المتساوي، الحجم يتركز عند:
        - سعر الإغلاق (الأكثر أهمية)
        - سعر الافتتاح
        - Point of Control الطبيعي
        """
        if len(highs) == 0:
            return []
        
        avg_range = np.mean(highs - lows)
        current_price = closes[-1] if len(closes) > 0 else 1.0
        tick_size = self._calculate_tick_size(avg_range, current_price)
        
        price_min = min(lows) - tick_size * 2
        price_max = max(highs) + tick_size * 2
        
        num_levels = int((price_max - price_min) / tick_size) + 1
        level_prices = np.linspace(price_min, price_max, num_levels)
        
        level_data = defaultdict(lambda: {'volume': 0.0, 'tpo_count': 0, 'vwap_weight': 0.0})
        
        for i in range(len(highs)):
            bar_low = lows[i]
            bar_high = highs[i]
            bar_volume = volumes[i] if i < len(volumes) else 0.0
            bar_close = closes[i] if i < len(closes) else bar_low
            bar_open = opens[i] if i < len(opens) else bar_low
            bar_range = bar_high - bar_low
            
            if bar_range == 0:
                level_idx = int((bar_low - price_min) / tick_size)
                if 0 <= level_idx < num_levels:
                    level_data[level_idx]['volume'] += bar_volume
                    level_data[level_idx]['tpo_count'] += 1
            else:
                # 🔴 تعديل 1: توزيع VWAP-like
                # الحجم يتركز حول الإغلاق والافتتاح
                for j, price in enumerate(level_prices):
                    if bar_low <= price <= bar_high:
                        # وزن VWAP: كلما اقترب السعر من الإغلاق، زاد الوزن
                        distance_to_close = abs(price - bar_close) / bar_range if bar_range > 0 else 0
                        distance_to_open = abs(price - bar_open) / bar_range if bar_range > 0 else 0
                        
                        # وزن مركب: 50% إغلاق + 30% افتتاح + 20% متوسط
                        close_weight = max(0, 1.0 - distance_to_close * 3)
                        open_weight = max(0, 1.0 - distance_to_open * 2) * 0.6
                        mid_weight = 0.2
                        
                        total_weight = close_weight * 0.5 + open_weight * 0.3 + mid_weight * 0.2
                        
                        # توزيع الحجم
                        vol_allocation = bar_volume * total_weight * (tick_size / bar_range)
                        
                        level_data[j]['volume'] += vol_allocation
                        level_data[j]['tpo_count'] += 1
                        level_data[j]['vwap_weight'] += total_weight
        
        # بناء القائمة
        total_vol = sum(d['volume'] for d in level_data.values())
        
        levels = []
        for j, price in enumerate(level_prices):
            if j in level_data:
                data = level_data[j]
                levels.append(PriceLevel(
                    price=round(price, precision),
                    total_volume=data['volume'],
                    tpo_count=data['tpo_count'],
                    volume_share=data['volume'] / total_vol if total_vol > 0 else 0.0,
                    is_poc=False,
                    is_value_area=False,
                    vwap_component=data['vwap_weight'],
                ))
        
        return levels
    
    def _calculate_tick_size(self, avg_range: float, current_price: float) -> float:
        """حساب حجم الخطوة السعرية ديناميكياً"""
        if current_price > 10000:
            base = 1.0
        elif current_price > 1000:
            base = 0.5
        elif current_price > 100:
            base = 0.1
        elif current_price > 10:
            base = 0.05
        else:
            base = 0.001
        
        adjustment = avg_range / max(current_price, 0.0001) * 10
        tick = base * max(0.5, min(2.0, adjustment))
        
        return tick
    
    def _find_poc(self, levels: List[PriceLevel]) -> float:
        """إيجاد نقطة التحكم (POC)"""
        if not levels:
            return 0.0
        
        max_tpo_level = max(levels, key=lambda l: l.tpo_count)
        max_tpo_level.is_poc = True
        
        max_vol_level = max(levels, key=lambda l: l.total_volume)
        if max_vol_level.price != max_tpo_level.price:
            max_vol_level.is_poc = True
        
        return max_tpo_level.price
    
    def _track_poc_migration(self, current_poc: float) -> Tuple[str, float]:
        """
        🟡 تعديل 4: POC Migration tracking
        
        يتتبع حركة POC عبر الجلسات
        """
        if len(self.previous_pocs) < 2:
            return 'stable', 0.0
        
        prev_poc = self.previous_pocs[-1]
        
        if prev_poc == 0:
            return 'stable', 0.0
        
        distance_pct = (current_poc - prev_poc) / prev_poc * 100
        
        if distance_pct > 0.5:
            return 'migrating_up', distance_pct
        elif distance_pct < -0.5:
            return 'migrating_down', abs(distance_pct)
        else:
            return 'stable', abs(distance_pct)
    
    def _calculate_va_overlap(self, current_va: ValueArea):
        """
        🟡 تعديل 5: Value Area Overlap مع الجلسات السابقة
        
        تداخل VA = استمرار. عدم تداخل = اتجاه جديد
        """
        if not self.previous_value_areas:
            current_va.overlap_with_previous = 0.0
            current_va.overlap_description = "لا يوجد VA سابق"
            return
        
        prev_va = self.previous_value_areas[-1]
        
        # حساب التداخل
        overlap_top = min(current_va.high, prev_va.high)
        overlap_bottom = max(current_va.low, prev_va.low)
        
        if overlap_top > overlap_bottom:
            overlap_range = overlap_top - overlap_bottom
            current_range = current_va.high - current_va.low
            
            if current_range > 0:
                overlap_pct = overlap_range / current_range
            else:
                overlap_pct = 0.0
            
            current_va.overlap_with_previous = overlap_pct
            
            if overlap_pct > 0.7:
                current_va.overlap_description = "تداخل عالي - استمرار"
            elif overlap_pct > 0.3:
                current_va.overlap_description = "تداخل جزئي - تحول"
            else:
                current_va.overlap_description = "تداخل منخفض - اتجاه جديد"
        else:
            current_va.overlap_with_previous = 0.0
            current_va.overlap_description = "لا تداخل - اتجاه جديد تماماً"
    
    def _detect_naked_poc(self, poc: float, closes: np.ndarray,
                           highs: np.ndarray, lows: np.ndarray) -> Tuple[bool, int]:
        """
        🟡 تعديل 6: Naked POC detection
        
        POC لم يُختبر منذ فترة = مغناطيس قوي للسعر
        """
        if len(closes) < 5:
            return False, 0
        
        # البحث عن آخر مرة لمس السعر POC
        bars_since = 0
        for i in range(len(closes) - 1, -1, -1):
            if lows[i] <= poc <= highs[i]:
                break
            bars_since += 1
        
        # Naked = أكثر من 10 شموع دون لمس
        is_naked = bars_since >= 10
        
        # تحديث تاريخ اللمس
        self.poc_touch_history.append(bars_since == 0)
        
        return is_naked, bars_since
    
    def _build_dynamic_value_area(self, levels: List[PriceLevel], 
                                   poc: float) -> ValueArea:
        """بناء منطقة القيمة ديناميكياً"""
        if not levels:
            return ValueArea(0, 0, 0, 0, 0, 0, 0, 'none')
        
        sorted_by_importance = sorted(levels, 
            key=lambda l: l.tpo_count * 0.6 + l.volume_share * 100 * 0.4, reverse=True)
        
        total_volume = sum(l.total_volume for l in levels)
        total_tpo = sum(l.tpo_count for l in levels)
        
        if total_tpo == 0:
            return ValueArea(max(l.price for l in levels), min(l.price for l in levels),
                           poc, total_volume, 0, 0, len(levels), 'flat')
        
        tpo_values = [l.tpo_count for l in levels if l.tpo_count > 0]
        if len(tpo_values) > 1:
            tpo_std = np.std(tpo_values)
            tpo_mean = np.mean(tpo_values)
            if tpo_mean > 0:
                concentration = tpo_std / tpo_mean
                target_pct = max(0.55, min(0.80, 0.70 - concentration * 0.1))
            else:
                target_pct = 0.70
        else:
            target_pct = 0.70
        
        va_levels = []
        va_volume = 0.0
        va_tpo = 0
        
        poc_levels = [l for l in levels if l.is_poc]
        for pl in poc_levels:
            if pl not in va_levels:
                va_levels.append(pl)
                va_volume += pl.total_volume
                va_tpo += pl.tpo_count
                pl.is_value_area = True
        
        all_levels_sorted = sorted(levels, 
            key=lambda l: (abs(l.price - poc) * 0.4 - l.tpo_count * 0.6))
        
        for level in all_levels_sorted:
            if level in va_levels:
                continue
            
            current_pct = va_tpo / total_tpo if total_tpo > 0 else 0
            if current_pct >= target_pct:
                break
            
            va_levels.append(level)
            va_volume += level.total_volume
            va_tpo += level.tpo_count
            level.is_value_area = True
        
        va_high = max(l.price for l in va_levels) if va_levels else poc
        va_low = min(l.price for l in va_levels) if va_levels else poc
        
        return ValueArea(
            high=va_high, low=va_low, poc=poc,
            total_volume=total_volume, volume_inside=va_volume,
            volume_percentage=va_tpo / total_tpo if total_tpo > 0 else 0,
            levels_count=len(va_levels),
            shape=self._determine_va_shape(levels, va_low, va_high, poc),
        )
    
    def _determine_va_shape(self, levels: List[PriceLevel], va_low: float,
                             va_high: float, poc: float) -> str:
        """تحديد شكل Value Area"""
        mid = (va_low + va_high) / 2
        
        if va_high == va_low:
            return 'single_price'
        
        if abs(poc - mid) < (va_high - va_low) * 0.1:
            return 'bell_curve'
        elif poc > mid:
            return 'p_shape'
        else:
            return 'b_shape'
    
    def _analyze_distribution(self, levels: List[PriceLevel]) -> str:
        """تحليل شكل توزيع الحجم"""
        if len(levels) < 5:
            return 'insufficient'
        
        tpo_values = [l.tpo_count for l in levels]
        
        peaks = []
        for i in range(2, len(tpo_values) - 2):
            if (tpo_values[i] > tpo_values[i-1] and tpo_values[i] > tpo_values[i-2] and
                tpo_values[i] > tpo_values[i+1] and tpo_values[i] > tpo_values[i+2]):
                peaks.append(i)
        
        if len(peaks) == 1:
            peak_pos = peaks[0] / len(levels)
            if 0.4 < peak_pos < 0.6:
                return 'normal'
            elif peak_pos <= 0.4:
                return 'skewed_down'
            else:
                return 'skewed_up'
        elif len(peaks) == 2:
            return 'double_distribution'
        elif len(peaks) >= 3:
            return 'multi_modal'
        
        tpo_std = np.std(tpo_values)
        tpo_mean = np.mean(tpo_values) if np.mean(tpo_values) > 0 else 1
        if tpo_std / tpo_mean < 0.2:
            return 'flat'
        
        return 'irregular'
    
    def _find_volume_nodes(self, levels: List[PriceLevel]) -> Tuple[List[float], List[float]]:
        """اكتشاف عقد الحجم المرتفعة والمنخفضة"""
        if len(levels) < 5:
            return [], []
        
        avg_volume = np.mean([l.total_volume for l in levels])
        avg_tpo = np.mean([l.tpo_count for l in levels])
        
        high_nodes = []
        low_nodes = []
        
        for level in levels:
            if level.tpo_count > avg_tpo * 1.8 or level.total_volume > avg_volume * 2.0:
                high_nodes.append(level.price)
            
            if level.tpo_count < avg_tpo * 0.25 and level.total_volume < avg_volume * 0.3:
                low_nodes.append(level.price)
        
        return high_nodes, low_nodes
    
    def _find_single_prints(self, levels: List[PriceLevel]) -> List[float]:
        """اكتشاف Single Prints"""
        return [l.price for l in levels if l.tpo_count == 1]
    
    def _is_poor_boundary(self, levels: List[PriceLevel], boundary: str) -> bool:
        """Poor High / Poor Low"""
        if len(levels) < 5:
            return False
        
        if boundary == 'high':
            top_levels = sorted(levels, key=lambda l: l.price, reverse=True)[:3]
        else:
            top_levels = sorted(levels, key=lambda l: l.price)[:3]
        
        avg_boundary_vol = np.mean([l.total_volume for l in top_levels]) if top_levels else 0.0
        avg_vol = np.mean([l.total_volume for l in levels]) if levels else 1.0
        
        if avg_vol == 0:
            return False
        
        return (avg_boundary_vol / avg_vol) < 0.3
    
    def _find_excess(self, levels: List[PriceLevel], highs: np.ndarray,
                     lows: np.ndarray) -> List[float]:
        """اكتشاف التجاوزات"""
        excess = []
        
        if len(levels) < 10:
            return excess
        
        avg_tpo = np.mean([l.tpo_count for l in levels])
        
        top_10pct = sorted(levels, key=lambda l: l.price, reverse=True)[:max(1, len(levels)//10)]
        bottom_10pct = sorted(levels, key=lambda l: l.price)[:max(1, len(levels)//10)]
        
        for level in top_10pct:
            if level.tpo_count < avg_tpo * 0.3:
                excess.append(level.price)
        
        for level in bottom_10pct:
            if level.tpo_count < avg_tpo * 0.3:
                excess.append(level.price)
        
        return excess
    
    def _assess_balance(self, levels: List[PriceLevel], value_area: ValueArea) -> str:
        """تقييم حالة التوازن"""
        if value_area.volume_percentage > 0.75:
            return 'balanced'
        
        above_poc_vol = sum(l.total_volume for l in levels if l.price > value_area.poc)
        below_poc_vol = sum(l.total_volume for l in levels if l.price < value_area.poc)
        
        if above_poc_vol > 0 and below_poc_vol > 0:
            ratio = above_poc_vol / below_poc_vol
        else:
            ratio = 1.0
        
        if ratio > 2.0:
            return 'imbalance_up'
        elif ratio < 0.5:
            return 'imbalance_down'
        elif 0.6 < ratio < 1.6:
            return 'balanced'
        else:
            return 'transition'


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: محلل النشاط المبادر والمستجيب (Activity Analyzer)   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ActivityAnalyzer:
    """
    يميز بين النشاط المبادر (Initiative) والمستجيب (Responsive).
    """
    
    def analyze(self, profile: VolumeProfile, closes: np.ndarray,
                volumes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Dict:
        """تحليل النشاط"""
        initiative = self._detect_initiative_activity(profile, closes, volumes, highs, lows)
        responsive = self._detect_responsive_activity(profile, closes, volumes, highs, lows)
        
        return {
            "initiative": initiative,
            "responsive": responsive,
            "dominant_activity": "initiative" if initiative['strength'] > responsive['strength'] else "responsive",
            "breakout_attempts": self._count_breakout_attempts(profile, highs, lows, closes),
        }
    
    def _detect_initiative_activity(self, profile: VolumeProfile, closes: np.ndarray,
                                     volumes: np.ndarray, highs: np.ndarray,
                                     lows: np.ndarray) -> Dict:
        """اكتشاف النشاط المبادر"""
        if len(closes) < 5:
            return {"detected": False, "strength": 0}
        
        va_high = profile.value_area.high
        va_low = profile.value_area.low
        
        initiative_count = 0
        initiative_volume = 0.0
        total_volume = sum(volumes[-20:]) if len(volumes) >= 20 else sum(volumes)
        
        for i in range(max(0, len(closes)-20), len(closes)):
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                continue
            
            outside_va = highs[i] > va_high or lows[i] < va_low
            
            if outside_va:
                avg_vol = np.mean(volumes[max(0,i-15):i]) if i >= 5 else volumes[i]
                if avg_vol > 0 and volumes[i] > avg_vol * 1.3:
                    initiative_count += 1
                    initiative_volume += volumes[i]
        
        strength = initiative_volume / total_volume if total_volume > 0 else 0
        
        return {
            "detected": initiative_count >= 2,
            "count": initiative_count,
            "volume_share": strength,
            "strength": min(1.0, strength * 3),
            "direction": 'up' if closes[-1] > va_high else 'down' if closes[-1] < va_low else 'neutral',
        }
    
    def _detect_responsive_activity(self, profile: VolumeProfile, closes: np.ndarray,
                                     volumes: np.ndarray, highs: np.ndarray,
                                     lows: np.ndarray) -> Dict:
        """اكتشاف النشاط المستجيب"""
        if len(closes) < 5:
            return {"detected": False, "strength": 0}
        
        va_high = profile.value_area.high
        va_low = profile.value_area.low
        
        responsive_count = 0
        
        for i in range(1, len(closes)):
            prev_outside = (highs[i-1] > va_high and closes[i-1] > va_high) or \
                          (lows[i-1] < va_low and closes[i-1] < va_low)
            curr_inside = va_low <= closes[i] <= va_high
            
            if prev_outside and curr_inside:
                responsive_count += 1
        
        return {
            "detected": responsive_count >= 2,
            "count": responsive_count,
            "strength": min(1.0, responsive_count * 0.25),
        }
    
    def _count_breakout_attempts(self, profile: VolumeProfile, highs: np.ndarray,
                                  lows: np.ndarray, closes: np.ndarray) -> Dict:
        """إحصاء محاولات الاختراق"""
        va_high = profile.value_area.high
        va_low = profile.value_area.low
        
        attempts_high = 0
        attempts_low = 0
        successful_high = 0
        successful_low = 0
        
        for i in range(len(closes)):
            if highs[i] > va_high:
                attempts_high += 1
                if closes[i] > va_high:
                    successful_high += 1
            
            if lows[i] < va_low:
                attempts_low += 1
                if closes[i] < va_low:
                    successful_low += 1
        
        return {
            "up_attempts": attempts_high,
            "up_successful": successful_high,
            "up_success_rate": successful_high / max(attempts_high, 1),
            "down_attempts": attempts_low,
            "down_successful": successful_low,
            "down_success_rate": successful_low / max(attempts_low, 1),
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثالثة: محلل الأيام والجلسات (Session/Day Analyzer) محسن    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SessionAnalyzer:
    """
    يحلل نوع اليوم/الجلسة من منظور Market Profile.
    
    🔴 تعديل 3: current_price و current_open يمرران كمعاملات
    """
    
    def analyze(self, profile: VolumeProfile, opens: np.ndarray, closes: np.ndarray,
                highs: np.ndarray, lows: np.ndarray) -> Dict:
        """تحديد نوع الجلسة"""
        
        # 🔴 تعديل 3: استخدام current_price و current_open الصحيحين
        current_price = closes[-1] if len(closes) > 0 else 0.0
        current_open = opens[-1] if len(opens) > 0 else current_price
        
        day_type = self._determine_day_type(profile, current_open, current_price)
        initial_balance = self._calculate_initial_balance(highs, lows, opens)
        range_extension = self._calculate_range_extension(profile, closes)
        
        return {
            "day_type": day_type,
            "initial_balance": initial_balance,
            "range_extension": range_extension,
            "day_structure": self._analyze_day_structure(profile, current_open, current_price),
        }
    
    def _determine_day_type(self, profile: VolumeProfile, open_price: float,
                            close_price: float) -> str:
        """تحديد نوع اليوم"""
        va_range = profile.value_area.high - profile.value_area.low
        
        if va_range == 0:
            return 'unknown'
        
        if profile.distribution_type == 'double_distribution':
            return 'double_distribution_day'
        
        if profile.balance_state == 'balanced':
            if abs(close_price - open_price) < va_range * 0.3:
                return 'neutral_day'
            else:
                return 'normal_day'
        
        if profile.balance_state == 'imbalance_up':
            return 'trend_day_up' if profile.poor_low else 'normal_variation_up'
        
        if profile.balance_state == 'imbalance_down':
            return 'trend_day_down' if profile.poor_high else 'normal_variation_down'
        
        return 'unknown'
    
    def _calculate_initial_balance(self, highs: np.ndarray, lows: np.ndarray,
                                    opens: np.ndarray) -> Tuple[float, float]:
        """حساب التوازن الأولي"""
        if len(highs) < 3:
            return (0.0, 0.0)
        
        ib_length = max(2, len(highs) // 5)
        ib_high = max(highs[:ib_length])
        ib_low = min(lows[:ib_length])
        
        return (ib_high, ib_low)
    
    def _calculate_range_extension(self, profile: VolumeProfile, closes: np.ndarray) -> float:
        """حساب امتداد النطاق"""
        if len(closes) < 2:
            return 0.0
        
        return closes[-1] - closes[0]
    
    def _analyze_day_structure(self, profile: VolumeProfile, open_price: float,
                                close_price: float) -> Dict:
        """
        🔴 تعديل 3: تحليل هيكل اليوم بمعاملات صحيحة
        """
        va_high = profile.value_area.high
        va_low = profile.value_area.low
        poc = profile.poc
        
        open_in_va = va_low <= open_price <= va_high
        close_in_va = va_low <= close_price <= va_high
        open_vs_close = close_price - open_price
        
        va_range = va_high - va_low
        if va_range > 0:
            poc_position = (poc - va_low) / va_range
        else:
            poc_position = 0.5
        
        return {
            "open_in_va": open_in_va,
            "close_in_va": close_in_va,
            "open_vs_close": open_vs_close,
            "poc_position": poc_position,
            "poc_description": "في المنتصف" if 0.4 < poc_position < 0.6 else "في الأعلى" if poc_position >= 0.6 else "في الأسفل",
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية Market Profile الموحدة (محسنة)   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MarketProfileStrategy:
    """
    استراتيجية Market Profile الديناميكية الكاملة - الإصدار 2.0
    
    تجمع:
    - بروفايل الحجم الديناميكي مع توزيع VWAP-like
    - POC Migration tracking
    - Value Area Overlap
    - Naked POC detection
    - Volume Holes في القرار
    - تحليل النشاط المبادر والمستجيب
    """
    
    def __init__(self):
        self.profile_builder = DynamicVolumeProfileBuilder()
        self.activity_analyzer = ActivityAnalyzer()
        self.session_analyzer = SessionAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 15:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 15 شمعة على الأقل"}
        
        # 🔴 تعديل 2: current_price من closes مباشرة
        current_price = closes[-1]
        
        profile_data = self.profile_builder.analyze(highs, lows, closes, volumes, opens)
        profile = profile_data.get('profile')
        activity_data = self.activity_analyzer.analyze(profile, closes, volumes, highs, lows)
        session_data = self.session_analyzer.analyze(profile, opens, closes, highs, lows)
        decision = self._make_decision(profile_data, activity_data, session_data, current_price)
        
        return {**decision, "profile_data": profile_data, "activity_data": activity_data, "session_data": session_data}
    
    def _make_decision(self, profile_data: Dict, activity_data: Dict,
                       session_data: Dict, current_price: float) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        profile = profile_data.get('profile')
        value_area = profile_data.get('value_area')
        balance_state = profile_data.get('balance_state')
        distribution_type = profile_data.get('distribution_type')
        
        if not profile:
            return {"recommendation": "محايد", "confidence": 20, "reason": "لا بيانات"}
        
        va_high = value_area.high
        va_low = value_area.low
        poc = profile.poc
        
        # ---- من POC Migration ----
        if profile.poc_migration == 'migrating_up':
            buy_signals.append((f"POC يهاجر للأعلى ({profile.poc_migration_distance:.1f}%)", 0.55))
        elif profile.poc_migration == 'migrating_down':
            sell_signals.append((f"POC يهاجر للأسفل ({profile.poc_migration_distance:.1f}%)", 0.55))
        
        # ---- من Value Area Overlap ----
        if value_area.overlap_with_previous > 0.7:
            if balance_state == 'balanced':
                buy_signals.append(("تداخل VA عالي - استمرار التوازن", 0.3))
        elif value_area.overlap_with_previous < 0.3 and value_area.overlap_with_previous > 0:
            warnings.append("تداخل VA منخفض - اتجاه جديد يتشكل")
        
        # ---- من Naked POC ----
        if profile.naked_poc:
            if current_price < poc:
                buy_signals.append((f"POC عاري ({profile.bars_since_poc_touched} شمعة) - جاذبية صاعدة", 0.55))
            elif current_price > poc:
                sell_signals.append((f"POC عاري ({profile.bars_since_poc_touched} شمعة) - جاذبية هابطة", 0.55))
        
        # ---- من Volume Holes (Low Volume Nodes) ----
        if profile.low_volume_nodes:
            lvn_above = [n for n in profile.low_volume_nodes if n > current_price]
            lvn_below = [n for n in profile.low_volume_nodes if n < current_price]
            
            if lvn_above:
                buy_signals.append(("ثقوب حجم علوية - السعر سيتحرك بسرعة للأعلى", 0.5))
            if lvn_below:
                sell_signals.append(("ثقوب حجم سفلية - السعر سيتحرك بسرعة للأسفل", 0.5))
        
        # ---- من حالة التوازن ----
        if balance_state == 'balanced':
            if current_price >= va_high * 0.99:
                sell_signals.append(("عند قمة VA في سوق متوازن - بيع للارتداد", 0.6))
            elif current_price <= va_low * 1.01:
                buy_signals.append(("عند قاع VA في سوق متوازن - شراء للارتداد", 0.6))
            else:
                buy_signals.append(("داخل VA في سوق متوازن - انتظار", 0.15))
                sell_signals.append(("داخل VA في سوق متوازن - انتظار", 0.15))
        
        elif balance_state == 'imbalance_up':
            if current_price > va_high:
                buy_signals.append(("اختراق VA للأعلى - استمرار صاعد", 0.7))
            elif current_price > poc:
                buy_signals.append(("فوق POC في سوق غير متوازن صاعداً", 0.55))
        
        elif balance_state == 'imbalance_down':
            if current_price < va_low:
                sell_signals.append(("كسر VA للأسفل - استمرار هابط", 0.7))
            elif current_price < poc:
                sell_signals.append(("تحت POC في سوق غير متوازن هابطاً", 0.55))
        
        # ---- من Poor High/Low ----
        if profile.poor_high and current_price > va_high:
            buy_signals.append(("Poor High - مقاومة ضعيفة - اختراق وشيك", 0.65))
        if profile.poor_low and current_price < va_low:
            sell_signals.append(("Poor Low - دعم ضعيف - كسر وشيك", 0.65))
        
        # ---- من Excess ----
        if profile.excess_points:
            excess_near = any(abs(current_price - ep) < current_price * 0.005 for ep in profile.excess_points)
            if excess_near:
                if current_price > va_high:
                    sell_signals.append(("Excess علوي - رفض سعري - انعكاس هابط", 0.7))
                elif current_price < va_low:
                    buy_signals.append(("Excess سفلي - رفض سعري - انعكاس صاعد", 0.7))
        
        # ---- من Single Prints ----
        if profile.single_prints:
            sp_above = [sp for sp in profile.single_prints if sp > va_high]
            sp_below = [sp for sp in profile.single_prints if sp < va_low]
            if sp_above:
                sell_signals.append(("Single Prints علوية - منطقة فراغ - السعر سيعود لملئها", 0.6))
            if sp_below:
                buy_signals.append(("Single Prints سفلية - منطقة فراغ - السعر سيعود لملئها", 0.6))
        
        # ---- من النشاط ----
        initiative = activity_data.get('initiative', {})
        responsive = activity_data.get('responsive', {})
        
        if initiative.get('detected'):
            if initiative.get('direction') == 'up':
                buy_signals.append(("نشاط مبادر صاعد", 0.5))
            elif initiative.get('direction') == 'down':
                sell_signals.append(("نشاط مبادر هابط", 0.5))
        
        if responsive.get('detected'):
            if current_price > va_high:
                sell_signals.append(("نشاط مستجيب - فشل اختراق علوي", 0.65))
            elif current_price < va_low:
                buy_signals.append(("نشاط مستجيب - فشل اختراق سفلي", 0.65))
        
        # ---- من التوزيع ----
        if distribution_type == 'double_distribution':
            if current_price > va_high:
                buy_signals.append(("توزيع مزدوج - اختراق لمنطقة جديدة", 0.6))
            elif current_price < va_low:
                sell_signals.append(("توزيع مزدوج - هبوط لمنطقة جديدة", 0.6))
        
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
        reason += f" | VA:[{va_low:.2f}-{va_high:.2f}] POC:{poc:.2f}"
        
        if profile.naked_poc:
            reason += f" | NakedPOC"
        if profile.poc_migration != 'stable':
            reason += f" | POC:{profile.poc_migration}"
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "balance": balance_state,
            "warnings": warnings,
        }


def create_market_profile_strategy():
    """إنشاء استراتيجية Market Profile الجاهزة (الإصدار 2.0)"""
    return MarketProfileStrategy()