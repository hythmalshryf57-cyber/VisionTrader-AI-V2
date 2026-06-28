"""
═══════════════════════════════════════════════════════════════════════════════
COMPOSITE OPERATOR THEORY - النسخة الديناميكية المتكاملة
المدرسة الحادية والثلاثون: نظرية المشغل المركب
═══════════════════════════════════════════════════════════════════════════════

ريتشارد وايكوف تحدث عن "Composite Operator" - الكيان الوهمي
الذي يمثل كل المؤسسات الكبرى مجتمعة. هذا الكيان:
1. يعرف أين توجد السيولة
2. يتحكم في السعر
3. يجمع ويوزع بصمت
4. يخدع القطيع

هذه الاستراتيجية تحاكي تفكير Composite Operator:
- أين سأجمع؟ (Accumulation)
- أين سأوزع؟ (Distribution)
- كيف سأخدع القطيع؟ (Manipulation)
- متى سأطلق السعر؟ (Markup/Markdown)

ديناميكي بالكامل - يفكر مثل المؤسسة الكبرى.

المفاهيم:
1. Composite Man (Wyckoff)
2. Operator's Intent
3. Liquidity Engineering
4. Stop Hunting Strategy
5. Accumulation Schematics
6. Distribution Schematics
7. Re-accumulation
8. Re-distribution
9. Spring & Upthrust
10. Creek & Ice
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class OperatorPosition:
    """مركز المشغل"""
    phase: str              # 'accumulation', 'distribution', 'markup', 'markdown', 'testing', 'neutral'
    estimated_inventory: float  # سالب = بيع، موجب = شراء
    inventory_pct: float    # نسبة المخزون للهدف
    average_price: float
    unrealized_pnl: float
    target_price: float
    stop_hunt_direction: str


@dataclass
class OperatorTrap:
    """مصيدة المشغل"""
    index: int
    trap_type: str          # 'spring', 'upthrust', 'fake_breakout', 'stop_run', 'liquidity_grab'
    direction: str
    price_level: float
    trapped_traders: str    # 'longs' or 'shorts'
    strength: float
    description: str


@dataclass
class OperatorSignal:
    """إشارة من المشغل"""
    index: int
    signal_type: str
    direction: str
    strength: float
    description: str


class CompositeOperatorStrategy:
    """
    استراتيجية تفكير المشغل المركب.
    """
    
    def __init__(self):
        self.inventory = 0
        self.avg_entry = 0
        self.total_trades = 0
        
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # 1. تقدير مركز المشغل
        position = self._estimate_operator_position(highs, lows, closes, volumes)
        
        # 2. اكتشاف المصائد
        traps = self._detect_operator_traps(highs, lows, closes, volumes, opens)
        
        # 3. اكتشاف مناطق التجميع والتوزيع
        zones = self._detect_accumulation_distribution(highs, lows, closes, volumes)
        
        # 4. تحليل نية المشغل
        intent = self._analyze_operator_intent(position, traps, zones, closes)
        
        # 5. القرار
        decision = self._make_decision(position, traps, zones, intent, current_price)
        
        return {
            **decision,
            "position": position,
            "traps": traps[-5:],
            "zones": zones,
            "intent": intent,
        }
    
    def _estimate_operator_position(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, volumes: np.ndarray) -> OperatorPosition:
        """
        تقدير مركز المشغل.
        """
        if len(closes) < 30:
            return OperatorPosition('neutral', 0, 0, 0, 0, 0, 'none')
        
        # تقدير التجميع/التوزيع من الحجم والسعر
        recent_closes = closes[-30:]
        recent_volumes = volumes[-30:]
        
        # سعر متوسط موزون بالحجم
        if np.sum(recent_volumes) > 0:
            vwap = np.average(recent_closes, weights=recent_volumes)
        else:
            vwap = np.mean(recent_closes)
        
        current = closes[-1]
        
        # تقدير المخزون
        up_vol = 0
        down_vol = 0
        
        for i in range(len(recent_closes)):
            if recent_closes[i] > recent_closes[i-1] if i > 0 else True:
                up_vol += recent_volumes[i]
            else:
                down_vol += recent_volumes[i]
        
        total_vol = up_vol + down_vol
        if total_vol > 0:
            buy_ratio = up_vol / total_vol
        else:
            buy_ratio = 0.5
        
        estimated_inventory = (buy_ratio - 0.5) * 2  # -1 إلى 1
        
        # تحديد الطور
        if estimated_inventory > 0.3 and current > vwap:
            phase = 'markup'
        elif estimated_inventory > 0.3 and current <= vwap:
            phase = 'accumulation'
        elif estimated_inventory < -0.3 and current < vwap:
            phase = 'markdown'
        elif estimated_inventory < -0.3 and current >= vwap:
            phase = 'distribution'
        elif abs(estimated_inventory) < 0.15:
            phase = 'testing'
        else:
            phase = 'neutral'
        
        # الهدف السعري
        if phase in ['accumulation', 'markup']:
            target = current * 1.05
        elif phase in ['distribution', 'markdown']:
            target = current * 0.95
        else:
            target = current
        
        return OperatorPosition(
            phase=phase,
            estimated_inventory=estimated_inventory,
            inventory_pct=abs(estimated_inventory),
            average_price=vwap,
            unrealized_pnl=(current - vwap) / vwap * estimated_inventory,
            target_price=target,
            stop_hunt_direction='up' if estimated_inventory > 0 else 'down' if estimated_inventory < 0 else 'none',
        )
    
    def _detect_operator_traps(self, highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray, volumes: np.ndarray,
                                opens: np.ndarray) -> List[OperatorTrap]:
        """
        اكتشاف مصائد المشغل.
        """
        traps = []
        
        if len(closes) < 10:
            return traps
        
        avg_vol = np.mean(volumes[-30:]) if len(volumes) >= 30 else np.mean(volumes)
        avg_range = np.mean(highs[-20:] - lows[-20:])
        
        for i in range(5, len(closes) - 3):
            bar_range = highs[i] - lows[i]
            
            if bar_range == 0:
                continue
            
            # Spring (كسر وهمي للأسفل)
            lower_wick = min(opens[i], closes[i]) - lows[i] if i < len(opens) else closes[i] - lows[i]
            if lower_wick > bar_range * 0.6 and closes[i] > (highs[i] + lows[i]) / 2:
                if volumes[i] > avg_vol * 1.3:
                    traps.append(OperatorTrap(
                        index=i,
                        trap_type='spring',
                        direction='bullish',
                        price_level=lows[i],
                        trapped_traders='shorts',
                        strength=0.75,
                        description="Spring - كسر وهمي لاصطياد البائعين",
                    ))
            
            # Upthrust (كسر وهمي للأعلى)
            upper_wick = highs[i] - max(opens[i], closes[i]) if i < len(opens) else highs[i] - closes[i]
            if upper_wick > bar_range * 0.6 and closes[i] < (highs[i] + lows[i]) / 2:
                if volumes[i] > avg_vol * 1.3:
                    traps.append(OperatorTrap(
                        index=i,
                        trap_type='upthrust',
                        direction='bearish',
                        price_level=highs[i],
                        trapped_traders='longs',
                        strength=0.75,
                        description="Upthrust - كسر وهمي لاصطياد المشترين",
                    ))
            
            # Fake Breakout
            if i >= 10:
                prev_high = max(highs[i-10:i])
                prev_low = min(lows[i-10:i])
                
                if highs[i] > prev_high and closes[i] < prev_high:
                    traps.append(OperatorTrap(
                        index=i,
                        trap_type='fake_breakout',
                        direction='bearish',
                        price_level=prev_high,
                        trapped_traders='longs',
                        strength=0.65,
                        description="اختراق وهمي للأعلى",
                    ))
                
                if lows[i] < prev_low and closes[i] > prev_low:
                    traps.append(OperatorTrap(
                        index=i,
                        trap_type='fake_breakout',
                        direction='bullish',
                        price_level=prev_low,
                        trapped_traders='shorts',
                        strength=0.65,
                        description="اختراق وهمي للأسفل",
                    ))
        
        return traps
    
    def _detect_accumulation_distribution(self, highs: np.ndarray, lows: np.ndarray,
                                           closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        اكتشاف مناطق التجميع والتوزيع.
        """
        if len(closes) < 30:
            return {"accumulation": [], "distribution": []}
        
        acc_zones = []
        dist_zones = []
        
        # تحليل كل 15 شمعة
        for start in range(0, len(closes) - 15, 5):
            end = min(start + 15, len(closes))
            
            segment_closes = closes[start:end]
            segment_volumes = volumes[start:end]
            segment_high = max(highs[start:end])
            segment_low = min(lows[start:end])
            
            # السعر في النطاق
            range_size = segment_high - segment_low
            if range_size == 0:
                continue
            
            avg_price = np.mean(segment_closes)
            
            # حجم منخفض = تجميع محتمل
            avg_vol = np.mean(segment_volumes)
            total_avg_vol = np.mean(volumes)
            
            if avg_vol < total_avg_vol * 0.7 and segment_closes[-1] > avg_price:
                acc_zones.append({
                    "start": start, "end": end,
                    "high": segment_high, "low": segment_low,
                    "confidence": 0.6,
                })
            
            # حجم مرتفع + عدم تحرك = توزيع
            if avg_vol > total_avg_vol * 1.3 and abs(segment_closes[-1] - segment_closes[0]) < range_size * 0.3:
                dist_zones.append({
                    "start": start, "end": end,
                    "high": segment_high, "low": segment_low,
                    "confidence": 0.6,
                })
        
        return {"accumulation": acc_zones[-3:], "distribution": dist_zones[-3:]}
    
    def _analyze_operator_intent(self, position: OperatorPosition,
                                   traps: List[OperatorTrap], zones: Dict,
                                   closes: np.ndarray) -> Dict:
        """
        تحليل نية المشغل.
        """
        intent = "غير واضح"
        confidence = 0.3
        
        if position.phase == 'accumulation':
            intent = "يجمع - سيصعد السعر لاحقاً"
            confidence = 0.65
        elif position.phase == 'distribution':
            intent = "يوزع - سيهبط السعر لاحقاً"
            confidence = 0.65
        elif position.phase == 'markup':
            intent = "يرفع السعر - استمر في الشراء"
            confidence = 0.6
        elif position.phase == 'markdown':
            intent = "يخفض السعر - استمر في البيع"
            confidence = 0.6
        elif position.phase == 'testing':
            intent = "يختبر السوق - انتظار حركة قوية"
            confidence = 0.4
        
        # تعزيز من المصائد
        recent_traps = traps[-3:]
        if len(recent_traps) >= 2:
            confidence = min(0.9, confidence + 0.15)
        
        return {"intent": intent, "confidence": confidence}
    
    def _make_decision(self, position: OperatorPosition,
                       traps: List[OperatorTrap], zones: Dict,
                       intent: Dict, current_price: float) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من طور المشغل ----
        if position.phase == 'accumulation':
            buy_signals.append(("المشغل يجمع - استعد للصعود", 0.6))
        elif position.phase == 'distribution':
            sell_signals.append(("المشغل يوزع - استعد للهبوط", 0.6))
        elif position.phase == 'markup':
            buy_signals.append(("المشغل يرفع السعر - كن معه", 0.65))
        elif position.phase == 'markdown':
            sell_signals.append(("المشغل يخفض السعر - كن معه", 0.65))
        elif position.phase == 'testing':
            buy_signals.append(("المشغل يختبر - انتظر التأكيد", 0.2))
            sell_signals.append(("المشغل يختبر - انتظر التأكيد", 0.2))
        
        # ---- من المخزون ----
        if position.estimated_inventory > 0.4:
            buy_signals.append(("مخزون شراء كبير - صعود متوقع", 0.5))
        elif position.estimated_inventory < -0.4:
            sell_signals.append(("مخزون بيع كبير - هبوط متوقع", 0.5))
        
        # ---- من المصائد ----
        for trap in traps[-5:]:
            if trap.direction == 'bullish':
                buy_signals.append((trap.description, trap.strength * 0.7))
            else:
                sell_signals.append((trap.description, trap.strength * 0.7))
        
        # ---- من المناطق ----
        for acc in zones.get('accumulation', []):
            if acc['low'] <= current_price <= acc['high']:
                buy_signals.append(("السعر في منطقة تجميع", 0.55))
        
        for dist in zones.get('distribution', []):
            if dist['low'] <= current_price <= dist['high']:
                sell_signals.append(("السعر في منطقة توزيع", 0.55))
        
        # ---- من النية ----
        if intent.get('confidence', 0) > 0.5:
            if 'يصعد' in intent.get('intent', ''):
                buy_signals.append((f"نية المشغل: {intent['intent']}", intent['confidence'] * 0.7))
            elif 'يهبط' in intent.get('intent', ''):
                sell_signals.append((f"نية المشغل: {intent['intent']}", intent['confidence'] * 0.7))
        
        # ---- اتجاه اصطياد الوقف ----
        if position.stop_hunt_direction == 'up':
            buy_signals.append(("المشغل سيصطاد وقف بيع - صعود لاصطيادهم", 0.55))
        elif position.stop_hunt_direction == 'down':
            sell_signals.append(("المشغل سيصطاد وقف شراء - هبوط لاصطيادهم", 0.55))
        
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
        reason += f" | الطور: {position.phase}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_composite_operator_strategy():
    """إنشاء استراتيجية المشغل المركب الجاهزة"""
    return CompositeOperatorStrategy()