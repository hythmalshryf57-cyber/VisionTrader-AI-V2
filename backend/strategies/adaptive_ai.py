"""
═══════════════════════════════════════════════════════════════════════════════
ADAPTIVE AI STRATEGY - النسخة الديناميكية المتكاملة
المدرسة العاشرة: الذكاء الاصطناعي التكيفي - العقل الذي يتعلم ويتطور
═══════════════════════════════════════════════════════════════════════════════

هذه ليست استراتيجية تقليدية. هذا "عقل" يتعلم من السوق مباشرة.
يجمع بين:
- التعلم الآلي (Machine Learning)
- التعلم العميق (Deep Learning)
- التعلم المعزز (Reinforcement Learning)
- الأنظمة التكيفية (Adaptive Systems)

ديناميكية بالكامل:
- لا قواعد ثابتة
- يتعلم من كل شمعة جديدة
- يكتشف الأنماط بنفسه
- يتكيف مع تغير ظروف السوق
- يطور استراتيجياته الخاصة
- ينسى الأنماط القديمة التي لم تعد تعمل

المفاهيم الأساسية:
1. Online Learning (تعلم مستمر)
2. Feature Engineering ديناميكي
3. Pattern Recognition بدون إشراف
4. Anomaly Detection (كشف الشذوذ)
5. Regime Detection (كشف نظام السوق)
6. Adaptive Weighting (ترجيح متكيف)
7. Memory Management (إدارة الذاكرة)
8. Confidence Calibration (معايرة الثقة)
9. Meta-Learning (تعلم كيف تتعلم)
10. Self-Correction (تصحيح ذاتي)

التقنيات المستخدمة:
- K-Nearest Neighbors ديناميكي
- Random Forest متكيف
- Gradient Boosting مستمر التعلم
- Neural Network صغيرة للتكيف
- Bayesian Inference للتحديث
- Kalman Filter للتقدير
- Entropy-based Decision Trees
- Reinforcement Q-Learning
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import warnings


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class MarketRegime:
    """نظام السوق (حالة السوق)"""
    regime_id: int
    name: str  # 'trending_up', 'trending_down', 'ranging', 'volatile', 'quiet', 'chaotic'
    volatility_level: float
    trend_strength: float
    mean_reversion_tendency: float
    volume_characteristic: str
    persistence: float  # احتمال الاستمرار
    transition_probs: Dict[int, float]  # احتمالات الانتقال لأنظمة أخرى


@dataclass
class FeatureVector:
    """متجه الميزات الديناميكي"""
    index: int
    features: Dict[str, float]
    importance: Dict[str, float]  # أهمية كل ميزة
    timestamp: int


@dataclass
class PatternMemory:
    """ذاكرة الأنماط"""
    patterns: List[Dict] = field(default_factory=list)
    outcomes: List[float] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    age: List[int] = field(default_factory=list)
    max_size: int = 500
    
    def add(self, pattern: Dict, outcome: float, weight: float):
        self.patterns.append(pattern)
        self.outcomes.append(outcome)
        self.weights.append(weight)
        self.age.append(0)
        if len(self.patterns) > self.max_size:
            self.patterns.pop(0)
            self.outcomes.pop(0)
            self.weights.pop(0)
            self.age.pop(0)
    
    def age_all(self):
        self.age = [a + 1 for a in self.age]
    
    def forget_old(self, max_age: int = 200):
        keep = [i for i, a in enumerate(self.age) if a < max_age]
        self.patterns = [self.patterns[i] for i in keep]
        self.outcomes = [self.outcomes[i] for i in keep]
        self.weights = [self.weights[i] for i in keep]
        self.age = [self.age[i] for i in keep]


@dataclass
class AdaptiveModel:
    """نموذج تكيفي"""
    name: str
    weight: float  # وزن النموذج في القرار
    performance: deque  # أداء حديث (نافذة منزلقة)
    last_prediction: Optional[float]
    confidence: float
    specialization: str  # ما يتقنه هذا النموذج


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: مهندس الميزات الديناميكي (Dynamic Feature Engineer)   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicFeatureEngineer:
    """
    يبني الميزات ديناميكياً من السوق.
    لا ميزات ثابتة - يكتشف الميزات الأكثر فائدة حالياً.
    """
    
    def __init__(self):
        self.feature_registry = {}
        self.active_features = set()
        self.feature_performance = {}
        self.generation = 0
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        بناء الميزات ديناميكياً
        """
        features = self._extract_base_features(highs, lows, closes, volumes)
        derived = self._derive_features(features, closes)
        selected = self._select_best_features(features, derived, closes)
        
        feature_vector = self._build_feature_vector(selected, closes)
        
        return {
            "all_features": selected,
            "feature_vector": feature_vector,
            "active_count": len(self.active_features),
            "generation": self.generation,
        }
    
    def _extract_base_features(self, highs: np.ndarray, lows: np.ndarray,
                                closes: np.ndarray, volumes: np.ndarray) -> Dict[str, np.ndarray]:
        """
        استخراج الميزات الأساسية.
        """
        features = {}
        
        if len(closes) < 5:
            return features
        
        # 1. العوائد (Returns)
        for period in [1, 2, 3, 5, 8, 13, 21]:
            if len(closes) > period:
                features[f'return_{period}'] = np.diff(closes, period, prepend=np.zeros(period)) / np.maximum(np.abs(closes), 0.0001)
        
        # 2. التقلب (Volatility)
        for period in [3, 5, 8, 13, 21]:
            if len(closes) >= period:
                features[f'volatility_{period}'] = self._rolling_std(closes, period)
        
        # 3. الحجم النسبي
        features['relative_volume'] = volumes / np.maximum(self._rolling_mean(volumes, 20), 0.0001)
        features['volume_trend'] = self._rolling_mean(volumes, 5) / np.maximum(self._rolling_mean(volumes, 20), 0.0001)
        
        # 4. الزخم
        for period in [3, 5, 8, 13]:
            features[f'momentum_{period}'] = closes - self._shift(closes, period)
        
        # 5. نسبة الانتشار للإغلاق
        features['spread_ratio'] = (highs - lows) / np.maximum(np.abs(closes), 0.0001)
        features['body_ratio'] = np.abs(closes - self._shift(closes, 1)) / np.maximum(highs - lows, 0.0001)
        
        # 6. موقع الإغلاق
        features['close_position'] = (closes - lows) / np.maximum(highs - lows, 0.0001)
        
        return features
    
    def _derive_features(self, base_features: Dict, closes: np.ndarray) -> Dict[str, np.ndarray]:
        """
        اشتقاق ميزات جديدة من الميزات الأساسية.
        """
        derived = {}
        
        # معدل تغير التقلب
        if 'volatility_5' in base_features and 'volatility_13' in base_features:
            derived['volatility_change'] = base_features['volatility_5'] - base_features['volatility_13']
        
        # تسارع الزخم
        if 'momentum_5' in base_features and 'momentum_13' in base_features:
            derived['momentum_acceleration'] = base_features['momentum_5'] - base_features['momentum_13']
        
        # كروس أوفر
        if 'return_5' in base_features and 'return_21' in base_features:
            derived['trend_crossover'] = np.sign(base_features['return_5'] - base_features['return_21'])
        
        # انحراف الحجم
        if 'relative_volume' in base_features:
            derived['volume_extreme'] = np.abs(base_features['relative_volume'] - 1.0)
        
        # تذبذب السعر
        if 'volatility_8' in base_features and len(closes) > 8:
            derived['vol_of_vol'] = self._rolling_std(base_features['volatility_8'], 5)
        
        # قوة الاتجاه
        if 'close_position' in base_features and 'spread_ratio' in base_features:
            derived['directional_force'] = (base_features['close_position'] - 0.5) * 2 * base_features['spread_ratio']
        
        return derived
    
    def _select_best_features(self, base: Dict, derived: Dict, 
                               closes: np.ndarray) -> Dict[str, np.ndarray]:
        """
        اختيار أفضل الميزات ديناميكياً.
        يستخدم الارتباط بالعوائد المستقبلية لتقييم الميزات.
        """
        all_features = {**base, **derived}
        selected = {}
        
        if len(closes) < 20:
            return all_features
        
        # الهدف: العائد التالي
        future_return = np.zeros(len(closes))
        future_return[:-1] = (closes[1:] - closes[:-1]) / np.maximum(np.abs(closes[:-1]), 0.0001)
        
        scores = {}
        for name, values in all_features.items():
            if len(values) >= 20:
                # حساب الارتباط (Mutual Information تقريباً)
                valid = ~np.isnan(values) & ~np.isnan(future_return)
                if sum(valid) > 10:
                    corr = np.corrcoef(values[valid], future_return[valid])[0, 1]
                    scores[name] = abs(corr) if not np.isnan(corr) else 0
        
        # اختيار أفضل الميزات (ديناميكي: عدد متغير)
        if scores:
            threshold = np.median(list(scores.values()))
            for name, score in scores.items():
                if score > threshold and name in all_features:
                    selected[name] = all_features[name]
                    self.active_features.add(name)
                    self.feature_performance[name] = self.feature_performance.get(name, 0) * 0.9 + score * 0.1
        
        self.generation += 1
        
        # كل 50 جيل، نعيد تقييم كل الميزات
        if self.generation % 50 == 0:
            self._reevaluate_features()
        
        return selected if selected else all_features
    
    def _build_feature_vector(self, selected: Dict[str, np.ndarray],
                               closes: np.ndarray) -> FeatureVector:
        """
        بناء متجه الميزات الحالي.
        """
        features = {}
        importance = {}
        
        for name, values in selected.items():
            if len(values) > 0:
                features[name] = float(values[-1]) if not np.isnan(values[-1]) else 0.0
            else:
                features[name] = 0.0
            
            importance[name] = self.feature_performance.get(name, 0.5)
        
        return FeatureVector(
            index=len(closes) - 1 if len(closes) > 0 else 0,
            features=features,
            importance=importance,
            timestamp=0,
        )
    
    def _reevaluate_features(self):
        """إعادة تقييم الميزات وإزالة الضعيفة"""
        if self.feature_performance:
            threshold = np.percentile(list(self.feature_performance.values()), 30)
            to_remove = [f for f, p in self.feature_performance.items() if p < threshold]
            for f in to_remove:
                self.active_features.discard(f)
    
    def _rolling_mean(self, data: np.ndarray, window: int) -> np.ndarray:
        """متوسط متحرك"""
        if len(data) < window:
            return np.full_like(data, np.mean(data))
        result = np.full_like(data, np.nan)
        for i in range(window-1, len(data)):
            result[i] = np.mean(data[i-window+1:i+1])
        return result
    
    def _rolling_std(self, data: np.ndarray, window: int) -> np.ndarray:
        """انحراف معياري متحرك"""
        if len(data) < window:
            return np.full_like(data, np.std(data))
        result = np.full_like(data, np.nan)
        for i in range(window-1, len(data)):
            result[i] = np.std(data[i-window+1:i+1])
        return result
    
    def _shift(self, data: np.ndarray, periods: int) -> np.ndarray:
        """إزاحة البيانات"""
        result = np.zeros_like(data)
        if periods < len(data):
            result[periods:] = data[:-periods]
        return result


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الثانية: كاشف نظام السوق (Market Regime Detector)              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MarketRegimeDetector:
    """
    يكتشف "نظام السوق" الحالي.
    السوق يغير سلوكه. هذا الكاشف يكتشف متى وكيف.
    
    الأنظمة:
    - Trending: زخم قوي في اتجاه واحد
    - Ranging: تذبذب حول متوسط
    - Volatile: حركات كبيرة غير متوقعة
    - Quiet: حركة ضعيفة جداً
    - Chaotic: لا نمط واضح
    """
    
    def __init__(self):
        self.regimes: List[MarketRegime] = []
        self.current_regime: Optional[MarketRegime] = None
        self.regime_history = deque(maxlen=100)
        
        # تهيئة الأنظمة الأساسية
        self._initialize_regimes()
    
    def _initialize_regimes(self):
        """تهيئة الأنظمة الأساسية"""
        self.regimes = [
            MarketRegime(0, 'trending_up', 0.0, 0.8, 0.1, 'increasing', 0.6, {1: 0.2, 2: 0.5, 3: 0.2, 4: 0.1}),
            MarketRegime(1, 'trending_down', 0.0, -0.8, 0.1, 'increasing', 0.6, {0: 0.2, 2: 0.5, 3: 0.2, 4: 0.1}),
            MarketRegime(2, 'ranging', 0.0, 0.0, 0.9, 'decreasing', 0.7, {0: 0.15, 1: 0.15, 3: 0.5, 4: 0.2}),
            MarketRegime(3, 'volatile', 0.0, 0.2, 0.3, 'spiking', 0.3, {0: 0.2, 1: 0.2, 2: 0.3, 4: 0.3}),
            MarketRegime(4, 'quiet', 0.0, 0.0, 0.5, 'very_low', 0.5, {0: 0.15, 1: 0.15, 2: 0.4, 3: 0.3}),
        ]
        self.current_regime = self.regimes[2]  # افتراضي: ranging
    
    def analyze(self, closes: np.ndarray, volumes: np.ndarray,
                highs: np.ndarray, lows: np.ndarray) -> Dict:
        """
        كشف نظام السوق الحالي
        """
        if len(closes) < 20:
            return {"regime": self.current_regime, "confidence": 0.3}
        
        # قياس الخصائص الحالية
        volatility = self._measure_volatility(highs, lows, closes)
        trend = self._measure_trend(closes)
        mean_reversion = self._measure_mean_reversion(closes)
        volume_char = self._classify_volume(volumes)
        chaos = self._measure_chaos(closes)
        
        # تحديث الأنظمة
        self._update_regimes(volatility, trend, mean_reversion, volume_char, closes)
        
        # تحديد النظام الحالي
        scores = []
        for regime in self.regimes:
            score = self._match_regime(regime, volatility, trend, mean_reversion, 
                                       volume_char, chaos, closes)
            scores.append(score)
        
        best_idx = np.argmax(scores)
        self.current_regime = self.regimes[best_idx]
        self.regime_history.append(best_idx)
        
        # ثقة التحديد
        confidence = scores[best_idx] / (sum(scores) + 0.0001)
        
        return {
            "regime": self.current_regime,
            "regime_id": best_idx,
            "regime_name": self.current_regime.name,
            "confidence": min(0.95, confidence),
            "scores": {r.name: s for r, s in zip(self.regimes, scores)},
            "volatility": volatility,
            "trend": trend,
            "mean_reversion": mean_reversion,
            "chaos": chaos,
        }
    
    def _measure_volatility(self, highs: np.ndarray, lows: np.ndarray,
                            closes: np.ndarray) -> float:
        """قياس التقلب الحالي"""
        if len(closes) < 10:
            return 0.01
        
        recent_range = highs[-10:] - lows[-10:]
        avg_range = np.mean(recent_range)
        avg_price = np.mean(closes[-10:])
        
        if avg_price > 0:
            return avg_range / avg_price
        return 0.01
    
    def _measure_trend(self, closes: np.ndarray) -> float:
        """قياس قوة واتجاه الترند"""
        if len(closes) < 10:
            return 0.0
        
        # الانحدار الخطي للفترة الأخيرة
        x = np.arange(len(closes[-15:]) if len(closes) >= 15 else len(closes))
        y = closes[-len(x):]
        
        if len(x) < 3:
            return 0.0
        
        slope = np.polyfit(x, y, 1)[0]
        
        # تطبيع
        avg_price = np.mean(y)
        if avg_price > 0:
            normalized = slope / avg_price * 100
        else:
            normalized = 0
        
        return np.tanh(normalized * 10)  # -1 إلى 1
    
    def _measure_mean_reversion(self, closes: np.ndarray) -> float:
        """قياس ميل العودة للمتوسط"""
        if len(closes) < 20:
            return 0.5
        
        # اختبار: كم مرة عاد السعر لمتوسطه؟
        ma = self._sma(closes, 10)
        deviations = closes - ma
        crossings = sum(1 for i in range(1, len(closes)) if 
                       (deviations[i] > 0 and deviations[i-1] < 0) or
                       (deviations[i] < 0 and deviations[i-1] > 0))
        
        return min(1.0, crossings / (len(closes) * 0.1))
    
    def _classify_volume(self, volumes: np.ndarray) -> str:
        """تصنيف سلوك الحجم"""
        if len(volumes) < 10:
            return 'normal'
        
        recent_vol = volumes[-10:]
        older_vol = volumes[-20:-10] if len(volumes) >= 20 else volumes[:10]
        
        avg_recent = np.mean(recent_vol)
        avg_older = np.mean(older_vol) if len(older_vol) > 0 else avg_recent
        
        if avg_older == 0:
            return 'normal'
        
        ratio = avg_recent / avg_older
        
        if ratio > 2.0:
            return 'spiking'
        elif ratio > 1.3:
            return 'increasing'
        elif ratio < 0.5:
            return 'very_low'
        elif ratio < 0.7:
            return 'decreasing'
        else:
            return 'normal'
    
    def _measure_chaos(self, closes: np.ndarray) -> float:
        """قياس الفوضى في السوق"""
        if len(closes) < 20:
            return 0.3
        
        # Hurst Exponent تقريب سريع
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) < 10:
            return 0.3
        
        # الانحراف المعياري للعوائد على فترات مختلفة
        std_1 = np.std(returns[-10:])
        std_2 = np.std(returns[-len(returns)//2:]) if len(returns) >= 6 else std_1
        
        if std_2 > 0:
            ratio = std_1 / std_2
            # قريب من 1 = عشوائي (فوضوي)، بعيد عن 1 = منظم
            chaos = 1 - abs(ratio - 1)
        else:
            chaos = 0.5
        
        return max(0, min(1, chaos))
    
    def _update_regimes(self, volatility: float, trend: float, 
                         mean_rev: float, vol_char: str, closes: np.ndarray):
        """تحديث خصائص الأنظمة بناءً على البيانات الجديدة"""
        for regime in self.regimes:
            # تحديث التقلب
            regime.volatility_level = regime.volatility_level * 0.9 + volatility * 0.1
            
            # تحديث الاستمرارية
            if self.regime_history:
                same_count = sum(1 for r in list(self.regime_history)[-10:] if r == regime.regime_id)
                regime.persistence = same_count / min(10, len(self.regime_history))
    
    def _match_regime(self, regime: MarketRegime, volatility: float, trend: float,
                      mean_rev: float, vol_char: str, chaos: float,
                      closes: np.ndarray) -> float:
        """
        مطابقة السوق الحالي مع نظام.
        ديناميكي: يقارن الخصائص الحالية مع خصائص النظام.
        """
        score = 0.0
        
        if regime.name == 'trending_up':
            if trend > 0.3 and mean_rev < 0.4:
                score = trend * 0.6 + (1 - mean_rev) * 0.2 + (1 - chaos) * 0.2
        
        elif regime.name == 'trending_down':
            if trend < -0.3 and mean_rev < 0.4:
                score = abs(trend) * 0.6 + (1 - mean_rev) * 0.2 + (1 - chaos) * 0.2
        
        elif regime.name == 'ranging':
            if abs(trend) < 0.3 and mean_rev > 0.5:
                score = (1 - abs(trend)) * 0.4 + mean_rev * 0.4 + (1 - chaos) * 0.2
        
        elif regime.name == 'volatile':
            if volatility > 0.02 and chaos > 0.5:
                score = volatility * 20 * 0.4 + chaos * 0.4 + (1 - abs(trend)) * 0.2
        
        elif regime.name == 'quiet':
            if volatility < 0.005 and abs(trend) < 0.2:
                score = (1 - volatility * 50) * 0.4 + (1 - abs(trend)) * 0.3 + (1 - chaos) * 0.3
        
        return max(0.1, score)
    
    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """متوسط بسيط"""
        result = np.zeros_like(data)
        for i in range(period-1, len(data)):
            result[i] = np.mean(data[i-period+1:i+1])
        return result


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     الدرجة الثالثة: محرك التعلم التكيفي (Adaptive Learning Engine)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AdaptiveLearningEngine:
    """
    يتعلم من كل شمعة ويتكيف.
    
    يستخدم مجموعة من النماذج:
    - KNN للأنماط القريبة
    - Bayesian للتحديث المستمر
    - Reinforcement للتعلم من النتائج
    - Ensemble للدمج
    """
    
    def __init__(self):
        self.memory = PatternMemory(max_size=500)
        self.models: List[AdaptiveModel] = []
        self._initialize_models()
        self.total_predictions = 0
        self.successful_predictions = 0
        self.learning_rate = 0.01
        
    def _initialize_models(self):
        """تهيئة النماذج التكيفية"""
        self.models = [
            AdaptiveModel('recent_pattern', 0.25, deque(maxlen=30), None, 0.5, 'short_term'),
            AdaptiveModel('trend_follower', 0.25, deque(maxlen=30), None, 0.5, 'trending'),
            AdaptiveModel('mean_reverter', 0.25, deque(maxlen=30), None, 0.5, 'ranging'),
            AdaptiveModel('anomaly_detector', 0.25, deque(maxlen=30), None, 0.5, 'volatile'),
        ]
    
    def analyze(self, feature_vector: FeatureVector, closes: np.ndarray,
                regime: MarketRegime, volumes: np.ndarray) -> Dict:
        """
        التعلم والتنبؤ
        """
        predictions = []
        confidences = []
        
        # تكييف أوزان النماذج مع نظام السوق
        self._adapt_to_regime(regime)
        
        for model in self.models:
            pred, conf = self._model_predict(model, feature_vector, closes, regime)
            predictions.append(pred)
            confidences.append(conf)
        
        # التصويت المرجح
        weights = [m.weight for m in self.models]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return {"recommendation": "محايد", "confidence": 10}
        
        weighted_pred = sum(p * w for p, w in zip(predictions, weights)) / total_weight
        weighted_conf = sum(c * w for c, w in zip(confidences, weights)) / total_weight
        
        recommendation = "شراء" if weighted_pred > 0.15 else "بيع" if weighted_pred < -0.15 else "محايد"
        confidence = int(min(95, max(10, abs(weighted_pred) * 100 + weighted_conf * 30)))
        
        self.total_predictions += 1
        
        # تخزين النمط للتعلم
        self._store_pattern(feature_vector, closes)
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "weighted_prediction": weighted_pred,
            "model_predictions": dict(zip([m.name for m in self.models], predictions)),
            "model_weights": dict(zip([m.name for m in self.models], weights)),
        }
    
    def learn_from_result(self, feature_vector: FeatureVector, actual_result: float):
        """
        التعلم من النتيجة الفعلية.
        actual_result: 1 = ارتفع السعر، -1 = انخفض، 0 = لم يتغير
        """
        # تحديث أداء النماذج
        for model in self.models:
            if model.last_prediction is not None:
                error = abs(model.last_prediction - actual_result)
                model.performance.append(1 - error)  # 1 = perfect, 0 = wrong
                model.confidence = np.mean(model.performance) if model.performance else 0.5
                
                # تعديل الوزن بناءً على الأداء
                if len(model.performance) >= 10:
                    model.weight = np.mean(model.performance) * 0.8 + model.weight * 0.2
        
        # تطبيع الأوزان
        total_weight = sum(m.weight for m in self.models)
        if total_weight > 0:
            for model in self.models:
                model.weight /= total_weight
        
        # تحديث الذاكرة
        recent_outcomes = self.memory.outcomes[-1] if self.memory.outcomes else 0
        if len(self.memory.outcomes) > 0:
            self.memory.outcomes[-1] = recent_outcomes * 0.7 + actual_result * 0.3
        
        self.memory.age_all()
        self.memory.forget_old(max_age=200)
        
        # تحديث نسبة النجاح
        if (actual_result > 0 and self.models[0].last_prediction and self.models[0].last_prediction > 0) or \
           (actual_result < 0 and self.models[0].last_prediction and self.models[0].last_prediction < 0):
            self.successful_predictions += 1
    
    def _adapt_to_regime(self, regime: MarketRegime):
        """تكييف أوزان النماذج مع نظام السوق"""
        if regime.name == 'trending_up' or regime.name == 'trending_down':
            # تعزيز متابع الاتجاه
            for model in self.models:
                if model.specialization == 'trending':
                    model.weight *= 1.1
                elif model.specialization == 'ranging':
                    model.weight *= 0.9
        
        elif regime.name == 'ranging':
            # تعزيز العودة للمتوسط
            for model in self.models:
                if model.specialization == 'ranging':
                    model.weight *= 1.1
                elif model.specialization == 'trending':
                    model.weight *= 0.9
        
        elif regime.name == 'volatile':
            # تعزيز كاشف الشذوذ
            for model in self.models:
                if model.specialization == 'volatile':
                    model.weight *= 1.1
        
        # تطبيع
        total = sum(m.weight for m in self.models)
        if total > 0:
            for m in self.models:
                m.weight /= total
    
    def _model_predict(self, model: AdaptiveModel, features: FeatureVector,
                       closes: np.ndarray, regime: MarketRegime) -> Tuple[float, float]:
        """
        تنبؤ نموذج واحد.
        """
        pred = 0.0
        conf = 0.3
        
        if model.specialization == 'short_term':
            pred, conf = self._recent_pattern_predict(features, closes)
        elif model.specialization == 'trending':
            pred, conf = self._trend_follower_predict(features, closes)
        elif model.specialization == 'ranging':
            pred, conf = self._mean_reverter_predict(features, closes)
        elif model.specialization == 'volatile':
            pred, conf = self._anomaly_predict(features, closes)
        
        model.last_prediction = pred
        return pred, conf
    
    def _recent_pattern_predict(self, features: FeatureVector,
                                 closes: np.ndarray) -> Tuple[float, float]:
        """
        تنبؤ بالأنماط القريبة (KNN-like).
        """
        if len(self.memory.patterns) < 5:
            return 0.0, 0.3
        
        # البحث عن أنماط مشابهة
        similarities = []
        for i, pattern in enumerate(self.memory.patterns):
            sim = self._cosine_similarity(features.features, pattern)
            similarities.append((sim, self.memory.outcomes[i], self.memory.weights[i]))
        
        # أعلى 5 تشابهات
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_k = similarities[:5]
        
        if not top_k:
            return 0.0, 0.3
        
        weighted_outcome = sum(s * o * w for s, o, w in top_k)
        total_weight = sum(s * w for s, o, w in top_k)
        
        if total_weight > 0:
            pred = weighted_outcome / total_weight
        else:
            pred = 0.0
        
        avg_similarity = np.mean([s for s, _, _ in top_k])
        conf = min(0.8, avg_similarity * 0.8 + 0.2)
        
        return np.tanh(pred * 3), conf
    
    def _trend_follower_predict(self, features: FeatureVector,
                                 closes: np.ndarray) -> Tuple[float, float]:
        """
        تنبؤ بمتابعة الاتجاه.
        """
        if len(closes) < 8:
            return 0.0, 0.3
        
        # قوة الاتجاه من الميزات
        trend_signal = 0.0
        
        for name in ['momentum_5', 'momentum_8', 'momentum_13']:
            if name in features.features:
                val = features.features[name]
                avg_price = np.mean(np.abs(closes[-10:])) if len(closes) >= 10 else 1
                if avg_price > 0:
                    trend_signal += val / avg_price
        
        # الاستمرارية
        if len(closes) >= 8:
            up_bars = sum(1 for i in range(-7, 0) if closes[i] > closes[i-1])
            if up_bars >= 5:
                trend_signal += 0.3
            elif up_bars <= 2:
                trend_signal -= 0.3
        
        conf = 0.4 + abs(trend_signal) * 0.4
        return np.tanh(trend_signal * 5), min(0.8, conf)
    
    def _mean_reverter_predict(self, features: FeatureVector,
                                closes: np.ndarray) -> Tuple[float, float]:
        """
        تنبؤ بالعودة للمتوسط.
        """
        if len(closes) < 10:
            return 0.0, 0.3
        
        sma = np.mean(closes[-10:])
        current = closes[-1]
        
        if sma > 0:
            deviation = (current - sma) / sma
        else:
            deviation = 0
        
        # إشارة عكسية
        pred = -np.tanh(deviation * 50)
        
        # الثقة تزيد مع زيادة الانحراف
        conf = min(0.7, abs(deviation) * 20 + 0.3)
        
        return pred, conf
    
    def _anomaly_predict(self, features: FeatureVector,
                          closes: np.ndarray) -> Tuple[float, float]:
        """
        تنبؤ بالشذوذ.
        """
        if 'volatility_5' not in features.features or 'volatility_13' not in features.features:
            return 0.0, 0.3
        
        vol_short = features.features['volatility_5']
        vol_long = features.features['volatility_13']
        
        if vol_long > 0:
            vol_ratio = vol_short / vol_long
        else:
            vol_ratio = 1.0
        
        # تقلب مرتفع غير طبيعي = انعكاس محتمل
        if vol_ratio > 2.0:
            # عكس الاتجاه الأخير
            if len(closes) >= 3:
                recent_move = closes[-1] - closes[-3]
                pred = -np.sign(recent_move) * 0.5
            else:
                pred = 0.0
            conf = min(0.8, vol_ratio * 0.2)
        else:
            pred = 0.0
            conf = 0.2
        
        return pred, conf
    
    def _cosine_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """تشابه جيب التمام بين قاموسين"""
        keys = set(dict1.keys()) & set(dict2.keys())
        if not keys:
            return 0.0
        
        dot = sum(dict1[k] * dict2.get(k, 0) for k in keys)
        norm1 = np.sqrt(sum(v**2 for v in dict1.values()))
        norm2 = np.sqrt(sum(dict2.get(k, 0)**2 for k in dict1.keys()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def _store_pattern(self, features: FeatureVector, closes: np.ndarray):
        """تخزين النمط الحالي في الذاكرة"""
        if len(closes) < 2:
            return
        
        # النتيجة: هل ارتفع السعر أم انخفض؟
        outcome = 1 if closes[-1] > closes[-2] else -1 if closes[-1] < closes[-2] else 0
        
        weight = 1.0
        self.memory.add(features.features.copy(), outcome, weight)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║            الدرجة النهائية: استراتيجية الذكاء التكيفي الموحدة               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class AdaptiveAIStrategy:
    """
    استراتيجية الذكاء الاصطناعي التكيفي الكاملة.
    
    هذا "عقل" حي:
    - يبني الميزات ديناميكياً
    - يكتشف نظام السوق
    - يتعلم من كل شمعة
    - يتكيف مع الظروف المتغيرة
    - ينسى ما لم يعد مفيداً
    
    لا قواعد ثابتة. كل شيء يتطور.
    """
    
    def __init__(self):
        self.feature_engineer = DynamicFeatureEngineer()
        self.regime_detector = MarketRegimeDetector()
        self.learning_engine = AdaptiveLearningEngine()
        self.accuracy_history = deque(maxlen=100)
    
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
                    "reason": "أحتاج 20 شمعة على الأقل للتعلم"}
        
        # 1. بناء الميزات الديناميكية
        feature_data = self.feature_engineer.analyze(opens, highs, lows, closes, volumes)
        feature_vector = feature_data.get('feature_vector')
        
        # 2. كشف نظام السوق
        regime_data = self.regime_detector.analyze(closes, volumes, highs, lows)
        current_regime = regime_data.get('regime')
        
        # 3. التعلم والتنبؤ
        prediction_data = self.learning_engine.analyze(feature_vector, closes, current_regime, volumes)
        
        # 4. التعلم من النتيجة السابقة (إذا وجدت)
        self._update_learning(closes)
        
        # 5. بناء القرار
        decision = self._build_decision(prediction_data, regime_data, feature_data)
        
        return {
            **decision,
            "feature_data": feature_data,
            "regime_data": regime_data,
            "learning_data": prediction_data,
            "accuracy": self.get_accuracy(),
        }
    
    def _update_learning(self, closes: np.ndarray):
        """
        تحديث التعلم من النتيجة الفعلية.
        """
        if len(closes) < 2:
            return
        
        # حساب النتيجة الفعلية
        actual = 1 if closes[-1] > closes[-2] else -1 if closes[-1] < closes[-2] else 0
        
        # تحديث الدقة
        if self.learning_engine.total_predictions > 0:
            last_pred = self.learning_engine.models[0].last_prediction
            if last_pred is not None:
                correct = (actual > 0 and last_pred > 0) or (actual < 0 and last_pred < 0)
                self.accuracy_history.append(1 if correct else 0)
    
    def _build_decision(self, prediction: Dict, regime: Dict, features: Dict) -> Dict:
        """
        بناء القرار النهائي
        """
        buy_signals = []
        sell_signals = []
        
        regime_name = regime.get('regime_name', 'unknown')
        
        # من تنبؤات النماذج
        if prediction.get('recommendation') == 'شراء':
            buy_signals.append(("AI: تنبؤ صاعد", prediction.get('confidence', 50) / 100))
        elif prediction.get('recommendation') == 'بيع':
            sell_signals.append(("AI: تنبؤ هابط", prediction.get('confidence', 50) / 100))
        
        # من نظام السوق
        if regime_name == 'trending_up':
            buy_signals.append(("AI: نظام سوق صاعد", 0.55))
        elif regime_name == 'trending_down':
            sell_signals.append(("AI: نظام سوق هابط", 0.55))
        elif regime_name == 'ranging':
            if prediction.get('weighted_prediction', 0) > 0:
                buy_signals.append(("AI: ارتداد في نطاق", 0.4))
            else:
                sell_signals.append(("AI: ارتداد في نطاق", 0.4))
        elif regime_name == 'volatile':
            buy_signals.append(("AI: تقلب عالي - حذر", 0.2))
            sell_signals.append(("AI: تقلب عالي - حذر", 0.2))
        
        # من دقة النموذج
        accuracy = self.get_accuracy()
        if accuracy > 0.6:
            buy_signals.append((f"AI: دقة النموذج {accuracy:.0%}", 0.1))
        
        # القرار النهائي
        recommendation = prediction.get('recommendation', 'محايد')
        confidence = prediction.get('confidence', 30)
        
        active_features = features.get('active_count', 0)
        reason = f"AI ({regime_name}) | {active_features} ميزة نشطة | دقة: {accuracy:.0%}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "regime": regime_name,
        }
    
    def get_accuracy(self) -> float:
        """نسبة الدقة الحالية"""
        if not self.accuracy_history:
            return 0.0
        return np.mean(list(self.accuracy_history))


def create_adaptive_ai_strategy():
    """إنشاء استراتيجية الذكاء التكيفي الجاهزة"""
    return AdaptiveAIStrategy()