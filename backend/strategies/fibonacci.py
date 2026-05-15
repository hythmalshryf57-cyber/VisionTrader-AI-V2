"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC FIBONACCI STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثامنة عشرة: فيبوناتشي الديناميكي
═══════════════════════════════════════════════════════════════════════════════

ليوناردو فيبوناتشي (1170-1250) اكتشف المتوالية الذهبية.
الأسواق تحترم هذه النسب... لكن ليس دائماً بنفس الطريقة.

النسخة الكلاسيكية: 23.6%, 38.2%, 50%, 61.8%, 78.6%, 127.2%, 161.8%
لكن السوق يختار أي نسبة يحترمها اليوم.

هذه النسخة ديناميكية بالكامل - محسنة بـ 6 تعديلات:
- النسب "المفضلة" تُكتشف من حركة السوق نفسه
- Fibonacci Time Zones
- Fibonacci + Trend Filter
- ATR-based tolerance
- إصلاح return مزدوج
- Auto-Fib محسن

المفاهيم المتقدمة:
1. Fibonacci Retracement / Extension / Expansion
2. Fibonacci Time Zones
3. Fibonacci Confluence (مناطق الالتقاء)
4. Fibonacci + Trend Filter
5. Auto-Fib (رسم تلقائي)
6. Dynamic Fibonacci Levels
7. Fibonacci Cluster Analysis
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class FibonacciLevel:
    """مستوى فيبوناتشي - محسن"""
    price: float
    ratio: float
    level_type: str
    source_swing_start: float
    source_swing_end: float
    strength: float
    touches: int
    last_touch_index: int
    active: bool
    # 🟡 تعديل 4: Fibonacci Time Zone
    time_projection: int = 0


@dataclass
class FibonacciZone:
    """منطقة فيبوناتشي"""
    price_low: float
    price_high: float
    ratios_in_zone: List[float]
    zone_type: str
    confluence_count: int
    strength: float
    description: str
    # 🟡 تعديل 5: Trend confirmation
    trend_aligned: bool = False


@dataclass
class SwingPair:
    """زوج قمة-قاع"""
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    direction: str
    magnitude: float
    significance: float


@dataclass
class FibSignal:
    """إشارة فيبوناتشي"""
    index: int
    signal_type: str
    direction: str
    price_level: float
    ratio: float
    strength: float
    description: str
    # 🟡 تعديل 5: Trend aligned
    trend_aligned: bool = False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: مكتشف التأرجحات الذكية (محسن)                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SmartSwingFinder:
    """
    يكتشف القمم والقيعان المهمة فقط.
    
    🔴 تعديل 1: إصلاح return مزدوج
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """اكتشاف التأرجحات المهمة"""
        swings = self._find_significant_swings(highs, lows, closes, volumes)
        pairs = self._create_swing_pairs(swings)
        active_swing = self._get_active_swing(pairs, closes)
        
        return {
            "swings": swings[-10:],
            "pairs": pairs[-5:],
            "active_swing": active_swing,
            "primary_swing": self._find_primary_swing(pairs),
            "secondary_swing": self._find_secondary_swing(pairs),
        }
    
    def _find_significant_swings(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> List[Dict]:
        """إيجاد التأرجحات المهمة فقط"""
        swings = []
        
        if len(highs) < 10:
            return swings
        
        for i in range(3, len(highs) - 3):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i-3] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2] and highs[i] > highs[i+3]):
                
                left_low = min(lows[max(0,i-10):i])
                significance = self._measure_swing_significance(left_low, highs[i], 
                                                                 volumes[max(0,i-5):i+1])
                
                if significance > 0.3:
                    swings.append({"index": i, "price": highs[i], "type": "peak",
                                   "significance": significance})
            
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i-3] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2] and lows[i] < lows[i+3]):
                
                right_high = max(highs[max(0,i-10):i])
                significance = self._measure_swing_significance(lows[i], right_high,
                                                                 volumes[max(0,i-5):i+1])
                
                if significance > 0.3:
                    swings.append({"index": i, "price": lows[i], "type": "trough",
                                   "significance": significance})
        
        return swings
    
    def _measure_swing_significance(self, low: float, high: float, 
                                      volumes: np.ndarray) -> float:
        """قياس أهمية التأرجح"""
        if low == 0:
            return 0.0
        
        move_size = (high - low) / low
        vol_factor = np.mean(volumes) / max(np.mean(volumes), 0.0001) if len(volumes) > 0 else 1.0
        
        return min(1.0, move_size * 10.0 + vol_factor * 0.2)
    
    def _create_swing_pairs(self, swings: List[Dict]) -> List[SwingPair]:
        """إنشاء أزواج قمة-قاع"""
        pairs = []
        
        for i in range(1, len(swings)):
            s1, s2 = swings[i-1], swings[i]
            
            if s1["type"] == "peak" and s2["type"] == "trough":
                direction = "down"
                start_price, end_price = s1["price"], s2["price"]
            elif s1["type"] == "trough" and s2["type"] == "peak":
                direction = "up"
                start_price, end_price = s1["price"], s2["price"]
            else:
                continue
            
            magnitude = abs(end_price - start_price)
            
            pairs.append(SwingPair(
                start_idx=s1["index"], end_idx=s2["index"],
                start_price=start_price, end_price=end_price,
                direction=direction, magnitude=magnitude,
                significance=(s1["significance"] + s2["significance"]) / 2.0,
            ))
        
        return pairs
    
    def _get_active_swing(self, pairs: List[SwingPair], closes: np.ndarray) -> Optional[SwingPair]:
        """
        🔴 تعديل 1: إصلاح return مزدوج - إرجاع واحد فقط
        """
        if not pairs:
            return None
        
        return pairs[-1]
    
    def _find_primary_swing(self, pairs: List[SwingPair]) -> Optional[SwingPair]:
        """التأرجح الرئيسي (الأكبر)"""
        if not pairs:
            return None
        
        recent = pairs[-10:] if len(pairs) >= 10 else pairs
        return max(recent, key=lambda p: p.magnitude * p.significance)
    
    def _find_secondary_swing(self, pairs: List[SwingPair]) -> Optional[SwingPair]:
        """التأرجح الثانوي"""
        if not pairs:
            return None
        
        recent = pairs[-10:] if len(pairs) >= 10 else pairs
        significant = [p for p in recent if p.significance > 0.5]
        if len(significant) >= 2:
            return sorted(significant, key=lambda p: p.magnitude, reverse=True)[1]
        
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: باني مستويات فيبوناتشي الديناميكية (محسن)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicFibonacciBuilder:
    """
    يبني مستويات فيبوناتشي ديناميكية.
    
    🔴 تعديل 3: ATR-based tolerance
    🟡 تعديل 4: Fibonacci Time Zones
    🟡 تعديل 5: Fibonacci + Trend Filter
    """
    
    RETRACEMENT_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.707, 0.786, 0.886]
    EXTENSION_RATIOS = [1.0, 1.272, 1.382, 1.5, 1.618, 2.0, 2.272, 2.618, 3.0, 3.618, 4.236]
    TIME_RATIOS = [0.382, 0.5, 0.618, 1.0, 1.272, 1.618, 2.0, 2.618]
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                swing_pairs: List[SwingPair], regime_data: Dict = None) -> Dict:
        """بناء مستويات فيبوناتشي"""
        
        # حساب ATR
        atr = self._calculate_atr(highs, lows, closes)
        
        all_levels = []
        for pair in swing_pairs[-5:]:
            levels = self._build_levels_from_swing(pair, highs, lows, closes, atr)
            all_levels.extend(levels)
        
        preferred_ratios = self._discover_preferred_ratios(all_levels, highs, lows, closes, atr)
        zones = self._cluster_levels(all_levels)
        
        # 🟡 تعديل 5: Trend Filter
        trend_direction = self._detect_trend(closes, regime_data)
        zones = self._apply_trend_filter(zones, trend_direction)
        
        # 🟡 تعديل 4: Fibonacci Time Zones
        time_zones = self._calculate_time_zones(swing_pairs)
        
        active_zones = self._find_active_zones(zones, closes[-1] if len(closes) > 0 else 0.0)
        
        return {
            "all_levels": all_levels,
            "preferred_ratios": preferred_ratios,
            "zones": zones[-10:],
            "active_zones": active_zones,
            "nearest_support": self._find_nearest_zone(zones, closes[-1], 'support') if len(closes) > 0 else None,
            "nearest_resistance": self._find_nearest_zone(zones, closes[-1], 'resistance') if len(closes) > 0 else None,
            "time_zones": time_zones,
            "trend_direction": trend_direction,
        }
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """حساب ATR"""
        if len(closes) < period:
            return np.mean(highs - lows)
        
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        
        return np.mean(tr[-period:])
    
    def _build_levels_from_swing(self, pair: SwingPair, highs: np.ndarray,
                                    lows: np.ndarray, closes: np.ndarray,
                                    atr: float) -> List[FibonacciLevel]:
        """بناء مستويات فيبوناتشي من زوج واحد"""
        levels = []
        
        start, end = pair.start_price, pair.end_price
        diff = end - start
        swing_duration = pair.end_idx - pair.start_idx
        
        # تصحيحات
        for ratio in self.RETRACEMENT_RATIOS:
            if pair.direction == "up":
                price = end - diff * ratio
            else:
                price = end + diff * ratio
            
            strength, touches, last_touch = self._measure_level_strength(
                price, pair.end_idx, highs, lows, closes, atr)
            
            # 🟡 تعديل 4: Fibonacci Time Zone
            time_proj = pair.end_idx + int(swing_duration * ratio)
            
            levels.append(FibonacciLevel(
                price=price, ratio=ratio, level_type="retracement",
                source_swing_start=start, source_swing_end=end,
                strength=strength, touches=touches,
                last_touch_index=last_touch, active=touches > 0,
                time_projection=time_proj,
            ))
        
        # امتدادات
        for ratio in self.EXTENSION_RATIOS:
            if pair.direction == "up":
                price = end + diff * ratio
            else:
                price = end - diff * ratio
            
            strength, touches, last_touch = self._measure_level_strength(
                price, pair.end_idx, highs, lows, closes, atr)
            
            time_proj = pair.end_idx + int(swing_duration * ratio)
            
            levels.append(FibonacciLevel(
                price=price, ratio=ratio, level_type="extension",
                source_swing_start=start, source_swing_end=end,
                strength=strength, touches=touches,
                last_touch_index=last_touch, active=touches > 0,
                time_projection=time_proj,
            ))
        
        return levels
    
    def _measure_level_strength(self, price: float, from_idx: int,
                                   highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, atr: float) -> Tuple[float, int, int]:
        """
        🔴 تعديل 3: ATR-based tolerance بدل price * 0.003 الثابت
        
        كان: tolerance = price * 0.003
        الآن: tolerance = atr * 0.3 (يتكيف مع التقلب)
        """
        touches = 0
        last_touch = from_idx
        
        # 🔴 تعديل 3: tolerance ديناميكي من ATR
        tolerance = max(price * 0.001, atr * 0.3)
        
        for i in range(from_idx + 1, len(closes)):
            if lows[i] <= price + tolerance and highs[i] >= price - tolerance:
                if (closes[i] > price and closes[i-1] < price) or \
                   (closes[i] < price and closes[i-1] > price) or \
                   abs(closes[i] - price) < tolerance:
                    touches += 1
                    last_touch = i
        
        strength = min(1.0, touches * 0.2)
        
        return strength, touches, last_touch
    
    def _discover_preferred_ratios(self, levels: List[FibonacciLevel],
                                      highs: np.ndarray, lows: np.ndarray,
                                      closes: np.ndarray, atr: float) -> Dict:
        """اكتشاف النسب المفضلة للسوق"""
        ratio_stats = defaultdict(lambda: {"touches": 0, "strength": 0.0, "count": 0})
        
        for level in levels:
            key = f"{level.ratio:.3f}"
            ratio_stats[key]["touches"] += level.touches
            ratio_stats[key]["strength"] += level.strength
            ratio_stats[key]["count"] += 1
        
        sorted_ratios = sorted(ratio_stats.items(), 
                               key=lambda x: x[1]["touches"] + x[1]["strength"] * 5,
                               reverse=True)
        
        preferred = {}
        for ratio_key, stats in sorted_ratios[:8]:
            preferred[ratio_key] = {
                "touches": stats["touches"],
                "strength": stats["strength"] / max(stats["count"], 1),
                "count": stats["count"],
            }
        
        return preferred
    
    def _calculate_time_zones(self, swing_pairs: List[SwingPair]) -> List[Dict]:
        """
        🟡 تعديل 4: Fibonacci Time Zones
        
        ليس فقط مستويات سعرية. أضف مناطق زمنية
        """
        time_zones = []
        
        for pair in swing_pairs[-3:]:
            duration = pair.end_idx - pair.start_idx
            if duration <= 0:
                continue
            
            for ratio in self.TIME_RATIOS:
                target_idx = pair.start_idx + int(duration * ratio)
                time_zones.append({
                    "start_idx": pair.start_idx,
                    "target_idx": target_idx,
                    "ratio": ratio,
                    "direction": pair.direction,
                    "description": f"منطقة زمنية {ratio:.1%} من الموجة",
                })
        
        return time_zones
    
    def _detect_trend(self, closes: np.ndarray, regime_data: Dict = None) -> str:
        """
        🟡 تعديل 5: اكتشاف الاتجاه
        """
        if regime_data:
            try:
                regime = regime_data.get('regime_data', {}).get('regime')
                if regime:
                    rt = str(regime.regime_type) if hasattr(regime, 'regime_type') else str(regime)
                    if 'BULL' in rt.upper():
                        return 'up'
                    elif 'BEAR' in rt.upper():
                        return 'down'
            except:
                pass
        
        if len(closes) < 20:
            return 'neutral'
        
        sma10 = np.mean(closes[-10:])
        sma20 = np.mean(closes[-20:])
        
        if sma10 > sma20 * 1.01:
            return 'up'
        elif sma10 < sma20 * 0.99:
            return 'down'
        return 'neutral'
    
    def _apply_trend_filter(self, zones: List[FibonacciZone], trend: str) -> List[FibonacciZone]:
        """
        🟡 تعديل 5: Fibonacci + Trend Filter
        
        في اتجاه صاعد: مناطق الدعم أقوى
        في اتجاه هابط: مناطق المقاومة أقوى
        """
        for zone in zones:
            if trend == 'up':
                if zone.zone_type in ['reversal', 'support']:
                    zone.trend_aligned = True
                    zone.strength *= 1.2
            elif trend == 'down':
                if zone.zone_type in ['reversal', 'resistance']:
                    zone.trend_aligned = True
                    zone.strength *= 1.2
        
        return zones
    
    def _cluster_levels(self, levels: List[FibonacciLevel]) -> List[FibonacciZone]:
        """تجميع المستويات المتقاربة في مناطق"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels, key=lambda l: l.price)
        zones = []
        current_cluster = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            current = sorted_levels[i]
            cluster_avg = np.mean([l.price for l in current_cluster])
            
            if abs(current.price - cluster_avg) < max(cluster_avg * 0.005, 0.0001):
                current_cluster.append(current)
            else:
                if len(current_cluster) >= 1:
                    zones.append(self._create_zone(current_cluster))
                current_cluster = [current]
        
        if current_cluster:
            zones.append(self._create_zone(current_cluster))
        
        return zones
    
    def _create_zone(self, cluster: List[FibonacciLevel]) -> FibonacciZone:
        """إنشاء منطقة من مجموعة مستويات"""
        prices = [l.price for l in cluster]
        ratios = [l.ratio for l in cluster]
        
        zone_low = min(prices)
        zone_high = max(prices)
        
        strength = min(1.0, len(cluster) * 0.2 + sum(l.strength for l in cluster) * 0.1)
        
        if "retracement" in [l.level_type for l in cluster]:
            zone_type = "reversal"
        else:
            zone_type = "extension_target"
        
        return FibonacciZone(
            price_low=zone_low, price_high=zone_high,
            ratios_in_zone=ratios, zone_type=zone_type,
            confluence_count=len(cluster), strength=strength,
            description=f"منطقة التقاء ({len(cluster)} مستويات)",
        )
    
    def _find_active_zones(self, zones: List[FibonacciZone], current_price: float) -> List[FibonacciZone]:
        """المناطق النشطة القريبة من السعر"""
        return [z for z in zones if abs(z.price_low - current_price) < current_price * 0.05]
    
    def _find_nearest_zone(self, zones: List[FibonacciZone], current_price: float,
                            zone_type: str) -> Optional[FibonacciZone]:
        """أقرب منطقة"""
        if zone_type == 'support':
            below = [z for z in zones if z.price_high < current_price]
            return max(below, key=lambda z: z.price_high) if below else None
        else:
            above = [z for z in zones if z.price_low > current_price]
            return min(above, key=lambda z: z.price_low) if above else None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية فيبوناتشي الموحدة (محسنة)           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicFibonacciStrategy:
    """
    استراتيجية فيبوناتشي الديناميكية الكاملة - الإصدار 2.0
    
    - النسب المفضلة ديناميكية
    - Fibonacci Time Zones
    - Fibonacci + Trend Filter
    - ATR-based tolerance
    - Auto-Fib محسن
    """
    
    def __init__(self):
        self.swing_finder = SmartSwingFinder()
        self.fib_builder = DynamicFibonacciBuilder()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        regime_data = chart_data.get('regime_data', None)
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        swing_data = self.swing_finder.analyze(highs, lows, closes, volumes)
        pairs = swing_data.get('pairs', [])
        fib_data = self.fib_builder.analyze(highs, lows, closes, pairs, regime_data)
        decision = self._make_decision(swing_data, fib_data, current_price)
        
        return {**decision, "swing_data": swing_data, "fib_data": fib_data}
    
    def _make_decision(self, swing_data: Dict, fib_data: Dict,
                       current_price: float) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        # ---- من مناطق الالتقاء ----
        nearest_support = fib_data.get('nearest_support')
        nearest_resistance = fib_data.get('nearest_resistance')
        trend = fib_data.get('trend_direction', 'neutral')
        
        if nearest_support and nearest_support.strength > 0.3:
            distance = (current_price - nearest_support.price_high) / max(current_price, 0.0001)
            weight = 0.6 * nearest_support.strength
            
            # 🟡 تعديل 5: Trend boost
            if nearest_support.trend_aligned:
                weight *= 1.3
            
            if distance < 0.01:
                buy_signals.append((f"منطقة دعم فيبوناتشي قوية ({nearest_support.confluence_count} مستويات)", weight))
            elif distance < 0.03:
                buy_signals.append((f"دعم فيبوناتشي قريب ({nearest_support.confluence_count} مستويات)", 0.4 * nearest_support.strength))
        
        if nearest_resistance and nearest_resistance.strength > 0.3:
            distance = (nearest_resistance.price_low - current_price) / max(current_price, 0.0001)
            weight = 0.6 * nearest_resistance.strength
            
            if nearest_resistance.trend_aligned:
                weight *= 1.3
            
            if distance < 0.01:
                sell_signals.append((f"منطقة مقاومة فيبوناتشي قوية ({nearest_resistance.confluence_count} مستويات)", weight))
            elif distance < 0.03:
                sell_signals.append((f"مقاومة فيبوناتشي قريبة ({nearest_resistance.confluence_count} مستويات)", 0.4 * nearest_resistance.strength))
        
        # ---- من النسب المفضلة ----
        preferred = fib_data.get('preferred_ratios', {})
        active_swing = swing_data.get('active_swing')
        
        if active_swing and preferred:
            diff = active_swing.end_price - active_swing.start_price
            
            for ratio_str, stats in preferred.items():
                ratio = float(ratio_str)
                if stats['strength'] > 0.3:
                    if active_swing.direction == 'up':
                        level = active_swing.end_price - diff * ratio
                    else:
                        level = active_swing.end_price + diff * ratio
                    
                    if abs(current_price - level) / max(current_price, 0.0001) < 0.005:
                        if level < current_price:
                            buy_signals.append((f"ارتداد من نسبة مفضلة {ratio:.1%}", 0.55))
                        else:
                            sell_signals.append((f"ارتداد من نسبة مفضلة {ratio:.1%}", 0.55))
        
        # ---- 🟡 تعديل 4: Fibonacci Time Zones ----
        time_zones = fib_data.get('time_zones', [])
        near_time_zone = [tz for tz in time_zones if abs(tz.get('target_idx', 0) - len(swing_data.get('swings', []))) <= 3]
        if near_time_zone:
            warnings.append(f"منطقة زمنية فيبوناتشي قريبة ({near_time_zone[0]['ratio']:.1%})")
        
        # ---- من الامتدادات ----
        if active_swing:
            diff = active_swing.end_price - active_swing.start_price
            
            if active_swing.direction == 'up' and current_price > active_swing.end_price:
                target = active_swing.end_price + diff * 1.618
                buy_signals.append((f"هدف امتداد 1.618: {target:.4f}", 0.4))
            elif active_swing.direction == 'down' and current_price < active_swing.end_price:
                target = active_swing.end_price - diff * 1.618
                sell_signals.append((f"هدف امتداد 1.618: {target:.4f}", 0.4))
        
        # ---- تحذير ضد الاتجاه ----
        if trend == 'up' and nearest_resistance:
            warnings.append("اتجاه صاعد - مقاومة فيبوناتشي قد تكون أضعف")
        elif trend == 'down' and nearest_support:
            warnings.append("اتجاه هابط - دعم فيبوناتشي قد يكون أضعف")
        
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
        
        if nearest_support:
            reason += f" | دعم: {nearest_support.price_high:.4f}"
        if nearest_resistance:
            reason += f" | مقاومة: {nearest_resistance.price_low:.4f}"
        reason += f" | اتجاه: {trend}"
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "warnings": warnings,
        }


def create_fibonacci_strategy():
    """إنشاء استراتيجية فيبوناتشي الديناميكية الجاهزة (الإصدار 2.0)"""
    return DynamicFibonacciStrategy()