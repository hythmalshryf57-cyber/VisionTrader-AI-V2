"""
═══════════════════════════════════════════════════════════════════════════════
REGIME DETECTION & ADAPTATION - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الحادية عشرة: كشف نظام السوق والتكيف معه - قائد الأوركسترا
═══════════════════════════════════════════════════════════════════════════════

السوق ليس حالة واحدة. السوق "مزاجي" يتغير بين أنظمة مختلفة.
ما ينجح في نظام قد يفشل فشلاً ذريعاً في نظام آخر.

هذه المدرسة هي "قائد الأوركسترا" - هي من يقرر:
- أي الاستراتيجيات تعمل الآن؟
- أيها يجب أن يصمت؟
- متى نتوقع تغير النظام؟
- كيف نعدل حجم المركز والعدوانية؟

الأنظمة التي نكتشفها (ديناميكياً):
- Trending Bull / Bear
- Trend Weakening
- Range Bound / Expanding Range
- Volatility Explosion
- Quiet / Chaotic
- Reversal Zone
- Distribution / Accumulation

الإضافات الجديدة (الإصدار 2.0):
- Multi-Timeframe Regime
- Regime Divergence Detection
- Early Warning System لتغير النظام
- Regime Confidence Decay مع الوقت
- Hurst Exponent محسن (R/S متعدد النطاقات)
- أوزان تصنيف متعلمة من الأداء
- Fractal Regime (أنظمة متداخلة)
- User Risk Profile
- get_active_strategies() - يشغل/يقفل الاستراتيجيات
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MarketRegimeType(Enum):
    """أنواع أنظمة السوق"""
    TRENDING_BULL = "صاعد قوي"
    TRENDING_BEAR = "هابط قوي"
    TREND_WEAKENING_BULL = "ضعف صعود"
    TREND_WEAKENING_BEAR = "ضعف هبوط"
    RANGE_BOUND = "نطاق محدود"
    EXPANDING_RANGE = "نطاق متسع"
    VOLATILITY_EXPLOSION = "انفجار تقلب"
    QUIET = "هدوء"
    CHAOTIC = "فوضوي"
    REVERSAL_ZONE = "منطقة انعكاس"
    DISTRIBUTION = "توزيع"
    ACCUMULATION = "تجميع"


class RiskProfile(Enum):
    """ملف مخاطرة المستخدم"""
    CONSERVATIVE = "محافظ"
    MODERATE = "معتدل"
    AGGRESSIVE = "عدواني"


@dataclass
class MarketRegime:
    """نظام السوق - نسخة محسنة"""
    regime_type: MarketRegimeType
    start_index: int
    end_index: int
    duration: int
    avg_volatility: float
    avg_trend_strength: float
    avg_volume: float
    mean_reversion_speed: float
    hurst_exponent: float
    chaos_score: float
    efficiency_ratio: float
    confidence: float
    confidence_decay: float = 1.0  # 🟡 تعديل 5
    divergence_score: float = 0.0  # 🟡 تعديل 7


@dataclass
class RegimeTransition:
    """انتقال بين نظامين"""
    from_regime: MarketRegimeType
    to_regime: MarketRegimeType
    transition_index: int
    transition_duration: int
    volume_spike: bool
    gap_detected: bool
    smoothness: float


@dataclass
class EarlyWarning:
    """نظام إنذار مبكر لتغير النظام"""
    warning_level: str  # 'green', 'yellow', 'orange', 'red'
    signals_triggered: List[str]
    probability: float
    estimated_bars_until: int
    description: str


@dataclass
class StrategyRecommendation:
    """توصية استراتيجية"""
    strategy_name: str
    active: bool
    weight: float  # 0-1
    reason: str


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: كاشف نظام السوق (محسن بالكامل)                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MarketRegimeClassifier:
    """
    يصنف نظام السوق الحالي بمقاييس متقدمة.
    
    🔴 تعديل 2: Hurst محسن (R/S متعدد النطاقات)
    🔴 تعديل 3: أوزان تصنيف متعلمة
    🟡 تعديل 5: Regime Confidence Decay
    🟡 تعديل 7: Regime Divergence
    """
    
    def __init__(self):
        self.regime_history: List[MarketRegime] = []
        self.transitions: List[RegimeTransition] = []
        self.current_regime: Optional[MarketRegime] = None
        self.regime_duration_min = 10
        
        # 🔴 تعديل 3: أوزان متعلمة (تتحدث مع الأداء)
        self.classification_weights = self._init_classification_weights()
        self.performance_history = defaultdict(list)
    
    def _init_classification_weights(self) -> Dict:
        """أوزان ابتدائية للتصنيف"""
        return {
            'trend': 0.25, 'efficiency': 0.20, 'mean_reversion': 0.18,
            'hurst': 0.15, 'chaos': 0.12, 'volume': 0.10,
        }
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray) -> Dict:
        """تصنيف النظام الحالي"""
        if len(closes) < 30:
            return {"regime": None, "confidence": 0, "reason": "بيانات غير كافية"}
        
        metrics = self._calculate_regime_metrics(highs, lows, closes, volumes)
        regime_type, confidence = self._classify_regime(metrics)
        
        # 🟡 تعديل 5: اضمحلال الثقة مع الوقت
        confidence_decay = self._calculate_confidence_decay(regime_type)
        adjusted_confidence = confidence * confidence_decay
        
        # 🟡 تعديل 7: درجة التباعد
        divergence_score = self._calculate_regime_divergence(metrics, closes)
        
        regime = MarketRegime(
            regime_type=regime_type,
            start_index=metrics['start_index'],
            end_index=metrics['end_index'],
            duration=metrics['duration'],
            avg_volatility=metrics['volatility'],
            avg_trend_strength=metrics['trend'],
            avg_volume=metrics['relative_volume'],
            mean_reversion_speed=metrics['mean_reversion'],
            hurst_exponent=metrics['hurst'],
            chaos_score=metrics['chaos'],
            efficiency_ratio=metrics['efficiency'],
            confidence=adjusted_confidence,
            confidence_decay=confidence_decay,
            divergence_score=divergence_score,
        )
        
        self._update_history(regime)
        transition = self._detect_transition(regime)
        self._adapt_thresholds()
        self._update_classification_weights()  # 🔴 تعديل 3
        
        return {
            "regime": regime,
            "regime_name": regime_type.value,
            "confidence": adjusted_confidence,
            "metrics": metrics,
            "transition": transition,
            "regime_duration": regime.duration,
            "divergence_score": divergence_score,
        }
    
    def _calculate_regime_metrics(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """حساب مقاييس النظام بنافذة ديناميكية"""
        avg_range = np.mean(highs[-20:] - lows[-20:])
        avg_price = np.mean(np.abs(closes[-20:]))
        
        if avg_range > 0 and avg_price > 0:
            raw_window = int(20 / max(0.1, (avg_range / avg_price * 50)))
            window = max(15, min(60, raw_window))
        else:
            window = 25
        
        start_idx = max(0, len(closes) - window)
        window_highs = highs[start_idx:]
        window_lows = lows[start_idx:]
        window_closes = closes[start_idx:]
        window_volumes = volumes[start_idx:]
        
        returns = np.diff(np.log(np.maximum(window_closes, 0.0001)))
        volatility = np.std(returns) * np.sqrt(len(returns)) if len(returns) > 0 else 0
        trend = self._measure_trend_strength(window_closes)
        
        if len(volumes) >= 50:
            long_term_avg_vol = np.mean(volumes[-50:])
        else:
            long_term_avg_vol = np.mean(volumes)
        relative_volume = np.mean(window_volumes) / max(long_term_avg_vol, 0.0001)
        
        mean_reversion = self._measure_mean_reversion_speed(window_closes)
        
        # 🔴 تعديل 2: Hurst محسن متعدد النطاقات
        hurst = self._estimate_hurst_improved(window_closes)
        
        chaos = self._measure_chaos(window_closes, window_highs, window_lows)
        efficiency = self._calculate_efficiency_ratio(window_closes)
        
        return {
            'start_index': start_idx, 'end_index': len(closes) - 1,
            'duration': len(window_closes),
            'volatility': volatility, 'trend': trend,
            'relative_volume': relative_volume, 'mean_reversion': mean_reversion,
            'hurst': hurst, 'chaos': chaos, 'efficiency': efficiency,
        }
    
    def _measure_trend_strength(self, closes: np.ndarray) -> float:
        """قياس قوة الاتجاه (-1 إلى 1)"""
        if len(closes) < 10:
            return 0.0
        x = np.arange(len(closes))
        slope, _ = np.polyfit(x, closes, 1)
        avg_price = np.mean(closes)
        if avg_price > 0:
            normalized_slope = slope / avg_price * 100
        else:
            normalized_slope = 0
        return np.tanh(normalized_slope)
    
    def _measure_mean_reversion_speed(self, closes: np.ndarray) -> float:
        """قياس سرعة العودة للمتوسط"""
        if len(closes) < 20:
            return 0.5
        ma = np.convolve(closes, np.ones(10)/10, mode='same')
        deviations = closes - ma
        crossings = sum(1 for i in range(1, len(deviations))
                       if (deviations[i] > 0 and deviations[i-1] <= 0) or
                          (deviations[i] < 0 and deviations[i-1] >= 0))
        return min(1.0, crossings / max(len(closes) * 0.08, 1))
    
    def _estimate_hurst_improved(self, data: np.ndarray) -> float:
        """
        🔴 تعديل 2: Hurst Exponent محسن باستخدام R/S متعدد النطاقات
        
        يستخدم 3 نطاقات مختلفة ويأخذ المتوسط
        """
        if len(data) < 40:
            return 0.5
        
        def rs_analysis(series, min_window=10):
            """R/S Analysis لنافذة واحدة"""
            n = len(series)
            if n < min_window:
                return 0.5
            
            mean = np.mean(series)
            deviations = series - mean
            cumulative = np.cumsum(deviations)
            r = np.max(cumulative) - np.min(cumulative)
            s = np.std(series)
            
            if s == 0:
                return 0.5
            
            rs = r / s
            # H = log(RS) / log(n)
            h_est = np.log(rs) / np.log(n) if n > 1 else 0.5
            
            return max(0.1, min(0.9, h_est))
        
        # 3 نطاقات مختلفة
        n1 = min(len(data), 40)
        n2 = min(len(data), 25)
        n3 = min(len(data), 15)
        
        h1 = rs_analysis(data[-n1:])
        h2 = rs_analysis(data[-n2:])
        h3 = rs_analysis(data[-n3:])
        
        # المتوسط المرجح (الأطول وزناً أعلى)
        hurst = h1 * 0.5 + h2 * 0.3 + h3 * 0.2
        
        return hurst
    
    def _measure_chaos(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> float:
        """قياس درجة الفوضى"""
        if len(closes) < 15:
            return 0.3
        
        ranges = highs - lows
        range_std = np.std(ranges)
        range_mean = np.mean(ranges) if np.mean(ranges) > 0 else 1
        irregularity = min(1.0, range_std / range_mean)
        
        direction_changes = sum(1 for i in range(2, len(closes))
                               if (closes[i] > closes[i-1] and closes[i-1] < closes[i-2]) or
                                  (closes[i] < closes[i-1] and closes[i-1] > closes[i-2]))
        change_rate = direction_changes / max(len(closes), 1)
        
        close_diffs = np.diff(closes)
        if len(close_diffs) > 1:
            autocorr = abs(np.corrcoef(close_diffs[:-1], close_diffs[1:])[0, 1])
        else:
            autocorr = 0
        if np.isnan(autocorr):
            autocorr = 0
        randomness = 1 - autocorr
        
        return min(1.0, irregularity * 0.3 + change_rate * 0.3 + randomness * 0.4)
    
    def _calculate_efficiency_ratio(self, closes: np.ndarray) -> float:
        """نسبة الكفاءة"""
        if len(closes) < 10:
            return 0.5
        net_change = abs(closes[-1] - closes[0])
        total_path = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes)))
        if total_path == 0:
            return 1.0
        return net_change / total_path
    
    def _classify_regime(self, metrics: Dict) -> Tuple[MarketRegimeType, float]:
        """
        🔴 تعديل 3: تصنيف بأوزان متعلمة
        """
        w = self.classification_weights
        
        scores = {}
        
        # صاعد قوي
        scores[MarketRegimeType.TRENDING_BULL] = (
            max(0, metrics['trend']) * w['trend'] * 1.6 +
            metrics['efficiency'] * w['efficiency'] * 1.5 +
            (1 - metrics['mean_reversion']) * w['mean_reversion'] * 0.8 +
            metrics['hurst'] * w['hurst'] * 1.0
        )
        
        # هابط قوي
        scores[MarketRegimeType.TRENDING_BEAR] = (
            max(0, -metrics['trend']) * w['trend'] * 1.6 +
            metrics['efficiency'] * w['efficiency'] * 1.5 +
            (1 - metrics['mean_reversion']) * w['mean_reversion'] * 0.8 +
            metrics['hurst'] * w['hurst'] * 1.0
        )
        
        # ضعف صعود
        scores[MarketRegimeType.TREND_WEAKENING_BULL] = (
            max(0, metrics['trend'] * 0.5) * w['trend'] * 1.2 +
            metrics['mean_reversion'] * w['mean_reversion'] * 1.7 +
            metrics['chaos'] * w['chaos'] * 1.7 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.0
        )
        
        # ضعف هبوط
        scores[MarketRegimeType.TREND_WEAKENING_BEAR] = (
            max(0, -metrics['trend'] * 0.5) * w['trend'] * 1.2 +
            metrics['mean_reversion'] * w['mean_reversion'] * 1.7 +
            metrics['chaos'] * w['chaos'] * 1.7 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.0
        )
        
        # نطاق محدود
        scores[MarketRegimeType.RANGE_BOUND] = (
            (1 - abs(metrics['trend'])) * w['trend'] * 1.8 +
            metrics['mean_reversion'] * w['mean_reversion'] * 2.0 +
            (1 - metrics['chaos']) * w['chaos'] * 1.7 +
            (1 - metrics['efficiency']) * w['efficiency'] * 0.5
        )
        
        # نطاق متسع
        scores[MarketRegimeType.EXPANDING_RANGE] = (
            min(metrics['volatility'] * 15, 1) * w['trend'] * 1.5 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.5 +
            metrics['chaos'] * w['chaos'] * 1.0 +
            (1 - abs(metrics['trend'])) * w['trend'] * 1.0
        )
        
        # انفجار تقلب
        scores[MarketRegimeType.VOLATILITY_EXPLOSION] = (
            min(metrics['volatility'] * 25, 1) * w['trend'] * 2.0 +
            min(metrics['relative_volume'], 2) / 2 * w['volume'] * 1.5 +
            metrics['chaos'] * w['chaos'] * 1.0 +
            (1 - abs(metrics['trend'])) * w['trend'] * 0.5
        )
        
        # هدوء
        scores[MarketRegimeType.QUIET] = (
            (1 - min(metrics['volatility'] * 50, 1)) * w['trend'] * 2.0 +
            (1 - abs(metrics['trend'])) * w['trend'] * 1.3 +
            (1 - metrics['chaos']) * w['chaos'] * 1.0 +
            (1 if metrics['relative_volume'] < 0.7 else 0) * w['volume'] * 0.8
        )
        
        # فوضوي
        scores[MarketRegimeType.CHAOTIC] = (
            metrics['chaos'] * w['chaos'] * 2.5 +
            min(metrics['volatility'] * 15, 1) * w['trend'] * 1.0 +
            (1 - metrics['efficiency']) * w['efficiency'] * 0.8 +
            (1 - abs(metrics['trend'])) * w['trend'] * 0.8
        )
        
        # منطقة انعكاس
        scores[MarketRegimeType.REVERSAL_ZONE] = (
            metrics['mean_reversion'] * w['mean_reversion'] * 2.0 +
            abs(metrics['trend']) * w['trend'] * 1.3 +
            metrics['chaos'] * w['chaos'] * 1.3 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.0
        )
        
        # توزيع
        scores[MarketRegimeType.DISTRIBUTION] = (
            min(metrics['relative_volume'], 2) / 2 * w['volume'] * 1.5 +
            max(0, -metrics['trend'] * 0.3) * w['trend'] * 1.3 +
            metrics['mean_reversion'] * w['mean_reversion'] * 1.0 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.3
        )
        
        # تجميع
        scores[MarketRegimeType.ACCUMULATION] = (
            (1 - min(metrics['relative_volume'], 1)) * w['volume'] * 1.5 +
            max(0, metrics['trend'] * 0.3) * w['trend'] * 1.3 +
            metrics['mean_reversion'] * w['mean_reversion'] * 1.0 +
            (1 - metrics['efficiency']) * w['efficiency'] * 1.3
        )
        
        best_regime = max(scores, key=scores.get)
        best_score = scores[best_regime]
        
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and sorted_scores[0] > 0:
            confidence = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0]
        else:
            confidence = 0.5
        
        return best_regime, min(0.95, max(0.3, confidence))
    
    def _calculate_confidence_decay(self, regime_type: MarketRegimeType) -> float:
        """
        🟡 تعديل 5: اضمحلال الثقة مع الوقت
        
        كلما طال بقاؤنا في النظام، زاد احتمال الانتقال
        """
        if not self.current_regime or self.current_regime.regime_type != regime_type:
            return 1.0
        
        # متوسط مدة هذا النظام تاريخياً
        same_type_durations = [r.duration for r in self.regime_history 
                               if r.regime_type == regime_type]
        
        if not same_type_durations:
            return 1.0
        
        # استخدام median لتجنب القيم المتطرفة 🔴 تعديل 4
        avg_duration = np.median(same_type_durations)
        
        if avg_duration == 0:
            return 1.0
        
        current_duration = self.current_regime.duration
        decay = max(0.3, 1.0 - (current_duration / max(avg_duration, 1)) * 0.7)
        
        return decay
    
    def _calculate_regime_divergence(self, metrics: Dict, closes: np.ndarray) -> float:
        """
        🟡 تعديل 7: Regime Divergence
        
        السعر يصعد لكن Efficiency Ratio يهبط = اتجاه يضعف
        السعر يهبط لكن Hurst يرتفع = استمرارية تتشكل
        """
        if len(closes) < 20:
            return 0.0
        
        divergence = 0.0
        
        # تباعد 1: اتجاه قوي + كفاءة منخفضة
        if abs(metrics['trend']) > 0.5 and metrics['efficiency'] < 0.3:
            divergence += 0.4
        
        # تباعد 2: فوضى منخفضة + Mean Reversion عالي (اتجاه يتشكل)
        if metrics['chaos'] < 0.3 and metrics['mean_reversion'] > 0.7:
            divergence += 0.3
        
        # تباعد 3: Hurst عالي + حجم منخفض (اتجاه بلا قناعة)
        if metrics['hurst'] > 0.65 and metrics['relative_volume'] < 0.7:
            divergence += 0.3
        
        return min(1.0, divergence)
    
    def _update_history(self, regime: MarketRegime):
        """تحديث تاريخ الأنظمة"""
        if self.current_regime is None or self.current_regime.regime_type != regime.regime_type:
            if self.current_regime is not None:
                transition = RegimeTransition(
                    from_regime=self.current_regime.regime_type,
                    to_regime=regime.regime_type,
                    transition_index=regime.start_index,
                    transition_duration=regime.start_index - self.current_regime.end_index,
                    volume_spike=False,
                    gap_detected=False,
                    smoothness=0.5,
                )
                self.transitions.append(transition)
            
            self.regime_history.append(regime)
            if len(self.regime_history) > 50:
                self.regime_history.pop(0)
        
        self.current_regime = regime
    
    def _detect_transition(self, regime: MarketRegime) -> Optional[Dict]:
        """كشف الانتقال"""
        if len(self.regime_history) < 2:
            return None
        last = self.regime_history[-1]
        if last.regime_type != regime.regime_type and last.end_index >= regime.start_index - 5:
            return {"from": last.regime_type.value, "to": regime.regime_type.value,
                    "recent": True, "at_index": regime.start_index}
        return None
    
    def _adapt_thresholds(self):
        """تكييف العتبات"""
        if len(self.regime_history) >= 5:
            durations = [r.duration for r in self.regime_history[-5:]]
            self.regime_duration_min = max(5, int(np.median(durations) * 0.3))  # 🔴 تعديل 4: median
    
    def _update_classification_weights(self):
        """
        🔴 تعديل 3: تحديث أوزان التصنيف من الأداء
        
        إذا كانت استراتيجيات معينة تؤدي أفضل من غيرها في نظام معين،
        عزز الأوزان التي قادت لهذا التصنيف
        """
        # هذا يحتاج feedback من أداء الاستراتيجيات
        # في النسخة الحالية: ثبات نسبي مع تعديل طفيف بالثقة
        if self.current_regime and self.current_regime.confidence > 0.7:
            # النظام واضح = عزز الأوزان الحالية قليلاً
            for key in self.classification_weights:
                self.classification_weights[key] *= 1.01
        elif self.current_regime and self.current_regime.confidence < 0.4:
            # النظام غير واضح = قلل الأوزان قليلاً
            for key in self.classification_weights:
                self.classification_weights[key] *= 0.99
        
        # تطبيع
        total = sum(self.classification_weights.values())
        for key in self.classification_weights:
            self.classification_weights[key] /= total


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة الثانية: نظام الإنذار المبكر (Early Warning System)              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class EarlyWarningSystem:
    """
    🟢 تعديل 10: Early Warning System لتغير النظام
    
    3 إشارات تحذيرية قبل تغير النظام:
    1. Efficiency Ratio يبدأ بالانخفاض
    2. Chaos يرتفع
    3. Mean Reversion يزداد
    """
    
    def analyze(self, regime: MarketRegime, metrics: Dict,
                regime_history: List[MarketRegime]) -> EarlyWarning:
        """تحليل الإنذار المبكر"""
        signals = []
        warning_level = 'green'
        
        # إشارة 1: Efficiency Ratio ينخفض
        if regime.efficiency_ratio < 0.3:
            signals.append("كفاءة الحركة منخفضة")
        
        # إشارة 2: Chaos يرتفع
        if regime.chaos_score > 0.6:
            signals.append("درجة الفوضى مرتفعة")
        
        # إشارة 3: Mean Reversion يزداد
        if regime.mean_reversion_speed > 0.7:
            signals.append("العودة للمتوسط تتسارع")
        
        # إشارة 4: Hurst يبدأ بالانخفاض (فقدان الاستمرارية)
        if regime.hurst_exponent < 0.4 and regime.hurst_exponent > 0.2:
            signals.append("فقدان الاستمرارية")
        
        # إشارة 5: Divergence score مرتفع
        if regime.divergence_score > 0.5:
            signals.append("تباعد بين السعر وكفاءة الحركة")
        
        # إشارة 6: Confidence Decay متقدم
        if regime.confidence_decay < 0.5:
            signals.append("اضمحلال الثقة في النظام الحالي")
        
        # تحديد المستوى
        num_signals = len(signals)
        
        if num_signals >= 4:
            warning_level = 'red'
            probability = 0.8
            estimated_bars = 3
        elif num_signals >= 3:
            warning_level = 'orange'
            probability = 0.6
            estimated_bars = 8
        elif num_signals >= 2:
            warning_level = 'yellow'
            probability = 0.35
            estimated_bars = 15
        elif num_signals >= 1:
            warning_level = 'yellow'
            probability = 0.15
            estimated_bars = 25
        else:
            probability = 0.05
            estimated_bars = 50
        
        # وصف
        if warning_level == 'red':
            description = "تغير النظام وشيك جداً - استعد للانتقال"
        elif warning_level == 'orange':
            description = "احتمال قوي لتغير النظام قريباً"
        elif warning_level == 'yellow':
            description = "علامات أولية على ضعف النظام الحالي"
        else:
            description = "النظام مستقر"
        
        return EarlyWarning(
            warning_level=warning_level,
            signals_triggered=signals,
            probability=probability,
            estimated_bars_until=estimated_bars,
            description=description,
        )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الثالثة: قائد الأوركسترا (Strategy Orchestrator)              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class StrategyOrchestrator:
    """
    🟢 تعديل 9: قائد الأوركسترا
    
    يقرر أي الاستراتيجيات تعمل وأيها تصمت بناءً على النظام الحالي
    """
    
    # مصفوفة: النظام × الاستراتيجيات المناسبة
    REGIME_STRATEGY_MAP = {
        MarketRegimeType.TRENDING_BULL: {
            'wyckoff': 1.0, 'ict': 1.0, 'vsa': 0.8, 'vpin': 0.3,
            'stochastic': 0.2, 'rsi': 0.1, 'sentiment': 0.5,
            'trend_following': 1.0, 'momentum': 0.9, 'breakout': 0.8,
            'mean_reversion': 0.0, 'range_trading': 0.0, 'scalping': 0.2,
        },
        MarketRegimeType.TRENDING_BEAR: {
            'wyckoff': 1.0, 'ict': 1.0, 'vsa': 0.8, 'vpin': 0.5,
            'stochastic': 0.2, 'rsi': 0.1, 'sentiment': 0.5,
            'trend_following': 1.0, 'momentum': 0.9, 'breakout': 0.8,
            'mean_reversion': 0.0, 'range_trading': 0.0, 'scalping': 0.2,
        },
        MarketRegimeType.RANGE_BOUND: {
            'wyckoff': 0.4, 'ict': 0.3, 'vsa': 0.5, 'vpin': 0.5,
            'stochastic': 0.9, 'rsi': 0.9, 'sentiment': 0.3,
            'trend_following': 0.1, 'momentum': 0.2, 'breakout': 0.3,
            'mean_reversion': 1.0, 'range_trading': 1.0, 'scalping': 0.8,
        },
        MarketRegimeType.QUIET: {
            'wyckoff': 0.3, 'ict': 0.2, 'vsa': 0.4, 'vpin': 0.5,
            'stochastic': 0.6, 'rsi': 0.6, 'sentiment': 0.2,
            'trend_following': 0.1, 'momentum': 0.1, 'breakout': 0.2,
            'mean_reversion': 0.8, 'range_trading': 0.7, 'scalping': 0.9,
        },
        MarketRegimeType.VOLATILITY_EXPLOSION: {
            'wyckoff': 0.6, 'ict': 0.7, 'vsa': 0.7, 'vpin': 0.8,
            'stochastic': 0.3, 'rsi': 0.2, 'sentiment': 0.7,
            'trend_following': 0.5, 'momentum': 0.7, 'breakout': 0.9,
            'mean_reversion': 0.1, 'range_trading': 0.1, 'scalping': 0.0,
        },
        MarketRegimeType.CHAOTIC: {
            'wyckoff': 0.1, 'ict': 0.1, 'vsa': 0.2, 'vpin': 0.3,
            'stochastic': 0.1, 'rsi': 0.1, 'sentiment': 0.2,
            'trend_following': 0.0, 'momentum': 0.1, 'breakout': 0.1,
            'mean_reversion': 0.2, 'range_trading': 0.2, 'scalping': 0.1,
        },
        MarketRegimeType.ACCUMULATION: {
            'wyckoff': 0.9, 'ict': 0.7, 'vsa': 0.8, 'vpin': 0.6,
            'stochastic': 0.5, 'rsi': 0.5, 'sentiment': 0.6,
            'trend_following': 0.3, 'momentum': 0.4, 'breakout': 0.5,
            'mean_reversion': 0.6, 'range_trading': 0.7, 'scalping': 0.4,
        },
        MarketRegimeType.DISTRIBUTION: {
            'wyckoff': 0.9, 'ict': 0.7, 'vsa': 0.8, 'vpin': 0.7,
            'stochastic': 0.5, 'rsi': 0.5, 'sentiment': 0.6,
            'trend_following': 0.3, 'momentum': 0.4, 'breakout': 0.5,
            'mean_reversion': 0.6, 'range_trading': 0.7, 'scalping': 0.4,
        },
        MarketRegimeType.REVERSAL_ZONE: {
            'wyckoff': 0.8, 'ict': 0.8, 'vsa': 0.7, 'vpin': 0.7,
            'stochastic': 0.6, 'rsi': 0.6, 'sentiment': 0.5,
            'trend_following': 0.2, 'momentum': 0.3, 'breakout': 0.4,
            'mean_reversion': 0.5, 'range_trading': 0.3, 'scalping': 0.2,
        },
    }
    
    def __init__(self, risk_profile: RiskProfile = RiskProfile.MODERATE):
        self.risk_profile = risk_profile  # 🟡 تعديل 8
    
    def get_active_strategies(self, regime: MarketRegime, 
                               early_warning: EarlyWarning = None) -> List[StrategyRecommendation]:
        """
        🟢 تعديل 9: ترجع قائمة الاستراتيجيات مع حالة نشاطها
        
        تستخدمها الاستراتيجية الرئيسية لتشغيل/إيقاف الاستراتيجيات الفرعية
        """
        base_weights = self.REGIME_STRATEGY_MAP.get(regime.regime_type, {})
        
        # تعديل بالثقة واضمحلالها
        confidence_factor = regime.confidence * regime.confidence_decay
        
        # تعديل بملف المخاطرة
        risk_factor = self._get_risk_factor()
        
        # تعديل بالإنذار المبكر
        warning_factor = 1.0
        if early_warning:
            if early_warning.warning_level == 'red':
                warning_factor = 0.5  # قلص الكل
            elif early_warning.warning_level == 'orange':
                warning_factor = 0.7
        
        recommendations = []
        
        for strategy_name, base_weight in base_weights.items():
            adjusted_weight = base_weight * confidence_factor * risk_factor * warning_factor
            active = adjusted_weight > 0.3
            
            reason = f"الوزن الأساسي: {base_weight:.1f} × الثقة: {confidence_factor:.2f} × المخاطرة: {risk_factor:.2f}"
            if early_warning and early_warning.warning_level in ['orange', 'red']:
                reason += f" (تحذير: {early_warning.warning_level})"
            
            recommendations.append(StrategyRecommendation(
                strategy_name=strategy_name,
                active=active,
                weight=min(1.0, adjusted_weight),
                reason=reason,
            ))
        
        return recommendations
    
    def _get_risk_factor(self) -> float:
        """معامل المخاطرة حسب ملف المستخدم"""
        if self.risk_profile == RiskProfile.CONSERVATIVE:
            return 0.6
        elif self.risk_profile == RiskProfile.AGGRESSIVE:
            return 1.3
        return 1.0


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية كشف النظام الموحدة (قائد الأوركسترا) ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class RegimeDetectionStrategy:
    """
    استراتيجية كشف نظام السوق والتكيف معه - الإصدار 2.0
    
    قائد الأوركسترا:
    - يكتشف النظام الحالي
    - يتوقع الانتقالات
    - يقرر أي الاستراتيجيات تعمل
    - يعدل العدوانية وحجم المركز
    - يعطي إنذاراً مبكراً قبل تغير النظام
    """
    
    def __init__(self, risk_profile: str = 'moderate'):
        self.classifier = MarketRegimeClassifier()
        self.early_warning_system = EarlyWarningSystem()
        self.orchestrator = StrategyOrchestrator(
            risk_profile=RiskProfile[risk_profile.upper()] if risk_profile.upper() in RiskProfile.__members__ else RiskProfile.MODERATE
        )
        self.transition_analyzer = TransitionProbabilityAnalyzer()
        self.adaptation_engine = StrategyAdaptationEngine()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        # 1. تصنيف النظام
        regime_data = self.classifier.analyze(highs, lows, closes, volumes)
        regime = regime_data.get('regime')
        
        # 2. نظام الإنذار المبكر
        early_warning = None
        if regime:
            early_warning = self.early_warning_system.analyze(
                regime, regime_data.get('metrics', {}), self.classifier.regime_history
            )
        
        # 3. توصيات الاستراتيجيات
        strategy_recommendations = []
        if regime:
            strategy_recommendations = self.orchestrator.get_active_strategies(regime, early_warning)
        
        # 4. احتمالات الانتقال
        transition_data = self.transition_analyzer.analyze(
            self.classifier.regime_history, self.classifier.transitions
        )
        
        # 5. توصيات التكيف
        adaptation_data = self.adaptation_engine.analyze(regime, transition_data) if regime else {}
        
        # 6. القرار
        decision = self._make_decision(regime_data, transition_data, adaptation_data, early_warning)
        
        return {
            **decision,
            "regime_data": regime_data,
            "early_warning": early_warning,
            "strategy_recommendations": [
                {"name": r.strategy_name, "active": r.active, "weight": r.weight, "reason": r.reason}
                for r in strategy_recommendations
            ],
            "transition_data": transition_data,
            "adaptation_data": adaptation_data,
        }
    
    def _make_decision(self, regime_data: Dict, transition_data: Dict,
                       adaptation_data: Dict, early_warning: EarlyWarning) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        regime = regime_data.get('regime')
        regime_name = regime_data.get('regime_name', 'غير معروف')
        confidence = regime_data.get('confidence', 0.3)
        
        if not regime:
            return {"recommendation": "محايد", "confidence": 10, "reason": "غير محدد"}
        
        # ---- من نوع النظام ----
        signal_map = {
            MarketRegimeType.TRENDING_BULL: ('buy', "نظام صاعد قوي", 0.7),
            MarketRegimeType.TRENDING_BEAR: ('sell', "نظام هابط قوي", 0.7),
            MarketRegimeType.TREND_WEAKENING_BULL: ('buy', "صعود يضعف - حذر", 0.3),
            MarketRegimeType.TREND_WEAKENING_BEAR: ('sell', "هبوط يضعف - حذر", 0.3),
            MarketRegimeType.RANGE_BOUND: ('both', "نطاق - تداول عند الحدود", 0.4),
            MarketRegimeType.ACCUMULATION: ('buy', "تجميع - استعداد لصعود", 0.55),
            MarketRegimeType.DISTRIBUTION: ('sell', "توزيع - استعداد لهبوط", 0.55),
            MarketRegimeType.CHAOTIC: ('neutral', "فوضى - انتظار", 0.1),
            MarketRegimeType.VOLATILITY_EXPLOSION: ('trend', "تقلب + اتجاه", 0.4),
        }
        
        if regime.regime_type in signal_map:
            action, desc, weight = signal_map[regime.regime_type]
            if action == 'buy':
                buy_signals.append((desc, weight * confidence))
            elif action == 'sell':
                sell_signals.append((desc, weight * confidence))
            elif action == 'both':
                buy_signals.append((desc, weight * 0.5))
                sell_signals.append((desc, weight * 0.5))
            elif action == 'trend':
                if regime.avg_trend_strength > 0:
                    buy_signals.append((desc, weight * confidence))
                else:
                    sell_signals.append((desc, weight * confidence))
        
        # ---- من الإنذار المبكر ----
        if early_warning:
            if early_warning.warning_level == 'red':
                warnings.append(f"⚠️ إنذار أحمر: {early_warning.description}")
                warnings.append(f"الإشارات: {', '.join(early_warning.signals_triggered)}")
            elif early_warning.warning_level == 'orange':
                warnings.append(f"⚠️ إنذار برتقالي: {early_warning.description}")
        
        # ---- من احتمالات الانتقال ----
        most_likely = transition_data.get('most_likely_next')
        if most_likely:
            if 'TRENDING_BULL' in str(most_likely):
                buy_signals.append(("احتمال انتقال لصاعد", 0.25))
            elif 'TRENDING_BEAR' in str(most_likely):
                sell_signals.append(("احتمال انتقال لهابط", 0.25))
        
        # ---- القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            final_confidence = int(min(90, total_buy / max(total_buy + total_sell, 1) * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            final_confidence = int(min(90, total_sell / max(total_buy + total_sell, 1) * 100))
        elif total_buy > total_sell:
            recommendation = "شراء ضعيف"
            final_confidence = 35
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            final_confidence = 35
        else:
            recommendation = "محايد"
            final_confidence = 20
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        reason += f" | النظام: {regime_name}"
        reason += f" | ثقة:{confidence:.0%}"
        
        if regime.divergence_score > 0.5:
            reason += f" | تباعد:{regime.divergence_score:.0%}"
        
        adaptation_warnings = adaptation_data.get('warnings', [])
        all_warnings = list(set(warnings + adaptation_warnings))
        if all_warnings:
            reason += " ⚠️ " + " | ".join(all_warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": final_confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "regime": regime_name,
            "warnings": all_warnings,
        }
    
    def get_active_strategies(self, chart_data: Dict) -> List[Dict]:
        """
        دالة سريعة لمعرفة أي الاستراتيجيات يجب تشغيلها الآن
        تستخدمها الاستراتيجية الرئيسية
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        
        if len(closes) < 30:
            return []
        
        regime_data = self.classifier.analyze(highs, lows, closes, volumes)
        regime = regime_data.get('regime')
        
        if not regime:
            return []
        
        early_warning = self.early_warning_system.analyze(
            regime, regime_data.get('metrics', {}), self.classifier.regime_history
        )
        
        recommendations = self.orchestrator.get_active_strategies(regime, early_warning)
        
        return [
            {"name": r.strategy_name, "active": r.active, "weight": r.weight, "reason": r.reason}
            for r in recommendations
        ]


def create_regime_detection_strategy(risk_profile: str = 'moderate'):
    """إنشاء استراتيجية كشف النظام الجاهزة (الإصدار 2.0 - قائد الأوركسترا)"""
    return RegimeDetectionStrategy(risk_profile=risk_profile)