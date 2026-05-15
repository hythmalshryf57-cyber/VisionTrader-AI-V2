"""
═══════════════════════════════════════════════════════════════════════════════
VPIN & TOXICITY STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.1 - نهائي)
المدرسة الثامنة والعشرون: مؤشر VPIN وسمية تدفق الأوامر
═══════════════════════════════════════════════════════════════════════════════

VPIN (Volume-Synchronized Probability of Informed Trading)
يقيس احتمالية وجود متداولين "مطلعين" في السوق.

طوره Easley, López de Prado, O'Hara.
الفكرة: عندما يرتفع VPIN، هناك "سمية" في السوق.
السوق "مسموم" = خطر انعكاس حاد.

هذه النسخة ديناميكية بالكامل - معدلة بـ 15+4 تحسيناً تداولياً:
- حجم الدلو (Bucket Size) يتكيف مع الحجم والزمن
- لا عتبات ثابتة لـ VPIN
- نسبة الشراء/البيع من موقع الإغلاق في الشمعة + BVC
- كشف السمية الصاعدة vs الهابطة
- تحليل شكل منحنى VPIN
- ربط VPIN بالسياق (تقلب، دعم/مقاومة، جلسات)
- Session-Aware VPIN مفعّل بالكامل
- عتبات slope ديناميكية
- دعم/مقاومة مرتبط بـ ATR

المفاهيم المتقدمة:
1. VPIN Calculation مع BVC
2. Volume Bucketing مع حدود زمنية
3. Toxicity Flow (صاعد vs هابط)
4. Informed vs Uninformed Trading
5. Adverse Selection Detection
6. Market Making Risk
7. VPIN + Volatility Adjustment
8. VPIN Crash Prediction (Spike Detection)
9. Dynamic Bucket Size
10. Microstructure Noise
11. Cumulative Delta Analysis
12. VPIN Curve Shape Analysis
13. VPIN Divergence
14. Bucket Memory (مناطق سامة سابقة)
15. Session-Aware VPIN (مفعّل)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class VolumeBucket:
    """دلو حجم - نسخة محسنة"""
    start_idx: int
    end_idx: int
    total_volume: float
    buy_volume: float
    sell_volume: float
    delta: float
    vpin_contribution: float
    price_change: float
    toxicity: float
    duration_bars: int = 0
    buy_ratio_method: str = 'close_position_bvc'
    bucket_price_high: float = 0.0
    bucket_price_low: float = 0.0
    avg_buy_ratio: float = 0.5
    is_forced_close: bool = False
    cumulative_delta: float = 0.0
    adverse_selection_score: float = 0.0
    session: str = 'unknown'  # 🟡 تعديل 15: الجلسة


@dataclass
class VPINResult:
    """نتيجة VPIN - نسخة محسنة"""
    vpin_value: float
    vpin_ma: float
    vpin_std: float
    toxicity_index: float
    bucket_count: int
    dynamic_threshold: float
    is_toxic: bool
    signal: str
    vpin_percentile: float = 0.5
    vpin_trend: str = 'stable'
    vpin_spike: bool = False
    vpin_curve_shape: str = 'flat'
    cumulative_delta: float = 0.0
    toxicity_direction: str = 'neutral'
    vpin_atr_adjusted: float = 0.0
    session_adjusted_threshold: float = 0.0  # 🟡 تعديل 15
    current_session: str = 'unknown'  # 🟡 تعديل 15


@dataclass
class ToxicitySignal:
    """إشارة سمية - نسخة محسنة"""
    index: int
    signal_type: str
    direction: str
    vpin_level: float
    strength: float
    description: str
    is_spike: bool = False
    divergence_type: str = 'none'
    at_support_resistance: bool = False
    volume_confirmation: float = 0.0
    session_aware: bool = False


class VPINToxicityStrategy:
    """
    استراتيجية VPIN وسمية تدفق الأوامر - الإصدار 2.1 (نهائي)
    
    تجمع:
    - حساب VPIN متقدم مع BVC
    - تحليل السمية الصاعدة والهابطة
    - كشف Spike و CDF
    - ربط VPIN بالسياق (تقلب، دعم/مقاومة، جلسات)
    - تحليل شكل المنحنى والتباعدات
    - Session-Aware VPIN مفعّل بالكامل
    - جميع العتبات ديناميكية
    """
    
    def __init__(self):
        self.base_bucket_volume = 0
        self.n_buckets = 50
        self.vpin_lookback = 50
        self.min_bucket_bars = 3
        self.max_bucket_bars = 15
        self.vpin_history = deque(maxlen=200)
        self.bucket_memory = []
        
        # 🟡 تعديل 15: عتبات ديناميكية لكل جلسة
        self.session_thresholds = {
            'asian': {'volatility_factor': 0.7, 'vpin_factor': 1.2},    # آسيا: هادئة، VPIN أخطر
            'european': {'volatility_factor': 1.0, 'vpin_factor': 1.0}, # أوروبا: طبيعي
            'american': {'volatility_factor': 1.3, 'vpin_factor': 0.85}, # أمريكا: متقلبة، VPIN أقل خطورة
            'overlap': {'volatility_factor': 1.2, 'vpin_factor': 0.9},  # تداخل: متوسط
            'unknown': {'volatility_factor': 1.0, 'vpin_factor': 1.0},
        }
        
        # 🟡 تعديل 4: تاريخ slope للعتبات الديناميكية
        self.slope_history = deque(maxlen=100)
        self.avg_historical_slope = 0.005  # قيمة ابتدائية
        
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        timestamps = chart_data.get('timestamps', [])  # 🟡 تعديل 15
        
        if len(closes) < 50:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 50 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # 🟡 تعديل 15: تحديد الجلسة الحالية
        current_session = self._determine_session(timestamps)
        
        # 1. بناء دلاء الحجم
        buckets = self._build_volume_buckets(highs, lows, closes, volumes, opens, timestamps)
        
        # 2. حساب VPIN
        vpin_result = self._calculate_vpin(buckets, current_session)
        
        # 3. تحليل السمية
        toxicity = self._analyze_toxicity(buckets, closes, volumes)
        
        # 4. كشف الأحداث
        events = self._detect_toxic_events(vpin_result, closes, volumes, highs, lows)
        
        # 5. تحديث ذاكرة الدلاء وتاريخ slope
        self._update_bucket_memory(buckets, vpin_result)
        self._update_slope_history(buckets)
        
        # 6. القرار
        decision = self._make_decision(vpin_result, toxicity, events, current_price, 
                                       closes, highs, lows)
        
        return {
            **decision,
            "vpin": vpin_result,
            "toxicity": toxicity,
            "events": events,
            "buckets_count": len(buckets),
            "bucket_memory_zones": self._get_active_memory_zones(current_price),
            "current_session": current_session,
        }
    
    def _determine_session(self, timestamps: List) -> str:
        """
        🟡 تعديل 15: تحديد جلسة التداول من الوقت
        
        يدعم أنواع مختلفة من timestamps
        """
        if not timestamps or len(timestamps) == 0:
            return 'unknown'
        
        last_ts = timestamps[-1]
        
        # محاولة استخراج الساعة
        hour = None
        
        if isinstance(last_ts, (int, float)):
            # Unix timestamp
            import datetime
            dt = datetime.datetime.fromtimestamp(last_ts / 1000 if last_ts > 1e10 else last_ts)
            hour = dt.hour
        elif isinstance(last_ts, str):
            # نص: نحاول parse
            try:
                if 'T' in last_ts:
                    hour = int(last_ts.split('T')[1].split(':')[0])
                elif ' ' in last_ts:
                    hour = int(last_ts.split(' ')[1].split(':')[0])
            except:
                pass
        elif hasattr(last_ts, 'hour'):
            hour = last_ts.hour
        
        if hour is None:
            return 'unknown'
        
        # تصنيف الجلسة (بتوقيت UTC)
        if 0 <= hour < 7:
            return 'asian'      # آسيا (طوكيو، سيدني)
        elif 7 <= hour < 12:
            return 'european'   # أوروبا (لندن، فرانكفورت)
        elif 12 <= hour < 16:
            return 'overlap'    # تداخل أوروبا وأمريكا
        elif 16 <= hour < 22:
            return 'american'   # أمريكا (نيويورك)
        else:
            return 'asian'      # آسيا متأخر
    
    def _build_volume_buckets(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray, volumes: np.ndarray,
                               opens: np.ndarray, timestamps: List = None) -> List[VolumeBucket]:
        """
        بناء دلاء الحجم - نسخة محسنة
        """
        buckets = []
        
        if len(volumes) < 10:
            return buckets
        
        total_vol = sum(volumes)
        self.base_bucket_volume = total_vol / max(self.n_buckets, 1)
        
        bucket_vol = 0
        bucket_start = 0
        bucket_buy_vol = 0
        bucket_sell_vol = 0
        bucket_price_start = closes[0] if len(closes) > 0 else 0
        bucket_bars = 0
        buy_ratios = []
        bucket_high = 0
        bucket_low = float('inf')
        cumulative_delta = 0
        
        for i in range(len(volumes)):
            bar_vol = volumes[i]
            bar_high = highs[i]
            bar_low = lows[i]
            bar_close = closes[i]
            bar_open = opens[i]
            
            buy_ratio = self._calculate_dynamic_buy_ratio(
                bar_open, bar_high, bar_low, bar_close, bar_vol, 
                volumes[i-1] if i > 0 else bar_vol, 
                closes[i-1] if i > 0 else bar_close
            )
            
            bar_buy = bar_vol * buy_ratio
            bar_sell = bar_vol * (1 - buy_ratio)
            
            bucket_vol += bar_vol
            bucket_buy_vol += bar_buy
            bucket_sell_vol += bar_sell
            bucket_bars += 1
            buy_ratios.append(buy_ratio)
            bucket_high = max(bucket_high, bar_high)
            bucket_low = min(bucket_low, bar_low)
            
            if bucket_price_start == 0:
                bucket_price_start = bar_close
            
            bucket_full_by_volume = bucket_vol >= self.base_bucket_volume
            bucket_full_by_time = bucket_bars >= self.max_bucket_bars
            is_forced_close = bucket_full_by_time and not bucket_full_by_volume
            
            if bucket_full_by_volume or (bucket_full_by_time and bucket_bars >= self.min_bucket_bars):
                price_change = bar_close - bucket_price_start if bucket_price_start > 0 else 0
                delta = bucket_buy_vol - bucket_sell_vol
                cumulative_delta += delta
                
                vpin_contrib = abs(delta) / max(bucket_vol, 0.0001)
                
                # 🟡 تعديل 15: تحديد جلسة الدلو
                bucket_session = self._determine_session(
                    [timestamps[bucket_start]] if timestamps and bucket_start < len(timestamps) else []
                )
                
                buckets.append(VolumeBucket(
                    start_idx=bucket_start,
                    end_idx=i,
                    total_volume=bucket_vol,
                    buy_volume=bucket_buy_vol,
                    sell_volume=bucket_sell_vol,
                    delta=delta,
                    vpin_contribution=vpin_contrib,
                    price_change=price_change,
                    toxicity=vpin_contrib * abs(price_change) / max(bar_close, 0.0001),
                    duration_bars=bucket_bars,
                    buy_ratio_method='close_position_bvc',
                    bucket_price_high=bucket_high,
                    bucket_price_low=bucket_low,
                    avg_buy_ratio=np.mean(buy_ratios) if buy_ratios else 0.5,
                    is_forced_close=is_forced_close,
                    cumulative_delta=cumulative_delta,
                    session=bucket_session,
                ))
                
                bucket_vol = 0
                bucket_start = i + 1
                bucket_buy_vol = 0
                bucket_sell_vol = 0
                bucket_bars = 0
                buy_ratios = []
                bucket_price_start = bar_close
                bucket_high = 0
                bucket_low = float('inf')
        
        if bucket_vol > 0 and bucket_start < len(closes) and bucket_bars >= self.min_bucket_bars:
            i = len(closes) - 1
            price_change = closes[i] - bucket_price_start if bucket_price_start > 0 else 0
            delta = bucket_buy_vol - bucket_sell_vol
            cumulative_delta += delta
            vpin_contrib = abs(delta) / max(bucket_vol, 0.0001)
            
            bucket_session = self._determine_session(
                [timestamps[bucket_start]] if timestamps and bucket_start < len(timestamps) else []
            )
            
            buckets.append(VolumeBucket(
                start_idx=bucket_start,
                end_idx=i,
                total_volume=bucket_vol,
                buy_volume=bucket_buy_vol,
                sell_volume=bucket_sell_vol,
                delta=delta,
                vpin_contribution=vpin_contrib,
                price_change=price_change,
                toxicity=vpin_contrib * abs(price_change) / max(closes[i], 0.0001),
                duration_bars=bucket_bars,
                buy_ratio_method='close_position_bvc',
                bucket_price_high=bucket_high if bucket_high > 0 else closes[i],
                bucket_price_low=bucket_low if bucket_low < float('inf') else closes[i],
                avg_buy_ratio=np.mean(buy_ratios) if buy_ratios else 0.5,
                is_forced_close=True,
                cumulative_delta=cumulative_delta,
                session=bucket_session,
            ))
        
        return buckets
    
    def _calculate_dynamic_buy_ratio(self, open_p: float, high: float, low: float,
                                      close: float, volume: float, 
                                      prev_volume: float, prev_close: float) -> float:
        """
        حساب نسبة الشراء ديناميكياً
        تجمع بين: موقع الإغلاق + BVC + تحليل الظلال
        """
        bar_range = high - low
        
        if bar_range == 0:
            return 0.5
        
        # 1. موقع الإغلاق
        close_position = (close - low) / bar_range
        
        # 2. BVC: مقارنة الحجم بالسابق
        if prev_volume > 0:
            volume_ratio = volume / prev_volume
        else:
            volume_ratio = 1.0
        
        price_direction = close - prev_close if prev_close > 0 else close - open_p
        
        if price_direction > 0:
            if volume_ratio > 1.2:
                bvc_buy_ratio = 0.8
            elif volume_ratio > 0.8:
                bvc_buy_ratio = 0.65
            else:
                bvc_buy_ratio = 0.55
        elif price_direction < 0:
            if volume_ratio > 1.2:
                bvc_buy_ratio = 0.2
            elif volume_ratio > 0.8:
                bvc_buy_ratio = 0.35
            else:
                bvc_buy_ratio = 0.45
        else:
            bvc_buy_ratio = 0.5
        
        # 3. المزج
        final_buy_ratio = close_position * 0.5 + bvc_buy_ratio * 0.5
        
        # 4. تعديل الظلال
        upper_wick = high - max(open_p, close)
        lower_wick = min(open_p, close) - low
        
        if upper_wick > bar_range * 0.6:
            final_buy_ratio *= 0.7
        if lower_wick > bar_range * 0.6:
            final_buy_ratio = min(1.0, final_buy_ratio * 1.3)
        
        return max(0.05, min(0.95, final_buy_ratio))
    
    def _calculate_vpin(self, buckets: List[VolumeBucket], current_session: str = 'unknown') -> VPINResult:
        """
        حساب VPIN - نسخة محسنة مع Session-Aware
        """
        if len(buckets) < 5:
            return VPINResult(0.5, 0.5, 0.1, 0, 0, 0.8, False, "لا بيانات")
        
        vpin_window = min(self.vpin_lookback, len(buckets))
        
        recent_buckets = buckets[-vpin_window:]
        vpin = np.mean([b.vpin_contribution for b in recent_buckets])
        
        if len(buckets) >= vpin_window * 2:
            older_buckets = buckets[-vpin_window*2:-vpin_window]
            vpin_ma = np.mean([b.vpin_contribution for b in older_buckets])
        else:
            vpin_ma = vpin
        
        all_vpin = [b.vpin_contribution for b in buckets[-min(100, len(buckets)):]]
        vpin_std = np.std(all_vpin) if len(all_vpin) > 1 else 0.1
        
        # 🟡 تعديل 15: تعديل VPIN حسب الجلسة
        session_config = self.session_thresholds.get(current_session, self.session_thresholds['unknown'])
        vpin_session_adjusted = vpin * session_config['vpin_factor']
        
        # VPIN معدل بالتقلب
        vpin_atr_adjusted = self._calculate_vpin_atr_adjusted(buckets, vpin)
        
        # Percentile
        if len(all_vpin) > 10:
            vpin_percentile = sum(1 for v in all_vpin if v < vpin) / len(all_vpin)
        else:
            vpin_percentile = 0.5
        
        # 🟡 تعديل 15: عتبة ديناميكية معدلة بالجلسة
        base_threshold = vpin_ma + vpin_std * 1.5
        dynamic_threshold = base_threshold * session_config['vpin_factor']
        
        # هل VPIN سام؟
        is_toxic = vpin_session_adjusted > dynamic_threshold or vpin_percentile > 0.85
        
        # مؤشر السمية
        toxicity_index = vpin_session_adjusted / max(dynamic_threshold, 0.0001)
        
        # Spike Detection
        vpin_spike = self._detect_vpin_spike(buckets, vpin, vpin_ma)
        
        # 🟡 تعديل 4: تحليل شكل المنحنى بعتبات ديناميكية
        vpin_curve_shape, vpin_trend = self._analyze_vpin_curve(buckets[-vpin_window:])
        
        # Cumulative Delta
        cumulative_delta = recent_buckets[-1].cumulative_delta if recent_buckets else 0
        
        # اتجاه السمية
        toxicity_direction = self._determine_toxicity_direction(
            vpin, cumulative_delta, recent_buckets
        )
        
        # الإشارة
        if vpin_spike:
            signal = "VPIN Spike - خطر انعكاس عنيف"
        elif is_toxic:
            if toxicity_index > 2.0:
                signal = f"سمية {toxicity_direction} عالية جداً - خطر انعكاس حاد"
            else:
                signal = f"سمية {toxicity_direction} مرتفعة - حذر"
        elif vpin > vpin_ma + vpin_std:
            signal = "سمية متوسطة - مراقبة"
        else:
            signal = "طبيعي"
        
        return VPINResult(
            vpin_value=vpin,
            vpin_ma=vpin_ma,
            vpin_std=vpin_std,
            toxicity_index=toxicity_index,
            bucket_count=len(buckets),
            dynamic_threshold=dynamic_threshold,
            is_toxic=is_toxic,
            signal=signal,
            vpin_percentile=vpin_percentile,
            vpin_trend=vpin_trend,
            vpin_spike=vpin_spike,
            vpin_curve_shape=vpin_curve_shape,
            cumulative_delta=cumulative_delta,
            toxicity_direction=toxicity_direction,
            vpin_atr_adjusted=vpin_atr_adjusted,
            session_adjusted_threshold=session_config['vpin_factor'],
            current_session=current_session,
        )
    
    def _calculate_vpin_atr_adjusted(self, buckets: List[VolumeBucket], vpin: float) -> float:
        """
        🟡 تعديل 2: VPIN معدل بالتقلب - تطبيع باستخدام النسبة المئوية
        
        بدل القسمة على معامل ثابت، نستخدم موقع VPIN في توزيعه
        """
        if len(buckets) < 10:
            return vpin
        
        # حساب متوسط المدى الحقيقي للدلاء
        price_ranges = [abs(b.price_change) for b in buckets[-20:] if abs(b.price_change) > 0]
        
        if not price_ranges:
            return vpin
        
        avg_range = np.mean(price_ranges)
        
        if avg_range > 0:
            # تطبيع VPIN بالتقلب باستخدام min-max normalization
            all_vpin = [b.vpin_contribution for b in buckets[-min(50, len(buckets)):]]
            if len(all_vpin) > 2:
                vpin_min = min(all_vpin)
                vpin_max = max(all_vpin)
                if vpin_max > vpin_min:
                    vpin_normalized = (vpin - vpin_min) / (vpin_max - vpin_min)
                else:
                    vpin_normalized = 0.5
            else:
                vpin_normalized = 0.5
            
            # دمج VPIN المعياري مع التقلب
            vpin_adjusted = vpin_normalized / (1 + avg_range * 50)
        else:
            vpin_adjusted = vpin
        
        return vpin_adjusted
    
    def _detect_vpin_spike(self, buckets: List[VolumeBucket], current_vpin: float, 
                           vpin_ma: float) -> bool:
        """كشف VPIN Spike"""
        if len(buckets) < 6:
            return False
        
        prev_vpins = [b.vpin_contribution for b in buckets[-6:-1]]
        prev_avg = np.mean(prev_vpins) if prev_vpins else vpin_ma
        
        if prev_avg > 0:
            spike_ratio = current_vpin / prev_avg
        else:
            spike_ratio = 1.0
        
        return spike_ratio > 1.5
    
    def _analyze_vpin_curve(self, buckets: List[VolumeBucket]) -> Tuple[str, str]:
        """
        🟡 تعديل 4: تحليل شكل منحنى VPIN بعتبات ديناميكية
        
        العتبات تُحسب من متوسط slope تاريخي
        """
        if len(buckets) < 5:
            return 'flat', 'stable'
        
        vpin_values = [b.vpin_contribution for b in buckets[-10:]]
        
        if len(vpin_values) < 5:
            return 'flat', 'stable'
        
        # حساب الميل
        x = np.arange(len(vpin_values))
        if len(x) > 1:
            slope = np.polyfit(x, vpin_values, 1)[0]
        else:
            slope = 0
        
        # 🟡 تعديل 4: عتبات ديناميكية من التاريخ
        dynamic_threshold = max(0.002, self.avg_historical_slope * 1.5)
        
        # حساب التسارع
        if len(vpin_values) > 3:
            first_half = np.mean(vpin_values[:len(vpin_values)//2])
            second_half = np.mean(vpin_values[len(vpin_values)//2:])
            acceleration = second_half - first_half
        else:
            acceleration = 0
        
        # تحديد الشكل بعتبات ديناميكية
        if slope > dynamic_threshold:
            if acceleration > dynamic_threshold * 10:
                curve_shape = 'accelerating_up'
            else:
                curve_shape = 'gradual_up'
            trend = 'increasing'
        elif slope < -dynamic_threshold:
            curve_shape = 'declining'
            trend = 'decreasing'
        else:
            curve_shape = 'flat'
            trend = 'stable'
        
        # Spike check
        if len(vpin_values) >= 3:
            if vpin_values[-1] > np.mean(vpin_values[:-1]) * 1.4:
                curve_shape = 'spike'
        
        return curve_shape, trend
    
    def _determine_toxicity_direction(self, vpin: float, cumulative_delta: float,
                                       recent_buckets: List[VolumeBucket]) -> str:
        """تحديد اتجاه السمية"""
        if len(recent_buckets) >= 5:
            last_5_delta = sum(b.delta for b in recent_buckets[-5:])
        else:
            last_5_delta = cumulative_delta
        
        last_delta = recent_buckets[-1].delta if recent_buckets else 0
        
        if vpin > 0.4:
            if cumulative_delta > 0 and last_delta > 0:
                return 'bullish'
            elif cumulative_delta < 0 and last_delta < 0:
                return 'bearish'
            else:
                return 'mixed'
        else:
            return 'neutral'
    
    def _analyze_toxicity(self, buckets: List[VolumeBucket], closes: np.ndarray,
                           volumes: np.ndarray) -> Dict:
        """تحليل شامل للسمية"""
        if len(buckets) < 10:
            return {"level": "low", "direction": "neutral"}
        
        recent = buckets[-10:]
        
        avg_toxicity = np.mean([b.toxicity for b in recent])
        
        first_half = np.mean([b.toxicity for b in recent[:5]])
        second_half = np.mean([b.toxicity for b in recent[5:]])
        
        if second_half > first_half * 1.3:
            trend = "increasing"
        elif second_half < first_half * 0.7:
            trend = "decreasing"
        else:
            trend = "stable"
        
        cumulative_delta = recent[-1].cumulative_delta if recent else 0
        delta_trend = 'positive' if cumulative_delta > 0 else 'negative'
        
        adverse_selection = self._detect_adverse_selection(recent)
        
        toxic_threshold = np.mean([b.toxicity for b in buckets[-30:]]) * 1.5 if len(buckets) >= 30 else 0.1
        toxic_buckets = [b for b in recent if b.toxicity > toxic_threshold]
        
        if len(toxic_buckets) >= 3 or adverse_selection:
            level = "high"
            if cumulative_delta > 0:
                direction = 'bullish'
            elif cumulative_delta < 0:
                direction = 'bearish'
            else:
                direction = 'neutral'
        elif len(toxic_buckets) >= 1:
            level = "medium"
            direction = 'neutral'
        else:
            level = "low"
            direction = 'neutral'
        
        return {
            "level": level,
            "direction": direction,
            "avg_toxicity": avg_toxicity,
            "trend": trend,
            "toxic_buckets_count": len(toxic_buckets),
            "cumulative_delta": cumulative_delta,
            "delta_trend": delta_trend,
            "adverse_selection": adverse_selection,
        }
    
    def _detect_adverse_selection(self, recent_buckets: List[VolumeBucket]) -> bool:
        """كشف Adverse Selection"""
        if len(recent_buckets) < 3:
            return False
        
        vpins = [b.vpin_contribution for b in recent_buckets]
        if len(vpins) < 3:
            return False
        
        vpin_rising = vpins[-1] > np.mean(vpins[:-1])
        
        price_changes = [b.price_change for b in recent_buckets]
        all_same_direction = all(pc > 0 for pc in price_changes[-3:]) or \
                            all(pc < 0 for pc in price_changes[-3:])
        
        total_price_move = sum(abs(pc) for pc in price_changes[-3:])
        avg_move = np.mean([abs(pc) for pc in price_changes]) if price_changes else 0
        
        strong_move = total_price_move > avg_move * 2
        
        return vpin_rising and all_same_direction and strong_move
    
    def _detect_toxic_events(self, vpin: VPINResult, closes: np.ndarray,
                              volumes: np.ndarray, highs: np.ndarray,
                              lows: np.ndarray) -> List[ToxicitySignal]:
        """كشف أحداث سمية"""
        events = []
        
        idx = len(closes) - 1
        
        # VPIN Spike
        if vpin.vpin_spike:
            direction = vpin.toxicity_direction
            events.append(ToxicitySignal(
                index=idx,
                signal_type='toxic_spike',
                direction='bearish' if direction == 'bearish' else 'bullish' if direction == 'bullish' else 'neutral',
                vpin_level=vpin.vpin_value,
                strength=0.9,
                description=f"VPIN Spike: قفزة حادة إلى {vpin.vpin_value:.3f} - انعكاس وشيك",
                is_spike=True,
            ))
        
        # VPIN مرتفع جداً
        if vpin.toxicity_index > 2.0:
            events.append(ToxicitySignal(
                index=idx,
                signal_type='toxic_spike',
                direction='bearish' if vpin.toxicity_direction == 'bearish' else 'bullish',
                vpin_level=vpin.vpin_value,
                strength=min(1.0, vpin.toxicity_index / 3),
                description=f"سمية {vpin.toxicity_direction} عالية: VPIN={vpin.vpin_value:.3f} - انعكاس وشيك",
            ))
        
        # VPIN يتزايد
        if vpin.vpin_value > vpin.vpin_ma + vpin.vpin_std:
            events.append(ToxicitySignal(
                index=idx,
                signal_type='increasing_toxicity',
                direction='neutral',
                vpin_level=vpin.vpin_value,
                strength=0.5,
                description=f"VPIN فوق المتوسط: {vpin.vpin_value:.3f} > {vpin.vpin_ma:.3f}",
            ))
        
        # VPIN مع حجم تأكيد
        if len(volumes) > 10:
            avg_vol = np.mean(volumes[-10:])
            current_vol = volumes[-1] if len(volumes) > 0 else avg_vol
            vol_confirmation = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            if vpin.is_toxic and vol_confirmation > 1.5:
                events.append(ToxicitySignal(
                    index=idx,
                    signal_type='toxic_with_volume',
                    direction=vpin.toxicity_direction,
                    vpin_level=vpin.vpin_value,
                    strength=0.7 * min(vol_confirmation / 2, 1.0),
                    description=f"VPIN سام + حجم مرتفع (×{vol_confirmation:.1f})",
                    volume_confirmation=vol_confirmation,
                ))
        
        # 🟡 تعديل 3: VPIN عند دعم/مقاومة (مرتبط بـ ATR)
        if len(highs) > 20:
            atr = self._calculate_atr(highs, lows, closes)
            at_sr = self._check_support_resistance(highs, lows, closes, atr)
            if at_sr and vpin.is_toxic:
                events.append(ToxicitySignal(
                    index=idx,
                    signal_type='toxic_at_sr',
                    direction=vpin.toxicity_direction,
                    vpin_level=vpin.vpin_value,
                    strength=0.75,
                    description=f"VPIN سام عند مستوى دعم/مقاومة رئيسي",
                    at_support_resistance=True,
                ))
        
        # VPIN Divergence
        divergence = self._detect_vpin_divergence(vpin, closes)
        if divergence != 'none':
            events.append(ToxicitySignal(
                index=idx,
                signal_type='vpin_divergence',
                direction='bearish' if divergence == 'bearish_divergence' else 'bullish',
                vpin_level=vpin.vpin_value,
                strength=0.65,
                description=f"تباعد VPIN: {divergence}",
                divergence_type=divergence,
            ))
        
        # VPIN منخفض
        if vpin.vpin_value < vpin.vpin_ma - vpin.vpin_std:
            events.append(ToxicitySignal(
                index=idx,
                signal_type='low_toxicity',
                direction='bullish',
                vpin_level=vpin.vpin_value,
                strength=0.4,
                description=f"VPIN منخفض: {vpin.vpin_value:.3f} - سوق صحي",
            ))
        
        # 🟡 تعديل 15: Session-Aware
        if vpin.current_session != 'unknown' and vpin.is_toxic:
            session_factor = self.session_thresholds.get(vpin.current_session, {}).get('vpin_factor', 1.0)
            if session_factor > 1.0:
                events.append(ToxicitySignal(
                    index=idx,
                    signal_type='session_toxic',
                    direction=vpin.toxicity_direction,
                    vpin_level=vpin.vpin_value,
                    strength=0.5 * session_factor,
                    description=f"VPIN سام في جلسة {vpin.current_session} (خطورة ×{session_factor:.1f})",
                    session_aware=True,
                ))
        
        # تحذير من شكل المنحنى
        if vpin.vpin_curve_shape == 'accelerating_up':
            events.append(ToxicitySignal(
                index=idx,
                signal_type='curve_warning',
                direction='bearish',
                vpin_level=vpin.vpin_value,
                strength=0.55,
                description=f"منحنى VPIN يتسارع صعوداً - تصحيح قريب",
            ))
        elif vpin.vpin_curve_shape == 'spike':
            events.append(ToxicitySignal(
                index=idx,
                signal_type='curve_spike',
                direction='neutral',
                vpin_level=vpin.vpin_value,
                strength=0.6,
                description=f"قفزة في منحنى VPIN - حدث سيولة",
            ))
        
        return events
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """حساب ATR"""
        if len(closes) < period:
            return np.mean(highs - lows)
        
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
        
        return np.mean(tr[-period:])
    
    def _check_support_resistance(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, atr: float) -> bool:
        """
        🟡 تعديل 3: فحص دعم/مقاومة باستخدام ATR بدل نسبة 1% ثابتة
        
        النسبة تتكيف مع تقلب السوق
        """
        if len(closes) < 50 or atr == 0:
            return False
        
        current = closes[-1]
        
        # البحث عن قمم وقيعان
        peaks = []
        valleys = []
        
        for i in range(5, len(closes) - 5):
            if all(highs[i] >= highs[i-j] for j in range(1, 6)) and \
               all(highs[i] >= highs[i+j] for j in range(1, 6)):
                peaks.append(highs[i])
            if all(lows[i] <= lows[i-j] for j in range(1, 6)) and \
               all(lows[i] <= lows[i+j] for j in range(1, 6)):
                valleys.append(lows[i])
        
        # 🟡 تعديل 3: استخدام ATR للمسافة
        # القرب من المستوى = نصف ATR
        proximity_threshold = atr * 0.5
        
        for peak in peaks[-5:]:
            if abs(current - peak) < proximity_threshold:
                return True
        
        for valley in valleys[-5:]:
            if abs(current - valley) < proximity_threshold:
                return True
        
        return False
    
    def _detect_vpin_divergence(self, vpin: VPINResult, closes: np.ndarray) -> str:
        """كشف تباعد VPIN"""
        if len(closes) < 20:
            return 'none'
        
        price_start = closes[-10] if len(closes) >= 10 else closes[0]
        price_end = closes[-1]
        price_trend = 'up' if price_end > price_start else 'down'
        
        vpin_trend = vpin.vpin_trend
        
        if price_trend == 'up' and vpin_trend == 'increasing':
            return 'bearish_divergence'
        
        if price_trend == 'down' and vpin_trend == 'decreasing':
            return 'bullish_divergence'
        
        return 'none'
    
    def _update_bucket_memory(self, buckets: List[VolumeBucket], vpin: VPINResult):
        """تحديث ذاكرة الدلاء السامة"""
        if not buckets:
            return
        
        last_bucket = buckets[-1]
        
        if vpin.is_toxic or last_bucket.vpin_contribution > vpin.dynamic_threshold:
            self.bucket_memory.append({
                'price_high': last_bucket.bucket_price_high,
                'price_low': last_bucket.bucket_price_low,
                'mid_price': (last_bucket.bucket_price_high + last_bucket.bucket_price_low) / 2,
                'vpin': last_bucket.vpin_contribution,
                'index': last_bucket.end_idx,
                'is_active': True,
                'session': last_bucket.session,
            })
        
        if len(self.bucket_memory) > 20:
            self.bucket_memory = self.bucket_memory[-20:]
    
    def _update_slope_history(self, buckets: List[VolumeBucket]):
        """
        🟡 تعديل 4: تحديث تاريخ slope لحساب العتبات الديناميكية
        """
        if len(buckets) < 10:
            return
        
        vpin_values = [b.vpin_contribution for b in buckets[-10:]]
        if len(vpin_values) >= 5:
            x = np.arange(len(vpin_values))
            slope = np.polyfit(x, vpin_values, 1)[0]
            self.slope_history.append(abs(slope))
            
            # تحديث المتوسط التاريخي
            if len(self.slope_history) > 0:
                self.avg_historical_slope = np.mean(list(self.slope_history))
    
    def _get_active_memory_zones(self, current_price: float) -> List[Dict]:
        """الحصول على مناطق الدلاء السامة القريبة"""
        active_zones = []
        
        for mem in self.bucket_memory:
            if abs(current_price - mem['mid_price']) / current_price < 0.02:
                active_zones.append(mem)
        
        return active_zones
    
    def _make_decision(self, vpin: VPINResult, toxicity: Dict,
                       events: List[ToxicitySignal], current_price: float,
                       closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        
        # ---- من VPIN ----
        if vpin.vpin_spike:
            if vpin.toxicity_direction == 'bearish':
                sell_signals.append((f"VPIN Spike هابط ({vpin.vpin_value:.3f})", 0.85))
            elif vpin.toxicity_direction == 'bullish':
                buy_signals.append((f"VPIN Spike صاعد ({vpin.vpin_value:.3f})", 0.85))
            else:
                sell_signals.append((f"VPIN Spike ({vpin.vpin_value:.3f})", 0.75))
        elif vpin.is_toxic:
            if vpin.toxicity_direction == 'bearish':
                sell_signals.append((f"VPIN سام هابط ({vpin.vpin_value:.3f})", 0.65))
            elif vpin.toxicity_direction == 'bullish':
                buy_signals.append((f"VPIN سام صاعد ({vpin.vpin_value:.3f})", 0.65))
            else:
                if vpin.toxicity_index > 2.0:
                    sell_signals.append((f"VPIN سام جداً ({vpin.vpin_value:.3f})", 0.7))
                else:
                    sell_signals.append((f"VPIN مرتفع ({vpin.vpin_value:.3f})", 0.5))
        elif vpin.vpin_value < vpin.vpin_ma * 0.7:
            buy_signals.append((f"VPIN منخفض ({vpin.vpin_value:.3f})", 0.4))
        
        # ---- من Percentile ----
        if vpin.vpin_percentile > 0.9:
            sell_signals.append((f"VPIN في أعلى 10% تاريخياً", 0.6))
        elif vpin.vpin_percentile < 0.2:
            buy_signals.append((f"VPIN في أدنى 20% تاريخياً", 0.35))
        
        # ---- من منحنى VPIN ----
        if vpin.vpin_curve_shape == 'accelerating_up':
            sell_signals.append(("منحنى VPIN يتسارع صعوداً", 0.5))
        elif vpin.vpin_curve_shape == 'spike':
            sell_signals.append(("قفزة في منحنى VPIN", 0.6))
        elif vpin.vpin_curve_shape == 'declining':
            buy_signals.append(("منحنى VPIN يهبط - تعافي", 0.35))
        
        # ---- من الجلسة ----
        if vpin.current_session != 'unknown' and vpin.is_toxic:
            session_factor = self.session_thresholds.get(vpin.current_session, {}).get('vpin_factor', 1.0)
            if session_factor > 1.0:
                sell_signals.append((f"VPIN سام في جلسة {vpin.current_session} (خطر مضاعف)", 0.55))
        
        # ---- من السمية ----
        if toxicity.get('level') == 'high':
            if toxicity.get('direction') == 'bearish':
                sell_signals.append(("تدفق سام هابط", 0.6))
            elif toxicity.get('direction') == 'bullish':
                buy_signals.append(("تدفق سام صاعد", 0.5))
        
        if toxicity.get('trend') == 'increasing':
            sell_signals.append(("السمية تتزايد", 0.45))
        elif toxicity.get('trend') == 'decreasing':
            buy_signals.append(("السمية تتناقص", 0.35))
        
        # ---- من Adverse Selection ----
        if toxicity.get('adverse_selection'):
            sell_signals.append(("Adverse Selection نشط - خطر", 0.7))
        
        # ---- من Cumulative Delta ----
        if toxicity.get('cumulative_delta', 0) > 0 and vpin.is_toxic:
            buy_signals.append(("دلتا تراكمية موجبة + VPIN عالي = تجميع", 0.55))
        elif toxicity.get('cumulative_delta', 0) < 0 and vpin.is_toxic:
            sell_signals.append(("دلتا تراكمية سالبة + VPIN عالي = توزيع", 0.55))
        
        # ---- من الأحداث ----
        for event in events:
            if event.signal_type == 'toxic_spike':
                if event.direction == 'bearish':
                    sell_signals.append((event.description, event.strength * 0.9))
                elif event.direction == 'bullish':
                    buy_signals.append((event.description, event.strength * 0.9))
                else:
                    sell_signals.append((event.description, event.strength * 0.8))
            elif event.signal_type == 'toxic_at_sr':
                if event.direction == 'bearish':
                    sell_signals.append((event.description, event.strength * 0.85))
                else:
                    buy_signals.append((event.description, event.strength * 0.85))
            elif event.signal_type == 'vpin_divergence':
                if event.divergence_type == 'bearish_divergence':
                    sell_signals.append((event.description, 0.65))
                else:
                    buy_signals.append((event.description, 0.65))
            elif event.signal_type == 'toxic_with_volume':
                sell_signals.append((event.description, event.strength))
            elif event.signal_type == 'session_toxic':
                sell_signals.append((event.description, event.strength))
            elif event.signal_type == 'low_toxicity':
                buy_signals.append((event.description, event.strength * 0.6))
            elif event.signal_type == 'curve_warning':
                sell_signals.append((event.description, event.strength))
        
        # ذاكرة الدلاء
        active_memory = self._get_active_memory_zones(current_price)
        if active_memory:
            avg_vpin_memory = np.mean([m['vpin'] for m in active_memory])
            if avg_vpin_memory > vpin.vpin_ma:
                sell_signals.append((f"عودة لمنطقة سامة سابقة (ذاكرة {len(active_memory)} دلو)", 0.5))
        
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
            confidence = 40 + int(min(40, (total_buy - total_sell) * 15))
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 40 + int(min(40, (total_sell - total_buy) * 15))
        else:
            recommendation = "محايد"
            confidence = 25
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        reason += f" | VPIN:{vpin.vpin_value:.3f} | Pctl:{vpin.vpin_percentile:.0%}"
        if vpin.vpin_spike:
            reason += " | ⚡SPIKE"
        if vpin.toxicity_direction != 'neutral':
            reason += f" | Dir:{vpin.toxicity_direction}"
        if vpin.current_session != 'unknown':
            reason += f" | Sess:{vpin.current_session}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_vpin_toxicity_strategy():
    """إنشاء استراتيجية VPIN الجاهزة (الإصدار 2.1 النهائي)"""
    return VPINToxicityStrategy()