"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC MEAN REVERSION STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السابعة والعشرون: استراتيجية العودة للمتوسط الديناميكية
═══════════════════════════════════════════════════════════════════════════════

أقدم استراتيجية في التاريخ: "ما ارتفع سينخفض، وما انخفض سيرتفع".
لكن السؤال: متى؟ وكم؟ وأي متوسط؟

هذه النسخة ديناميكية بالكامل:
- المتوسط يتغير مع السوق
- مسافة الارتداد ديناميكية
- نكتشف متى يفشل الارتداد (الاتجاه أقوى من العودة)
- أنواع مختلفة من المتوسطات
- Regime Filter: لا ترتد في اتجاه قوي
- Volume-Weighted Reversion
- Half-Life Target Timing
- Failed Reversion Detection

المفاهيم المتقدمة:
1. Mean Reversion Velocity
2. Half-Life of Mean Reversion (محسن)
3. Ornstein-Uhlenbeck Process
4. Hurst Exponent (محسن - 6 فترات)
5. Z-Score Dynamic Thresholds
6. Kalman Filter Mean
7. Regime-Switching Reversion
8. Volume-Weighted Reversion
9. Failed Reversion / Breakdown Signals
10. Half-Life Target Projection
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class MeanReversionMetrics:
    """مقاييس العودة للمتوسط - محسنة"""
    half_life: int
    hurst_exponent: float
    z_score_current: float
    mean_type: str
    mean_value: float
    mean_slope: float
    reversion_speed: float
    reversion_strength: float
    is_mean_reverting: bool
    confidence: float
    # 🟡 تعديل 7: Half-Life Target
    estimated_bars_to_mean: int = 0
    target_price_at_mean: float = 0.0


@dataclass
class DynamicMean:
    """متوسط ديناميكي - محسن"""
    values: np.ndarray
    upper_band: np.ndarray
    lower_band: np.ndarray
    bandwidth: np.ndarray
    percent_distance: float
    z_score: float
    extreme_level: float
    # 🟡 تعديل 8: مستويات الفشل
    breakdown_upper: float = 0.0
    breakdown_lower: float = 0.0


@dataclass
class ReversionSignal:
    """إشارة عودة للمتوسط - محسنة"""
    index: int
    signal_type: str  # 'extreme', 'reversion', 'breakdown_bullish', 'breakdown_bearish', 'half_life_target'
    direction: str
    entry_price: float
    target_price: float
    stop_price: float
    strength: float
    risk_reward: float
    description: str
    # 🟡 تعديل 6: Volume Confirmation
    volume_confirmed: bool = False
    # 🟡 تعديل 5: Regime Filtered
    regime_filtered: bool = False
    regime_note: str = ""


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل العودة للمتوسط (محسن بالكامل)                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MeanReversionAnalyzer:
    """
    يحلل خصائص العودة للمتوسط.
    
    🔴 تعديل 1-4: إصلاحات تقنية
    🟡 تعديل 5: Regime Filter
    🟡 تعديل 6: Volume-Weighted Reversion
    🟡 تعديل 7: Half-Life Target
    🟡 تعديل 8: Failed Reversion Detection
    """
    
    def __init__(self):
        self.lookback = 100
        self.z_threshold = 2.0
        
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                volumes: np.ndarray, regime_data: Dict = None) -> Dict:
        """تحليل العودة للمتوسط"""
        if len(closes) < 30:
            return {"is_mean_reverting": False, "confidence": 0}
        
        # اختيار أفضل نوع متوسط
        best_mean = self._find_best_mean(closes)
        
        # حساب المقاييس
        metrics = self._calculate_metrics(closes, best_mean)
        
        # بناء المتوسط الديناميكي
        dynamic_mean = self._build_dynamic_mean(closes, best_mean, metrics)
        
        # 🟡 تعديل 5: تحقق من نظام السوق
        regime_ok = self._check_regime_for_mean_reversion(regime_data)
        
        # إشارات
        signals = self._generate_signals(dynamic_mean, closes, metrics, volumes, regime_ok)
        
        return {
            "metrics": metrics,
            "dynamic_mean": dynamic_mean,
            "signals": signals[-5:],
            "is_mean_reverting": metrics.is_mean_reverting,
            "half_life": metrics.half_life,
            "z_score": metrics.z_score_current,
            "regime_ok_for_mr": regime_ok,
        }
    
    def _find_best_mean(self, closes: np.ndarray) -> Dict:
        """إيجاد أفضل نوع متوسط للسوق الحالي"""
        if len(closes) < 50:
            return {"type": "ema", "period": 20, "values": self._ema(closes, 20)}
        
        candidates = []
        
        # SMA
        for period in [10, 20, 30, 50]:
            sma = self._sma(closes, period)
            score = self._score_mean(closes, sma)
            candidates.append({"type": "sma", "period": period, "score": score, "values": sma})
        
        # EMA
        for period in [10, 20, 30, 50]:
            ema = self._ema(closes, period)
            score = self._score_mean(closes, ema)
            candidates.append({"type": "ema", "period": period, "score": score, "values": ema})
        
        # KAMA
        for period in [10, 20, 30]:
            kama = self._kama(closes, period)
            score = self._score_mean(closes, kama)
            candidates.append({"type": "kama", "period": period, "score": score, "values": kama})
        
        # Kalman Filter
        kalman = self._kalman_filter(closes)
        score = self._score_mean(closes, kalman)
        candidates.append({"type": "kalman", "period": 0, "score": score, "values": kalman})
        
        best = max(candidates, key=lambda c: c['score'])
        return best
    
    def _score_mean(self, closes: np.ndarray, mean: np.ndarray) -> float:
        """
        🔴 تعديل 1: تقييم جودة المتوسط بأوزان صحيحة
        
        كان: std_score * 0.0001 (عديم التأثير)
        الآن: أوزان متوازنة
        """
        if len(closes) < 20:
            return 0.0
        
        n = min(50, len(closes), len(mean))
        deviations = closes[-n:] - mean[-n:]
        
        # عدد مرات عبور الصفر (كلما أكثر = أفضل)
        crossings = sum(1 for i in range(1, len(deviations))
                       if (deviations[i] > 0 and deviations[i-1] <= 0) or
                          (deviations[i] < 0 and deviations[i-1] >= 0))
        
        # متوسط وقت العودة (كلما أقل = أفضل)
        if crossings > 0:
            avg_return_time = len(deviations) / crossings
        else:
            avg_return_time = len(deviations)
        
        speed_score = 1.0 / max(avg_return_time, 1.0)
        
        # 🔴 تعديل 1: استقرار الانحرافات (كلما كان الانحراف المعياري أقل = أفضل)
        dev_std = np.std(deviations)
        if dev_std > 0:
            stability_score = 1.0 / (1.0 + dev_std / np.mean(np.abs(closes[-n:])))
        else:
            stability_score = 1.0
        
        # دمج بالوزن الصحيح
        return speed_score * 0.5 + stability_score * 0.5
    
    def _calculate_metrics(self, closes: np.ndarray, best_mean: Dict) -> MeanReversionMetrics:
        """حساب مقاييس العودة للمتوسط"""
        mean_values = best_mean['values']
        deviations = closes - mean_values
        
        # Z-Score الحالي
        recent_dev = deviations[-20:] if len(deviations) >= 20 else deviations
        dev_std = np.std(recent_dev)
        dev_mean = np.mean(recent_dev)
        
        if dev_std > 0:
            z_score = (deviations[-1] - dev_mean) / dev_std
        else:
            z_score = 0.0
        
        # عمر النصف
        half_life = self._estimate_half_life(deviations)
        
        # أس هيرست (محسن)
        hurst = self._estimate_hurst_improved(closes)
        
        # سرعة العودة
        reversion_speed = self._estimate_reversion_speed(deviations)
        
        # هل السوق يعود للمتوسط؟
        is_reverting = hurst < 0.5 and half_life < 20
        
        # ميل المتوسط
        if len(mean_values) >= 5:
            mean_slope = (mean_values[-1] - mean_values[-5]) / 5
        else:
            mean_slope = 0.0
        
        # 🟡 تعديل 7: تقدير وقت الوصول للمتوسط
        estimated_bars = 0
        target_price = mean_values[-1]
        if half_life < 50 and half_life > 0:
            estimated_bars = int(half_life * 0.7)  # 70% من عمر النصف
            target_price = mean_values[-1] + mean_slope * estimated_bars
        
        return MeanReversionMetrics(
            half_life=half_life,
            hurst_exponent=hurst,
            z_score_current=z_score,
            mean_type=best_mean['type'],
            mean_value=mean_values[-1] if len(mean_values) > 0 else 0.0,
            mean_slope=mean_slope,
            reversion_speed=reversion_speed,
            reversion_strength=1.0 - hurst if hurst < 0.5 else 0.0,
            is_mean_reverting=is_reverting,
            confidence=0.7 if is_reverting else 0.3,
            estimated_bars_to_mean=estimated_bars,
            target_price_at_mean=target_price,
        )
    
    def _estimate_half_life(self, deviations: np.ndarray) -> int:
        """
        🔴 تعديل 3: Half-Life محسن باستخدام AR(1) process
        
        الانحدار الذاتي من الدرجة الأولى
        """
        if len(deviations) < 10:
            return 99
        
        # AR(1): y_t = φ * y_{t-1} + ε_t
        y = deviations[1:]
        x = deviations[:-1]
        
        if len(x) < 2:
            return 99
        
        # إزالة القيم المتطرفة
        mask = np.abs(x) < np.std(x) * 3
        if np.sum(mask) >= 5:
            x_clean = x[mask]
            y_clean = y[mask]
        else:
            x_clean = x
            y_clean = y
        
        # الانحدار
        if len(x_clean) >= 2:
            try:
                phi = np.polyfit(x_clean, y_clean, 1)[0]
            except Exception:
                phi = 0.5
        else:
            phi = 0.5
        
        # Half-Life = -ln(2) / ln(φ)
        if 0 < phi < 1:
            half_life = -np.log(2) / np.log(phi)
        elif phi <= 0:
            half_life = 1  # عودة فورية
        else:
            half_life = 99  # لا عودة
        
        return max(1, min(99, int(half_life)))
    
    def _estimate_hurst_improved(self, closes: np.ndarray) -> float:
        """
        🔴 تعديل 4: Hurst Exponent محسن بـ 6 فترات زمنية
        
        كان: 4 فترات فقط (2, 4, 8, 16)
        الآن: 6 فترات (2, 4, 8, 16, 32, 64)
        """
        if len(closes) < 70:
            # بيانات غير كافية لكل الفترات - استخدم الأقل
            return self._estimate_hurst_simple(closes)
        
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) < 64:
            return self._estimate_hurst_simple(closes)
        
        # 6 فترات زمنية
        lags = [2, 4, 8, 16, 32, 64]
        variances = []
        
        for lag in lags:
            if lag < len(returns):
                lagged_returns = returns[lag:] - returns[:-lag]
                variances.append(np.var(lagged_returns))
        
        # نحتاج على الأقل 4 نقاط لانحدار موثوق
        valid_indices = [i for i, v in enumerate(variances) if v > 0]
        if len(valid_indices) < 4:
            return self._estimate_hurst_simple(closes)
        
        log_lags = np.log([lags[i] for i in valid_indices])
        log_vars = np.log([variances[i] for i in valid_indices])
        
        # الانحدار
        hurst = np.polyfit(log_lags, log_vars, 1)[0] / 2.0
        
        return max(0.1, min(0.9, hurst))
    
    def _estimate_hurst_simple(self, closes: np.ndarray) -> float:
        """Hurst بسيط للبيانات القصيرة"""
        if len(closes) < 30:
            return 0.5
        
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) < 10:
            return 0.5
        
        lags = [2, 4, 8]
        variances = []
        
        for lag in lags:
            if lag < len(returns):
                lagged_returns = returns[lag:] - returns[:-lag]
                variances.append(np.var(lagged_returns))
        
        valid = [v for v in variances if v > 0]
        if len(valid) < 2:
            return 0.5
        
        log_lags = np.log(lags[:len(valid)])
        log_vars = np.log(valid)
        
        hurst = np.polyfit(log_lags, log_vars, 1)[0] / 2.0
        
        return max(0.1, min(0.9, hurst))
    
    def _estimate_reversion_speed(self, deviations: np.ndarray) -> float:
        """تقدير سرعة العودة للمتوسط"""
        if len(deviations) < 5:
            return 0.0
        
        max_dev = np.max(np.abs(deviations[-20:])) if len(deviations) >= 20 else 1.0
        current_dev = abs(deviations[-1])
        
        if max_dev > 0:
            return 1.0 - (current_dev / max_dev)
        
        return 0.0
    
    def _build_dynamic_mean(self, closes: np.ndarray, best_mean: Dict,
                            metrics: MeanReversionMetrics) -> DynamicMean:
        """بناء المتوسط الديناميكي مع النطاقات"""
        mean_vals = best_mean['values']
        deviations = closes - mean_vals
        
        # 🔴 تعديل 2: انحراف معياري متحرك آمن
        dynamic_std = self._rolling_std_safe(deviations, min(20, len(closes)))
        
        # عرض النطاق ديناميكي
        bandwidth_mult = 1.5 + metrics.hurst_exponent
        
        upper = mean_vals + dynamic_std * bandwidth_mult
        lower = mean_vals - dynamic_std * bandwidth_mult
        
        # المسافة الحالية
        if mean_vals[-1] > 0 and len(mean_vals) > 0:
            percent_dist = (closes[-1] - mean_vals[-1]) / mean_vals[-1] * 100
        else:
            percent_dist = 0.0
        
        # مستوى التطرف
        extreme_level = 2.0 + (1.0 - metrics.reversion_strength) * 1.5
        
        # 🟡 تعديل 8: مستويات الفشل (Breakdown Levels)
        breakdown_upper = upper[-1] * 1.02 if len(upper) > 0 else closes[-1] * 1.05
        breakdown_lower = lower[-1] * 0.98 if len(lower) > 0 else closes[-1] * 0.95
        
        return DynamicMean(
            values=mean_vals,
            upper_band=upper,
            lower_band=lower,
            bandwidth=upper - lower,
            percent_distance=percent_dist,
            z_score=metrics.z_score_current,
            extreme_level=extreme_level,
            breakdown_upper=breakdown_upper,
            breakdown_lower=breakdown_lower,
        )
    
    def _rolling_std_safe(self, data: np.ndarray, period: int) -> np.ndarray:
        """
        🔴 تعديل 2: انحراف معياري متحرك آمن
        
        كان: القيم الأولى = نفس الانحراف (غير دقيق)
        الآن: حساب تراكمي للقيم الأولى
        """
        n = len(data)
        result = np.full(n, np.nan)
        
        if n < 2:
            return np.full(n, 0.0)
        
        # حساب الانحراف بشكل تراكمي للقيم الأولى
        for i in range(min(period - 1, n)):
            if i >= 1:
                result[i] = np.std(data[:i+1])
            else:
                result[i] = 0.0
        
        # النافذة الكاملة
        for i in range(period - 1, n):
            result[i] = np.std(data[i-period+1:i+1])
        
        # استبدال NaN بقيم معقولة
        result = np.where(np.isnan(result), np.nanmean(result) if not np.all(np.isnan(result)) else 0.0, result)
        
        return result
    
    def _check_regime_for_mean_reversion(self, regime_data: Dict = None) -> Dict:
        """
        🟡 تعديل 5: Regime Filter
        
        لا تتداول ارتداد المتوسط في اتجاه قوي
        """
        if regime_data is None:
            return {"ok_for_mr": True, "note": "لا توجد بيانات نظام"}
        
        try:
            regime = regime_data.get('regime_data', {}).get('regime')
            if regime is None:
                return {"ok_for_mr": True, "note": "نظام غير محدد"}
            
            regime_type = str(regime.regime_type) if hasattr(regime, 'regime_type') else str(regime)
            
            # الأنظمة المناسبة للعودة للمتوسط
            mr_friendly = ['RANGE_BOUND', 'QUIET', 'REVERSAL_ZONE', 'MEAN_REVERSION']
            
            # الأنظمة غير المناسبة
            mr_hostile = ['TRENDING_BULL', 'TRENDING_BEAR', 'VOLATILITY_EXPLOSION', 'CHAOTIC']
            
            for friendly in mr_friendly:
                if friendly in regime_type.upper():
                    return {"ok_for_mr": True, "note": f"نظام مناسب: {regime_type}"}
            
            for hostile in mr_hostile:
                if hostile in regime_type.upper():
                    return {"ok_for_mr": False, "note": f"نظام غير مناسب للارتداد: {regime_type}"}
            
            return {"ok_for_mr": True, "note": f"نظام محايد: {regime_type}"}
            
        except Exception as e:
            logger.debug(f"تعذر فحص النظام: {e}")
            return {"ok_for_mr": True, "note": "خطأ في فحص النظام"}
    
    def _generate_signals(self, dynamic_mean: DynamicMean, closes: np.ndarray,
                          metrics: MeanReversionMetrics, volumes: np.ndarray,
                          regime_ok: Dict) -> List[ReversionSignal]:
        """توليد إشارات العودة للمتوسط"""
        signals = []
        
        idx = len(closes) - 1
        current = closes[-1]
        mean_val = dynamic_mean.values[-1]
        
        regime_note = regime_ok.get('note', '')
        regime_filtered = not regime_ok.get('ok_for_mr', True)
        
        # 🟡 تعديل 6: Volume Confirmation
        avg_vol = np.mean(volumes[-10:]) if len(volumes) >= 10 else volumes[-1]
        long_avg_vol = np.mean(volumes[-30:]) if len(volumes) >= 30 else avg_vol
        vol_ratio = volumes[-1] / long_avg_vol if long_avg_vol > 0 else 1.0
        volume_confirmed = vol_ratio > 1.2
        
        if not metrics.is_mean_reverting:
            # 🟡 تعديل 8: حتى لو السوق لا يعود للمتوسط، قد يكون هناك Breakdown
            if current > dynamic_mean.breakdown_upper:
                signals.append(ReversionSignal(
                    index=idx, signal_type='breakdown_bullish',
                    direction='bullish',
                    entry_price=current,
                    target_price=current * 1.05,
                    stop_price=dynamic_mean.upper_band[-1],
                    strength=0.55,
                    risk_reward=2.0,
                    description="اختراق علوي للنطاق - اتجاه صاعد جديد",
                    volume_confirmed=volume_confirmed,
                    regime_filtered=regime_filtered,
                    regime_note=regime_note,
                ))
            
            if current < dynamic_mean.breakdown_lower:
                signals.append(ReversionSignal(
                    index=idx, signal_type='breakdown_bearish',
                    direction='bearish',
                    entry_price=current,
                    target_price=current * 0.95,
                    stop_price=dynamic_mean.lower_band[-1],
                    strength=0.55,
                    risk_reward=2.0,
                    description="اختراق سفلي للنطاق - اتجاه هابط جديد",
                    volume_confirmed=volume_confirmed,
                    regime_filtered=regime_filtered,
                    regime_note=regime_note,
                ))
            
            return signals
        
        # Z-Score متطرف
        if abs(dynamic_mean.z_score) > dynamic_mean.extreme_level:
            direction = 'bullish' if dynamic_mean.z_score < 0 else 'bearish'
            
            target = mean_val
            stop = current * 0.98 if direction == 'bullish' else current * 1.02
            
            risk = abs(current - stop)
            reward = abs(target - current)
            rr = reward / risk if risk > 0 else 0.0
            
            # 🟡 تعديل 6: تضخيم القوة مع تأكيد الحجم
            base_strength = min(1.0, abs(dynamic_mean.z_score) / 4.0)
            if volume_confirmed:
                base_strength *= 1.3
            
            # 🟡 تعديل 5: تضعيف إذا كان النظام غير مناسب
            if regime_filtered:
                base_strength *= 0.4
            
            signals.append(ReversionSignal(
                index=idx, signal_type='extreme',
                direction=direction,
                entry_price=current, target_price=target, stop_price=stop,
                strength=base_strength, risk_reward=rr,
                description=f"Z-Score متطرف: {dynamic_mean.z_score:.1f} - ارتداد متوقع نحو {target:.4f}",
                volume_confirmed=volume_confirmed,
                regime_filtered=regime_filtered,
                regime_note=regime_note,
            ))
        
        # لمس النطاق
        if current > dynamic_mean.upper_band[-1]:
            strength = 0.6
            if volume_confirmed:
                strength *= 1.2
            if regime_filtered:
                strength *= 0.4
            
            signals.append(ReversionSignal(
                index=idx, signal_type='extreme',
                direction='bearish',
                entry_price=current, target_price=mean_val,
                stop_price=dynamic_mean.upper_band[-1] * 1.01,
                strength=strength,
                risk_reward=abs(current - mean_val) / max(abs(current - dynamic_mean.upper_band[-1] * 1.01), 0.0001),
                description="السعر فوق النطاق العلوي - ارتداد هابط متوقع",
                volume_confirmed=volume_confirmed,
                regime_filtered=regime_filtered,
                regime_note=regime_note,
            ))
        
        if current < dynamic_mean.lower_band[-1]:
            strength = 0.6
            if volume_confirmed:
                strength *= 1.2
            if regime_filtered:
                strength *= 0.4
            
            signals.append(ReversionSignal(
                index=idx, signal_type='extreme',
                direction='bullish',
                entry_price=current, target_price=mean_val,
                stop_price=dynamic_mean.lower_band[-1] * 0.99,
                strength=strength,
                risk_reward=abs(mean_val - current) / max(abs(current - dynamic_mean.lower_band[-1] * 0.99), 0.0001),
                description="السعر تحت النطاق السفلي - ارتداد صاعد متوقع",
                volume_confirmed=volume_confirmed,
                regime_filtered=regime_filtered,
                regime_note=regime_note,
            ))
        
        # 🟡 تعديل 7: Half-Life Target Signal
        if metrics.estimated_bars_to_mean > 0 and metrics.estimated_bars_to_mean <= 5:
            direction = 'bullish' if current < mean_val else 'bearish'
            signals.append(ReversionSignal(
                index=idx, signal_type='half_life_target',
                direction=direction,
                entry_price=current,
                target_price=metrics.target_price_at_mean,
                stop_price=current * 0.97 if direction == 'bullish' else current * 1.03,
                strength=0.45,
                risk_reward=abs(metrics.target_price_at_mean - current) / max(abs(current * 0.03), 0.0001),
                description=f"هدف Half-Life: {metrics.estimated_bars_to_mean} شمعة للمتوسط ({metrics.target_price_at_mean:.4f})",
                volume_confirmed=volume_confirmed,
                regime_filtered=regime_filtered,
                regime_note=regime_note,
            ))
        
        return signals
    
    # ---- دوال المتوسطات ----
    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.full_like(data, np.nan)
        for i in range(period-1, len(data)):
            result[i] = np.mean(data[i-period+1:i+1])
        return result
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        alpha = 2.0 / (period + 1.0)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1.0 - alpha) * result[i-1]
        return result
    
    def _kama(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros_like(data)
        result[period-1] = data[period-1]
        fastest = 2.0 / (2.0 + 1.0)
        slowest = 2.0 / (30.0 + 1.0)
        
        for i in range(period, len(data)):
            direction = abs(data[i] - data[i-period])
            volatility = sum(abs(data[j] - data[j-1]) for j in range(i-period+1, i+1))
            er = direction / volatility if volatility > 0 else 0.0
            sc = (er * (fastest - slowest) + slowest) ** 2
            result[i] = result[i-1] + sc * (data[i] - result[i-1])
        
        return result
    
    def _kalman_filter(self, data: np.ndarray) -> np.ndarray:
        """فلتر كالمان البسيط"""
        n = len(data)
        result = np.zeros(n)
        result[0] = data[0]
        
        q = 0.001
        r = np.var(data) * 0.1 if len(data) > 1 else 0.01
        p = 1.0
        
        for i in range(1, n):
            p = p + q
            k = p / (p + r)
            result[i] = result[i-1] + k * (data[i] - result[i-1])
            p = (1.0 - k) * p
        
        return result


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية العودة للمتوسط الموحدة (محسنة)      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MeanReversionStrategy:
    """
    استراتيجية العودة للمتوسط الديناميكية الكاملة - الإصدار 2.0
    
    - Regime Filter: لا ترتد في اتجاه قوي
    - Volume-Weighted Reversion
    - Half-Life Target Timing
    - Failed Reversion / Breakdown Signals
    """
    
    def __init__(self):
        self.analyzer = MeanReversionAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        regime_data = chart_data.get('regime_data', None)
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        mr_data = self.analyzer.analyze(closes, highs, lows, volumes, regime_data)
        decision = self._make_decision(mr_data, closes)
        
        return {**decision, "mr_data": mr_data}
    
    def _make_decision(self, mr_data: Dict, closes: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        metrics = mr_data.get('metrics')
        signals = mr_data.get('signals', [])
        dynamic_mean = mr_data.get('dynamic_mean')
        regime_ok = mr_data.get('regime_ok_for_mr', {})
        
        # ---- تحذير النظام ----
        if regime_ok and not regime_ok.get('ok_for_mr', True):
            warnings.append(f"⚠️ نظام غير مناسب للارتداد: {regime_ok.get('note', '')}")
        
        # ---- من قابلية العودة للمتوسط ----
        if metrics:
            if not metrics.is_mean_reverting:
                # 🟡 تعديل 8: حتى لو لا يعود للمتوسط، قد يكون هناك Breakdown
                breakdown_signals = [s for s in signals if 'breakdown' in s.signal_type]
                if not breakdown_signals:
                    return {
                        "recommendation": "محايد",
                        "confidence": 20,
                        "reason": f"السوق لا يعود للمتوسط (Hurst: {metrics.hurst_exponent:.2f})",
                        "buy_signals": [], "sell_signals": [], "warnings": warnings,
                    }
            
            if metrics.z_score_current > 2.5:
                sell_signals.append((f"Z-Score مرتفع: {metrics.z_score_current:.1f}", 0.6))
            elif metrics.z_score_current < -2.5:
                buy_signals.append((f"Z-Score منخفض: {metrics.z_score_current:.1f}", 0.6))
            
            # 🟡 تعديل 7: Half-Life Target
            if metrics.estimated_bars_to_mean > 0 and metrics.estimated_bars_to_mean <= 3:
                if metrics.z_score_current < 0:
                    buy_signals.append((f"عودة للمتوسط خلال {metrics.estimated_bars_to_mean} شمعة", 0.5))
                else:
                    sell_signals.append((f"عودة للمتوسط خلال {metrics.estimated_bars_to_mean} شمعة", 0.5))
        
        # ---- من الإشارات ----
        for sig in signals:
            weight = sig.strength * 0.7
            
            # 🟡 تعديل 6: Volume boost
            if sig.volume_confirmed:
                weight *= 1.2
            
            # 🟡 تعديل 5: Regime penalty
            if sig.regime_filtered:
                weight *= 0.5
            
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, weight))
            else:
                sell_signals.append((sig.description, weight))
        
        # ---- من النطاقات ----
        if dynamic_mean:
            if closes[-1] > dynamic_mean.upper_band[-1]:
                sell_signals.append(("فوق النطاق العلوي", 0.5))
            elif closes[-1] < dynamic_mean.lower_band[-1]:
                buy_signals.append(("تحت النطاق السفلي", 0.5))
            
            if dynamic_mean.percent_distance > 3:
                sell_signals.append(("انحراف إيجابي كبير عن المتوسط", 0.55))
            elif dynamic_mean.percent_distance < -3:
                buy_signals.append(("انحراف سلبي كبير عن المتوسط", 0.55))
        
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
        
        if metrics:
            reason += f" | Hurst:{metrics.hurst_exponent:.2f} HL:{metrics.half_life}"
        
        if warnings:
            reason += " ⚠️ " + " | ".join(warnings[:1])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "warnings": warnings,
        }


def create_mean_reversion_strategy():
    """إنشاء استراتيجية العودة للمتوسط الجاهزة (الإصدار 2.0)"""
    return MeanReversionStrategy()