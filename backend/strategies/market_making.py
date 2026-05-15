"""
═══════════════════════════════════════════════════════════════════════════════
MARKET MAKING & LIQUIDITY ENGINEERING - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثانية عشرة: صناعة السوق وهندسة السيولة
═══════════════════════════════════════════════════════════════════════════════

هذه المدرسة تنظر للسوق من منظور صانع السوق (Market Maker).
صانع السوق يرى السوق بشكل مختلف تماماً عن المتداول العادي.

الفلسفة:
صانع السوق لا يتنبأ. صانع السوق:
1. يوفر سيولة (يبيع ويشتري في نفس الوقت)
2. يجني الفارق (Spread)
3. يدير مخزونه (Inventory)
4. يحمي نفسه من الانزلاق (Adverse Selection)
5. يكتشف تدفق الأوامر (Order Flow)

الإضافات الجديدة (الإصدار 2.0):
- Spread Analysis للقرار
- Iceberg Absorption Ratio
- Stop Run Probability
- إصلاح cumulative_imbalance
- إصلاح np.polyfit على قائمة قصيرة
- تحديد نطاق زمني لـ nearby_vol
- current_price صحيح في القرار
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class OrderBookLevel:
    """مستوى في دفتر الأوامر"""
    price: float
    bid_volume: float
    ask_volume: float
    bid_depth: int
    ask_depth: int
    imbalance: float
    spread: float
    mid_price: float
    pressure: str


@dataclass
class LiquidityPool:
    """تجمع سيولة - محسن"""
    price_high: float
    price_low: float
    total_volume: float
    dominant_side: str
    pool_type: str
    estimated_age: int
    strength: float
    consumed: float
    # 🟡 تعديل 6: Iceberg Absorption Ratio
    iceberg_ratio: float = 0.0
    # 🟡 تعديل 7: Stop Run Probability
    stop_run_probability: float = 0.0


@dataclass
class MarketMakerProfile:
    """بروفايل صانع السوق - محسن"""
    estimated_inventory: float
    inventory_pressure: float
    optimal_spread: float
    risk_aversion: float
    skew_bias: float
    hedging_pressure: float
    manipulation_score: float
    # 🟡 تعديل 5: Spread Analysis
    spread_risk: str = 'normal'


@dataclass
class PainZone:
    """منطقة ألم"""
    price_level: float
    trapped_side: str
    estimated_volume: float
    pain_intensity: float
    age: int
    likely_target: bool


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: مقدر دفتر الأوامر (Order Book Estimator) محسن        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OrderBookEstimator:
    """
    يقدر دفتر الأوامر من بيانات OHLCV.
    في غياب Level 2 Data حقيقي، نبني نموذجاً للسيولة.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """تقدير دفتر الأوامر"""
        levels = self._build_order_book_levels(highs, lows, closes, volumes)
        imbalance = self._analyze_imbalance(levels)
        spread = self._estimate_dynamic_spread(highs, lows, closes, volumes)
        
        return {
            "current_level": levels[-1] if levels else None,
            "levels": levels[-20:],
            "imbalance": imbalance,
            "estimated_spread": spread,
            "market_pressure": self._assess_pressure(levels),
        }
    
    def _build_order_book_levels(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> List[OrderBookLevel]:
        """بناء مستويات دفتر الأوامر من حركة السعر"""
        levels = []
        
        for i in range(len(closes)):
            bar_high = highs[i]
            bar_low = lows[i]
            bar_close = closes[i]
            bar_volume = volumes[i]
            bar_range = bar_high - bar_low
            
            if bar_range == 0:
                continue
            
            close_position = (bar_close - bar_low) / bar_range
            
            if i > 0 and bar_close > closes[i-1]:
                bid_ratio = 0.5 + close_position * 0.4
                ask_ratio = 1.0 - bid_ratio
            elif i > 0:
                ask_ratio = 0.5 + (1.0 - close_position) * 0.4
                bid_ratio = 1.0 - ask_ratio
            else:
                bid_ratio = 0.5
                ask_ratio = 0.5
            
            bid_vol = bar_volume * bid_ratio
            ask_vol = bar_volume * ask_ratio
            
            avg_vol_window = np.mean(volumes[max(0,i-20):i+1]) if i >= 5 else max(volumes[i], 1.0)
            bid_depth = max(1, int(bid_vol / max(1.0, avg_vol_window) * 10))
            ask_depth = max(1, int(ask_vol / max(1.0, avg_vol_window) * 10))
            
            total = bid_vol + ask_vol
            imbalance = (bid_vol - ask_vol) / total if total > 0 else 0.0
            
            spread = bar_range * 0.1
            mid_price = (bar_high + bar_low) / 2.0
            
            if imbalance > 0.2:
                pressure = 'bid'
            elif imbalance < -0.2:
                pressure = 'ask'
            else:
                pressure = 'balanced'
            
            levels.append(OrderBookLevel(
                price=bar_close, bid_volume=bid_vol, ask_volume=ask_vol,
                bid_depth=bid_depth, ask_depth=ask_depth,
                imbalance=imbalance, spread=spread, mid_price=mid_price,
                pressure=pressure,
            ))
        
        return levels
    
    def _analyze_imbalance(self, levels: List[OrderBookLevel]) -> Dict:
        """
        🔴 تعديل 2: تحليل عدم التوازن مع فحص طول القائمة
        """
        if not levels:
            return {"trend": "balanced", "strength": 0.0}
        
        recent = levels[-20:] if len(levels) >= 20 else levels
        imbalances = [l.imbalance for l in recent]
        
        avg_imbalance = np.mean(imbalances) if imbalances else 0.0
        
        # 🔴 تعديل 2: فحص طول القائمة قبل polyfit
        if len(imbalances) >= 2:
            trend = np.polyfit(range(len(imbalances)), imbalances, 1)[0]
        else:
            trend = 0.0
        
        if avg_imbalance > 0.15:
            direction = "طلب مسيطر"
        elif avg_imbalance < -0.15:
            direction = "عرض مسيطر"
        else:
            direction = "متوازن"
        
        if trend > 0.01:
            trend_desc = "الطلب يتزايد"
        elif trend < -0.01:
            trend_desc = "العرض يتزايد"
        else:
            trend_desc = "مستقر"
        
        return {
            "direction": direction,
            "avg_imbalance": avg_imbalance,
            "trend": trend_desc,
            "strength": abs(avg_imbalance),
        }
    
    def _estimate_dynamic_spread(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """تقدير الفارق الديناميكي"""
        if len(closes) < 10:
            return {"spread": 0.0, "width": "unknown"}
        
        ranges = highs[-10:] - lows[-10:]
        avg_range = np.mean(ranges)
        avg_price = np.mean(closes[-10:])
        
        if avg_price > 0:
            base_spread = avg_range / avg_price
        else:
            base_spread = 0.001
        
        avg_vol = np.mean(volumes[-10:])
        long_avg_vol = np.mean(volumes) if len(volumes) > 0 else avg_vol
        
        if long_avg_vol > 0:
            liquidity_factor = avg_vol / long_avg_vol
        else:
            liquidity_factor = 1.0
        
        dynamic_spread = base_spread * (1.0 / max(liquidity_factor, 0.3)) * \
                        (1.0 + np.std(ranges) / max(avg_range, 0.0001))
        
        if dynamic_spread > 0.005:
            width = "واسع جداً"
        elif dynamic_spread > 0.002:
            width = "واسع"
        elif dynamic_spread > 0.0005:
            width = "طبيعي"
        else:
            width = "ضيق"
        
        return {
            "spread": dynamic_spread,
            "spread_pips": dynamic_spread * 10000,
            "width": width,
            "volatility_component": base_spread,
            "liquidity_factor": liquidity_factor,
        }
    
    def _assess_pressure(self, levels: List[OrderBookLevel]) -> Dict:
        """تقييم الضغط الكلي"""
        if not levels:
            return {"direction": "balanced", "strength": 0.0}
        
        recent = levels[-10:] if len(levels) >= 10 else levels
        bid_pressure = sum(1 for l in recent if l.pressure == 'bid')
        ask_pressure = sum(1 for l in recent if l.pressure == 'ask')
        
        if bid_pressure > ask_pressure * 2:
            return {"direction": "bid_pressure", "strength": min(1.0, bid_pressure / len(recent))}
        elif ask_pressure > bid_pressure * 2:
            return {"direction": "ask_pressure", "strength": min(1.0, ask_pressure / len(recent))}
        else:
            return {"direction": "balanced", "strength": 0.3}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف تجمعات السيولة (محسن)                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LiquidityPoolDetector:
    """
    يكتشف تجمعات السيولة.
    
    🔴 تعديل 3: تحديد نطاق زمني لـ nearby_vol
    🟡 تعديل 6: Iceberg Absorption Ratio
    🟡 تعديل 7: Stop Run Probability
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """اكتشاف تجمعات السيولة"""
        current_price = closes[-1] if len(closes) > 0 else 0.0
        
        pools = self._detect_all_pools(highs, lows, closes, volumes)
        largest_pools = self._rank_pools(pools)
        
        return {
            "all_pools": pools[-15:],
            "largest_pools": largest_pools[:5],
            "total_liquidity_above": sum(p.total_volume for p in pools if p.price_low > current_price),
            "total_liquidity_below": sum(p.total_volume for p in pools if p.price_high < current_price),
            "nearest_pool_above": self._find_nearest_pool(pools, current_price, 'above'),
            "nearest_pool_below": self._find_nearest_pool(pools, current_price, 'below'),
        }
    
    def _detect_all_pools(self, highs: np.ndarray, lows: np.ndarray,
                           closes: np.ndarray, volumes: np.ndarray) -> List[LiquidityPool]:
        """اكتشاف كل تجمعات السيولة"""
        pools = []
        
        stops_above = self._detect_stop_pools(highs, lows, closes, volumes, 'above')
        stops_below = self._detect_stop_pools(highs, lows, closes, volumes, 'below')
        pools.extend(stops_above)
        pools.extend(stops_below)
        
        limit_pools = self._detect_limit_pools(highs, lows, closes, volumes)
        pools.extend(limit_pools)
        
        iceberg_pools = self._detect_iceberg_pools(highs, lows, closes, volumes)
        pools.extend(iceberg_pools)
        
        absorption_pools = self._detect_absorption_pools(highs, lows, closes, volumes)
        pools.extend(absorption_pools)
        
        # 🟡 تعديل 7: حساب Stop Run Probability لكل تجمع
        for pool in pools:
            if pool.pool_type == 'stops':
                pool.stop_run_probability = self._calculate_stop_run_probability(
                    pool, highs, lows, closes, volumes
                )
        
        return sorted(pools, key=lambda p: p.strength, reverse=True)
    
    def _detect_stop_pools(self, highs: np.ndarray, lows: np.ndarray,
                            closes: np.ndarray, volumes: np.ndarray,
                            side: str) -> List[LiquidityPool]:
        """اكتشاف تجمعات وقف الخسارة"""
        pools = []
        
        for i in range(10, len(highs) - 5):
            if side == 'above':
                if abs(highs[i] - highs[i-5]) < highs[i] * 0.002:
                    pool_high = highs[i] * 1.005
                    pool_low = highs[i] * 0.998
                    estimated_vol = np.sum(volumes[max(0,i-10):i+1]) * 0.3
                    
                    pools.append(LiquidityPool(
                        price_high=pool_high, price_low=pool_low,
                        total_volume=estimated_vol, dominant_side='sell',
                        pool_type='stops', estimated_age=len(highs) - i,
                        strength=min(1.0, estimated_vol / max(1.0, np.mean(volumes) * 5)),
                        consumed=0.0,
                    ))
            else:
                if abs(lows[i] - lows[i-5]) < lows[i] * 0.002:
                    pool_high = lows[i] * 1.002
                    pool_low = lows[i] * 0.995
                    estimated_vol = np.sum(volumes[max(0,i-10):i+1]) * 0.3
                    
                    pools.append(LiquidityPool(
                        price_high=pool_high, price_low=pool_low,
                        total_volume=estimated_vol, dominant_side='buy',
                        pool_type='stops', estimated_age=len(lows) - i,
                        strength=min(1.0, estimated_vol / max(1.0, np.mean(volumes) * 5)),
                        consumed=0.0,
                    ))
        
        return pools
    
    def _detect_limit_pools(self, highs: np.ndarray, lows: np.ndarray,
                             closes: np.ndarray, volumes: np.ndarray) -> List[LiquidityPool]:
        """
        🔴 تعديل 3: اكتشاف تجمعات الأوامر المحددة مع نطاق زمني محدد
        
        كان: nearby_vol يبحث في كل البيانات
        الآن: يبحث في آخر 100 شمعة فقط
        """
        pools = []
        
        if len(closes) < 20:
            return pools
        
        current = closes[-1]
        round_levels = []
        
        step = self._calculate_round_step(current)
        base = round(current / step) * step
        
        for i in range(-5, 6):
            level = base + i * step
            if abs(level - current) < current * 0.03:
                round_levels.append(level)
        
        # 🔴 تعديل 3: تحديد نطاق زمني (آخر 100 شمعة)
        search_window = min(100, len(closes))
        search_start = max(0, len(closes) - search_window)
        
        for level in round_levels:
            nearby_vol = 0.0
            for i in range(search_start, len(closes)):
                if abs(closes[i] - level) < step * 0.3:
                    nearby_vol += volumes[i]
            
            if nearby_vol > np.mean(volumes[search_start:]) * 3:
                pools.append(LiquidityPool(
                    price_high=level * 1.001, price_low=level * 0.999,
                    total_volume=nearby_vol, dominant_side='mixed',
                    pool_type='limits', estimated_age=0,
                    strength=min(1.0, nearby_vol / max(1.0, np.mean(volumes[search_start:]) * 10)),
                    consumed=0.0,
                ))
        
        return pools
    
    def _calculate_round_step(self, price: float) -> float:
        """حساب خطوة الرقم الدائري"""
        if price > 10000:
            return 100.0
        elif price > 1000:
            return 50.0
        elif price > 100:
            return 10.0
        elif price > 10:
            return 1.0
        elif price > 1:
            return 0.1
        else:
            return 0.01
    
    def _detect_iceberg_pools(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray, volumes: np.ndarray) -> List[LiquidityPool]:
        """
        اكتشاف أوامر جبل الجليد مع Iceberg Ratio
        
        🟡 تعديل 6: Iceberg Absorption Ratio
        """
        pools = []
        
        for i in range(5, len(closes)):
            avg_vol = np.mean(volumes[max(0,i-10):i])
            avg_range = np.mean(highs[max(0,i-10):i] - lows[max(0,i-10):i])
            
            if avg_vol > 0 and avg_range > 0:
                vol_ratio = volumes[i] / avg_vol
                range_ratio = (highs[i] - lows[i]) / avg_range
                
                if vol_ratio > 2.0 and range_ratio < 0.5:
                    # 🟡 تعديل 6: Iceberg Ratio = الحجم المخفي المقدر / الحجم الظاهر
                    visible_volume = volumes[i]
                    estimated_hidden = volumes[i] * 2.0  # تقدير: ضعف الحجم الظاهر
                    iceberg_ratio = estimated_hidden / max(visible_volume, 0.0001)
                    
                    pools.append(LiquidityPool(
                        price_high=highs[i], price_low=lows[i],
                        total_volume=visible_volume + estimated_hidden,
                        dominant_side='buy' if closes[i] > (highs[i] + lows[i]) / 2 else 'sell',
                        pool_type='iceberg', estimated_age=len(closes) - i,
                        strength=min(1.0, vol_ratio * 0.3),
                        consumed=0.3,
                        iceberg_ratio=iceberg_ratio,
                    ))
        
        return pools
    
    def _detect_absorption_pools(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> List[LiquidityPool]:
        """اكتشاف تجمعات الامتصاص"""
        pools = []
        
        if len(closes) < 30:
            return pools
        
        all_prices = np.concatenate([highs, lows, closes])
        price_min = np.min(all_prices)
        price_max = np.max(all_prices)
        
        if price_max == price_min:
            return pools
        
        num_zones = 20
        zone_size = (price_max - price_min) / num_zones
        
        for z in range(num_zones):
            zone_low = price_min + z * zone_size
            zone_high = zone_low + zone_size
            
            zone_volume = 0.0
            visits = 0
            
            for i in range(len(closes)):
                if lows[i] <= zone_high and highs[i] >= zone_low:
                    zone_volume += volumes[i] * 0.5
                    visits += 1
            
            total_avg_vol = np.mean(volumes) if len(volumes) > 0 else 1.0
            
            if zone_volume > total_avg_vol * 5 and visits >= 5:
                pools.append(LiquidityPool(
                    price_high=zone_high, price_low=zone_low,
                    total_volume=zone_volume, dominant_side='mixed',
                    pool_type='absorption', estimated_age=0,
                    strength=min(1.0, zone_volume / max(1.0, total_avg_vol * 10)),
                    consumed=0.5,
                ))
        
        return pools
    
    def _calculate_stop_run_probability(self, pool: LiquidityPool, highs: np.ndarray,
                                          lows: np.ndarray, closes: np.ndarray,
                                          volumes: np.ndarray) -> float:
        """
        🟡 تعديل 7: Stop Run Probability
        
        إذا كان تجمع الـ Stops كبيراً وقريباً، فاحتمال الاصطياد مرتفع
        """
        if len(closes) < 10:
            return 0.0
        
        current_price = closes[-1]
        
        # المسافة إلى التجمع
        pool_mid = (pool.price_high + pool.price_low) / 2.0
        distance_pct = abs(pool_mid - current_price) / max(current_price, 0.0001)
        
        # كلما كان أقرب = احتمال أعلى
        proximity_score = max(0.0, 1.0 - distance_pct * 50)
        
        # حجم التجمع
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        size_score = min(1.0, pool.total_volume / max(avg_vol * 5, 0.0001))
        
        # عمر التجمع (الأحدث = أقوى)
        age_score = max(0.0, 1.0 - pool.estimated_age / 50.0)
        
        return min(1.0, proximity_score * 0.4 + size_score * 0.35 + age_score * 0.25)
    
    def _rank_pools(self, pools: List[LiquidityPool]) -> List[LiquidityPool]:
        """ترتيب التجمعات حسب الأهمية"""
        return sorted(pools, key=lambda p: p.strength * (1.0 - p.consumed), reverse=True)
    
    def _find_nearest_pool(self, pools: List[LiquidityPool], current_price: float,
                            side: str) -> Optional[LiquidityPool]:
        """أقرب تجمع سيولة"""
        if side == 'above':
            above = [p for p in pools if p.price_low > current_price]
            if above:
                return min(above, key=lambda p: p.price_low - current_price)
        else:
            below = [p for p in pools if p.price_high < current_price]
            if below:
                return min(below, key=lambda p: current_price - p.price_high)
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثالثة: محلل مناطق الألم (Pain Zone Analyzer)               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PainZoneAnalyzer:
    """
    يكتشف "مناطق الألم" - حيث المتداولون محاصرون.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """تحليل مناطق الألم"""
        pain_zones = self._detect_pain_zones(highs, lows, closes, volumes)
        trapped_traders = self._estimate_trapped_traders(highs, lows, closes)
        
        return {
            "pain_zones": pain_zones[-10:],
            "trapped_traders": trapped_traders,
            "most_painful_zone": max(pain_zones, key=lambda p: p.pain_intensity) if pain_zones else None,
        }
    
    def _detect_pain_zones(self, highs: np.ndarray, lows: np.ndarray,
                            closes: np.ndarray, volumes: np.ndarray) -> List[PainZone]:
        """اكتشاف مناطق الألم"""
        pain_zones = []
        
        for i in range(5, len(highs) - 3):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1]:
                if i + 5 < len(closes) and closes[i+1] > highs[i] and closes[i+3] < highs[i]:
                    trapped_vol = volumes[i+1] + volumes[i+2]
                    pain_zones.append(PainZone(
                        price_level=highs[i] * 1.002,
                        trapped_side='longs',
                        estimated_volume=trapped_vol,
                        pain_intensity=min(1.0, trapped_vol / max(1.0, np.mean(volumes) * 5)),
                        age=len(closes) - i,
                        likely_target=True,
                    ))
        
        for i in range(5, len(lows) - 3):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1]:
                if i + 5 < len(closes) and closes[i+1] < lows[i] and closes[i+3] > lows[i]:
                    trapped_vol = volumes[i+1] + volumes[i+2]
                    pain_zones.append(PainZone(
                        price_level=lows[i] * 0.998,
                        trapped_side='shorts',
                        estimated_volume=trapped_vol,
                        pain_intensity=min(1.0, trapped_vol / max(1.0, np.mean(volumes) * 5)),
                        age=len(closes) - i,
                        likely_target=True,
                    ))
        
        return pain_zones
    
    def _estimate_trapped_traders(self, highs: np.ndarray, lows: np.ndarray,
                                    closes: np.ndarray) -> Dict:
        """تقدير المتداولين المحاصرين"""
        if len(closes) < 20:
            return {"longs_trapped": 0, "shorts_trapped": 0}
        
        sma_20 = np.mean(closes[-20:])
        sma_5 = np.mean(closes[-5:])
        
        if sma_5 > sma_20 * 1.02:
            return {"longs_trapped": 0, "shorts_trapped": 70, "dominant_trap": "shorts"}
        elif sma_5 < sma_20 * 0.98:
            return {"longs_trapped": 70, "shorts_trapped": 0, "dominant_trap": "longs"}
        else:
            return {"longs_trapped": 30, "shorts_trapped": 30, "dominant_trap": "both"}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الرابعة: محلل إدارة المخزون (محسن)                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class InventoryManagementAnalyzer:
    """
    يحلل كيف يدير صانع السوق مخزونه.
    
    🔴 تعديل 1: إصلاح صيغة cumulative_imbalance
    🟡 تعديل 5: Spread Analysis
    """
    
    def analyze(self, closes: np.ndarray, volumes: np.ndarray,
                order_levels: List[OrderBookLevel]) -> Dict:
        """تحليل إدارة المخزون"""
        profile = self._estimate_market_maker_profile(closes, volumes, order_levels)
        pressure = self._calculate_pressure(profile, closes, volumes)
        
        return {
            "profile": profile,
            "pressure": pressure,
            "mm_bias": self._determine_mm_bias(profile),
        }
    
    def _estimate_market_maker_profile(self, closes: np.ndarray, volumes: np.ndarray,
                                         levels: List[OrderBookLevel]) -> MarketMakerProfile:
        """
        🔴 تعديل 1: تقدير بروفايل صانع السوق بصيغة صحيحة
        
        كان: sum(l.imbalance * l.bid_volume + l.ask_volume)  ← خطأ في أولوية العمليات
        الآن: sum(l.bid_volume - l.ask_volume)  ← الصيغة الصحيحة
        """
        if levels:
            # 🔴 تعديل 1: الصيغة الصحيحة - الفرق بين العرض والطلب
            cumulative_imbalance = sum(l.bid_volume - l.ask_volume for l in levels)
            total_volume = sum(l.bid_volume + l.ask_volume for l in levels)
            if total_volume > 0:
                estimated_inventory = cumulative_imbalance / total_volume
            else:
                estimated_inventory = 0.0
        else:
            estimated_inventory = 0.0
        
        inventory_pressure = -np.tanh(estimated_inventory * 3)
        
        if len(closes) >= 10:
            returns = np.diff(np.log(np.maximum(closes[-10:], 0.0001)))
            vol = np.std(returns) if len(returns) > 0 else 0.0
            risk_aversion = min(1.0, vol * 50 + 0.3)
        else:
            risk_aversion = 0.5
        
        optimal_spread = 0.001 * (1.0 + risk_aversion)
        skew_bias = -estimated_inventory * 0.2
        hedging_pressure = abs(estimated_inventory) * risk_aversion
        
        manipulation_score = 0.0
        if abs(estimated_inventory) > 0.5 and risk_aversion > 0.6:
            manipulation_score = min(1.0, abs(estimated_inventory) * risk_aversion)
        
        # 🟡 تعديل 5: Spread Analysis للقرار
        spread_risk = 'normal'
        if optimal_spread > 0.005:
            spread_risk = 'high'
        elif optimal_spread < 0.001:
            spread_risk = 'low'
        
        return MarketMakerProfile(
            estimated_inventory=estimated_inventory,
            inventory_pressure=inventory_pressure,
            optimal_spread=optimal_spread,
            risk_aversion=risk_aversion,
            skew_bias=skew_bias,
            hedging_pressure=hedging_pressure,
            manipulation_score=manipulation_score,
            spread_risk=spread_risk,
        )
    
    def _calculate_pressure(self, profile: MarketMakerProfile, closes: np.ndarray,
                             volumes: np.ndarray) -> Dict:
        """حساب الضغوط على صانع السوق"""
        buy_pressure = max(0.0, -profile.inventory_pressure) + profile.hedging_pressure * 0.3
        sell_pressure = max(0.0, profile.inventory_pressure) + profile.hedging_pressure * 0.3
        
        if buy_pressure > sell_pressure * 1.5:
            direction = "ضغط شراء"
        elif sell_pressure > buy_pressure * 1.5:
            direction = "ضغط بيع"
        else:
            direction = "متوازن"
        
        return {
            "direction": direction,
            "buy_pressure": buy_pressure,
            "sell_pressure": sell_pressure,
            "net": buy_pressure - sell_pressure,
        }
    
    def _determine_mm_bias(self, profile: MarketMakerProfile) -> str:
        """تحديد ميل صانع السوق"""
        if profile.manipulation_score > 0.7:
            if profile.inventory_pressure > 0.3:
                return "صانع السوق يميل للبيع - احتمال تلاعب هابط"
            elif profile.inventory_pressure < -0.3:
                return "صانع السوق يميل للشراء - احتمال تلاعب صاعد"
        
        if profile.inventory_pressure > 0.5:
            return "صانع السوق بحاجة للبيع"
        elif profile.inventory_pressure < -0.5:
            return "صانع السوق بحاجة للشراء"
        else:
            return "صانع السوق متوازن"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║          الدرجة النهائية: استراتيجية صناعة السوق الموحدة (محسنة)          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MarketMakingStrategy:
    """
    استراتيجية منظور صانع السوق الكاملة - الإصدار 2.0
    
    - Spread Analysis للقرار
    - Iceberg Absorption Ratio
    - Stop Run Probability
    - إصلاح cumulative_imbalance
    - current_price صحيح
    """
    
    def __init__(self):
        self.order_book = OrderBookEstimator()
        self.liquidity_pools = LiquidityPoolDetector()
        self.pain_zones = PainZoneAnalyzer()
        self.inventory = InventoryManagementAnalyzer()
    
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
        
        # 🔴 تعديل 4: current_price صحيح
        current_price = closes[-1]
        
        ob_data = self.order_book.analyze(highs, lows, closes, volumes)
        pool_data = self.liquidity_pools.analyze(highs, lows, closes, volumes)
        pain_data = self.pain_zones.analyze(highs, lows, closes, volumes)
        levels = ob_data.get('levels', [])
        inv_data = self.inventory.analyze(closes, volumes, levels)
        decision = self._make_decision(ob_data, pool_data, pain_data, inv_data, current_price)
        
        return {**decision, "ob_data": ob_data, "pool_data": pool_data, "pain_data": pain_data, "inv_data": inv_data}
    
    def _make_decision(self, ob_data: Dict, pool_data: Dict,
                       pain_data: Dict, inv_data: Dict,
                       current_price: float) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        # ---- من ضغط دفتر الأوامر ----
        imbalance = ob_data.get('imbalance', {})
        if imbalance.get('direction') == 'طلب مسيطر' and imbalance.get('strength', 0) > 0.3:
            buy_signals.append(("دفتر أوامر: طلب مسيطر", 0.5))
        elif imbalance.get('direction') == 'عرض مسيطر' and imbalance.get('strength', 0) > 0.3:
            sell_signals.append(("دفتر أوامر: عرض مسيطر", 0.5))
        
        # ---- 🟡 تعديل 5: Spread Analysis ----
        spread_info = ob_data.get('estimated_spread', {})
        spread_width = spread_info.get('width', '')
        if spread_width in ['واسع جداً', 'واسع']:
            warnings.append(f"الفارق {spread_width} - خطر انزلاق")
        elif spread_width == 'ضيق':
            buy_signals.append(("فارق ضيق - سيولة جيدة", 0.2))
        
        # ---- من تجمعات السيولة ----
        nearest_above = pool_data.get('nearest_pool_above')
        nearest_below = pool_data.get('nearest_pool_below')
        
        if nearest_above:
            if nearest_above.pool_type == 'stops':
                # 🟡 تعديل 7: Stop Run Probability
                srp = nearest_above.stop_run_probability
                if srp > 0.6:
                    buy_signals.append((f"اصطياد وقف علوي محتمل (SRP:{srp:.0%}) عند {nearest_above.price_high:.4f}", 0.6))
                else:
                    sell_signals.append((f"سيولة وقف خسارة علوية عند {nearest_above.price_high:.4f}", 0.5))
            elif nearest_above.pool_type == 'iceberg':
                # 🟡 تعديل 6: Iceberg Ratio
                if nearest_above.iceberg_ratio > 3.0:
                    buy_signals.append((f"أوامر مخفية علوية (Iceberg ×{nearest_above.iceberg_ratio:.1f})", 0.5))
        
        if nearest_below:
            if nearest_below.pool_type == 'stops':
                srp = nearest_below.stop_run_probability
                if srp > 0.6:
                    sell_signals.append((f"اصطياد وقف سفلي محتمل (SRP:{srp:.0%}) عند {nearest_below.price_low:.4f}", 0.6))
                else:
                    buy_signals.append((f"سيولة وقف خسارة سفلية عند {nearest_below.price_low:.4f}", 0.5))
            elif nearest_below.pool_type == 'iceberg':
                if nearest_below.iceberg_ratio > 3.0:
                    sell_signals.append((f"أوامر مخفية سفلية (Iceberg ×{nearest_below.iceberg_ratio:.1f})", 0.5))
        
        # أين السيولة أكثر؟
        liq_above = pool_data.get('total_liquidity_above', 0.0)
        liq_below = pool_data.get('total_liquidity_below', 0.0)
        
        if liq_above > liq_below * 1.5:
            buy_signals.append(("سيولة أعلى أكثر - السعر قد يصعد لاصطيادها", 0.6))
        elif liq_below > liq_above * 1.5:
            sell_signals.append(("سيولة أسفل أكثر - السعر قد يهبط لاصطيادها", 0.6))
        
        # ---- من مناطق الألم ----
        most_painful = pain_data.get('most_painful_zone')
        trapped = pain_data.get('trapped_traders', {})
        
        if most_painful and most_painful.likely_target:
            if most_painful.trapped_side == 'longs':
                sell_signals.append((f"منطقة ألم للمشترين عند {most_painful.price_level:.4f}", 0.5))
            elif most_painful.trapped_side == 'shorts':
                buy_signals.append((f"منطقة ألم للبائعين عند {most_painful.price_level:.4f}", 0.5))
        
        if trapped.get('dominant_trap') == 'longs':
            sell_signals.append(("مشترين محاصرين - السوق قد يهبط أكثر", 0.45))
        elif trapped.get('dominant_trap') == 'shorts':
            buy_signals.append(("بائعين محاصرين - السوق قد يصعد أكثر", 0.45))
        
        # ---- من إدارة المخزون ----
        pressure = inv_data.get('pressure', {})
        mm_bias = inv_data.get('mm_bias', '')
        profile = inv_data.get('profile')
        
        if pressure.get('direction') == 'ضغط شراء':
            buy_signals.append(("صانع سوق بحاجة للشراء", 0.5))
        elif pressure.get('direction') == 'ضغط بيع':
            sell_signals.append(("صانع سوق بحاجة للبيع", 0.5))
        
        if profile:
            # 🟡 تعديل 5: تحذير من spread risk
            if profile.spread_risk == 'high':
                warnings.append("صانع السوق يوسع الفارق - خطر مرتفع")
            
            if profile.manipulation_score > 0.6:
                if profile.inventory_pressure > 0:
                    sell_signals.append(("احتمال تلاعب هابط", 0.55))
                else:
                    buy_signals.append(("احتمال تلاعب صاعد", 0.55))
        
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
        reason += f" | الفارق: {spread_width}"
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "mm_bias": mm_bias,
            "warnings": warnings,
        }


def create_market_making_strategy():
    """إنشاء استراتيجية صناعة السوق الجاهزة (الإصدار 2.0)"""
    return MarketMakingStrategy()