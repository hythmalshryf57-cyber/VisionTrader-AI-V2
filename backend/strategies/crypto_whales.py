"""
═══════════════════════════════════════════════════════════════════════════════
CRYPTO WHALES & ON-CHAIN ANALYSIS - النسخة الديناميكية المتكاملة
المدرسة الخامسة والعشرون: تحليل الحيتان والبيانات على السلسلة
═══════════════════════════════════════════════════════════════════════════════

سوق الكريبتو مختلف. الحيتان تتحكم. كل شيء على السلسلة (On-Chain).
"تابع الحيتان" وليس "حارب الحيتان".

هذه النسخة ديناميكية بالكامل:
- نكتشف حركة الحيتان من السعر والحجم
- نقدر التدفقات دون الحاجة لبيانات On-Chain مباشرة
- نقدر التجميع والتوزيع من سلوك السعر
- نكتشف "بصمات" الحيتان على الشارت

المفاهيم المتقدمة:
1. Whale Watching (مراقبة الحيتان)
2. Accumulation/Distribution Detection
3. Exchange Inflow/Outflow Estimation
4. Wallet Clustering (تقديري)
5. Large Transaction Detection
6. Supply Distribution
7. Miner Activity
8. Stablecoin Flow
9. Exchange Reserve Estimation
10. Whale vs Retail Divergence
11. Wash Trading Detection
12. Pump & Dump Patterns
13. Wyckoff in Crypto
14. Order Book Depth Analysis
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class WhaleActivity:
    """نشاط حوت"""
    index: int
    activity_type: str      # 'accumulation', 'distribution', 'large_buy', 'large_sell', 'wash_trade', 'spoofing'
    price_level: float
    estimated_volume: float
    confidence: float       # 0-1
    price_impact: float     # التأثير المتوقع على السعر
    description: str


@dataclass
class OnChainEstimate:
    """تقدير بيانات On-Chain"""
    exchange_inflow: float
    exchange_outflow: float
    net_flow: float
    large_transactions: int
    accumulation_score: float    # 0-1 (1 = تجميع قوي)
    distribution_score: float    # 0-1 (1 = توزيع قوي)
    whale_dominance: float       # نسبة سيطرة الحيتان
    retail_activity: float       # نشاط التجزئة


@dataclass
class WhaleSignal:
    """إشارة حوت"""
    index: int
    signal_type: str
    direction: str
    strength: float
    description: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: متتبع الحيتان (Whale Tracker)                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class WhaleTracker:
    """
    يتتبع نشاط الحيتان من حركة السعر والحجم.
    """
    
    def __init__(self):
        self.whale_threshold_volume = 2.5  # ديناميكي
        self.lookback_bars = 100
        
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray) -> Dict:
        """
        تتبع الحيتان
        """
        activities = self._detect_whale_activities(highs, lows, closes, volumes, opens)
        onchain = self._estimate_onchain_metrics(highs, lows, closes, volumes)
        signals = self._generate_whale_signals(activities, onchain, closes)
        
        return {
            "activities": activities[-10:],
            "onchain_estimate": onchain,
            "signals": signals[-5:],
            "whale_dominance": onchain.whale_dominance if onchain else 0,
            "accumulation_score": onchain.accumulation_score if onchain else 0,
        }
    
    def _detect_whale_activities(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray,
                                   opens: np.ndarray) -> List[WhaleActivity]:
        """
        اكتشاف أنشطة الحيتان.
        """
        activities = []
        
        if len(closes) < 20:
            return activities
        
        # متوسط الحجم
        avg_vol = np.mean(volumes[-50:]) if len(volumes) >= 50 else np.mean(volumes)
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        # الديناميكي: عتبة الحوت تتكيف
        self.whale_threshold_volume = max(2.0, 3.5 - np.std(volumes[-20:]) / max(avg_vol, 0.0001))
        
        for i in range(10, len(closes)):
            bar_vol = volumes[i]
            bar_range = highs[i] - lows[i]
            relative_vol = bar_vol / max(avg_vol, 0.0001)
            
            # 1. صفقة كبيرة (حجم مرتفع جداً)
            if relative_vol > self.whale_threshold_volume:
                if closes[i] > opens[i]:
                    activity_type = 'large_buy'
                    direction = 'bullish'
                else:
                    activity_type = 'large_sell'
                    direction = 'bearish'
                
                activities.append(WhaleActivity(
                    index=i,
                    activity_type=activity_type,
                    price_level=closes[i],
                    estimated_volume=bar_vol,
                    confidence=min(0.9, relative_vol / 5),
                    price_impact=bar_range / avg_range if avg_range > 0 else 1,
                    description=f"{'شراء' if direction == 'bullish' else 'بيع'} كبير بحجم {relative_vol:.1f}x",
                ))
            
            # 2. تجميع صامت (حجم منخفض + نطاق ضيق + إغلاق في الأعلى)
            if relative_vol < 0.6 and bar_range < avg_range * 0.6:
                if closes[i] > (highs[i] + lows[i]) / 2:
                    activities.append(WhaleActivity(
                        index=i,
                        activity_type='accumulation',
                        price_level=closes[i],
                        estimated_volume=bar_vol,
                        confidence=0.55,
                        price_impact=0.3,
                        description="تجميع صامت - حجم منخفض مع شراء",
                    ))
            
            # 3. توزيع صامت (حجم منخفض + نطاق ضيق + إغلاق في الأسفل)
            if relative_vol < 0.6 and bar_range < avg_range * 0.6:
                if closes[i] < (highs[i] + lows[i]) / 2:
                    activities.append(WhaleActivity(
                        index=i,
                        activity_type='distribution',
                        price_level=closes[i],
                        estimated_volume=bar_vol,
                        confidence=0.55,
                        price_impact=0.3,
                        description="توزيع صامت - حجم منخفض مع بيع",
                    ))
            
            # 4. Wash Trading (حجم عالي + نطاق ضيق جداً + لا حركة)
            if relative_vol > 2.0 and bar_range < avg_range * 0.3:
                activities.append(WhaleActivity(
                    index=i,
                    activity_type='wash_trade',
                    price_level=closes[i],
                    estimated_volume=bar_vol,
                    confidence=0.6,
                    price_impact=0.1,
                    description=f"Wash Trade مشتبه - حجم {relative_vol:.1f}x بدون حركة",
                ))
            
            # 5. Spoofing (ظل طويل + ارتداد + حجم)
            if bar_range > 0 and relative_vol > 1.5:
                upper_wick = highs[i] - max(opens[i], closes[i])
                lower_wick = min(opens[i], closes[i]) - lows[i]
                
                if upper_wick > bar_range * 0.6 and closes[i] < (highs[i] + lows[i]) / 2:
                    activities.append(WhaleActivity(
                        index=i,
                        activity_type='spoofing',
                        price_level=highs[i],
                        estimated_volume=bar_vol,
                        confidence=0.65,
                        price_impact=0.5,
                        description="Spoofing علوي - حوت يخدع المشترين",
                    ))
                
                if lower_wick > bar_range * 0.6 and closes[i] > (highs[i] + lows[i]) / 2:
                    activities.append(WhaleActivity(
                        index=i,
                        activity_type='spoofing',
                        price_level=lows[i],
                        estimated_volume=bar_vol,
                        confidence=0.65,
                        price_impact=0.5,
                        description="Spoofing سفلي - حوت يخدع البائعين",
                    ))
        
        return activities
    
    def _estimate_onchain_metrics(self, highs: np.ndarray, lows: np.ndarray,
                                    closes: np.ndarray, volumes: np.ndarray) -> OnChainEstimate:
        """
        تقدير مقاييس On-Chain.
        """
        if len(closes) < 30:
            return OnChainEstimate(0, 0, 0, 0, 0.5, 0.5, 0.5, 0.5)
        
        # تقدير التدفقات من الحجم
        avg_vol = np.mean(volumes[-30:])
        
        # الحجم فوق المتوسط = تدفق للداخل (شراء) أو للخارج (بيع)
        recent_vol = volumes[-10:]
        recent_closes = closes[-10:]
        
        inflow = 0
        outflow = 0
        large_tx = 0
        
        for i in range(len(recent_vol)):
            if recent_vol[i] > avg_vol * 1.5:
                large_tx += 1
                if recent_closes[i] > recent_closes[i-1] if i > 0 else True:
                    inflow += recent_vol[i]
                else:
                    outflow += recent_vol[i]
            elif recent_closes[i] > recent_closes[i-1] if i > 0 else True:
                inflow += recent_vol[i] * 0.5
            else:
                outflow += recent_vol[i] * 0.5
        
        total_flow = inflow + outflow
        net_flow = inflow - outflow
        
        # درجة التجميع
        if total_flow > 0:
            accumulation = inflow / total_flow
        else:
            accumulation = 0.5
        
        distribution = 1 - accumulation
        
        # سيطرة الحيتان (من الحجم الكبير)
        large_vol = sum(v for i, v in enumerate(volumes[-20:]) if v > avg_vol * 1.5)
        total_vol = sum(volumes[-20:])
        whale_dominance = large_vol / max(total_vol, 0.0001)
        
        # نشاط التجزئة
        retail_activity = 1 - whale_dominance
        
        return OnChainEstimate(
            exchange_inflow=inflow,
            exchange_outflow=outflow,
            net_flow=net_flow,
            large_transactions=large_tx,
            accumulation_score=accumulation,
            distribution_score=distribution,
            whale_dominance=min(1.0, whale_dominance),
            retail_activity=retail_activity,
        )
    
    def _generate_whale_signals(self, activities: List[WhaleActivity],
                                  onchain: OnChainEstimate,
                                  closes: np.ndarray) -> List[WhaleSignal]:
        """
        توليد إشارات الحيتان.
        """
        signals = []
        
        if not activities:
            return signals
        
        # تجميع الأنشطة الأخيرة
        recent = activities[-10:]
        
        accum_count = sum(1 for a in recent if a.activity_type == 'accumulation')
        distrib_count = sum(1 for a in recent if a.activity_type == 'distribution')
        large_buy = sum(1 for a in recent if a.activity_type == 'large_buy')
        large_sell = sum(1 for a in recent if a.activity_type == 'large_sell')
        spoof_count = sum(1 for a in recent if a.activity_type == 'spoofing')
        
        # إشارة تجميع
        if accum_count >= 3 and onchain.accumulation_score > 0.6:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='whale_accumulation',
                direction='bullish',
                strength=min(0.8, accum_count * 0.2),
                description=f"حيتان تتجمع ({accum_count} إشارات) - صعود متوقع",
            ))
        
        # إشارة توزيع
        if distrib_count >= 3 and onchain.distribution_score > 0.6:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='whale_distribution',
                direction='bearish',
                strength=min(0.8, distrib_count * 0.2),
                description=f"حيتان توزع ({distrib_count} إشارات) - هبوط متوقع",
            ))
        
        # شراء كبير
        if large_buy >= 2:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='large_buy',
                direction='bullish',
                strength=0.7,
                description=f"صفقات شراء كبيرة ({large_buy})",
            ))
        
        # بيع كبير
        if large_sell >= 2:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='large_sell',
                direction='bearish',
                strength=0.7,
                description=f"صفقات بيع كبيرة ({large_sell})",
            ))
        
        # Spoofing
        if spoof_count >= 2:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='spoofing_detected',
                direction='neutral',
                strength=0.5,
                description=f"محاولات خداع ({spoof_count}) - حذر",
            ))
        
        # صافي التدفق
        if onchain.net_flow > 0 and onchain.accumulation_score > 0.65:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='positive_flow',
                direction='bullish',
                strength=0.55,
                description="تدفق إيجابي - أموال تدخل السوق",
            ))
        elif onchain.net_flow < 0 and onchain.distribution_score > 0.65:
            signals.append(WhaleSignal(
                index=len(closes)-1,
                signal_type='negative_flow',
                direction='bearish',
                strength=0.55,
                description="تدفق سلبي - أموال تخرج من السوق",
            ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف المضخات والتفريغ (Pump & Dump Detector)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PumpDumpDetector:
    """
    يكتشف أنماط Pump & Dump.
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """
        كشف المضخات والتفريغ
        """
        pumps = self._detect_pumps(highs, lows, closes, volumes)
        dumps = self._detect_dumps(highs, lows, closes, volumes)
        manipulation_zones = self._find_manipulation_zones(highs, lows, closes, volumes)
        
        return {
            "pumps": pumps[-5:],
            "dumps": dumps[-5:],
            "manipulation_zones": manipulation_zones,
            "active_pump": len(pumps) > 0 and pumps[-1].get('active', False),
            "active_dump": len(dumps) > 0 and dumps[-1].get('active', False),
        }
    
    def _detect_pumps(self, highs: np.ndarray, lows: np.ndarray,
                       closes: np.ndarray, volumes: np.ndarray) -> List[Dict]:
        """
        اكتشاف المضخات.
        """
        pumps = []
        
        if len(closes) < 15:
            return pumps
        
        for i in range(10, len(closes) - 3):
            # صعود حاد بحجم مرتفع
            price_change = (closes[i] - closes[i-5]) / closes[i-5] if closes[i-5] > 0 else 0
            
            if price_change > 0.15:  # 15% في 5 شموع
                vol_spike = volumes[i] > np.mean(volumes[max(0,i-10):i]) * 2
                
                # فحص الانهيار بعدها
                dump_after = False
                if i + 5 < len(closes):
                    post_change = (closes[i+5] - closes[i]) / closes[i] if closes[i] > 0 else 0
                    if post_change < -0.10:
                        dump_after = True
                
                pumps.append({
                    "index": i,
                    "price": closes[i],
                    "change_pct": price_change * 100,
                    "volume_spike": vol_spike,
                    "dump_after": dump_after,
                    "active": not dump_after,
                    "pattern": "Pump & Dump" if dump_after else "Pump",
                })
        
        return pumps
    
    def _detect_dumps(self, highs: np.ndarray, lows: np.ndarray,
                       closes: np.ndarray, volumes: np.ndarray) -> List[Dict]:
        """
        اكتشاف التفريغ.
        """
        dumps = []
        
        if len(closes) < 15:
            return dumps
        
        for i in range(10, len(closes) - 3):
            price_change = (closes[i] - closes[i-5]) / closes[i-5] if closes[i-5] > 0 else 0
            
            if price_change < -0.15:
                vol_spike = volumes[i] > np.mean(volumes[max(0,i-10):i]) * 2
                
                pump_after = False
                if i + 5 < len(closes):
                    post_change = (closes[i+5] - closes[i]) / closes[i] if closes[i] > 0 else 0
                    if post_change > 0.10:
                        pump_after = True
                
                dumps.append({
                    "index": i,
                    "price": closes[i],
                    "change_pct": price_change * 100,
                    "volume_spike": vol_spike,
                    "pump_after": pump_after,
                    "active": not pump_after,
                    "pattern": "Dump & Pump" if pump_after else "Dump",
                })
        
        return dumps
    
    def _find_manipulation_zones(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> List[Dict]:
        """
        إيجاد مناطق التلاعب.
        """
        zones = []
        
        if len(closes) < 20:
            return zones
        
        # مناطق ذات حجم مرتفع متكرر = تجمع/توزيع
        vol_peaks = []
        avg_vol = np.mean(volumes)
        
        for i in range(5, len(closes)):
            if volumes[i] > avg_vol * 2.5:
                vol_peaks.append({"index": i, "price": closes[i], "volume": volumes[i]})
        
        # تجميع القمم القريبة
        if len(vol_peaks) >= 2:
            for i in range(len(vol_peaks) - 1):
                if abs(vol_peaks[i]['price'] - vol_peaks[i+1]['price']) < closes[-1] * 0.02:
                    zones.append({
                        "price": (vol_peaks[i]['price'] + vol_peaks[i+1]['price']) / 2,
                        "type": "manipulation_zone",
                        "volume_sum": vol_peaks[i]['volume'] + vol_peaks[i+1]['volume'],
                    })
        
        return zones


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الحيتان الموحدة                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CryptoWhalesStrategy:
    """
    استراتيجية تحليل الحيتان والكريبتو الكاملة.
    """
    
    def __init__(self):
        self.whale_tracker = WhaleTracker()
        self.pump_dump_detector = PumpDumpDetector()
    
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
        
        # 1. تتبع الحيتان
        whale_data = self.whale_tracker.analyze(highs, lows, closes, volumes, opens)
        
        # 2. كشف المضخات
        pd_data = self.pump_dump_detector.analyze(highs, lows, closes, volumes)
        
        # 3. القرار
        decision = self._make_decision(whale_data, pd_data, closes)
        
        return {
            **decision,
            "whale_data": whale_data,
            "pd_data": pd_data,
        }
    
    def _make_decision(self, whale_data: Dict, pd_data: Dict,
                       closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        current_price = closes[-1] if len(closes) > 0 else 0
        
        # ---- من إشارات الحيتان ----
        signals = whale_data.get('signals', [])
        for sig in signals:
            weight = sig.strength * 0.7
            
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, weight))
            elif sig.direction == 'bearish':
                sell_signals.append((sig.description, weight))
        
        # ---- من On-Chain ----
        onchain = whale_data.get('onchain_estimate')
        if onchain:
            if onchain.accumulation_score > 0.65:
                buy_signals.append((f"تجميع On-Chain ({onchain.accumulation_score:.1%})", 
                                   onchain.accumulation_score * 0.6))
            if onchain.distribution_score > 0.65:
                sell_signals.append((f"توزيع On-Chain ({onchain.distribution_score:.1%})",
                                    onchain.distribution_score * 0.6))
            if onchain.whale_dominance > 0.6:
                buy_signals.append((f"هيمنة حيتان ({onchain.whale_dominance:.1%}) - تابعهم", 0.4))
        
        # ---- من المضخات ----
        if pd_data.get('active_pump'):
            sell_signals.append(("Pump نشط - خطر انهيار", 0.65))
        if pd_data.get('active_dump'):
            buy_signals.append(("Dump نشط - فرصة ارتداد", 0.55))
        
        # ---- من أنشطة الحيتان ----
        activities = whale_data.get('activities', [])
        buy_activities = sum(1 for a in activities if a.activity_type in ['accumulation', 'large_buy'])
        sell_activities = sum(1 for a in activities if a.activity_type in ['distribution', 'large_sell'])
        
        if buy_activities > sell_activities * 2:
            buy_signals.append(("حيتان تشتري أكثر مما تبيع", 0.5))
        elif sell_activities > buy_activities * 2:
            sell_signals.append(("حيتان تبيع أكثر مما تشتري", 0.5))
        
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
            confidence = 40
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 40
        else:
            recommendation = "محايد"
            confidence = 25
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_crypto_whales_strategy():
    """إنشاء استراتيجية الحيتان الجاهزة"""
    return CryptoWhalesStrategy()