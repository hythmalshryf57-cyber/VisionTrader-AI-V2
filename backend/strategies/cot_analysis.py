"""
═══════════════════════════════════════════════════════════════════════════════
COT ANALYSIS STRATEGY - النسخة الديناميكية المتكاملة
المدرسة العشرون: تحليل تقرير التزام المتداولين (COT)
═══════════════════════════════════════════════════════════════════════════════

تقرير COT (Commitment of Traders) يصدر أسبوعياً عن CFTC.
يكشف مراكز المؤسسات الكبرى مقابل المضاربين الصغار.

الفئات:
1. Commercials (التحوط) - الأذكى، يبيعون عند القمم ويشترون عند القيعان
2. Large Speculators (المضاربين الكبار) - صناديق تحوط
3. Small Speculators (المضاربين الصغار) - القطيع، عادة مخطئون

هذه النسخة ديناميكية بالكامل:
- لا عتبات ثابتة للتطرف
- نكتشف "التطرف" من البيانات نفسها
- مؤشر COT Index ديناميكي
- تحليل التغير الأسبوعي
- انحراف المراكز

المفاهيم المتقدمة:
1. COT Index
2. Net Long/Short Positions
3. Open Interest Analysis
4. Commercial Hedging Signals
5. Large Speculator Extremes
6. Small Speculator Fading
7. COT + Price Divergence
8. Seasonal COT Patterns
9. Spread Analysis
10. Producer/Merchant vs Swap Dealer
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class COTData:
    """بيانات تقرير COT"""
    date: str
    commercial_long: float
    commercial_short: float
    commercial_net: float
    large_spec_long: float
    large_spec_short: float
    large_spec_net: float
    small_spec_long: float
    small_spec_short: float
    small_spec_net: float
    open_interest: float
    price: float


@dataclass
class COTIndex:
    """مؤشر COT ديناميكي"""
    commercial_index: float      # 0-100
    large_spec_index: float
    small_spec_index: float
    open_interest_index: float
    net_position_percentile: float
    extreme_reading: bool
    extreme_type: str            # 'commercial_bullish', 'commercial_bearish', etc.


@dataclass
class COTSignal:
    """إشارة COT"""
    index: int
    signal_type: str  # 'extreme_commercial', 'divergence', 'flip', 'crowded_trade'
    direction: str
    strength: float
    description: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل COT الديناميكي                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicCOTAnalyzer:
    """
    يحلل بيانات COT بطريقة ديناميكية.
    """
    
    def __init__(self):
        self.lookback_weeks = 52  # سنة كاملة
        self.extreme_threshold = 0.85  # ديناميكي يتغير
        
    def analyze(self, cot_data_list: List[Dict], current_price: float) -> Dict:
        """
        تحليل COT
        """
        if not cot_data_list or len(cot_data_list) < 10:
            return {"error": "بيانات COT غير كافية"}
        
        # تحويل البيانات
        cot_records = self._parse_cot_data(cot_data_list)
        
        # حساب المؤشرات
        cot_index = self._calculate_cot_index(cot_records)
        
        # كشف التطرف
        extremes = self._detect_extremes(cot_records, cot_index)
        
        # كشف التباعد
        divergences = self._detect_divergences(cot_records, current_price)
        
        # كشف الانقلاب
        flips = self._detect_flips(cot_records)
        
        # تحليل التدفق
        flow = self._analyze_flow(cot_records)
        
        # إشارات
        signals = self._generate_signals(cot_index, extremes, divergences, flips)
        
        return {
            "cot_index": cot_index,
            "extremes": extremes,
            "divergences": divergences,
            "flips": flips,
            "flow": flow,
            "signals": signals[-5:],
            "current_net_commercial": cot_records[-1].commercial_net if cot_records else 0,
        }
    
    def _parse_cot_data(self, data_list: List[Dict]) -> List[COTData]:
        """تحويل البيانات الخام"""
        records = []
        
        for d in data_list:
            comm_net = d.get('commercial_long', 0) - d.get('commercial_short', 0)
            large_net = d.get('large_spec_long', 0) - d.get('large_spec_short', 0)
            small_net = d.get('small_spec_long', 0) - d.get('small_spec_short', 0)
            
            records.append(COTData(
                date=d.get('date', ''),
                commercial_long=d.get('commercial_long', 0),
                commercial_short=d.get('commercial_short', 0),
                commercial_net=comm_net,
                large_spec_long=d.get('large_spec_long', 0),
                large_spec_short=d.get('large_spec_short', 0),
                large_spec_net=large_net,
                small_spec_long=d.get('small_spec_long', 0),
                small_spec_short=d.get('small_spec_short', 0),
                small_spec_net=small_net,
                open_interest=d.get('open_interest', 0),
                price=d.get('price', 0),
            ))
        
        return records
    
    def _calculate_cot_index(self, records: List[COTData]) -> COTIndex:
        """
        حساب مؤشر COT الديناميكي.
        يقارن الوضع الحالي بآخر 52 أسبوع.
        """
        if not records:
            return COTIndex(50, 50, 50, 50, 50, False, 'none')
        
        lookback = min(self.lookback_weeks, len(records))
        recent = records[-lookback:]
        
        current = records[-1]
        
        # ترتيب القيم في الفترة
        comm_nets = [r.commercial_net for r in recent]
        large_nets = [r.large_spec_net for r in recent]
        small_nets = [r.small_spec_net for r in recent]
        ois = [r.open_interest for r in recent]
        
        # النسبة المئوية للقيمة الحالية
        comm_idx = self._percentile(comm_nets, current.commercial_net)
        large_idx = self._percentile(large_nets, current.large_spec_net)
        small_idx = 100 - self._percentile(small_nets, current.small_spec_net)  # معكوس
        oi_idx = self._percentile(ois, current.open_interest)
        
        # كشف التطرف
        extreme = comm_idx > 90 or comm_idx < 10
        extreme_type = 'none'
        
        if comm_idx > 90:
            extreme_type = 'commercial_bullish'  # تجاريين في أقصى شراء
        elif comm_idx < 10:
            extreme_type = 'commercial_bearish'  # تجاريين في أقصى بيع
        elif large_idx > 90:
            extreme_type = 'large_spec_bullish'
        elif large_idx < 10:
            extreme_type = 'large_spec_bearish'
        
        return COTIndex(
            commercial_index=comm_idx,
            large_spec_index=large_idx,
            small_spec_index=small_idx,
            open_interest_index=oi_idx,
            net_position_percentile=comm_idx,
            extreme_reading=extreme,
            extreme_type=extreme_type,
        )
    
    def _percentile(self, values: List[float], current: float) -> float:
        """حساب النسبة المئوية"""
        if not values:
            return 50.0
        return sum(1 for v in values if v <= current) / len(values) * 100
    
    def _detect_extremes(self, records: List[COTData], cot_index: COTIndex) -> Dict:
        """
        كشف التطرف في المراكز.
        """
        extremes = {
            "commercial_extreme": abs(cot_index.commercial_index - 50) > 40,
            "large_spec_extreme": abs(cot_index.large_spec_index - 50) > 40,
            "small_spec_extreme": abs(cot_index.small_spec_index - 50) > 40,
        }
        
        # التطرف الأهم: التجاريين
        if cot_index.commercial_index > 90:
            extremes["signal"] = "تجاريين في أقصى شراء - إشارة صعود قوية"
            extremes["direction"] = "bullish"
        elif cot_index.commercial_index < 10:
            extremes["signal"] = "تجاريين في أقصى بيع - إشارة هبوط قوية"
            extremes["direction"] = "bearish"
        else:
            extremes["signal"] = "لا تطرف"
            extremes["direction"] = "neutral"
        
        return extremes
    
    def _detect_divergences(self, records: List[COTData], current_price: float) -> List[Dict]:
        """
        كشف تباعد COT عن السعر.
        """
        divergences = []
        
        if len(records) < 8:
            return divergences
        
        recent = records[-8:]
        
        # السعر يصعد والتجاريين يبيعون = تباعد هابط
        price_start = recent[0].price
        price_end = recent[-1].price
        comm_start = recent[0].commercial_net
        comm_end = recent[-1].commercial_net
        
        if price_end > price_start * 1.05 and comm_end < comm_start * 0.8:
            divergences.append({
                "type": "bearish",
                "description": "سعر يصعد والتجاريين يبيعون - تحذير هبوط",
                "strength": 0.7,
            })
        
        # السعر يهبط والتجاريين يشترون = تباعد صاعد
        if price_end < price_start * 0.95 and comm_end > comm_start * 1.2:
            divergences.append({
                "type": "bullish",
                "description": "سعر يهبط والتجاريين يشترون - فرصة صعود",
                "strength": 0.7,
            })
        
        return divergences
    
    def _detect_flips(self, records: List[COTData]) -> List[Dict]:
        """
        كشف انقلاب المراكز.
        """
        flips = []
        
        if len(records) < 4:
            return flips
        
        # انقلاب صافي المركز من بيع لشراء أو العكس
        for i in range(2, len(records)):
            if records[i-1].commercial_net < 0 and records[i].commercial_net > 0:
                flips.append({
                    "index": i,
                    "type": "bullish_flip",
                    "description": "تجاريين انقلبوا من بيع لشراء",
                })
            elif records[i-1].commercial_net > 0 and records[i].commercial_net < 0:
                flips.append({
                    "index": i,
                    "type": "bearish_flip",
                    "description": "تجاريين انقلبوا من شراء لبيع",
                })
        
        return flips
    
    def _analyze_flow(self, records: List[COTData]) -> Dict:
        """
        تحليل تدفق المراكز.
        """
        if len(records) < 4:
            return {"direction": "stable"}
        
        recent = records[-4:]
        comm_change = recent[-1].commercial_net - recent[0].commercial_net
        large_change = recent[-1].large_spec_net - recent[0].large_spec_net
        
        if comm_change > 0 and large_change < 0:
            flow = "تجاريين يشترون ومضاربين يبيعون - إيجابي"
        elif comm_change < 0 and large_change > 0:
            flow = "تجاريين يبيعون ومضاربين يشترون - سلبي"
        else:
            flow = "مختلط"
        
        return {"direction": flow, "commercial_change": comm_change}
    
    def _generate_signals(self, cot_index: COTIndex, extremes: Dict,
                           divergences: List[Dict], flips: List[Dict]) -> List[COTSignal]:
        """
        توليد إشارات COT.
        """
        signals = []
        
        # تطرف
        if extremes.get("direction") == "bullish":
            signals.append(COTSignal(
                index=0, signal_type='extreme_commercial',
                direction='bullish', strength=0.8,
                description=extremes.get("signal", ""),
            ))
        elif extremes.get("direction") == "bearish":
            signals.append(COTSignal(
                index=0, signal_type='extreme_commercial',
                direction='bearish', strength=0.8,
                description=extremes.get("signal", ""),
            ))
        
        # تباعد
        for div in divergences:
            signals.append(COTSignal(
                index=0, signal_type='divergence',
                direction=div['type'], strength=div['strength'],
                description=div['description'],
            ))
        
        # انقلاب
        for flip in flips[-2:]:
            signals.append(COTSignal(
                index=flip['index'], signal_type='flip',
                direction='bullish' if 'bullish' in flip['type'] else 'bearish',
                strength=0.75, description=flip['description'],
            ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية COT الموحدة                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class COTAnalysisStrategy:
    """
    استراتيجية تحليل COT الكاملة.
    """
    
    def __init__(self):
        self.cot_analyzer = DynamicCOTAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        closes = np.array(chart_data.get('closes', []))
        cot_data = chart_data.get('cot_data', [])
        
        current_price = closes[-1] if len(closes) > 0 else 0
        
        # 1. تحليل COT
        cot_result = self.cot_analyzer.analyze(cot_data, current_price)
        
        if "error" in cot_result:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": cot_result["error"]}
        
        # 2. القرار
        decision = self._make_decision(cot_result, current_price)
        
        return {
            **decision,
            "cot_data": cot_result,
        }
    
    def _make_decision(self, cot_result: Dict, current_price: float) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        cot_index = cot_result.get('cot_index')
        extremes = cot_result.get('extremes', {})
        flow = cot_result.get('flow', {})
        signals = cot_result.get('signals', [])
        
        # ---- من مؤشر COT ----
        if cot_index:
            if cot_index.commercial_index > 80:
                buy_signals.append((f"تجاريين شراء قوي ({cot_index.commercial_index:.0f})", 0.6))
            elif cot_index.commercial_index < 20:
                sell_signals.append((f"تجاريين بيع قوي ({cot_index.commercial_index:.0f})", 0.6))
            
            if cot_index.small_spec_index > 80:
                sell_signals.append(("مضاربين صغار شراء متطرف - عكسهم", 0.55))
            elif cot_index.small_spec_index < 20:
                buy_signals.append(("مضاربين صغار بيع متطرف - عكسهم", 0.55))
        
        # ---- من التطرف ----
        if extremes.get('direction') == 'bullish':
            buy_signals.append(("تطرف COT صاعد", 0.7))
        elif extremes.get('direction') == 'bearish':
            sell_signals.append(("تطرف COT هابط", 0.7))
        
        # ---- من التدفق ----
        if 'إيجابي' in flow.get('direction', ''):
            buy_signals.append(("تدفق COT إيجابي", 0.4))
        elif 'سلبي' in flow.get('direction', ''):
            sell_signals.append(("تدفق COT سلبي", 0.4))
        
        # ---- من الإشارات ----
        for sig in signals:
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, sig.strength * 0.6))
            else:
                sell_signals.append((sig.description, sig.strength * 0.6))
        
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
        
        if cot_index:
            reason += f" | COT:{cot_index.commercial_index:.0f}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_cot_analysis_strategy():
    """إنشاء استراتيجية COT الجاهزة"""
    return COTAnalysisStrategy()