"""
═══════════════════════════════════════════════════════════════════════════════
HFT & SPOOFING DETECTION - النسخة الديناميكية المتكاملة
المدرسة الثالثة والثلاثون: كشف التلاعب عالي التردد والخداع
═══════════════════════════════════════════════════════════════════════════════

في عالم HFT (High Frequency Trading)، الخوارزميات تتقاتل بالمللي ثانية.
أشهر أساليب التلاعب: Spoofing, Layering, Quote Stuffing.

هذه الاستراتيجية تكتشف "بصمات" هذه الممارسات من السعر والحجم،
حتى بدون بيانات Level 2 حقيقية.

المفاهيم:
1. Spoofing Detection (الخداع)
2. Layering Detection (الطبقات)
3. Quote Stuffing (حشو الأوامر)
4. Wash Trading (تداول وهمي)
5. Momentum Ignition (إشعال الزخم)
6. Order Book Imbalance
7. Flash Crash Patterns
8. Algorithmic Footprints
9. Iceberg Orders
10. Stop Hunting Algorithms
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class SpoofEvent:
    """حدث خداع"""
    index: int
    event_type: str        # 'spoof', 'layer', 'stuff', 'wash', 'ignition', 'iceberg', 'stop_hunt'
    direction: str
    price_level: float
    volume_anomaly: float
    confidence: float
    description: str


@dataclass
class AlgoFootprint:
    """بصمة خوارزمية"""
    footprint_type: str    # 'vwap', 'twap', 'iceberg', 'pegging', 'dark_pool', 'aggressive'
    active: bool
    intensity: float
    price_impact: float
    description: str


@dataclass
class HFTProfile:
    """بروفايل نشاط HFT"""
    spoofing_score: float        # 0-1
    manipulation_risk: float     # 0-1
    algo_dominance: float        # 0-1
    flash_crash_risk: float      # 0-1
    market_fragility: float      # 0-1
    active_algorithms: List[str]


class HFTSpoofingStrategy:
    """
    استراتيجية كشف التلاعب HFT والخداع.
    """
    
    def __init__(self):
        self.spoof_patterns = deque(maxlen=100)
        self.vol_anomaly_threshold = 3.0
        
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
        
        current_price = closes[-1]
        
        # 1. كشف أحداث الخداع
        spoof_events = self._detect_spoofing(highs, lows, closes, volumes, opens)
        
        # 2. كشف البصمات الخوارزمية
        footprints = self._detect_algo_footprints(highs, lows, closes, volumes)
        
        # 3. بناء بروفايل HFT
        hft_profile = self._build_hft_profile(spoof_events, footprints, closes, volumes)
        
        # 4. كشف أنماط Flash Crash
        flash_crash = self._detect_flash_crash_pattern(highs, lows, closes, volumes)
        
        # 5. القرار
        decision = self._make_decision(spoof_events, footprints, hft_profile, 
                                        flash_crash, current_price)
        
        return {
            **decision,
            "spoof_events": spoof_events[-10:],
            "footprints": footprints,
            "hft_profile": hft_profile,
            "flash_crash": flash_crash,
        }
    
    def _detect_spoofing(self, highs: np.ndarray, lows: np.ndarray,
                          closes: np.ndarray, volumes: np.ndarray,
                          opens: np.ndarray) -> List[SpoofEvent]:
        """
        كشف الخداع (Spoofing).
        """
        events = []
        
        if len(closes) < 5:
            return events
        
        avg_vol = np.mean(volumes[-30:]) if len(volumes) >= 30 else np.mean(volumes)
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        for i in range(3, len(closes) - 2):
            bar_range = highs[i] - lows[i]
            bar_vol = volumes[i]
            
            if bar_range == 0:
                continue
            
            # 1. Spoofing كلاسيكي: ظل طويل + ارتداد فوري + حجم مرتفع
            upper_wick = highs[i] - max(opens[i], closes[i])
            lower_wick = min(opens[i], closes[i]) - lows[i]
            
            if upper_wick > bar_range * 0.55 and closes[i] < (highs[i] + lows[i]) / 2:
                if bar_vol > avg_vol * 1.8:
                    events.append(SpoofEvent(
                        index=i,
                        event_type='spoof',
                        direction='bearish',
                        price_level=highs[i],
                        volume_anomaly=bar_vol / max(avg_vol, 0.0001),
                        confidence=min(0.9, upper_wick / bar_range),
                        description=f"خداع علوي - أوامر وهمية فوق {highs[i]:.4f}",
                    ))
            
            if lower_wick > bar_range * 0.55 and closes[i] > (highs[i] + lows[i]) / 2:
                if bar_vol > avg_vol * 1.8:
                    events.append(SpoofEvent(
                        index=i,
                        event_type='spoof',
                        direction='bullish',
                        price_level=lows[i],
                        volume_anomaly=bar_vol / max(avg_vol, 0.0001),
                        confidence=min(0.9, lower_wick / bar_range),
                        description=f"خداع سفلي - أوامر وهمية تحت {lows[i]:.4f}",
                    ))
            
            # 2. Layering: شموع صغيرة متتالية مع حجم مرتفع
            if i >= 5:
                recent_ranges = highs[i-3:i+1] - lows[i-3:i+1]
                recent_vols = volumes[i-3:i+1]
                
                if np.mean(recent_ranges) < avg_range * 0.4 and np.mean(recent_vols) > avg_vol * 1.5:
                    events.append(SpoofEvent(
                        index=i,
                        event_type='layer',
                        direction='neutral',
                        price_level=closes[i],
                        volume_anomaly=np.mean(recent_vols) / max(avg_vol, 0.0001),
                        confidence=0.65,
                        description="Layering - طبقات أوامر وهمية",
                    ))
            
            # 3. Quote Stuffing: حجم هائل + نطاق ضيق جداً
            if bar_vol > avg_vol * self.vol_anomaly_threshold and bar_range < avg_range * 0.2:
                events.append(SpoofEvent(
                    index=i,
                    event_type='stuff',
                    direction='neutral',
                    price_level=closes[i],
                    volume_anomaly=bar_vol / max(avg_vol, 0.0001),
                    confidence=0.75,
                    description="Quote Stuffing - حشو أوامر",
                ))
            
            # 4. Momentum Ignition: حركة سريعة متبوعة بحجم
            if i >= 4:
                price_change = abs(closes[i] - closes[i-3]) / closes[i-3] if closes[i-3] > 0 else 0
                if price_change > 0.02 and bar_vol > avg_vol * 2:
                    events.append(SpoofEvent(
                        index=i,
                        event_type='ignition',
                        direction='bullish' if closes[i] > closes[i-3] else 'bearish',
                        price_level=closes[i],
                        volume_anomaly=bar_vol / max(avg_vol, 0.0001),
                        confidence=0.7,
                        description="Momentum Ignition - إشعال الزخم",
                    ))
            
            # 5. Iceberg: حجم ثابت مع حركة مستمرة
            if i >= 10 and bar_vol > avg_vol * 1.3 and bar_range < avg_range * 0.7:
                if 0.35 < ((closes[i] - lows[i]) / bar_range) < 0.65:
                    events.append(SpoofEvent(
                        index=i,
                        event_type='iceberg',
                        direction='neutral',
                        price_level=closes[i],
                        volume_anomaly=bar_vol / max(avg_vol, 0.0001),
                        confidence=0.55,
                        description="Iceberg - أوامر مخفية",
                    ))
        
        return events
    
    def _detect_algo_footprints(self, highs: np.ndarray, lows: np.ndarray,
                                  closes: np.ndarray, volumes: np.ndarray) -> List[AlgoFootprint]:
        """
        كشف بصمات الخوارزميات.
        """
        footprints = []
        
        if len(closes) < 20:
            return footprints
        
        avg_vol = np.mean(volumes[-20:])
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        # VWAP Algorithm
        if avg_range > 0:
            close_position_consistency = np.std((closes[-10:] - lows[-10:]) / 
                                                 np.maximum(highs[-10:] - lows[-10:], 0.0001))
            if close_position_consistency < 0.15:
                footprints.append(AlgoFootprint(
                    footprint_type='vwap',
                    active=True,
                    intensity=0.7,
                    price_impact=0.3,
                    description="خوارزمية VWAP نشطة - تنفيذ متوازن",
                ))
        
        # TWAP Algorithm
        vol_std = np.std(volumes[-20:])
        vol_mean = np.mean(volumes[-20:])
        if vol_mean > 0 and vol_std / vol_mean < 0.4:
            footprints.append(AlgoFootprint(
                footprint_type='twap',
                active=True,
                intensity=0.6,
                price_impact=0.2,
                description="خوارزمية TWAP نشطة - حجم منتظم",
            ))
        
        # Iceberg Algorithm
        high_vol_bars = sum(1 for v in volumes[-20:] if v > avg_vol * 1.5)
        if high_vol_bars >= 3 and avg_range < np.mean(highs[-50:-20] - lows[-50:-20]) * 0.7 if len(highs) >= 50 else 1:
            footprints.append(AlgoFootprint(
                footprint_type='iceberg',
                active=True,
                intensity=0.65,
                price_impact=0.4,
                description="Iceberg - حجم كبير مخفي",
            ))
        
        # Dark Pool (حركة بدون حجم)
        ranges = highs[-10:] - lows[-10:]
        vols = volumes[-10:]
        if np.mean(ranges) > avg_range * 0.8 and np.mean(vols) < avg_vol * 0.6:
            footprints.append(AlgoFootprint(
                footprint_type='dark_pool',
                active=True,
                intensity=0.55,
                price_impact=0.5,
                description="Dark Pool - حركة بدون حجم واضح",
            ))
        
        # Aggressive Algo
        if len(closes) >= 5:
            price_change = abs(closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
            vol_spike = volumes[-1] / max(avg_vol, 0.0001)
            if price_change > 0.01 and vol_spike > 2.0:
                footprints.append(AlgoFootprint(
                    footprint_type='aggressive',
                    active=True,
                    intensity=0.8,
                    price_impact=0.7,
                    description="خوارزمية عدوانية - دخول/خروج سريع",
                ))
        
        return footprints
    
    def _build_hft_profile(self, spoof_events: List[SpoofEvent],
                             footprints: List[AlgoFootprint],
                             closes: np.ndarray, volumes: np.ndarray) -> HFTProfile:
        """
        بناء بروفايل نشاط HFT.
        """
        # درجة الخداع
        recent_spoofs = spoof_events[-10:]
        spoof_score = min(1.0, len(recent_spoofs) * 0.15)
        
        # خطر التلاعب
        high_conf_spoofs = [e for e in recent_spoofs if e.confidence > 0.7]
        manipulation_risk = min(1.0, len(high_conf_spoofs) * 0.25)
        
        # هيمنة الخوارزميات
        active_algos = [f.footprint_type for f in footprints if f.active]
        algo_dominance = min(1.0, len(active_algos) * 0.25)
        
        # خطر Flash Crash
        flash_risk = 0.0
        if len(closes) >= 5:
            recent_volatility = np.std(closes[-5:]) / np.mean(closes[-5:]) if np.mean(closes[-5:]) > 0 else 0
            vol_spike = np.max(volumes[-5:]) / max(np.mean(volumes[-20:]), 0.0001)
            flash_risk = min(1.0, recent_volatility * 50 + (vol_spike - 1) * 0.3)
        
        # هشاشة السوق
        fragility = min(1.0, spoof_score * 0.5 + manipulation_risk * 0.3 + flash_risk * 0.2)
        
        return HFTProfile(
            spoofing_score=spoof_score,
            manipulation_risk=manipulation_risk,
            algo_dominance=algo_dominance,
            flash_crash_risk=flash_risk,
            market_fragility=fragility,
            active_algorithms=active_algos,
        )
    
    def _detect_flash_crash_pattern(self, highs: np.ndarray, lows: np.ndarray,
                                      closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        كشف نمط Flash Crash.
        """
        if len(closes) < 15:
            return {"risk": 0, "pattern": "none"}
        
        # هبوط حاد + ارتداد سريع = Flash Crash
        for i in range(10, len(closes) - 3):
            drop = (closes[i] - closes[i-3]) / closes[i-3] if closes[i-3] > 0 else 0
            
            if drop < -0.05:  # 5% هبوط في 3 شموع
                recovery = (closes[i+3] - closes[i]) / closes[i] if closes[i] > 0 else 0
                
                if recovery > 0.03:  # ارتداد 3%
                    return {
                        "risk": 0.8,
                        "pattern": "flash_crash",
                        "index": i,
                        "drop_pct": drop * 100,
                        "recovery_pct": recovery * 100,
                        "description": "نمط Flash Crash - هبوط حاد وارتداد سريع",
                    }
        
        return {"risk": 0.2, "pattern": "none"}
    
    def _make_decision(self, spoof_events: List[SpoofEvent],
                       footprints: List[AlgoFootprint],
                       hft: HFTProfile, flash_crash: Dict,
                       current_price: float) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من أحداث الخداع ----
        recent_spoofs = spoof_events[-5:]
        
        for event in recent_spoofs:
            if event.event_type == 'spoof':
                if event.direction == 'bullish':
                    buy_signals.append((f"خداع سفلي: {event.description}", 
                                       event.confidence * 0.6))
                else:
                    sell_signals.append((f"خداع علوي: {event.description}", 
                                        event.confidence * 0.6))
            
            elif event.event_type == 'ignition':
                if event.direction == 'bullish':
                    buy_signals.append(("إشعال زخم صاعد", 0.55))
                else:
                    sell_signals.append(("إشعال زخم هابط", 0.55))
            
            elif event.event_type in ['stuff', 'layer']:
                sell_signals.append(("تلاعب HFT نشط - حذر", 0.4))
                buy_signals.append(("تلاعب HFT نشط - حذر", 0.4))
        
        # ---- من بصمات الخوارزميات ----
        algo_types = [f.footprint_type for f in footprints if f.active]
        
        if 'aggressive' in algo_types:
            buy_signals.append(("خوارزمية عدوانية - حركة قوية", 0.45))
        if 'dark_pool' in algo_types:
            buy_signals.append(("Dark Pool نشط - تجميع سري", 0.5))
        if 'iceberg' in algo_types:
            buy_signals.append(("Iceberg - أوامر كبيرة مخفية", 0.4))
        
        # ---- من هشاشة السوق ----
        if hft.market_fragility > 0.7:
            sell_signals.append((f"سوق هش ({hft.market_fragility:.1%}) - خطر", 0.55))
            buy_signals.append((f"سوق هش ({hft.market_fragility:.1%}) - خطر", 0.3))
        
        if hft.flash_crash_risk > 0.5:
            sell_signals.append((f"خطر Flash Crash ({hft.flash_crash_risk:.1%})", 0.6))
        
        # ---- من Flash Crash ----
        if flash_crash.get('pattern') == 'flash_crash':
            buy_signals.append(("نمط Flash Crash - ارتداد متوقع", 0.65))
        
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
        
        if hft.spoofing_score > 0.3:
            reason += f" | Spoof:{hft.spoofing_score:.1%}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_hft_spoofing_strategy():
    """إنشاء استراتيجية HFT & Spoofing الجاهزة"""
    return HFTSpoofingStrategy()