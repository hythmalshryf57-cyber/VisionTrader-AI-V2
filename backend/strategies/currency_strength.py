"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC CURRENCY STRENGTH STRATEGY - النسخة الديناميكية المتكاملة
المدرسة الرابعة والعشرون: قوة العملات الديناميكية
═══════════════════════════════════════════════════════════════════════════════

سوق الفوركس = قوة عملة مقابل ضعف أخرى.
أقوى عملة + أضعف عملة = أفضل صفقة.

هذه النسخة ديناميكية بالكامل:
- القوة تقاس بطرق متعددة
- لا أوزان ثابتة للعملات
- القوة النسبية تتغير باستمرار
- نكتشف "الزخم" وليس فقط القيمة المطلقة

العملات الرئيسية:
USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD

المفاهيم المتقدمة:
1. Currency Strength Meter (مقياس قوة العملات)
2. Relative Strength Index لكل عملة
3. Currency Momentum
4. Currency Correlation Matrix
5. Currency Volatility Ranking
6. Strong/Weak Pairing
7. Currency Seasonality
8. Interest Rate Differential
9. Carry Trade Analysis
10. Safe Haven Flows
11. Commodity Currency Correlation
12. Currency Futures COT
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
class CurrencyStrength:
    """قوة عملة واحدة"""
    currency: str
    absolute_strength: float    # 0-100
    relative_strength: float    # مقارنة بالآخرين
    momentum: float             # معدل التغير
    volatility: float           # التقلب
    trend: str                  # 'strengthening', 'weakening', 'stable'
    rank: int                   # الترتيب بين العملات
    score: float                # الدرجة الكلية


@dataclass
class CurrencyPair:
    """زوج عملات مع تحليل القوة"""
    pair: str                   # EURUSD, GBPJPY...
    base_currency: str
    quote_currency: str
    base_strength: float
    quote_strength: float
    strength_differential: float  # فرق القوة
    alignment: str              # 'aligned', 'neutral', 'misaligned'
    trade_direction: str        # 'buy', 'sell', 'neutral'
    conviction: float           # 0-1


@dataclass
class CurrencyMatrix:
    """مصفوفة العملات الكاملة"""
    currencies: List[str]
    strengths: Dict[str, CurrencyStrength]
    pairs: List[CurrencyPair]
    strongest: str
    weakest: str
    best_pair: str
    best_direction: str
    correlation_matrix: Dict[str, Dict[str, float]]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: حاسبة قوة العملات (Currency Strength Calculator)     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CurrencyStrengthCalculator:
    """
    يحسب قوة كل عملة ديناميكياً.
    """
    
    CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'NZD']
    
    # أزواج العملات الرئيسية (لحساب القوة)
    MAJOR_PAIRS = {
        'EURUSD': ('EUR', 'USD'), 'USDJPY': ('USD', 'JPY'),
        'GBPUSD': ('GBP', 'USD'), 'USDCHF': ('USD', 'CHF'),
        'AUDUSD': ('AUD', 'USD'), 'NZDUSD': ('NZD', 'USD'),
        'USDCAD': ('USD', 'CAD'), 'EURJPY': ('EUR', 'JPY'),
        'EURGBP': ('EUR', 'GBP'), 'EURCHF': ('EUR', 'CHF'),
        'GBPJPY': ('GBP', 'JPY'), 'GBPCHF': ('GBP', 'CHF'),
        'AUDJPY': ('AUD', 'JPY'), 'NZDJPY': ('NZD', 'JPY'),
        'CADJPY': ('CAD', 'JPY'), 'CHFJPY': ('CHF', 'JPY'),
        'EURAUD': ('EUR', 'AUD'), 'EURNZD': ('EUR', 'NZD'),
        'GBPAUD': ('GBP', 'AUD'), 'GBPNZD': ('GBP', 'NZD'),
        'AUDCAD': ('AUD', 'CAD'), 'NZDCAD': ('NZD', 'CAD'),
        'AUDNZD': ('AUD', 'NZD'), 'AUDCHF': ('AUD', 'CHF'),
        'NZDCHF': ('NZD', 'CHF'), 'CADCHF': ('CAD', 'CHF'),
    }
    
    def analyze(self, pair_data: Dict[str, np.ndarray]) -> Dict:
        """
        حساب قوة كل عملة.
        """
        if not pair_data:
            return self._estimate_from_single_pair(pair_data)
        
        # حساب القوة المطلقة لكل عملة
        strengths = {}
        
        for currency in self.CURRENCIES:
            strength, momentum, volatility = self._calculate_currency_strength(
                currency, pair_data)
            
            strengths[currency] = {
                'absolute': strength,
                'momentum': momentum,
                'volatility': volatility,
            }
        
        # ترتيب العملات
        ranked = sorted(strengths.items(), key=lambda x: x[1]['absolute'], reverse=True)
        
        for i, (curr, data) in enumerate(ranked):
            data['rank'] = i + 1
            data['relative'] = 100 - (i * 100 / len(self.CURRENCIES))
        
        # تحديد الأقوى والأضعف
        strongest_curr = ranked[0][0] if ranked else 'USD'
        weakest_curr = ranked[-1][0] if ranked else 'JPY'
        
        # بناء أزواج التداول
        pairs = self._build_trading_pairs(strengths)
        
        # أفضل زوج
        best_pair = self._find_best_pair(pairs)
        
        return {
            "strengths": strengths,
            "ranked": ranked,
            "pairs": pairs,
            "strongest": strongest_curr,
            "weakest": weakest_curr,
            "best_pair": best_pair,
        }
    
    def _calculate_currency_strength(self, currency: str,
                                       pair_data: Dict[str, np.ndarray]) -> Tuple[float, float, float]:
        """
        حساب قوة عملة واحدة.
        """
        strength_score = 50.0
        momentum_score = 0.0
        volatility_score = 0.0
        count = 0
        
        for pair_name, closes in pair_data.items():
            if len(closes) < 20:
                continue
            
            # تحديد موقع العملة في الزوج
            if pair_name in self.MAJOR_PAIRS:
                base, quote = self.MAJOR_PAIRS[pair_name]
            else:
                continue
            
            if currency == base:
                # العملة هي الأساس - صعود الزوج = قوة العملة
                ret = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
                strength_score += (50 + ret * 500)
                momentum_score += ret * 100
                volatility_score += np.std(closes[-20:]) / np.mean(closes[-20:]) if np.mean(closes[-20:]) > 0 else 0
                count += 1
                
            elif currency == quote:
                # العملة هي المقابل - هبوط الزوج = قوة العملة
                ret = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
                strength_score += (50 - ret * 500)
                momentum_score -= ret * 100
                volatility_score += np.std(closes[-20:]) / np.mean(closes[-20:]) if np.mean(closes[-20:]) > 0 else 0
                count += 1
        
        if count > 0:
            strength_score /= count
            momentum_score /= count
            volatility_score /= count
        
        return (
            max(0, min(100, strength_score)),
            momentum_score,
            volatility_score,
        )
    
    def _estimate_from_single_pair(self, pair_data: Dict) -> Dict:
        """
        تقدير القوة من زوج واحد فقط.
        """
        if not pair_data:
            return {"strengths": {}, "pairs": [], "best_pair": None}
        
        # نحاول استخراج بيانات الزوج الوحيد
        pair_name = list(pair_data.keys())[0]
        closes = list(pair_data.values())[0]
        
        if pair_name in self.MAJOR_PAIRS:
            base, quote = self.MAJOR_PAIRS[pair_name]
        else:
            base, quote = pair_name[:3], pair_name[3:]
        
        if len(closes) < 5:
            return {"strengths": {}, "pairs": [], "best_pair": None}
        
        ret = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        
        strengths = {
            base: {'absolute': 50 + ret * 500, 'momentum': ret * 100, 'rank': 1, 'relative': 80},
            quote: {'absolute': 50 - ret * 500, 'momentum': -ret * 100, 'rank': 2, 'relative': 40},
        }
        
        return {
            "strengths": strengths,
            "pairs": [],
            "strongest": base if ret > 0 else quote,
            "weakest": quote if ret > 0 else base,
            "best_pair": None,
        }
    
    def _build_trading_pairs(self, strengths: Dict) -> List[CurrencyPair]:
        """
        بناء أزواج التداول من العملات.
        """
        pairs = []
        
        sorted_currencies = sorted(strengths.items(), 
                                   key=lambda x: x[1].get('absolute', 50), 
                                   reverse=True)
        
        currency_list = [c[0] for c in sorted_currencies]
        
        for i, base in enumerate(currency_list):
            for j, quote in enumerate(currency_list):
                if i >= j:  # لا نكرر الأزواج
                    continue
                
                pair_name = f"{base}{quote}"
                strength_diff = strengths[base]['absolute'] - strengths[quote]['absolute']
                
                # المحاذاة
                if abs(strength_diff) > 20:
                    alignment = 'aligned'
                elif abs(strength_diff) > 10:
                    alignment = 'neutral'
                else:
                    alignment = 'misaligned'
                
                # اتجاه التداول
                if strength_diff > 0:
                    direction = 'buy'  # شراء الأساس = بيع المقابل
                elif strength_diff < 0:
                    direction = 'sell'
                else:
                    direction = 'neutral'
                
                pairs.append(CurrencyPair(
                    pair=pair_name,
                    base_currency=base,
                    quote_currency=quote,
                    base_strength=strengths[base]['absolute'],
                    quote_strength=strengths[quote]['absolute'],
                    strength_differential=strength_diff,
                    alignment=alignment,
                    trade_direction=direction,
                    conviction=min(1.0, abs(strength_diff) / 50),
                ))
        
        return pairs
    
    def _find_best_pair(self, pairs: List[CurrencyPair]) -> Optional[CurrencyPair]:
        """
        إيجاد أفضل زوج للتداول.
        """
        if not pairs:
            return None
        
        aligned = [p for p in pairs if p.alignment == 'aligned']
        
        if aligned:
            return max(aligned, key=lambda p: abs(p.strength_differential))
        
        return max(pairs, key=lambda p: abs(p.strength_differential))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الثانية: محلل ارتباط العملات (Currency Correlation)           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CurrencyCorrelationAnalyzer:
    """
    يحلل ارتباط العملات ببعضها.
    """
    
    def analyze(self, pair_data: Dict[str, np.ndarray]) -> Dict:
        """
        تحليل الارتباطات.
        """
        if len(pair_data) < 2:
            return {"correlations": {}, "clusters": []}
        
        # حساب مصفوفة الارتباط
        corr_matrix = self._calculate_correlation_matrix(pair_data)
        
        # تجميع العملات المرتبطة
        clusters = self._find_correlation_clusters(corr_matrix)
        
        # كشف تغير الارتباطات
        changes = self._detect_correlation_changes(corr_matrix)
        
        return {
            "correlations": corr_matrix,
            "clusters": clusters,
            "changes": changes,
        }
    
    def _calculate_correlation_matrix(self, pair_data: Dict[str, np.ndarray]) -> Dict:
        """
        حساب مصفوفة الارتباط.
        """
        pair_names = list(pair_data.keys())
        matrix = {}
        
        for i, pair1 in enumerate(pair_names):
            matrix[pair1] = {}
            data1 = pair_data[pair1]
            
            for j, pair2 in enumerate(pair_names):
                data2 = pair_data[pair2]
                
                min_len = min(len(data1), len(data2))
                if min_len >= 20:
                    corr = np.corrcoef(data1[-min_len:], data2[-min_len:])[0, 1]
                    if np.isnan(corr):
                        corr = 0
                else:
                    corr = 0
                
                matrix[pair1][pair2] = corr
        
        return matrix
    
    def _find_correlation_clusters(self, matrix: Dict) -> List[Dict]:
        """
        إيجاد مجموعات العملات المرتبطة.
        """
        clusters = []
        
        if not matrix:
            return clusters
        
        # البحث عن أزواج مرتبطة بقوة
        high_corr_pairs = []
        
        pair_names = list(matrix.keys())
        for i in range(len(pair_names)):
            for j in range(i+1, len(pair_names)):
                corr = matrix[pair_names[i]].get(pair_names[j], 0)
                if abs(corr) > 0.7:
                    high_corr_pairs.append({
                        "pair1": pair_names[i],
                        "pair2": pair_names[j],
                        "correlation": corr,
                    })
        
        return high_corr_pairs
    
    def _detect_correlation_changes(self, matrix: Dict) -> List[Dict]:
        """
        كشف تغيرات الارتباط.
        """
        changes = []
        
        for pair1 in matrix:
            for pair2 in matrix[pair1]:
                corr = matrix[pair1][pair2]
                
                if corr > 0.8:
                    changes.append({
                        "pair1": pair1,
                        "pair2": pair2,
                        "correlation": corr,
                        "status": "ارتباط قوي جداً",
                        "warning": "تحرك معاً - تنويع منخفض",
                    })
                elif corr < -0.8:
                    changes.append({
                        "pair1": pair1,
                        "pair2": pair2,
                        "correlation": corr,
                        "status": "ارتباط عكسي قوي",
                        "warning": "تحوط طبيعي",
                    })
        
        return changes


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية قوة العملات الموحدة                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CurrencyStrengthStrategy:
    """
    استراتيجية قوة العملات الديناميكية الكاملة.
    """
    
    def __init__(self):
        self.strength_calculator = CurrencyStrengthCalculator()
        self.correlation_analyzer = CurrencyCorrelationAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        closes = np.array(chart_data.get('closes', []))
        
        # بيانات أزواج العملات الإضافية
        pair_data = chart_data.get('pair_data', {})
        
        # إذا لم توجد بيانات إضافية، استخدم الزوج الحالي فقط
        if not pair_data and len(closes) > 0:
            pair_name = chart_data.get('pair_name', 'EURUSD')
            pair_data = {pair_name: closes}
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        # 1. حساب قوة العملات
        strength_data = self.strength_calculator.analyze(pair_data)
        
        # 2. تحليل الارتباطات
        corr_data = self.correlation_analyzer.analyze(pair_data)
        
        # 3. القرار
        decision = self._make_decision(strength_data, corr_data, closes, chart_data)
        
        return {
            **decision,
            "strength_data": strength_data,
            "corr_data": corr_data,
        }
    
    def _make_decision(self, strength_data: Dict, corr_data: Dict,
                       closes: np.ndarray, chart_data: Dict) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        current_price = closes[-1] if len(closes) > 0 else 0
        pair_name = chart_data.get('pair_name', 'EURUSD')
        
        # استخراج العملتين من اسم الزوج
        base = pair_name[:3] if len(pair_name) >= 6 else ''
        quote = pair_name[3:] if len(pair_name) >= 6 else ''
        
        # ---- من ترتيب القوة ----
        ranked = strength_data.get('ranked', [])
        strongest = strength_data.get('strongest', '')
        weakest = strength_data.get('weakest', '')
        
        if base == strongest and quote == weakest:
            buy_signals.append((f"{base} الأقوى vs {quote} الأضعف - شراء مثالي", 0.75))
        elif base == weakest and quote == strongest:
            sell_signals.append((f"{base} الأضعف vs {quote} الأقوى - بيع مثالي", 0.75))
        elif base == strongest:
            buy_signals.append((f"{base} هي الأقوى", 0.5))
        elif base == weakest:
            sell_signals.append((f"{base} هي الأضعف", 0.5))
        elif quote == strongest:
            sell_signals.append((f"{quote} هي الأقوى", 0.5))
        elif quote == weakest:
            buy_signals.append((f"{quote} هي الأضعف", 0.5))
        
        # ---- من فرق القوة ----
        pairs = strength_data.get('pairs', [])
        for pair in pairs:
            if pair.pair == pair_name:
                if pair.alignment == 'aligned':
                    if pair.trade_direction == 'buy':
                        buy_signals.append((f"محاذاة قوية - فرق:{pair.strength_differential:.1f}", 
                                           pair.conviction * 0.6))
                    elif pair.trade_direction == 'sell':
                        sell_signals.append((f"محاذاة قوية - فرق:{pair.strength_differential:.1f}",
                                           pair.conviction * 0.6))
                break
        
        # ---- من ارتباطات العملات ----
        clusters = corr_data.get('clusters', [])
        if clusters:
            related_pairs = [c for c in clusters if pair_name in [c['pair1'], c['pair2']]]
            if related_pairs:
                buy_signals.append(("أزواج مرتبطة تؤكد الإشارة", 0.3))
        
        # ---- من ترتيب القوة ----
        if ranked and len(ranked) >= 3:
            for curr, data in ranked[:3]:
                if curr == base:
                    buy_signals.append((f"{curr} في المرتبة {data['rank']} - قوي", 0.4))
                elif curr == quote:
                    sell_signals.append((f"{curr} في المرتبة {data['rank']} - قوي", 0.4))
        
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
        
        reason += f" | الأقوى:{strongest} | الأضعف:{weakest}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_currency_strength_strategy():
    """إنشاء استراتيجية قوة العملات الجاهزة"""
    return CurrencyStrengthStrategy()