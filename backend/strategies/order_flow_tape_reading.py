"""
═══════════════════════════════════════════════════════════════════════════════
ORDER FLOW & TAPE READING - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثامنة: تدفق الأوامر وقراءة الشريط - عيون صانع السوق
═══════════════════════════════════════════════════════════════════════════════

أقدم وأقوى مدرسة في التداول. تعود لزمن "الشريط" (Ticker Tape).
اليوم، نستخدم بيانات Time & Sales و Depth of Market.

هذه النسخة ديناميكية بالكامل:
- لا نعتمد على Delta ثابت (فرق الحجم)
- نقرأ "سرعة" و"عدوانية" التدفق
- نميز بين المشتري الحقيقي والخوارزمية
- حجم التداول يقرأ في سياقه اللحظي
- السرعة والزمن أهم من الحجم المطلق

المفاهيم الأساسية:
1. Delta (الفرق بين حجم الشراء والبيع)
2. Cumulative Delta (التراكمي)
3. Absorption (الامتصاص)
4. Exhaustion (الإنهاك)
5. Iceberg Orders (الأوامر المخفية)
6. Spoofing (الخداع)
7. Stop Runs (اصطياد الوقف)
8. Pacing (النسق - سرعة التدفق)
9. Aggressive vs Passive (عدواني مقابل سلبي)
10. Large Lots vs Small Lots
11. Block Trades (صفقات كبيرة)
12. Hidden Liquidity (سيولة مخفية)
13. Multi-Timeframe Delta Divergence
14. Large Lot Detection
15. Iceberg Detection حقيقي
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class OrderFlowBar:
    """تحليل تدفق الأوامر لشمعة واحدة - نسخة محسنة"""
    index: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float
    sell_volume: float
    delta: float
    cumulative_delta: float
    delta_pace: float
    aggression: float
    absorption_score: float
    exhaustion_score: float
    bar_type: str
    # 🔴 تعديل 1 + 2: حقول مضافة
    is_up_bar: bool = True
    close_position: float = 0.5
    # 🟡 تعديل 4: Large Lot Detection
    is_large_lot: bool = False
    large_lot_ratio: float = 1.0
    # 🟡 تعديل 5: Iceberg Score
    iceberg_score: float = 0.0


@dataclass
class DeltaDivergence:
    """تباعد الدلتا عن السعر - نسخة محسنة"""
    index: int
    divergence_type: str
    price_direction: str
    delta_direction: str
    strength: float
    bars_count: int
    significance: str
    # 🟡 تعديل 3: Multi-Timeframe
    timeframe_short: str = 'none'  # تباعد على 5 شموع
    timeframe_medium: str = 'none'  # تباعد على 15 شمعة
    timeframe_long: str = 'none'  # تباعد على 30 شمعة
    multi_timeframe_score: float = 0.0  # قوة مضاعفة إذا تطابقت


@dataclass
class LiquidityZone:
    """منطقة سيولة من تدفق الأوامر"""
    price_level: float
    total_volume: float
    buy_volume: float
    sell_volume: float
    net_delta: float
    zone_type: str
    strength: float
    active: bool


@dataclass
class AggressionProfile:
    """بروفايل العدوانية"""
    aggressive_buy_ratio: float
    aggressive_sell_ratio: float
    passive_buy_ratio: float
    passive_sell_ratio: float
    dominant_side: str
    aggression_trend: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الأولى: مقدر تدفق الأوامر (Order Flow Estimator) محسن         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OrderFlowEstimator:
    """
    يقدر تدفق الأوامر من بيانات OHLCV.
    
    في غياب بيانات Time & Sales الحقيقية، نستخدم:
    - موقع الإغلاق في الشمعة لتقدير Delta
    - علاقة الحجم بالانتشار لتقدير العدوانية
    - تغير الدلتا لتقدير الامتصاص والإنهاك
    
    🔴 تعديل 1+2: is_up_bar و close_position مضافان
    🟡 تعديل 4: Large Lot Detection
    🟡 تعديل 5: Iceberg Detection حقيقي
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """تحليل تدفق الأوامر الكامل"""
        bars = []
        cumulative_delta = 0
        
        for i in range(len(closes)):
            bar = self._estimate_order_flow(opens[i], highs[i], lows[i], 
                                             closes[i], volumes[i], i, 
                                             volumes, highs, lows, cumulative_delta)
            cumulative_delta = bar.cumulative_delta
            bars.append(bar)
        
        # تحليل متقدم للشموع
        enhanced_bars = self._enhance_bars(bars, highs, lows, closes, volumes)
        
        # 🟡 تعديل 3: اكتشاف التباعدات متعددة الأطر الزمنية
        divergences = self._detect_delta_divergences_mtf(enhanced_bars, closes)
        
        # اكتشاف مناطق السيولة
        liquidity_zones = self._find_liquidity_zones(enhanced_bars)
        
        return {
            "bars": enhanced_bars[-30:],
            "divergences": divergences[-10:],
            "liquidity_zones": liquidity_zones[-10:],
            "current_bar": enhanced_bars[-1] if enhanced_bars else None,
            "cumulative_delta": cumulative_delta,
            "delta_trend": self._analyze_delta_trend(enhanced_bars),
        }
    
    def _estimate_order_flow(self, open_p: float, high: float, low: float,
                              close: float, volume: float, index: int,
                              all_volumes: np.ndarray, all_highs: np.ndarray,
                              all_lows: np.ndarray, cum_delta: float) -> OrderFlowBar:
        """تقدير تدفق الأوامر من شمعة OHLCV"""
        spread = high - low
        body = abs(close - open_p)
        is_up = close > open_p
        
        # 🔴 تعديل 2: حساب close_position
        if spread > 0:
            close_pos = (close - low) / spread
        else:
            close_pos = 0.5
        
        # تقدير نسبة الشراء/البيع
        if spread > 0:
            if is_up:
                if close_pos > 0.8:
                    buy_ratio = 0.75 + (close_pos - 0.8) * 1.25
                elif close_pos > 0.6:
                    buy_ratio = 0.6 + (close_pos - 0.6) * 0.75
                elif close_pos > 0.4:
                    buy_ratio = 0.5
                else:
                    buy_ratio = 0.4
            else:
                if close_pos < 0.2:
                    buy_ratio = 0.25 - (0.2 - close_pos) * 1.25
                elif close_pos < 0.4:
                    buy_ratio = 0.4 - (0.4 - close_pos) * 0.75
                elif close_pos < 0.6:
                    buy_ratio = 0.5
                else:
                    buy_ratio = 0.6
        else:
            buy_ratio = 0.5
        
        buy_ratio = max(0.1, min(0.9, buy_ratio))
        
        buy_vol = volume * buy_ratio
        sell_vol = volume * (1 - buy_ratio)
        delta = buy_vol - sell_vol
        cum_delta += delta
        
        delta_pace = delta / max(volume, 0.0001) * (1 if is_up else -1)
        
        # تقدير العدوانية
        if index >= 5:
            avg_vol = np.mean(all_volumes[max(0,index-5):index])
        else:
            avg_vol = volume if volume > 0 else 1
        
        aggression = 0.0
        if avg_vol > 0 and volume > avg_vol * 1.5:
            aggression += 0.4
        if spread > 0 and body > spread * 0.6:
            aggression += 0.3
        if abs(close_pos - 0.5) > 0.3:
            aggression += 0.3
        
        # 🟡 تعديل 4: Large Lot Detection
        is_large_lot = False
        large_lot_ratio = 1.0
        if index >= 20:
            avg_vol_long = np.mean(all_volumes[max(0,index-20):index])
            if avg_vol_long > 0:
                large_lot_ratio = volume / avg_vol_long
                is_large_lot = large_lot_ratio > 3.0
        
        return OrderFlowBar(
            index=index,
            open=open_p, high=high, low=low, close=close,
            volume=volume,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            delta=delta,
            cumulative_delta=cum_delta,
            delta_pace=delta_pace,
            aggression=min(1.0, aggression),
            absorption_score=0.0,
            exhaustion_score=0.0,
            bar_type='normal',
            # 🔴 تعديل 1+2
            is_up_bar=is_up,
            close_position=close_pos,
            # 🟡 تعديل 4
            is_large_lot=is_large_lot,
            large_lot_ratio=large_lot_ratio,
            iceberg_score=0.0,
        )
    
    def _enhance_bars(self, bars: List[OrderFlowBar], highs: np.ndarray,
                      lows: np.ndarray, closes: np.ndarray,
                      volumes: np.ndarray) -> List[OrderFlowBar]:
        """تحسين تحليل الشموع"""
        for i in range(len(bars)):
            bar = bars[i]
            if i < 5:
                continue
            
            bar.absorption_score = self._calculate_absorption(bars, i)
            bar.exhaustion_score = self._calculate_exhaustion(bars, closes, i)
            
            # 🟡 تعديل 5: Iceberg Detection حقيقي
            bar.iceberg_score = self._calculate_iceberg_score(bars, i, volumes)
            
            bar.bar_type = self._classify_bar_type(bar, bars, volumes, i)
        
        return bars
    
    def _calculate_absorption(self, bars: List[OrderFlowBar], index: int) -> float:
        """حساب درجة الامتصاص"""
        if index < 5:
            return 0.0
        
        bar = bars[index]
        prev_bars = bars[max(0,index-5):index]
        
        avg_vol = np.mean([b.volume for b in prev_bars])
        avg_spread = np.mean([b.high - b.low for b in prev_bars])
        
        if avg_vol == 0 or avg_spread == 0:
            return 0.0
        
        vol_ratio = bar.volume / avg_vol
        spread_ratio = (bar.high - bar.low) / avg_spread
        
        if vol_ratio > 1.5 and spread_ratio < 0.7:
            return min(1.0, (vol_ratio - 1.0) * 0.5)
        
        return 0.0
    
    def _calculate_exhaustion(self, bars: List[OrderFlowBar], closes: np.ndarray,
                               index: int) -> float:
        """حساب درجة الإنهاك"""
        if index < 5:
            return 0.0
        
        recent = bars[max(0,index-5):index+1]
        deltas = [b.delta for b in recent]
        price_change = closes[index] - closes[max(0,index-5)]
        
        if len(deltas) >= 3:
            delta_trend = deltas[-1] - deltas[0]
            if abs(price_change) > 0 and abs(delta_trend) > 0:
                if (price_change > 0 and delta_trend < 0) or (price_change < 0 and delta_trend > 0):
                    return min(1.0, abs(delta_trend) / max(abs(price_change), 0.0001) * 10)
        
        return 0.0
    
    def _calculate_iceberg_score(self, bars: List[OrderFlowBar], index: int,
                                   volumes: np.ndarray) -> float:
        """
        🟡 تعديل 5: Iceberg Detection حقيقي
        
        حجم كبير + انتشار ضيق + تكرار عند نفس السعر = أوامر مخفية
        """
        if index < 10:
            return 0.0
        
        bar = bars[index]
        score = 0.0
        
        # 1. حجم كبير مع انتشار ضيق
        if index >= 10:
            avg_vol = np.mean(volumes[max(0,index-10):index])
            avg_spread = np.mean([b.high - b.low for b in bars[max(0,index-10):index]])
            
            if avg_vol > 0 and avg_spread > 0:
                vol_ratio = bar.volume / avg_vol
                spread_ratio = (bar.high - bar.low) / avg_spread
                
                if vol_ratio > 2.0 and spread_ratio < 0.5:
                    score += 0.4
        
        # 2. تكرار عند نفس السعر
        same_price_count = 0
        for j in range(max(0, index-15), index):
            if abs(bars[j].close - bar.close) / max(bar.close, 0.0001) < 0.001:
                same_price_count += 1
        
        if same_price_count >= 3:
            score += 0.3
        elif same_price_count >= 2:
            score += 0.15
        
        # 3. حجم كبير بدون عدوانية (أوامر مخفية = سلبية)
        if bar.is_large_lot and bar.aggression < 0.5:
            score += 0.3
        
        return min(1.0, score)
    
    def _classify_bar_type(self, bar: OrderFlowBar, bars: List[OrderFlowBar],
                           volumes: np.ndarray, index: int) -> str:
        """تصنيف نوع الشمعة - محسن"""
        if bar.iceberg_score > 0.6:
            return 'iceberg'
        
        if bar.absorption_score > 0.7:
            return 'absorption'
        
        if bar.exhaustion_score > 0.7:
            return 'exhaustion'
        
        if bar.is_large_lot and bar.aggression > 0.8:
            return 'climax'
        
        if bar.aggression > 0.8 and abs(bar.delta_pace) > 0.7:
            return 'stop_run'
        
        return 'normal'
    
    def _detect_delta_divergences_mtf(self, bars: List[OrderFlowBar],
                                        closes: np.ndarray) -> List[DeltaDivergence]:
        """
        🟡 تعديل 3: اكتشاف تباعدات الدلتا متعددة الأطر الزمنية
        
        تباعد على 5 + 15 + 30 شمعة = قوة مضاعفة
        """
        divergences = []
        
        if len(bars) < 10:
            return divergences
        
        # فحص على 3 أطر زمنية مختلفة
        timeframes = [
            (5, 'short'),
            (15, 'medium'),
            (30, 'long'),
        ]
        
        for i in range(10, len(bars)):
            tf_results = {}
            
            for window_size, tf_name in timeframes:
                if i < window_size:
                    continue
                
                window = bars[i-window_size:i+1]
                if len(window) < 3:
                    continue
                
                price_start = window[0].close
                price_end = window[-1].close
                delta_start = window[0].cumulative_delta
                delta_end = window[-1].cumulative_delta
                
                price_change = price_end - price_start
                delta_change = delta_end - delta_start
                
                if price_change > 0 and delta_change < 0 and abs(delta_change) > 0:
                    tf_results[tf_name] = 'bearish'
                elif price_change < 0 and delta_change > 0 and abs(delta_change) > 0:
                    tf_results[tf_name] = 'bullish'
                else:
                    tf_results[tf_name] = 'none'
            
            # حساب القوة متعددة الأطر
            if tf_results.get('short', 'none') != 'none':
                div_type = tf_results['short']
                mtf_score = 0.0
                
                if tf_results.get('medium') == div_type:
                    mtf_score += 0.3
                if tf_results.get('long') == div_type:
                    mtf_score += 0.3
                
                if mtf_score > 0:
                    # تباعد مؤكد على أطر متعددة
                    total_strength = 0.5 + mtf_score
                    significance = 'major' if mtf_score >= 0.5 else 'significant'
                    
                    divergences.append(DeltaDivergence(
                        index=i,
                        divergence_type=div_type,
                        price_direction='up' if closes[i] > closes[i-5] else 'down',
                        delta_direction='falling' if div_type == 'bearish' else 'rising',
                        strength=min(1.0, total_strength),
                        bars_count=30,
                        significance=significance,
                        timeframe_short=tf_results.get('short', 'none'),
                        timeframe_medium=tf_results.get('medium', 'none'),
                        timeframe_long=tf_results.get('long', 'none'),
                        multi_timeframe_score=mtf_score,
                    ))
        
        return divergences
    
    def _find_liquidity_zones(self, bars: List[OrderFlowBar]) -> List[LiquidityZone]:
        """اكتشاف مناطق السيولة"""
        zones = []
        
        if len(bars) < 10:
            return zones
        
        price_volumes = defaultdict(lambda: {'total': 0, 'buy': 0, 'sell': 0})
        
        for bar in bars[-50:]:
            key = round(bar.close, 3)
            price_volumes[key]['total'] += bar.volume
            price_volumes[key]['buy'] += bar.buy_volume
            price_volumes[key]['sell'] += bar.sell_volume
        
        if not price_volumes:
            return zones
        
        max_vol = max(d['total'] for d in price_volumes.values())
        
        for price, data in price_volumes.items():
            if data['total'] > max_vol * 0.5:
                net_delta = data['buy'] - data['sell']
                
                if data['total'] > max_vol * 0.8:
                    zone_type = 'absorption' if abs(net_delta) < data['total'] * 0.2 else \
                                'iceberg' if data['buy'] > data['sell'] * 2 else \
                                'stop_pool'
                else:
                    zone_type = 'support' if data['buy'] > data['sell'] else 'resistance'
                
                zones.append(LiquidityZone(
                    price_level=price,
                    total_volume=data['total'],
                    buy_volume=data['buy'],
                    sell_volume=data['sell'],
                    net_delta=net_delta,
                    zone_type=zone_type,
                    strength=data['total'] / max_vol,
                    active=True,
                ))
        
        return sorted(zones, key=lambda z: z.strength, reverse=True)
    
    def _analyze_delta_trend(self, bars: List[OrderFlowBar]) -> Dict:
        """تحليل اتجاه الدلتا التراكمي"""
        if len(bars) < 10:
            return {"trend": "غير كافٍ"}
        
        recent = bars[-10:]
        cum_delta_start = recent[0].cumulative_delta
        cum_delta_end = recent[-1].cumulative_delta
        delta_change = cum_delta_end - cum_delta_start
        
        if delta_change > 0:
            delta_trend = 'صاعد'
            bias = 'bullish'
        elif delta_change < 0:
            delta_trend = 'هابط'
            bias = 'bearish'
        else:
            delta_trend = 'محايد'
            bias = 'neutral'
        
        total_volume = sum(b.volume for b in recent)
        if total_volume > 0:
            strength = abs(delta_change) / total_volume
        else:
            strength = 0
        
        return {
            "trend": delta_trend,
            "bias": bias,
            "strength": min(1.0, strength * 5),
            "change": delta_change,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الثانية: محلل العدوانية (Aggression Analyzer)                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AggressionAnalyzer:
    """
    يحلل عدوانية المشترين والبائعين.
    
    العدوانية = من يدفع السعر بقوة؟
    - Aggressive Buyers: يشترون بسعر الطلب (Market Orders)
    - Aggressive Sellers: يبيعون بسعر العرض (Market Orders)
    - Passive: ينتظرون بسعرهم (Limit Orders)
    """
    
    def analyze(self, bars: List[OrderFlowBar], highs: np.ndarray,
                lows: np.ndarray, closes: np.ndarray) -> Dict:
        """تحليل العدوانية"""
        profile = self._build_aggression_profile(bars)
        waves = self._analyze_aggression_waves(bars, highs, lows, closes)
        
        return {
            "profile": profile,
            "waves": waves,
            "current_aggression": self._current_aggression_state(bars),
        }
    
    def _build_aggression_profile(self, bars: List[OrderFlowBar]) -> AggressionProfile:
        """بناء بروفايل العدوانية"""
        if not bars:
            return AggressionProfile(0, 0, 0, 0, 'balanced', 'stable')
        
        recent = bars[-30:] if len(bars) >= 30 else bars
        
        agg_buy = 0.0
        agg_sell = 0.0
        pass_buy = 0.0
        pass_sell = 0.0
        
        for bar in recent:
            if bar.is_up_bar:
                if bar.aggression > 0.6:
                    agg_buy += bar.buy_volume
                else:
                    pass_buy += bar.buy_volume
            else:
                if bar.aggression > 0.6:
                    agg_sell += bar.sell_volume
                else:
                    pass_sell += bar.sell_volume
        
        total = agg_buy + agg_sell + pass_buy + pass_sell
        if total == 0:
            return AggressionProfile(0.25, 0.25, 0.25, 0.25, 'balanced', 'stable')
        
        agg_buy_r = agg_buy / total
        agg_sell_r = agg_sell / total
        pass_buy_r = pass_buy / total
        pass_sell_r = pass_sell / total
        
        if agg_buy_r > agg_sell_r * 1.5:
            dominant = 'aggressive_buyers'
        elif agg_sell_r > agg_buy_r * 1.5:
            dominant = 'aggressive_sellers'
        else:
            dominant = 'balanced'
        
        # اتجاه العدوانية
        if len(recent) >= 15:
            early = recent[:len(recent)//2]
            late = recent[len(recent)//2:]
            
            early_agg = sum(b.aggression for b in early)
            late_agg = sum(b.aggression for b in late)
            
            if early_agg > 0:
                if late_agg > early_agg * 1.3:
                    aggression_trend = 'increasing'
                elif late_agg < early_agg * 0.7:
                    aggression_trend = 'decreasing'
                else:
                    aggression_trend = 'stable'
            else:
                aggression_trend = 'stable'
        else:
            aggression_trend = 'stable'
        
        return AggressionProfile(
            aggressive_buy_ratio=agg_buy_r,
            aggressive_sell_ratio=agg_sell_r,
            passive_buy_ratio=pass_buy_r,
            passive_sell_ratio=pass_sell_r,
            dominant_side=dominant,
            aggression_trend=aggression_trend,
        )
    
    def _analyze_aggression_waves(self, bars: List[OrderFlowBar], highs: np.ndarray,
                                   lows: np.ndarray, closes: np.ndarray) -> List[Dict]:
        """تحليل موجات العدوانية"""
        waves = []
        
        if len(bars) < 10:
            return waves
        
        current_wave = None
        
        for i in range(len(bars)):
            bar = bars[i]
            if bar.aggression > 0.65:
                if current_wave is None:
                    current_wave = {
                        "start": i,
                        "end": i,
                        "direction": 'buying' if bar.is_up_bar else 'selling',
                        "peak_aggression": bar.aggression,
                        "total_volume": bar.volume,
                    }
                else:
                    current_wave["end"] = i
                    current_wave["peak_aggression"] = max(current_wave["peak_aggression"], bar.aggression)
                    current_wave["total_volume"] += bar.volume
            else:
                if current_wave is not None:
                    current_wave["duration"] = current_wave["end"] - current_wave["start"] + 1
                    waves.append(current_wave)
                    current_wave = None
        
        if current_wave is not None:
            current_wave["duration"] = current_wave["end"] - current_wave["start"] + 1
            waves.append(current_wave)
        
        return waves[-5:]
    
    def _current_aggression_state(self, bars: List[OrderFlowBar]) -> Dict:
        """حالة العدوانية الحالية"""
        if len(bars) < 3:
            return {"state": "غير كافٍ"}
        
        recent = bars[-3:]
        avg_agg = np.mean([b.aggression for b in recent])
        
        if avg_agg > 0.7:
            state = "عدوانية عالية"
            implication = "حركة قوية - دخول أو خروج كبير"
        elif avg_agg > 0.5:
            state = "عدوانية متوسطة"
            implication = "اهتمام بالسوق - تداول طبيعي"
        else:
            state = "عدوانية منخفضة"
            implication = "هدوء - تجميع أو توزيع صامت"
        
        return {"state": state, "implication": implication, "score": avg_agg}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║          الدرجة النهائية: استراتيجية Order Flow الموحدة (محسنة)          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OrderFlowStrategy:
    """
    استراتيجية تدفق الأوامر وقراءة الشريط الكاملة - الإصدار 2.0
    
    تجمع:
    - تقدير تدفق الأوامر
    - تحليل دلتا متعدد الأطر الزمنية
    - تحليل العدوانية
    - كشف التباعدات
    - مناطق السيولة
    - Large Lot Detection
    - Iceberg Detection
    """
    
    def __init__(self):
        self.flow_estimator = OrderFlowEstimator()
        self.aggression_analyzer = AggressionAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 10:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 10 شموع على الأقل"}
        
        # 1. تقدير تدفق الأوامر
        flow_data = self.flow_estimator.analyze(opens, highs, lows, closes, volumes)
        
        # 2. تحليل العدوانية
        bars = flow_data.get('bars', [])
        aggression_data = self.aggression_analyzer.analyze(bars, highs, lows, closes)
        
        # 3. القرار
        decision = self._make_decision(flow_data, aggression_data, closes)
        
        return {
            **decision,
            "flow_data": flow_data,
            "aggression_data": aggression_data,
        }
    
    def _make_decision(self, flow_data: Dict, aggression_data: Dict,
                       closes: np.ndarray) -> Dict:
        """اتخاذ القرار - محسن"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        # ---- من الدلتا ----
        delta_trend = flow_data.get('delta_trend', {})
        current_bar = flow_data.get('current_bar')
        divergences = flow_data.get('divergences', [])
        liquidity_zones = flow_data.get('liquidity_zones', [])
        all_bars = flow_data.get('bars', [])
        
        if delta_trend.get('bias') == 'bullish' and delta_trend.get('strength', 0) > 0.3:
            buy_signals.append(("Delta تراكمي صاعد", delta_trend['strength'] * 0.5))
        elif delta_trend.get('bias') == 'bearish' and delta_trend.get('strength', 0) > 0.3:
            sell_signals.append(("Delta تراكمي هابط", delta_trend['strength'] * 0.5))
        
        # ---- من الشمعة الحالية ----
        if current_bar:
            # امتصاص
            if current_bar.absorption_score > 0.7:
                if current_bar.close_position > 0.6:
                    buy_signals.append(("امتصاص صاعد - المؤسسات تشتري بهدوء", 0.7))
                elif current_bar.close_position < 0.4:
                    sell_signals.append(("امتصاص هابط - المؤسسات تبيع بهدوء", 0.7))
            
            # إنهاك
            if current_bar.exhaustion_score > 0.7:
                if current_bar.is_up_bar:
                    sell_signals.append(("إنهاك شراء - الدلتا تضعف", 0.7))
                else:
                    buy_signals.append(("إنهاك بيع - الدلتا تضعف", 0.7))
            
            # 🟡 تعديل 5: Iceberg
            if current_bar.bar_type == 'iceberg' or current_bar.iceberg_score > 0.6:
                if current_bar.is_up_bar:
                    buy_signals.append(("أوامر مخفية صاعدة (Iceberg)", 0.65))
                else:
                    sell_signals.append(("أوامر مخفية هابطة (Iceberg)", 0.65))
            
            # ذروة
            if current_bar.bar_type == 'climax':
                if current_bar.is_up_bar:
                    sell_signals.append(("ذروة شراء - نهاية الصعود", 0.75))
                else:
                    buy_signals.append(("ذروة بيع - نهاية الهبوط", 0.75))
            
            # Stop Run
            if current_bar.bar_type == 'stop_run':
                if current_bar.is_up_bar:
                    sell_signals.append(("Stop Run علوي - اصطياد وقف خسارة", 0.8))
                else:
                    buy_signals.append(("Stop Run سفلي - اصطياد وقف خسارة", 0.8))
            
            # 🟡 تعديل 4: Large Lot
            if current_bar.is_large_lot:
                lot_desc = f"صفقة كبيرة (×{current_bar.large_lot_ratio:.1f})"
                if current_bar.is_up_bar and current_bar.close_position > 0.7:
                    buy_signals.append((f"{lot_desc} - شراء مؤسسي", 0.7))
                elif not current_bar.is_up_bar and current_bar.close_position < 0.3:
                    sell_signals.append((f"{lot_desc} - بيع مؤسسي", 0.7))
                else:
                    warnings.append(f"{lot_desc} - مراقبة")
        
        # ---- من التباعدات ----
        recent_divs = divergences[-3:] if len(divergences) >= 3 else divergences
        for div in recent_divs:
            if div.significance in ['significant', 'major']:
                base_strength = div.strength * 0.7
                
                # 🟡 تعديل 3: Multi-Timeframe boost
                if div.multi_timeframe_score > 0.3:
                    base_strength *= 1.3
                    desc_suffix = f" (MTF:{div.multi_timeframe_score:.0%})"
                else:
                    desc_suffix = ""
                
                if div.divergence_type == 'bullish':
                    buy_signals.append((f"تباعد دلتا صاعد ({div.significance}){desc_suffix}", base_strength))
                else:
                    sell_signals.append((f"تباعد دلتا هابط ({div.significance}){desc_suffix}", base_strength))
        
        # ---- من العدوانية ----
        profile = aggression_data.get('profile')
        if profile:
            if profile.dominant_side == 'aggressive_buyers':
                buy_signals.append(("مشترين عدوانيين", 0.55))
            elif profile.dominant_side == 'aggressive_sellers':
                sell_signals.append(("بائعين عدوانيين", 0.55))
            
            if profile.aggression_trend == 'increasing':
                if profile.dominant_side == 'aggressive_buyers':
                    buy_signals.append(("عدوانية شراء متزايدة", 0.6))
                elif profile.dominant_side == 'aggressive_sellers':
                    sell_signals.append(("عدوانية بيع متزايدة", 0.6))
        
        # ---- من مناطق السيولة ----
        if liquidity_zones and current_bar:
            for zone in liquidity_zones[:3]:
                if abs(zone.price_level - current_bar.close) < current_bar.close * 0.002:
                    if zone.zone_type == 'absorption' and zone.net_delta > 0:
                        buy_signals.append(("منطقة امتصاص صاعدة", 0.5))
                    elif zone.zone_type == 'absorption' and zone.net_delta < 0:
                        sell_signals.append(("منطقة امتصاص هابطة", 0.5))
        
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
        
        if delta_trend:
            reason += f" | Delta:{delta_trend.get('trend', '?')}"
        
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


def create_order_flow_strategy():
    """إنشاء استراتيجية Order Flow الجاهزة (الإصدار 2.0)"""
    return OrderFlowStrategy()