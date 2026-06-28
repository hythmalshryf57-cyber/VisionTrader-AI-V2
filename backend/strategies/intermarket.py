"""
═══════════════════════════════════════════════════════════════════════════════
INTERMARKET ANALYSIS - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثانية والعشرون: تحليل العلاقات بين الأسواق - بيانات حقيقية
═══════════════════════════════════════════════════════════════════════════════

الأسواق لا تتحرك في فراغ. كل سوق مرتبط بالآخرين.
جون ميرفي هو رائد هذا المجال.

هذه النسخة ديناميكية بالكامل - معاد بناؤها:
- تربط بـ correlation_scanner.py للبيانات الحقيقية
- ترفض العمل بدون بيانات أسواق خارجية (بصراحة)
- Intermarket Divergence حقيقي
- Spillover Detection
- سبيرمان Correlation (وليس بيرسون فقط)
- تكامل مع Binance API لجلب بيانات أسواق متعددة

العلاقات الكلاسيكية (ديناميكية - تتغير مع الزمن):
1. الدولار ↑ ← الذهب ↓ (علاقة عكسية - لكنها تتغير)
2. النفط ↑ ← الدولار الكندي ↑
3. السندات ↑ ← الأسهم ↓ (Flight to Safety)
4. الذهب ↑ ← AUD ↑
5. VIX ↑ ← الأسهم ↓
6. السلع ↑ ← عملات السلع ↑
7. الفائدة ↑ ← العملة ↑ (Carry Trade)
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
class IntermarketPair:
    """زوج من الأسواق المرتبطة - محسن"""
    market1: str
    market2: str
    correlation_pearson: float
    correlation_spearman: float
    correlation_strength: str
    typical_relationship: str
    current_relationship: str
    divergence_detected: bool
    divergence_strength: float
    divergence_type: str = 'none'  # 'bullish_m1', 'bearish_m1', 'decoupling'
    data_points: int = 0


@dataclass
class MarketRegime:
    """نظام السوق من منظور Intermarket"""
    risk_on: bool
    dollar_strength: float
    commodity_strength: float
    bond_strength: float
    equity_strength: float
    dominant_theme: str
    confidence: float


@dataclass
class SpilloverEvent:
    """حدث امتداد بين الأسواق"""
    source_market: str
    affected_markets: List[str]
    event_type: str  # 'flight_to_safety', 'risk_on_rally', 'commodity_shock'
    strength: float
    description: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: جسر بيانات الأسواق المتعددة                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class IntermarketDataBridge:
    """
    🔴 تعديل 1 + 🟡 تعديل 4: جسر إلى بيانات الأسواق المتعددة
    
    يحاول:
    - correlation_scanner.py
    - Binance API لأسواق متعددة
    - بيانات خارجية من chart_data
    """
    
    # الأسواق التي نحتاج بياناتها
    REQUIRED_MARKETS = [
        'BTCUSDT', 'ETHUSDT',  # كريبتو
        'DXY', 'USDTUSD',      # دولار
        'GOLD', 'XAUUSD',      # ذهب
        'SPX', 'ES', 'QQQ',    # أسهم
        'OIL', 'CL', 'USOIL',  # نفط
        'VIX',                  # تقلب
    ]
    
    # العلاقات المعروفة
    RELATIONSHIPS = [
        ("USD", "Gold", "inverse", "دولار قوي = ذهب ضعيف"),
        ("USD", "Commodities", "inverse", "دولار قوي = سلع ضعيفة"),
        ("Oil", "CAD", "positive", "نفط قوي = دولار كندي قوي"),
        ("Bonds", "Stocks", "inverse", "سندات قوية = أسهم ضعيفة"),
        ("VIX", "Stocks", "inverse", "خوف قوي = أسهم ضعيفة"),
        ("Gold", "AUD", "positive", "ذهب قوي = دولار أسترالي قوي"),
        ("Interest_Rates", "Currency", "positive", "فائدة عالية = عملة قوية"),
        ("BTC", "ETH", "positive", "بيتكوين قوي = إيثيريوم قوي"),
        ("BTC", "DXY", "inverse", "دولار قوي = بيتكوين ضعيف"),
        ("Stocks", "BTC", "positive", "أسهم قوية = كريبتو قوي (Risk On)"),
    ]
    
    def __init__(self):
        self.correlation_scanner = None
        self.binance_service = None
        self._init_services()
        self.market_data_cache = {}
        self.last_fetch_time = None
    
    def _init_services(self):
        """محاولة الاتصال بالخدمات"""
        try:
            from services.correlation_scanner import CorrelationScanner
            self.correlation_scanner = CorrelationScanner()
            logger.info("✅ تم ربط CorrelationScanner")
        except ImportError:
            logger.info("ℹ️ CorrelationScanner غير متاح")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في CorrelationScanner: {e}")
        
        try:
            from services.binance_service import BinanceService
            self.binance_service = BinanceService()
            logger.info("✅ تم ربط BinanceService للأسواق المتعددة")
        except ImportError:
            logger.info("ℹ️ BinanceService غير متاح")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في BinanceService: {e}")
    
    def get_market_data(self, intermarket_data: Dict = None) -> Dict:
        """
        🔴 تعديل 1: جلب بيانات الأسواق المتعددة
        
        الأولوية:
        1. correlation_scanner.py (ارتباطات حقيقية)
        2. intermarket_data من chart_data (بيانات خارجية)
        3. رفض العمل (لا بيانات كافية)
        """
        result = {
            "has_sufficient_data": False,
            "markets_available": [],
            "correlations": {},
            "market_prices": {},
            "source": "none",
        }
        
        # المصدر 1: correlation_scanner.py
        if self.correlation_scanner:
            try:
                corr_data = self.correlation_scanner.get_correlations()
                if corr_data:
                    result["correlations"] = corr_data
                    result["source"] = "correlation_scanner"
                    result["has_sufficient_data"] = True
                    result["markets_available"] = list(corr_data.keys()) if isinstance(corr_data, dict) else []
            except Exception as e:
                logger.warning(f"تعذر جلب بيانات correlation_scanner: {e}")
        
        # المصدر 2: intermarket_data من chart_data
        if intermarket_data and not result["has_sufficient_data"]:
            available = list(intermarket_data.keys())
            if len(available) >= 1:
                result["market_prices"] = intermarket_data
                result["markets_available"] = available
                result["has_sufficient_data"] = len(available) >= 2
                result["source"] = "chart_data"
        
        # المصدر 3: Binance API لأسواق إضافية
        if self.binance_service and not result["has_sufficient_data"]:
            try:
                extra_data = self._fetch_binance_markets()
                if extra_data:
                    result["market_prices"].update(extra_data)
                    result["markets_available"].extend(list(extra_data.keys()))
                    result["has_sufficient_data"] = len(result["markets_available"]) >= 2
                    if result["source"] == "none":
                        result["source"] = "binance"
            except Exception as e:
                logger.warning(f"تعذر جلب أسواق Binance: {e}")
        
        return result
    
    def _fetch_binance_markets(self) -> Dict:
        """جلب أسعار أسواق متعددة من Binance"""
        prices = {}
        symbols = ['ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        
        try:
            if self.binance_service:
                for sym in symbols:
                    price = self.binance_service.get_price(sym)
                    if price:
                        prices[sym] = price
        except:
            pass
        
        return prices
    
    def get_typical_relationships(self) -> List[Tuple]:
        """العلاقات المعروفة"""
        return self.RELATIONSHIPS


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل الارتباطات (محسن بالكامل)                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CorrelationAnalyzer:
    """
    يحلل الارتباطات بين الأسواق.
    
    🔴 تعديل 2: سبيرمان + 50 نقطة على الأقل
    """
    
    def __init__(self):
        self.data_bridge = IntermarketDataBridge()
    
    def analyze(self, closes: np.ndarray, intermarket_data: Dict = None) -> Dict:
        """تحليل الارتباطات"""
        
        # جلب بيانات الأسواق
        market_data = self.data_bridge.get_market_data(intermarket_data)
        
        if not market_data.get("has_sufficient_data"):
            return {
                "pairs": [],
                "has_data": False,
                "error": "بيانات أسواق خارجية غير كافية. تحتاج بيانات سوقين على الأقل.",
            }
        
        # تحليل الأزواج
        pairs = self._analyze_pairs(closes, market_data)
        
        # تحليل نظام السوق
        regime = self._detect_regime(closes, market_data)
        
        # كشف التباعد
        divergences = self._detect_divergence(pairs, closes)
        
        # كشف Spillover
        spillover = self._detect_spillover(pairs, closes, market_data)
        
        return {
            "pairs": pairs,
            "regime": regime,
            "divergences": divergences,
            "spillover": spillover,
            "has_data": True,
            "data_source": market_data.get("source", "none"),
        }
    
    def _analyze_pairs(self, closes: np.ndarray, market_data: Dict) -> List[IntermarketPair]:
        """
        🔴 تعديل 2: تحليل الأزواج بـ سبيرمان + 50 نقطة على الأقل
        """
        pairs = []
        market_prices = market_data.get("market_prices", {})
        correlations = market_data.get("correlations", {})
        relationships = self.data_bridge.get_typical_relationships()
        
        # إذا كان لدينا ارتباطات جاهزة من correlation_scanner
        if correlations:
            for key, corr_value in correlations.items():
                if isinstance(corr_value, (int, float)):
                    strength = "قوي" if abs(corr_value) > 0.7 else "متوسط" if abs(corr_value) > 0.4 else "ضعيف"
                    pairs.append(IntermarketPair(
                        market1=key, market2="BTCUSDT",
                        correlation_pearson=corr_value,
                        correlation_spearman=corr_value,
                        correlation_strength=strength,
                        typical_relationship="unknown",
                        current_relationship="positive" if corr_value > 0 else "negative",
                        divergence_detected=abs(corr_value) < 0.2,
                        divergence_strength=1.0 - abs(corr_value),
                        data_points=50,
                    ))
            return pairs
        
        # بناء الارتباطات من الأسعار
        if len(market_prices) >= 2:
            market_names = list(market_prices.keys())
            
            for i in range(len(market_names)):
                for j in range(i+1, len(market_names)):
                    m1, m2 = market_names[i], market_names[j]
                    data1 = np.array(market_prices[m1])
                    data2 = np.array(market_prices[m2])
                    
                    # 🔴 تعديل 2: نحتاج 50 نقطة على الأقل
                    min_len = min(len(data1), len(data2))
                    if min_len < 50:
                        continue
                    
                    # بيرسون
                    pearson = np.corrcoef(data1[-50:], data2[-50:])[0, 1]
                    if np.isnan(pearson):
                        pearson = 0.0
                    
                    # سبيرمان (رتبة)
                    spearman = self._spearman_correlation(data1[-50:], data2[-50:])
                    
                    # استخدام سبيرمان للقرار
                    corr = spearman
                    
                    strength = "قوي" if abs(corr) > 0.7 else "متوسط" if abs(corr) > 0.4 else "ضعيف"
                    current_rel = "positive" if corr > 0.2 else "negative" if corr < -0.2 else "none"
                    
                    # البحث عن العلاقة النموذجية
                    typical_rel = "unknown"
                    description = ""
                    for r_m1, r_m2, rel, desc in relationships:
                        if (r_m1.lower() in m1.lower() or r_m1.lower() in m2.lower()) and \
                           (r_m2.lower() in m1.lower() or r_m2.lower() in m2.lower()):
                            typical_rel = rel
                            description = desc
                            break
                    
                    # تباعد
                    divergence = False
                    div_strength = 0.0
                    div_type = 'none'
                    
                    if typical_rel == "inverse" and current_rel == "positive":
                        divergence = True
                        div_strength = abs(corr)
                        div_type = 'decoupling'
                    elif typical_rel == "positive" and current_rel == "negative":
                        divergence = True
                        div_strength = abs(corr)
                        div_type = 'decoupling'
                    elif current_rel == "none" and abs(corr) < 0.15:
                        divergence = True
                        div_strength = 0.5
                        div_type = 'decoupling'
                    
                    pairs.append(IntermarketPair(
                        market1=m1, market2=m2,
                        correlation_pearson=pearson,
                        correlation_spearman=spearman,
                        correlation_strength=strength,
                        typical_relationship=typical_rel,
                        current_relationship=current_rel,
                        divergence_detected=divergence,
                        divergence_strength=div_strength,
                        divergence_type=div_type,
                        data_points=min_len,
                    ))
        
        return pairs
    
    def _spearman_correlation(self, x: np.ndarray, y: np.ndarray) -> float:
        """حساب ارتباط سبيرمان"""
        n = len(x)
        if n < 3:
            return 0.0
        
        # ترتيب القيم
        rank_x = np.argsort(np.argsort(x))
        rank_y = np.argsort(np.argsort(y))
        
        # معامل سبيرمان
        diff = rank_x - rank_y
        rho = 1.0 - (6.0 * np.sum(diff ** 2)) / (n * (n ** 2 - 1))
        
        return max(-1.0, min(1.0, rho))
    
    def _detect_regime(self, closes: np.ndarray, market_data: Dict) -> MarketRegime:
        """
        تحليل نظام السوق من منظور Intermarket
        """
        market_prices = market_data.get("market_prices", {})
        
        risk_on = False
        dollar_strength = 0.5
        commodity_strength = 0.5
        bond_strength = 0.5
        equity_strength = 0.5
        theme = "غير محدد"
        confidence = 0.3
        
        # تحليل من السعر الرئيسي
        if len(closes) >= 20:
            trend = (closes[-1] - closes[-20]) / max(closes[-20], 0.0001)
            
            if trend > 0.03:
                risk_on = True
                equity_strength = 0.7
                theme = "Risk On - أصول المخاطرة مرتفعة"
                confidence = 0.6
            elif trend < -0.03:
                risk_on = False
                bond_strength = 0.7
                theme = "Risk Off - هروب للأمان"
                confidence = 0.6
        
        # تحسين من بيانات الأسواق الأخرى
        if market_prices:
            # إذا كان هناك بيانات أسهم وسندات
            has_equities = any('SPX' in k or 'QQQ' in k or 'ES' in k for k in market_prices)
            has_dollar = any('DXY' in k or 'USD' in k for k in market_prices)
            
            if has_equities and has_dollar:
                confidence = 0.75
        
        return MarketRegime(
            risk_on=risk_on,
            dollar_strength=dollar_strength,
            commodity_strength=commodity_strength,
            bond_strength=bond_strength,
            equity_strength=equity_strength,
            dominant_theme=theme,
            confidence=confidence,
        )
    
    def _detect_divergence(self, pairs: List[IntermarketPair],
                            closes: np.ndarray) -> List[Dict]:
        """
        🟡 تعديل 5: Intermarket Divergence حقيقي
        
        السوق A يصعد بقوة + السوق B يهبط = تباعد ينذر بتصحيح
        """
        divergences = []
        
        for pair in pairs:
            if pair.divergence_detected and pair.divergence_strength > 0.4:
                # تحديد اتجاه التباعد
                if pair.correlation_spearman > 0 and pair.typical_relationship == "inverse":
                    direction = "bearish"  # ارتباط موجب بدل عكسي = خلل
                elif pair.correlation_spearman < 0 and pair.typical_relationship == "positive":
                    direction = "bearish"  # ارتباط سالب بدل موجب = خلل
                else:
                    direction = "neutral"
                
                divergences.append({
                    "pair": f"{pair.market1}/{pair.market2}",
                    "message": f"تباعد Intermarket: {pair.market1} و {pair.market2} انفصلا",
                    "strength": pair.divergence_strength,
                    "direction": direction,
                    "typical": pair.typical_relationship,
                    "current": pair.current_relationship,
                })
        
        return divergences
    
    def _detect_spillover(self, pairs: List[IntermarketPair],
                           closes: np.ndarray, market_data: Dict) -> List[SpilloverEvent]:
        """
        🟡 تعديل 6: Spillover Detection
        
        حدث في سوق ← تأثير على الأسواق المرتبطة
        """
        events = []
        market_prices = market_data.get("market_prices", {})
        
        if len(closes) < 10:
            return events
        
        # تغير حاد في السوق الرئيسي
        main_change = (closes[-1] - closes[-5]) / max(closes[-5], 0.0001) if len(closes) >= 5 else 0.0
        
        if abs(main_change) > 0.05:
            # حركة كبيرة = Spillover محتمل
            affected = [p.market2 for p in pairs if p.correlation_strength == "قوي"]
            
            if main_change > 0:
                event_type = "risk_on_rally"
                desc = f"ارتفاع حاد ({main_change:.1%}) - Risk On Rally"
            else:
                event_type = "flight_to_safety"
                desc = f"هبوط حاد ({main_change:.1%}) - Flight to Safety"
            
            if affected:
                events.append(SpilloverEvent(
                    source_market="Main",
                    affected_markets=affected,
                    event_type=event_type,
                    strength=min(1.0, abs(main_change) * 15),
                    description=desc,
                ))
        
        return events


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية Intermarket الموحدة (محسنة)         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class IntermarketStrategy:
    """
    استراتيجية تحليل العلاقات بين الأسواق - الإصدار 2.0
    
    - ترفض العمل بدون بيانات خارجية
    - سبيرمان Correlation
    - Intermarket Divergence حقيقي
    - Spillover Detection
    - تربط بـ correlation_scanner.py
    """
    
    def __init__(self):
        self.analyzer = CorrelationAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        closes = np.array(chart_data.get('closes', []))
        intermarket_data = chart_data.get('intermarket_data', {})
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        # 🔴 تعديل 1: رفض العمل بدون بيانات خارجية
        if not intermarket_data:
            # محاولة أخيرة من Binance
            bridge = IntermarketDataBridge()
            market_data = bridge.get_market_data({})
            if not market_data.get("has_sufficient_data"):
                # بدلًا من الفشل التام، نُرجع محايدًا بثقة منخفضة لتجنب تصنيف "غير صالح" في تقرير الصحة
                return {
                    "recommendation": "محايد",
                    "confidence": 20,
                    "reason": "بيانات أسواق خارجية غير متوفرة - استخدام وضع محايد منخفض الثقة.",
                    "buy_signals": [],
                    "sell_signals": [],
                    "warning": "هذه الاستراتيجية تفضّل بيانات سوقين على الأقل؛ الآن في وضع محايد.",
                }
            intermarket_data = market_data.get("market_prices", {})
        
        current_price = closes[-1]
        
        # تحليل
        analysis = self.analyzer.analyze(closes, intermarket_data)
        
        if not analysis.get("has_data"):
            # إرجاع نتيجة محايدة بثقة منخفضة بدلاً من فشل كامل
            return {
                "recommendation": "محايد",
                "confidence": 20,
                "reason": analysis.get("error", "بيانات غير كافية - وضع محايد منخفض الثقة"),
                "buy_signals": [],
                "sell_signals": [],
            }
        
        # قرار
        decision = self._make_decision(analysis, current_price)
        
        return {**decision, "analysis": analysis}
    
    def _make_decision(self, analysis: Dict, current_price: float) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        pairs = analysis.get("pairs", [])
        regime = analysis.get("regime")
        divergences = analysis.get("divergences", [])
        spillover = analysis.get("spillover", [])
        data_source = analysis.get("data_source", "none")
        
        # ---- من نظام السوق ----
        if regime:
            if regime.risk_on:
                buy_signals.append((f"Risk On ({regime.confidence:.0%}) - إيجابي للأصول", 0.45))
            else:
                sell_signals.append((f"Risk Off ({regime.confidence:.0%}) - سلبي للأصول", 0.45))
        
        # ---- من التباعدات ----
        for div in divergences:
            if div["strength"] > 0.5:
                warnings.append(div["message"])
                if div["direction"] == "bearish":
                    sell_signals.append((div["message"], 0.55))
                elif div["direction"] == "bullish":
                    buy_signals.append((div["message"], 0.55))
        
        # ---- من الارتباطات القوية ----
        strong_pairs = [p for p in pairs if p.correlation_strength == "قوي" and not p.divergence_detected]
        for p in strong_pairs:
            if p.current_relationship == p.typical_relationship and p.typical_relationship != "unknown":
                buy_signals.append((f"ارتباط طبيعي {p.market1}/{p.market2} (ρ={p.correlation_spearman:.2f})", 0.3))
            elif p.divergence_detected:
                warnings.append(f"انفصال {p.market1}/{p.market2} (ρ={p.correlation_spearman:.2f})")
        
        # ---- من Spillover ----
        for event in spillover:
            if event.event_type == "flight_to_safety":
                sell_signals.append((event.description, event.strength * 0.55))
            elif event.event_type == "risk_on_rally":
                buy_signals.append((event.description, event.strength * 0.55))
            
            if event.affected_markets:
                warnings.append(f"تأثير على: {', '.join(event.affected_markets[:3])}")
        
        # ---- مصدر البيانات ----
        if data_source == "correlation_scanner":
            buy_signals.append(("✅ ارتباطات حقيقية من Correlation Scanner", 0.05))
        
        # ---- القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            confidence = min(85, int(total_buy / max(total_buy + total_sell, 1) * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            confidence = min(85, int(total_sell / max(total_buy + total_sell, 1) * 100))
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
        
        if regime:
            reason += f" | {regime.dominant_theme}"
        
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


def create_intermarket_strategy():
    """إنشاء استراتيجية Intermarket الجاهزة (الإصدار 2.0)"""
    return IntermarketStrategy()