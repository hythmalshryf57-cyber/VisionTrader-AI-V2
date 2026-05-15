"""
═══════════════════════════════════════════════════════════════════════════════
LIQUIDATION HEATMAP STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السادسة والعشرون: خريطة التصفيات الحرارية - بيانات حقيقية
═══════════════════════════════════════════════════════════════════════════════

في أسواق العملات الرقمية، التصفيات (Liquidations) هي الوقود.
عندما تتم تصفية مراكز، السعر يتحرك بعنف.

هذه النسخة ديناميكية بالكامل - معاد بناؤها:
- تحاول جلب Liquidations حقيقية من Binance API
- Funding Rate Analysis
- Open Interest Analysis
- إذا فشل الاتصال: تقدير احتياطي مع إفصاح صريح
- Leverage تقديري من Funding Rate (ليس 10x ثابت)

المفاهيم:
1. Real Liquidation Data (Binance API)
2. Estimated Liquidation Levels (احتياطي)
3. Funding Rate Pressure
4. Open Interest Impact
5. Liquidation Cascade Detection
6. Long/Short Squeeze Zones
7. Max Pain for Leverage
8. Leverage Flush Detection
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المعاد بناؤها                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class LiquidationLevel:
    """مستوى تصفية"""
    price: float
    direction: str
    estimated_size: float
    intensity: float
    cumulative: float
    cascade_risk: float
    data_source: str = 'estimated'  # 'real' or 'estimated'


@dataclass
class LiquidationHeatmap:
    """خريطة التصفيات"""
    levels: List[LiquidationLevel]
    max_pain_long: float
    max_pain_short: float
    long_squeeze_zone: Tuple[float, float]
    short_squeeze_zone: Tuple[float, float]
    total_estimated_longs: float
    total_estimated_shorts: float
    imbalance_ratio: float
    data_source: str = 'estimated'
    # 🟡 تعديل 5: Funding Rate
    funding_rate: float = 0.0
    funding_pressure: str = 'neutral'
    # 🟡 تعديل 6: Open Interest
    open_interest: float = 0.0
    oi_change_24h: float = 0.0


@dataclass
class LiquidationSignal:
    """إشارة تصفية"""
    index: int
    signal_type: str
    direction: str
    strength: float
    description: str
    data_quality: str = 'estimated'


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: جسر بيانات التصفيات الحقيقية                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LiquidationDataBridge:
    """
    🔴 تعديل 1 + 🟡 تعديل 4: جسر إلى بيانات التصفيات الحقيقية
    
    يحاول جلب:
    - Liquidations من Binance API
    - Funding Rate
    - Open Interest
    """
    
    def __init__(self):
        self.binance_service = None
        self._init_binance()
        self.cached_liquidations = []
        self.cached_funding_rate = None
        self.cached_open_interest = None
        self.last_fetch_time = None
    
    def _init_binance(self):
        """محاولة الاتصال بـ Binance"""
        try:
            from services.binance_service import BinanceService
            self.binance_service = BinanceService()
            logger.info("✅ تم ربط BinanceService لبيانات التصفيات")
        except ImportError:
            logger.info("ℹ️ BinanceService غير متاح - استخدام التقدير الاحتياطي")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تهيئة BinanceService: {e}")
    
    def get_liquidation_data(self, symbol: str = "BTCUSDT") -> Dict:
        """
        جلب بيانات التصفيات الحقيقية
        """
        result = {
            "has_real_data": False,
            "liquidations": [],
            "funding_rate": None,
            "open_interest": None,
            "oi_change_24h": None,
            "source": "none",
        }
        
        if self.binance_service:
            try:
                # جلب التصفيات
                liqs = self._fetch_liquidations(symbol)
                if liqs:
                    result["liquidations"] = liqs
                    result["has_real_data"] = True
                    result["source"] = "binance"
                
                # جلب Funding Rate
                fr = self._fetch_funding_rate(symbol)
                if fr is not None:
                    result["funding_rate"] = fr
                
                # جلب Open Interest
                oi = self._fetch_open_interest(symbol)
                if oi:
                    result["open_interest"] = oi.get("current")
                    result["oi_change_24h"] = oi.get("change_24h")
                    
            except Exception as e:
                logger.warning(f"تعذر جلب بيانات التصفيات من Binance: {e}")
        
        return result
    
    def _fetch_liquidations(self, symbol: str) -> List[Dict]:
        """جلب التصفيات من Binance"""
        try:
            if self.binance_service:
                liqs = self.binance_service.get_liquidations(symbol, limit=100)
                if liqs:
                    self.cached_liquidations = liqs
                    self.last_fetch_time = datetime.now()
                    return liqs
        except:
            pass
        return []
    
    def _fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        🟡 تعديل 5: جلب Funding Rate
        """
        try:
            if self.binance_service:
                fr = self.binance_service.get_funding_rate(symbol)
                if fr is not None:
                    self.cached_funding_rate = fr
                    return fr
        except:
            pass
        return None
    
    def _fetch_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        🟡 تعديل 6: جلب Open Interest
        """
        try:
            if self.binance_service:
                oi = self.binance_service.get_open_interest(symbol)
                if oi:
                    self.cached_open_interest = oi
                    return oi
        except:
            pass
        return None
    
    def estimate_leverage_from_funding(self, funding_rate: float) -> float:
        """
        🔴 تعديل 2: تقدير الرافعة من Funding Rate
        
        Funding Rate مرتفع = رافعة عالية (Shorts تدفع للLongs)
        Funding Rate سالب = رافعة عالية (Longs تدفع للShorts)
        """
        if funding_rate is None:
            return 10.0  # افتراضي
        
        # Funding Rate طبيعي ≈ 0.01% كل 8 ساعات
        # إذا ارتفع لـ 0.1% = رافعة عالية
        base_leverage = 5.0
        additional = abs(funding_rate) * 10000  # تطبيع
        
        return min(100.0, max(3.0, base_leverage + additional))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: باني خريطة التصفيات (محسن)                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LiquidationHeatmapBuilder:
    """
    يبني خريطة التصفيات - حقيقية أو تقديرية.
    
    🔴 تعديل 1: بيانات حقيقية من Binance
    🔴 تعديل 2: Leverage ديناميكي من Funding Rate
    """
    
    def __init__(self):
        self.data_bridge = LiquidationDataBridge()
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, symbol: str = "BTCUSDT") -> LiquidationHeatmap:
        """بناء خريطة التصفيات"""
        
        current_price = closes[-1] if len(closes) > 0 else 0.0
        
        # جلب بيانات حقيقية
        real_data = self.data_bridge.get_liquidation_data(symbol)
        has_real = real_data.get("has_real_data", False)
        funding_rate = real_data.get("funding_rate", 0.0) or 0.0
        open_interest = real_data.get("open_interest", 0.0) or 0.0
        oi_change = real_data.get("oi_change_24h", 0.0) or 0.0
        
        # 🔴 تعديل 2: تقدير الرافعة من Funding Rate
        leverage_estimate = self.data_bridge.estimate_leverage_from_funding(funding_rate)
        
        # بناء المستويات
        if has_real and real_data.get("liquidations"):
            levels = self._build_from_real_data(real_data["liquidations"], current_price)
            data_source = 'real'
        else:
            levels = self._build_estimated_levels(highs, lows, closes, volumes, 
                                                   current_price, leverage_estimate)
            data_source = 'estimated'
        
        # ترتيب المستويات
        levels.sort(key=lambda l: l.price)
        
        # حساب التراكمي
        cum_long = 0.0
        cum_short = 0.0
        for level in levels:
            if level.direction == 'longs':
                cum_long += level.estimated_size
                level.cumulative = cum_long
            else:
                cum_short += level.estimated_size
                level.cumulative = cum_short
        
        # خطر التتالي
        for i, level in enumerate(levels):
            nearby = [l for l in levels[max(0,i-3):min(len(levels),i+4)] 
                     if l.direction == level.direction]
            if len(nearby) >= 3:
                level.cascade_risk = min(1.0, len(nearby) * 0.25)
        
        # Max Pain
        long_levels = [l for l in levels if l.direction == 'longs' and l.price < current_price]
        short_levels = [l for l in levels if l.direction == 'shorts' and l.price > current_price]
        
        max_pain_long = max(long_levels, key=lambda l: l.intensity).price if long_levels else current_price * 0.9
        max_pain_short = max(short_levels, key=lambda l: l.intensity).price if short_levels else current_price * 1.1
        
        long_squeeze = (max_pain_long * 0.99, max_pain_long * 1.01)
        short_squeeze = (max_pain_short * 0.99, max_pain_short * 1.01)
        
        total_longs = sum(l.estimated_size for l in levels if l.direction == 'longs')
        total_shorts = sum(l.estimated_size for l in levels if l.direction == 'shorts')
        imbalance = total_longs / max(total_shorts, 0.0001)
        
        # 🟡 تعديل 5: Funding Pressure
        if funding_rate > 0.0005:
            funding_pressure = 'short_paying'  # Shorts تدفع = Longs أكثر
        elif funding_rate < -0.0005:
            funding_pressure = 'long_paying'   # Longs تدفع = Shorts أكثر
        else:
            funding_pressure = 'neutral'
        
        return LiquidationHeatmap(
            levels=levels,
            max_pain_long=max_pain_long,
            max_pain_short=max_pain_short,
            long_squeeze_zone=long_squeeze,
            short_squeeze_zone=short_squeeze,
            total_estimated_longs=total_longs,
            total_estimated_shorts=total_shorts,
            imbalance_ratio=imbalance,
            data_source=data_source,
            funding_rate=funding_rate,
            funding_pressure=funding_pressure,
            open_interest=open_interest,
            oi_change_24h=oi_change,
        )
    
    def _build_from_real_data(self, liquidations: List[Dict], 
                                current_price: float) -> List[LiquidationLevel]:
        """
        🔴 تعديل 1: بناء المستويات من بيانات حقيقية
        """
        levels = []
        
        # تجميع التصفيات حسب السعر
        price_buckets = defaultdict(lambda: {'long_vol': 0.0, 'short_vol': 0.0, 'count': 0})
        
        for liq in liquidations:
            price = liq.get('price', 0)
            side = liq.get('side', '')
            volume = liq.get('volume', 0) or liq.get('quantity', 0)
            
            # تقريب لأقرب مستوى
            if price > 10000:
                bucket = round(price / 50) * 50
            elif price > 1000:
                bucket = round(price / 10) * 10
            elif price > 100:
                bucket = round(price / 1) * 1
            else:
                bucket = round(price, 2)
            
            if 'long' in str(side).lower() or 'buy' in str(side).lower():
                price_buckets[bucket]['long_vol'] += float(volume)
            else:
                price_buckets[bucket]['short_vol'] += float(volume)
            price_buckets[bucket]['count'] += 1
        
        max_vol = max(
            max(d['long_vol'], d['short_vol']) for d in price_buckets.values()
        ) if price_buckets else 1.0
        
        for price, data in price_buckets.items():
            if data['long_vol'] > 0:
                levels.append(LiquidationLevel(
                    price=price,
                    direction='longs',
                    estimated_size=data['long_vol'],
                    intensity=min(1.0, data['long_vol'] / max_vol),
                    cumulative=0.0,
                    cascade_risk=0.0,
                    data_source='real',
                ))
            
            if data['short_vol'] > 0:
                levels.append(LiquidationLevel(
                    price=price,
                    direction='shorts',
                    estimated_size=data['short_vol'],
                    intensity=min(1.0, data['short_vol'] / max_vol),
                    cumulative=0.0,
                    cascade_risk=0.0,
                    data_source='real',
                ))
        
        return levels
    
    def _build_estimated_levels(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray,
                                  current_price: float, 
                                  leverage: float) -> List[LiquidationLevel]:
        """
        بناء مستويات تقديرية (احتياطي)
        """
        levels = []
        
        # من القمم والقيعان
        for i in range(5, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1]:
                size = volumes[i] * leverage * 0.3
                levels.append(LiquidationLevel(
                    price=highs[i] * 1.005, direction='shorts',
                    estimated_size=size,
                    intensity=min(1.0, size / max(np.sum(volumes) * 0.1, 0.0001)),
                    cumulative=0.0, cascade_risk=0.0, data_source='estimated',
                ))
            
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1]:
                size = volumes[i] * leverage * 0.3
                levels.append(LiquidationLevel(
                    price=lows[i] * 0.995, direction='longs',
                    estimated_size=size,
                    intensity=min(1.0, size / max(np.sum(volumes) * 0.1, 0.0001)),
                    cumulative=0.0, cascade_risk=0.0, data_source='estimated',
                ))
        
        # مستويات دائرية
        round_levels = self._generate_round_levels(current_price)
        for rl in round_levels:
            levels.append(LiquidationLevel(
                price=rl,
                direction='shorts' if rl > current_price else 'longs',
                estimated_size=np.sum(volumes) * 0.05,
                intensity=0.3, cumulative=0.0, cascade_risk=0.0,
                data_source='estimated',
            ))
        
        return levels
    
    def _generate_round_levels(self, price: float) -> List[float]:
        """توليد مستويات دائرية"""
        levels = []
        step = 100.0 if price > 10000 else 10.0 if price > 1000 else 1.0 if price > 100 else 0.1
        base = round(price / step) * step
        for i in range(-10, 11):
            levels.append(base + i * step)
        return levels


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║          الدرجة النهائية: استراتيجية خريطة التصفيات الموحدة (محسنة)       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LiquidationHeatmapStrategy:
    """
    استراتيجية خريطة التصفيات - الإصدار 2.0
    
    - بيانات حقيقية من Binance API
    - Funding Rate Analysis
    - Open Interest Analysis
    - Leverage ديناميكي
    - تقدير احتياطي مع إفصاح
    """
    
    def __init__(self):
        self.heatmap_builder = LiquidationHeatmapBuilder()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        symbol = chart_data.get('symbol', 'BTCUSDT')
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # بناء Heatmap
        heatmap = self.heatmap_builder.analyze(highs, lows, closes, volumes, symbol)
        
        # كشف مناطق الخطر
        danger_zones = self._detect_danger_zones(heatmap, current_price)
        
        # كشف Cascade
        cascade = self._detect_cascade_risk(closes, volumes)
        
        # قرار
        decision = self._make_decision(heatmap, danger_zones, cascade, current_price)
        
        return {**decision, "heatmap": heatmap, "danger_zones": danger_zones, "cascade": cascade}
    
    def _detect_danger_zones(self, heatmap: LiquidationHeatmap,
                              current_price: float) -> List[Dict]:
        """كشف مناطق الخطر"""
        zones = []
        
        long_zone = heatmap.long_squeeze_zone
        if long_zone[0] > 0 and abs(current_price - long_zone[0]) < current_price * 0.02:
            zones.append({
                "type": "long_squeeze", "price": long_zone[0],
                "message": "منطقة تصفية لونج قريبة - خطر هبوط حاد", "severity": "high",
            })
        
        short_zone = heatmap.short_squeeze_zone
        if short_zone[0] > 0 and abs(current_price - short_zone[1]) < current_price * 0.02:
            zones.append({
                "type": "short_squeeze", "price": short_zone[1],
                "message": "منطقة تصفية شورت قريبة - خطر صعود حاد", "severity": "high",
            })
        
        if heatmap.imbalance_ratio > 2.0:
            zones.append({
                "type": "imbalance",
                "message": f"لونج أكثر بـ {heatmap.imbalance_ratio:.1f}x - قابل للتصفية", "severity": "medium",
            })
        elif heatmap.imbalance_ratio < 0.5:
            zones.append({
                "type": "imbalance",
                "message": f"شورت أكثر بـ {1/heatmap.imbalance_ratio:.1f}x - قابل للتصفية", "severity": "medium",
            })
        
        return zones
    
    def _detect_cascade_risk(self, closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """كشف خطر سلسلة التصفيات"""
        if len(closes) < 10:
            return {"active": False, "risk": 0.0}
        
        recent_change = abs(closes[-1] - closes[-5]) / max(closes[-5], 0.0001) if len(closes) >= 5 else 0.0
        recent_vol = np.mean(volumes[-3:]) / max(np.mean(volumes[-10:]), 0.0001) if len(volumes) >= 10 else 1.0
        
        cascade_score = recent_change * 20.0 + max(0, (recent_vol - 1.0)) * 0.3
        
        return {
            "active": cascade_score > 0.5,
            "risk": min(1.0, cascade_score),
            "direction": 'down' if closes[-1] < closes[-5] else 'up',
        }
    
    def _make_decision(self, heatmap: LiquidationHeatmap,
                       danger_zones: List[Dict], cascade: Dict,
                       current_price: float) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        data_source = heatmap.data_source
        
        # ---- من Funding Rate ----
        if heatmap.funding_pressure == 'short_paying':
            buy_signals.append((f"Funding Rate موجب ({heatmap.funding_rate:.4%}) - Shorts تدفع", 0.5))
            if heatmap.funding_rate > 0.001:
                warnings.append("Funding Rate مرتفع - خطر Short Squeeze")
        elif heatmap.funding_pressure == 'long_paying':
            sell_signals.append((f"Funding Rate سالب ({heatmap.funding_rate:.4%}) - Longs تدفع", 0.5))
            if heatmap.funding_rate < -0.001:
                warnings.append("Funding Rate سالب - خطر Long Squeeze")
        
        # ---- من Open Interest ----
        if heatmap.oi_change_24h > 5.0 and closes[-1] > closes[-5] if len(closes) >= 5 else False:
            buy_signals.append((f"OI + سعر + ({heatmap.oi_change_24h:.0f}%) - استمرار صاعد", 0.5))
        elif heatmap.oi_change_24h > 5.0 and closes[-1] < closes[-5] if len(closes) >= 5 else False:
            sell_signals.append((f"OI + سعر - ({heatmap.oi_change_24h:.0f}%) - توزيع", 0.5))
        
        # ---- من اختلال التوازن ----
        if heatmap.imbalance_ratio > 2.0:
            sell_signals.append((f"خلل توازن: لونج {heatmap.imbalance_ratio:.1f}x", 0.55))
        elif heatmap.imbalance_ratio < 0.5:
            buy_signals.append((f"خلل توازن: شورت {1/heatmap.imbalance_ratio:.1f}x", 0.55))
        
        # ---- من مناطق الخطر ----
        for zone in danger_zones:
            if zone['type'] == 'long_squeeze' and zone['severity'] == 'high':
                sell_signals.append((zone['message'], 0.65))
            elif zone['type'] == 'short_squeeze' and zone['severity'] == 'high':
                buy_signals.append((zone['message'], 0.65))
        
        # ---- من Cascade ----
        if cascade.get('active'):
            if cascade.get('direction') == 'down':
                sell_signals.append(("سلسلة تصفيات هابطة محتملة", 0.7))
            else:
                buy_signals.append(("سلسلة تصفيات صاعدة محتملة", 0.7))
        
        # ---- تحذير البيانات ----
        if data_source == 'estimated':
            warnings.append("⚠️ بيانات التصفيات تقديرية (لا يوجد مصدر حقيقي)")
        else:
            buy_signals.append(("✅ بيانات تصفيات حقيقية من Binance", 0.1))
        
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
        reason += f" | جودة:{'حقيقي' if data_source == 'real' else 'تقديري'}"
        
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


def create_liquidation_heatmap_strategy():
    """إنشاء استراتيجية Liquidation Heatmap الجاهزة (الإصدار 2.0)"""
    return LiquidationHeatmapStrategy()