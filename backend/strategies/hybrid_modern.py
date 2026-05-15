"""
═══════════════════════════════════════════════════════════════════════════════
HYBRID MODERN STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السادسة والثلاثون: الاستراتيجية الهجينة الحديثة - Meta Strategy
═══════════════════════════════════════════════════════════════════════════════

هذه الاستراتيجية تجمع أفضل ما في كل المدارس السابقة.
لا تلتزم بمدرسة واحدة. تختار الأفضل من كل مدرسة حسب حالة السوق.

مبدأ "التكامل": الكل أكبر من مجموع الأجزاء.

تدمج:
- Price Action + SMC/ICT (الهيكل والسيولة)
- Wyckoff (دورات التجميع والتوزيع)
- Volume Analysis (تأكيد الحجم)
- Market Profile (مناطق القيمة)
- Order Flow (تدفق الأوامر)
- Sentiment (المشاعر)
- Adaptive Indicators (مؤشرات متكيفة)
- Regime Detection (نظام السوق)

الإضافات الجديدة (الإصدار 2.0):
- Performance History لكل مدرسة
- Conflict Resolution (كسر التعادل بالوزن)
- إصلاح MACD Signal Line
- إصلاح choppiness calculation
- استدعاء استراتيجيات حقيقية (اختياري)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class SchoolScore:
    """تقييم مدرسة - محسن"""
    name: str
    score: float
    weight: float
    recommendation: str
    confidence: float
    reason: str
    regime_match: float
    # 🟡 تعديل 4: Performance History
    historical_accuracy: float = 0.5
    recent_performance: float = 0.0
    total_weight: float = 0.0


@dataclass
class HybridSignal:
    """إشارة هجينة"""
    signal_type: str
    direction: str
    strength: float
    schools_agreeing: List[str]
    description: str
    # 🟡 تعديل 5: Conflict Resolution
    tie_breaker: str = 'none'


@dataclass
class PerformanceRecord:
    """سجل أداء مدرسة"""
    school_name: str
    correct_calls: int = 0
    total_calls: int = 0
    accuracy: float = 0.5
    avg_confidence_when_correct: float = 0.0
    last_updated: int = 0


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: الاستراتيجية الهجينة (محسنة)                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HybridModernStrategy:
    """
    الاستراتيجية الهجينة الحديثة - Meta Strategy - الإصدار 2.0
    
    - Performance History لكل مدرسة
    - Conflict Resolution
    - استدعاء استراتيجيات حقيقية
    - أوزان متعلمة
    """
    
    SCHOOLS = [
        'price_action', 'smc_ict', 'wyckoff', 'elliott_wave',
        'harmonic', 'vsa', 'market_profile', 'order_flow',
        'auction_market', 'moving_averages', 'bollinger', 'rsi',
        'stochastic', 'macd', 'fibonacci', 'sentiment'
    ]
    
    def __init__(self):
        self.school_weights = {s: 1.0/len(self.SCHOOLS) for s in self.SCHOOLS}
        # 🟡 تعديل 4: سجل الأداء
        self.performance_history = {s: PerformanceRecord(school_name=s) for s in self.SCHOOLS}
        self.total_analyses = 0
        # استراتيجيات حقيقية (تحميل كسول)
        self.real_strategies = {}
    
    def _get_real_strategy(self, name: str):
        """
        🟡 تعديل 6: استدعاء استراتيجية حقيقية (اختياري)
        """
        if name in self.real_strategies:
            return self.real_strategies[name]
        
        strategy_map = {
            'wyckoff': ('strategies.wyckoff_strategy', 'WyckoffStrategy'),
            'vsa': ('strategies.vsa_strategy', 'VSAStrategy'),
            'market_profile': ('strategies.market_profile_strategy', 'MarketProfileStrategy'),
            'order_flow': ('strategies.order_flow_strategy', 'OrderFlowStrategy'),
            'macd': ('strategies.macd_strategy', 'DynamicMACDStrategy'),
            'stochastic': ('strategies.stochastic_strategy', 'DynamicStochasticStrategy'),
            'moving_averages': ('strategies.moving_averages_strategy', 'DynamicMovingAverageStrategy'),
            'sentiment': ('strategies.social_sentiment_strategy', 'SocialSentimentStrategy'),
        }
        
        if name in strategy_map:
            try:
                module_path, class_name = strategy_map[name]
                module = __import__(module_path, fromlist=[class_name])
                strategy_class = getattr(module, class_name)
                self.real_strategies[name] = strategy_class()
                logger.info(f"✅ تم تحميل استراتيجية {name} الحقيقية")
                return self.real_strategies[name]
            except Exception as e:
                logger.debug(f"استخدام تحليل مبسط لـ {name}: {e}")
        
        return None
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل - يجمع كل المدارس"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # 1. كشف نظام السوق
        regime = self._detect_regime(highs, lows, closes, volumes)
        
        # 2. تحليل كل مدرسة
        school_scores = self._analyze_all_schools(highs, lows, closes, volumes, opens, regime, chart_data)
        
        # 3. دمج الإشارات
        hybrid_signals = self._fuse_signals(school_scores, current_price)
        
        # 4. تكييف الأوزان
        self._adapt_weights(school_scores, regime)
        
        # 5. القرار النهائي
        decision = self._make_final_decision(school_scores, hybrid_signals, regime)
        
        self.total_analyses += 1
        
        return {
            **decision,
            "regime": regime,
            "school_scores": {k: {
                "recommendation": v.recommendation, "confidence": v.confidence,
                "weight": v.total_weight, "accuracy": v.historical_accuracy,
                "reason": v.reason,
            } for k, v in school_scores.items()},
            "hybrid_signals": hybrid_signals,
            "weights": self.school_weights,
        }
    
    def _detect_regime(self, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        🔴 تعديل 3: كشف نظام السوق مع choppiness صحيح
        """
        if len(closes) < 20:
            return {"type": "unknown", "best_schools": []}
        
        trend = (closes[-1] - closes[-20]) / max(closes[-20], 0.0001)
        
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        volatility = np.std(ranges) / max(avg_range, 0.0001)
        
        # 🔴 تعديل 3: choppiness صحيح
        window = closes[-20:]
        direction_changes = sum(1 for i in range(2, len(window))
                               if (window[i] > window[i-1] and window[i-1] < window[i-2]) or
                                  (window[i] < window[i-1] and window[i-1] > window[i-2]))
        choppiness = direction_changes / max(len(window) - 2, 1)
        
        if abs(trend) > 0.05 and volatility < 0.5:
            regime_type = "trending"
            best_schools = ['price_action', 'smc_ict', 'moving_averages', 'elliott_wave', 'macd']
        elif abs(trend) < 0.02 and choppiness > 0.5:
            regime_type = "choppy"
            best_schools = ['wyckoff', 'market_profile', 'auction_market', 'rsi', 'stochastic']
        elif abs(trend) < 0.02 and volatility < 0.3:
            regime_type = "ranging"
            best_schools = ['harmonic', 'bollinger', 'fibonacci', 'wyckoff']
        elif volatility > 0.7:
            regime_type = "volatile"
            best_schools = ['vsa', 'order_flow', 'sentiment', 'bollinger']
        else:
            regime_type = "mixed"
            best_schools = ['price_action', 'vsa', 'market_profile', 'macd']
        
        return {"type": regime_type, "best_schools": best_schools}
    
    def _analyze_all_schools(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray, volumes: np.ndarray,
                               opens: np.ndarray, regime: Dict,
                               chart_data: Dict) -> Dict[str, SchoolScore]:
        """تحليل كل مدرسة"""
        scores = {}
        current = closes[-1]
        
        # تعريف المدارس مع دوال التحليل
        school_analyzers = [
            ('price_action', self._price_action_analysis),
            ('smc_ict', self._smc_analysis),
            ('vsa', self._vsa_analysis),
            ('market_profile', self._market_profile_analysis),
            ('order_flow', self._order_flow_analysis),
            ('moving_averages', self._ma_analysis),
            ('bollinger', self._bollinger_analysis),
            ('rsi', self._rsi_analysis),
            ('macd', self._macd_analysis),
            ('sentiment', self._sentiment_analysis),
            ('wyckoff', self._wyckoff_analysis),
            ('fibonacci', self._fibonacci_analysis),
            ('stochastic', self._stochastic_analysis),
            ('elliott_wave', self._elliott_analysis),
            ('harmonic', self._harmonic_analysis),
            ('auction_market', self._auction_analysis),
        ]
        
        for school_name, analyzer_func in school_analyzers:
            # 🟡 تعديل 6: محاولة استخدام استراتيجية حقيقية
            real_strategy = self._get_real_strategy(school_name)
            
            if real_strategy:
                try:
                    result = real_strategy.analyze(chart_data)
                    rec = result.get('recommendation', 'محايد')
                    conf = result.get('confidence', 30)
                    
                    if 'شراء' in rec:
                        direction = 'شراء'
                        score = 50.0 + conf * 0.4
                    elif 'بيع' in rec:
                        direction = 'بيع'
                        score = 50.0 + conf * 0.4
                    else:
                        direction = 'محايد'
                        score = 50.0
                    
                    reason = result.get('reason', '')[:80]
                except Exception as e:
                    logger.debug(f"استراتيجية {school_name} فشلت: {e}")
                    score, direction, conf, reason = analyzer_func(highs, lows, closes, volumes)
            else:
                score, direction, conf, reason = analyzer_func(highs, lows, closes, volumes)
            
            # 🟡 تعديل 4: الأداء التاريخي
            perf = self.performance_history.get(school_name, PerformanceRecord(school_name=school_name))
            
            scores[school_name] = SchoolScore(
                name=school_name,
                score=score,
                weight=self.school_weights[school_name],
                recommendation=direction,
                confidence=conf,
                reason=reason,
                regime_match=1.5 if school_name in regime.get('best_schools', []) else 0.8,
                historical_accuracy=perf.accuracy,
                recent_performance=perf.avg_confidence_when_correct,
                total_weight=self.school_weights[school_name] * (1.5 if school_name in regime.get('best_schools', []) else 0.8) * perf.accuracy,
            )
        
        return scores
    
    def _price_action_analysis(self, highs, lows, closes, volumes=None):
        """تحليل Price Action"""
        if len(closes) < 10:
            return 50, 'محايد', 30, "PA: غير كاف"
        
        higher_high = closes[-1] > max(closes[-10:-1])
        higher_low = min(lows[-5:]) > min(lows[-10:-5])
        lower_low = closes[-1] < min(closes[-10:-1])
        lower_high = max(highs[-5:]) < max(highs[-10:-5])
        
        if higher_high and higher_low:
            return 70, 'شراء', 65, "PA: هيكل صاعد (HH+HL)"
        elif lower_low and lower_high:
            return 70, 'بيع', 65, "PA: هيكل هابط (LL+LH)"
        elif higher_high:
            return 55, 'شراء', 45, "PA: قمة أعلى"
        elif lower_low:
            return 55, 'بيع', 45, "PA: قاع أدنى"
        else:
            return 50, 'محايد', 30, "PA: غير محدد"
    
    def _smc_analysis(self, highs, lows, closes, volumes=None):
        """تحليل SMC"""
        if len(closes) < 15:
            return 50, 'محايد', 30, "SMC: غير كاف"
        
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        current = closes[-1]
        range_size = recent_high - recent_low
        
        if range_size > 0:
            position = (current - recent_low) / range_size
        else:
            position = 0.5
        
        if current > recent_high:
            return 65, 'شراء', 55, "SMC: اختراق قمة"
        elif current < recent_low:
            return 65, 'بيع', 55, "SMC: كسر قاع"
        elif position > 0.6:
            return 55, 'شراء', 40, "SMC: فوق المنتصف"
        elif position < 0.4:
            return 55, 'بيع', 40, "SMC: تحت المنتصف"
        
        return 50, 'محايد', 30, "SMC: منطقة توازن"
    
    def _vsa_analysis(self, highs, lows, closes, volumes, opens=None):
        """تحليل VSA"""
        if len(volumes) < 10:
            return 50, 'محايد', 30, "VSA: غير كاف"
        
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        recent_vol = volumes[-1]
        
        vol_ratio = recent_vol / max(avg_vol, 0.0001)
        price_up = closes[-1] > closes[-2] if len(closes) >= 2 else True
        
        if vol_ratio > 1.5 and price_up:
            return 65, 'شراء', 55, f"VSA: حجم عالي + صعود (×{vol_ratio:.1f})"
        elif vol_ratio > 1.5 and not price_up:
            return 65, 'بيع', 55, f"VSA: حجم عالي + هبوط (×{vol_ratio:.1f})"
        
        return 50, 'محايد', 30, "VSA: حجم طبيعي"
    
    def _market_profile_analysis(self, highs, lows, closes, volumes, opens=None):
        """تحليل Market Profile"""
        if len(closes) < 20:
            return 50, 'محايد', 30, "MP: غير كاف"
        
        total_vol = sum(volumes[-20:])
        vwap = np.average(closes[-20:], weights=volumes[-20:]) if total_vol > 0 else np.mean(closes[-20:])
        
        if closes[-1] > vwap * 1.02:
            return 60, 'شراء', 45, "MP: فوق VWAP"
        elif closes[-1] < vwap * 0.98:
            return 60, 'بيع', 45, "MP: تحت VWAP"
        
        return 50, 'محايد', 30, "MP: عند VWAP"
    
    def _order_flow_analysis(self, highs, lows, closes, volumes, opens=None):
        """تحليل Order Flow"""
        if len(closes) < 10:
            return 50, 'محايد', 30, "OF: غير كاف"
        
        delta = 0.0
        for i in range(-5, 0):
            if closes[i] > closes[i-1]:
                delta += volumes[i] * 0.7
            else:
                delta -= volumes[i] * 0.7
        
        total_vol = sum(volumes[-5:])
        delta_norm = delta / max(total_vol, 0.0001)
        
        if delta_norm > 0.2:
            return 65, 'شراء', 50, f"OF: دلتا موجبة ({delta_norm:.2f})"
        elif delta_norm < -0.2:
            return 65, 'بيع', 50, f"OF: دلتا سالبة ({delta_norm:.2f})"
        
        return 50, 'محايد', 30, "OF: دلتا محايدة"
    
    def _ma_analysis(self, closes, volumes=None):
        """تحليل المتوسطات"""
        if len(closes) < 20:
            return 50, 'محايد', 30, "MA: غير كاف"
        
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        
        if closes[-1] > ma5 > ma10 > ma20:
            return 70, 'شراء', 60, "MA: ترتيب صاعد مثالي"
        elif closes[-1] < ma5 < ma10 < ma20:
            return 70, 'بيع', 60, "MA: ترتيب هابط مثالي"
        elif closes[-1] > ma5:
            return 55, 'شراء', 40, "MA: فوق MA5"
        elif closes[-1] < ma5:
            return 55, 'بيع', 40, "MA: تحت MA5"
        
        return 50, 'محايد', 30, "MA: متقاطعة"
    
    def _bollinger_analysis(self, closes, volumes=None):
        """تحليل بولينجر"""
        if len(closes) < 20:
            return 50, 'محايد', 30, "BB: غير كاف"
        
        ma = np.mean(closes[-20:])
        std = np.std(closes[-20:])
        upper = ma + 2 * std
        lower = ma - 2 * std
        
        if closes[-1] < lower:
            return 70, 'شراء', 55, "BB: تحت السفلي - ارتداد متوقع"
        elif closes[-1] > upper:
            return 70, 'بيع', 55, "BB: فوق العلوي - ارتداد متوقع"
        elif closes[-1] > ma:
            return 55, 'شراء', 35, "BB: فوق المتوسط"
        else:
            return 55, 'بيع', 35, "BB: تحت المتوسط"
    
    def _rsi_analysis(self, closes, volumes=None):
        """تحليل RSI"""
        if len(closes) < 14:
            return 50, 'محايد', 30, "RSI: غير كاف"
        
        deltas = np.diff(closes[-15:])
        gains = np.sum(deltas[deltas > 0]) if any(deltas > 0) else 0.0
        losses = abs(np.sum(deltas[deltas < 0])) if any(deltas < 0) else 0.0
        
        if losses > 0:
            rs = gains / losses
            rsi = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi = 100.0 if gains > 0 else 50.0
        
        if rsi < 30:
            return 75, 'شراء', 60, f"RSI: تشبع بيع ({rsi:.0f})"
        elif rsi > 70:
            return 75, 'بيع', 60, f"RSI: تشبع شراء ({rsi:.0f})"
        elif rsi < 50:
            return 55, 'شراء', 35, f"RSI: تحت 50 ({rsi:.0f})"
        else:
            return 55, 'بيع', 35, f"RSI: فوق 50 ({rsi:.0f})"
    
    def _macd_analysis(self, closes, volumes=None):
        """
        🔴 تعديل 1: MACD Signal Line صحيح
        """
        if len(closes) < 26:
            return 50, 'محايد', 30, "MACD: غير كاف"
        
        # حساب MACD Line كامل
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line = ema12 - ema26
        
        # 🔴 تعديل 1: Signal Line على آخر 9 قيم من MACD
        if len(macd_line) >= 9:
            signal_line = self._ema(macd_line, 9)
            macd = macd_line[-1]
            signal = signal_line[-1]
        else:
            macd = macd_line[-1]
            signal = macd
        
        if macd > signal and macd > 0:
            return 65, 'شراء', 50, "MACD: فوق Signal + فوق صفر"
        elif macd < signal and macd < 0:
            return 65, 'بيع', 50, "MACD: تحت Signal + تحت صفر"
        elif macd > signal:
            return 55, 'شراء', 35, "MACD: فوق Signal"
        elif macd < signal:
            return 55, 'بيع', 35, "MACD: تحت Signal"
        
        return 50, 'محايد', 30, "MACD: محايد"
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """EMA"""
        alpha = 2.0 / (period + 1.0)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1.0 - alpha) * result[i-1]
        return result
    
    def _sentiment_analysis(self, closes, volumes=None):
        """تحليل المشاعر"""
        if len(closes) < 10:
            return 50, 'محايد', 30, "Sent: غير كاف"
        
        window = closes[-10:]
        up_bars = sum(1 for i in range(1, len(window)) if window[i] > window[i-1])
        ratio = up_bars / max(len(window) - 1, 1)
        
        if ratio > 0.8:
            return 70, 'بيع', 55, f"Sent: تفاؤل زائد ({ratio:.0%})"
        elif ratio < 0.2:
            return 70, 'شراء', 55, f"Sent: تشاؤم زائد ({ratio:.0%})"
        elif ratio > 0.6:
            return 55, 'شراء', 35, f"Sent: إيجابي ({ratio:.0%})"
        elif ratio < 0.4:
            return 55, 'بيع', 35, f"Sent: سلبي ({ratio:.0%})"
        
        return 50, 'محايد', 30, "Sent: محايد"
    
    def _wyckoff_analysis(self, highs, lows, closes, volumes, opens=None):
        """تحليل وايكوف"""
        if len(closes) < 20:
            return 50, 'محايد', 30, "Wyckoff: غير كاف"
        
        range_high = max(highs[-20:])
        range_low = min(lows[-20:])
        range_size = range_high - range_low
        current = closes[-1]
        position = (current - range_low) / max(range_size, 0.0001)
        
        avg_vol = np.mean(volumes[-20:])
        recent_vol = np.mean(volumes[-5:])
        
        if position < 0.3 and recent_vol < avg_vol:
            return 60, 'شراء', 45, "Wyckoff: تجميع"
        elif position > 0.7 and recent_vol > avg_vol:
            return 60, 'بيع', 45, "Wyckoff: توزيع"
        
        return 50, 'محايد', 30, "Wyckoff: غير محدد"
    
    def _fibonacci_analysis(self, highs, lows, closes, volumes=None):
        """تحليل فيبوناتشي"""
        if len(closes) < 30:
            return 50, 'محايد', 30, "Fib: غير كاف"
        
        swing_high = max(highs[-30:])
        swing_low = min(lows[-30:])
        diff = swing_high - swing_low
        current = closes[-1]
        
        fib_618 = swing_low + diff * 0.618
        fib_382 = swing_low + diff * 0.382
        
        if abs(current - fib_618) < diff * 0.02:
            return 65, 'شراء', 50, f"Fib: عند 61.8% ({fib_618:.2f})"
        elif abs(current - fib_382) < diff * 0.02:
            return 60, 'شراء', 40, f"Fib: عند 38.2% ({fib_382:.2f})"
        elif current > fib_618:
            return 55, 'شراء', 35, "Fib: فوق 61.8%"
        
        return 50, 'محايد', 30, "Fib: غير محدد"
    
    def _stochastic_analysis(self, closes, volumes=None):
        """تحليل ستوكاستيك"""
        if len(closes) < 14:
            return 50, 'محايد', 30, "Stoch: غير كاف"
        
        period = 14
        highest = np.max(closes[-period:])
        lowest = np.min(closes[-period:])
        
        if highest != lowest:
            k = 100.0 * (closes[-1] - lowest) / (highest - lowest)
        else:
            k = 50.0
        
        if k < 20:
            return 70, 'شراء', 55, f"Stoch: تشبع بيع ({k:.0f})"
        elif k > 80:
            return 70, 'بيع', 55, f"Stoch: تشبع شراء ({k:.0f})"
        elif k < 50:
            return 55, 'شراء', 35, f"Stoch: تحت 50 ({k:.0f})"
        else:
            return 55, 'بيع', 35, f"Stoch: فوق 50 ({k:.0f})"
    
    def _elliott_analysis(self, highs, lows, closes, volumes=None):
        """تحليل موجات إليوت"""
        if len(closes) < 50:
            return 50, 'محايد', 30, "Elliott: غير كاف"
        
        # تبسيط: البحث عن 5 موجات
        trend = (closes[-1] - closes[-30]) / max(closes[-30], 0.0001)
        
        if trend > 0.05:
            return 60, 'شراء', 40, "Elliott: موجة دافعة صاعدة"
        elif trend < -0.05:
            return 60, 'بيع', 40, "Elliott: موجة دافعة هابطة"
        
        return 50, 'محايد', 30, "Elliott: غير محدد"
    
    def _harmonic_analysis(self, highs, lows, closes, volumes=None):
        """تحليل هارمونيك"""
        if len(closes) < 30:
            return 50, 'محايد', 30, "Harmonic: غير كاف"
        
        # تبسيط: البحث عن أنماط XABCD
        swing_high = max(highs[-30:])
        swing_low = min(lows[-30:])
        diff = swing_high - swing_low
        current = closes[-1]
        position = (current - swing_low) / max(diff, 0.0001)
        
        # مناطق انعكاس هارمونيك
        if 0.75 < position < 0.85:
            return 65, 'بيع', 45, "Harmonic: منطقة انعكاس بيع"
        elif 0.15 < position < 0.25:
            return 65, 'شراء', 45, "Harmonic: منطقة انعكاس شراء"
        
        return 50, 'محايد', 30, "Harmonic: غير محدد"
    
    def _auction_analysis(self, highs, lows, closes, volumes=None):
        """تحليل Auction Market"""
        if len(closes) < 20:
            return 50, 'محايد', 30, "Auction: غير كاف"
        
        # تبسيط: توازن وعدم توازن
        range_high = max(highs[-20:])
        range_low = min(lows[-20:])
        current = closes[-1]
        mid = (range_high + range_low) / 2.0
        
        if current > range_high:
            return 65, 'شراء', 50, "Auction: اختراق لأعلى"
        elif current < range_low:
            return 65, 'بيع', 50, "Auction: كسر لأسفل"
        elif current > mid:
            return 55, 'شراء', 35, "Auction: فوق التوازن"
        else:
            return 55, 'بيع', 35, "Auction: تحت التوازن"
    
    def _fuse_signals(self, school_scores: Dict[str, SchoolScore],
                      current_price: float) -> List[HybridSignal]:
        """
        🟡 تعديل 5: دمج الإشارات مع Conflict Resolution
        """
        signals = []
        
        buy_schools = [s for s in school_scores.values() if s.recommendation == 'شراء' and s.confidence > 40]
        sell_schools = [s for s in school_scores.values() if s.recommendation == 'بيع' and s.confidence > 40]
        
        # مجموع الأوزان (للتعادل)
        buy_weight = sum(s.total_weight for s in buy_schools)
        sell_weight = sum(s.total_weight for s in sell_schools)
        
        # إجماع قوي
        if len(buy_schools) >= 7:
            signals.append(HybridSignal(
                'strong_consensus', 'شراء', min(0.9, len(buy_schools) * 0.1),
                [s.name for s in buy_schools],
                f"إجماع {len(buy_schools)} مدرسة على الشراء",
            ))
        elif len(sell_schools) >= 7:
            signals.append(HybridSignal(
                'strong_consensus', 'بيع', min(0.9, len(sell_schools) * 0.1),
                [s.name for s in sell_schools],
                f"إجماع {len(sell_schools)} مدرسة على البيع",
            ))
        
        # أفضل المدارس تتفق
        top_schools = sorted(school_scores.values(), key=lambda s: s.total_weight, reverse=True)[:5]
        top_buy = [s for s in top_schools if s.recommendation == 'شراء']
        top_sell = [s for s in top_schools if s.recommendation == 'بيع']
        
        if len(top_buy) >= 4:
            signals.append(HybridSignal(
                'top_consensus', 'شراء', 0.8,
                [s.name for s in top_buy],
                "أفضل 5 مدارس تتفق على الشراء",
            ))
        elif len(top_sell) >= 4:
            signals.append(HybridSignal(
                'top_consensus', 'بيع', 0.8,
                [s.name for s in top_sell],
                "أفضل 5 مدارس تتفق على البيع",
            ))
        
        # 🟡 تعديل 5: Conflict Resolution - كسر التعادل بالوزن
        if len(buy_schools) == len(sell_schools) and len(buy_schools) >= 4:
            if buy_weight > sell_weight * 1.3:
                signals.append(HybridSignal(
                    'tie_break_weight', 'شراء', 0.55,
                    [s.name for s in buy_schools],
                    f"تعادل {len(buy_schools)}-{len(sell_schools)} - كسر بالوزن (شراء {buy_weight:.2f} vs بيع {sell_weight:.2f})",
                    tie_breaker='weight',
                ))
            elif sell_weight > buy_weight * 1.3:
                signals.append(HybridSignal(
                    'tie_break_weight', 'بيع', 0.55,
                    [s.name for s in sell_schools],
                    f"تعادل {len(buy_schools)}-{len(sell_schools)} - كسر بالوزن (بيع {sell_weight:.2f} vs شراء {buy_weight:.2f})",
                    tie_breaker='weight',
                ))
            else:
                signals.append(HybridSignal(
                    'tie_break_accuracy', 'محايد', 0.1,
                    [s.name for s in buy_schools + sell_schools],
                    f"تعادل حقيقي {len(buy_schools)}-{len(sell_schools)} - انتظار",
                    tie_breaker='none',
                ))
        
        return signals
    
    def _adapt_weights(self, school_scores: Dict[str, SchoolScore], regime: Dict):
        """
        🟡 تعديل 4: تكييف الأوزان مع نظام السوق والأداء التاريخي
        """
        best_schools = regime.get('best_schools', [])
        
        for school in self.SCHOOLS:
            # المدارس المناسبة للنظام تحصل على وزن أكبر
            if school in best_schools:
                self.school_weights[school] *= 1.1
            else:
                self.school_weights[school] *= 0.95
            
            # 🟡 تعديل 4: المدارس ذات الأداء التاريخي الأعلى
            perf = self.performance_history.get(school)
            if perf and perf.accuracy > 0.55:
                self.school_weights[school] *= 1.05
            
            # المدارس الواثقة تحصل على وزن أكبر
            if school in school_scores:
                if school_scores[school].confidence > 50:
                    self.school_weights[school] *= 1.03
        
        # تطبيع
        total = sum(self.school_weights.values())
        if total > 0:
            for s in self.SCHOOLS:
                self.school_weights[s] /= total
    
    def update_performance(self, school_name: str, was_correct: bool, confidence: float):
        """
        🟡 تعديل 4: تحديث سجل الأداء
        """
        if school_name in self.performance_history:
            perf = self.performance_history[school_name]
            perf.total_calls += 1
            if was_correct:
                perf.correct_calls += 1
                perf.avg_confidence_when_correct = (perf.avg_confidence_when_correct * (perf.correct_calls - 1) + confidence) / perf.correct_calls
            perf.accuracy = perf.correct_calls / max(perf.total_calls, 1)
            perf.last_updated = self.total_analyses
    
    def _make_final_decision(self, school_scores: Dict[str, SchoolScore],
                              hybrid_signals: List[HybridSignal],
                              regime: Dict) -> Dict:
        """القرار النهائي"""
        buy_signals = []
        sell_signals = []
        
        # من المدارس (مرجحة بالأداء والدقة)
        for score in school_scores.values():
            weight = score.total_weight * score.confidence / 100.0
            
            if score.recommendation == 'شراء':
                buy_signals.append((f"{score.name}: {score.reason}", weight))
            elif score.recommendation == 'بيع':
                sell_signals.append((f"{score.name}: {score.reason}", weight))
        
        # من الإشارات الهجينة
        for sig in hybrid_signals:
            if sig.direction == 'شراء':
                buy_signals.append((sig.description, sig.strength * 0.8))
            elif sig.direction == 'بيع':
                sell_signals.append((sig.description, sig.strength * 0.8))
        
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        # 🟡 تعديل 5: Conflict Resolution في القرار النهائي
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
        
        buy_count = sum(1 for s in school_scores.values() if s.recommendation == 'شراء')
        sell_count = sum(1 for s in school_scores.values() if s.recommendation == 'بيع')
        reason += f" | {buy_count} شراء vs {sell_count} بيع | {regime['type']}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "buy_count": buy_count,
            "sell_count": sell_count,
        }


def create_hybrid_modern_strategy():
    """إنشاء الاستراتيجية الهجينة الحديثة الجاهزة (الإصدار 2.0)"""
    return HybridModernStrategy()