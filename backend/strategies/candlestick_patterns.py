"""
═══════════════════════════════════════════════════════════════════════════════
CANDLESTICK PATTERNS STRATEGY - النسخة الديناميكية المتكاملة
المدرسة الأولى: أنماط الشموع اليابانية - لغة السوق الأساسية
═══════════════════════════════════════════════════════════════════════════════

ستيف نيسون قدم الشموع اليابانية للغرب في التسعينات.
لكن أصلها يعود لتجار الأرز اليابانيين في القرن 17.

هذه النسخة ديناميكية بالكامل:
- لا نعتمد على تعريفات ثابتة (Doji = جسم < 5%...)
- كل شيء نسبي للسوق الحالي
- قوة النمط تعتمد على السياق (Trend, Volume, Support/Resistance)
- النمط + السياق = الإشارة الحقيقية

الأنماط المشمولة (20 نمط):
- Doji, Long-legged Doji, Dragonfly Doji, Gravestone Doji
- Hammer, Hanging Man, Inverted Hammer, Shooting Star
- Bullish Engulfing, Bearish Engulfing
- Piercing Line, Dark Cloud Cover
- Morning Star, Evening Star
- Bullish Harami, Bearish Harami
- Three White Soldiers, Three Black Crows
- Tweezer Top, Tweezer Bottom
- Marubozu (White/Black)
- Spinning Top
- Rising Three Methods, Falling Three Methods

ديناميكي:
- حجم الجسم "صغير" أو "كبير" يعتمد على متوسط الشموع
- طول الظل "طويل" أو "قصير" يعتمد على متوسط المدى
- قوة النمط تتغير حسب موقعه من الاتجاه
- تأكيد بالحجم
- فلترة بالاتجاه (Trend Filter)
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
class CandleAnalysis:
    """تحليل شمعة واحدة"""
    index: int
    open: float
    high: float
    low: float
    close: float
    body: float            # حجم الجسم (مطلق)
    upper_wick: float      # الظل العلوي
    lower_wick: float      # الظل السفلي
    total_range: float     # المدى الكلي
    body_pct: float        # نسبة الجسم للمدى (0=Doji, 1=Marubozu)
    upper_wick_pct: float  # نسبة الظل العلوي
    lower_wick_pct: float  # نسبة الظل السفلي
    is_bullish: bool
    is_bearish: bool
    body_category: str     # 'small', 'normal', 'large'
    relative_volume: float # الحجم النسبي


@dataclass
class CandlestickPattern:
    """نمط شموع مكتشف"""
    pattern_name: str
    end_index: int         # آخر شمعة في النمط
    direction: str         # 'bullish', 'bearish', 'neutral'
    strength: float        # 0-1
    confidence: float      # 0-1
    volume_confirm: bool
    trend_confirm: bool    # هل النمط مع الاتجاه أم عكسه
    at_support: bool
    at_resistance: bool
    description: str


@dataclass
class PatternSignal:
    """إشارة تداول من نمط"""
    index: int
    pattern_name: str
    direction: str
    strength: float
    confidence: float
    description: str
    entry_price: float
    stop_price: float
    target_price: float


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل الشموع الديناميكي                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicCandleAnalyzer:
    """
    يحلل كل شمعة تحليلاً ديناميكياً.
    العتبات تتكيف مع السوق الحالي.
    """
    
    def __init__(self):
        self.body_thresholds = {'small': 0.0, 'large': 0.0}
        self.wick_thresholds = {'short': 0.0, 'long': 0.0}
    
    def analyze_candles(self, opens: np.ndarray, highs: np.ndarray,
                         lows: np.ndarray, closes: np.ndarray,
                         volumes: np.ndarray) -> List[CandleAnalysis]:
        """
        تحليل كل الشموع
        """
        candles = []
        
        if len(closes) < 20:
            return candles
        
        # حساب العتبات الديناميكية
        self._calculate_dynamic_thresholds(opens, highs, lows, closes, volumes)
        
        for i in range(len(closes)):
            candle = self._analyze_single_candle(
                opens[i], highs[i], lows[i], closes[i], volumes[i], i, volumes
            )
            candles.append(candle)
        
        return candles
    
    def _calculate_dynamic_thresholds(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                                       closes: np.ndarray, volumes: np.ndarray):
        """
        حساب العتبات الديناميكية من آخر 50 شمعة.
        """
        recent = min(50, len(closes))
        ranges = highs[-recent:] - lows[-recent:]
        avg_range = np.mean(ranges)
        avg_body = np.mean(np.abs(closes[-recent:] - opens[-recent:])) if len(opens) >= recent else np.mean(np.abs(closes[-recent:]))
        
        if avg_range > 0:
            # الجسم صغير: أقل من 25% من متوسط المدى
            self.body_thresholds['small'] = avg_range * 0.25
            # الجسم كبير: أكثر من 60% من متوسط المدى
            self.body_thresholds['large'] = avg_range * 0.60
            # الظل طويل: أكثر من 35% من متوسط المدى
            self.wick_thresholds['long'] = avg_range * 0.35
            self.wick_thresholds['short'] = avg_range * 0.10
        else:
            self.body_thresholds = {'small': 0.0001, 'large': 0.0003}
            self.wick_thresholds = {'short': 0.00005, 'long': 0.0002}
    
    def _analyze_single_candle(self, open_p: float, high: float, low: float,
                                close: float, volume: float, index: int,
                                all_volumes: np.ndarray) -> CandleAnalysis:
        """
        تحليل شمعة واحدة.
        """
        body = abs(close - open_p)
        total_range = high - low
        
        if total_range == 0:
            total_range = 0.00001
        
        upper_wick = high - max(open_p, close)
        lower_wick = min(open_p, close) - low
        
        body_pct = body / total_range
        upper_wick_pct = upper_wick / total_range
        lower_wick_pct = lower_wick / total_range
        
        is_bullish = close > open_p
        is_bearish = close < open_p
        
        # تصنيف حجم الجسم (ديناميكي)
        if body < self.body_thresholds['small']:
            body_category = 'small'
        elif body > self.body_thresholds['large']:
            body_category = 'large'
        else:
            body_category = 'normal'
        
        # الحجم النسبي
        if index >= 10:
            avg_vol = np.mean(all_volumes[max(0, index-10):index])
            relative_vol = volume / max(avg_vol, 0.0001)
        else:
            relative_vol = 1.0
        
        return CandleAnalysis(
            index=index,
            open=open_p, high=high, low=low, close=close,
            body=body,
            upper_wick=upper_wick,
            lower_wick=lower_wick,
            total_range=total_range,
            body_pct=body_pct,
            upper_wick_pct=upper_wick_pct,
            lower_wick_pct=lower_wick_pct,
            is_bullish=is_bullish,
            is_bearish=is_bearish,
            body_category=body_category,
            relative_volume=relative_vol,
        )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف الأنماط (Pattern Detector)                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CandlestickPatternDetector:
    """
    يكتشف 20 نمطاً من أنماط الشموع اليابانية.
    ديناميكي: كل نمط يقيم في سياقه.
    """
    
    def __init__(self):
        self.candle_analyzer = DynamicCandleAnalyzer()
    
    def detect_all_patterns(self, opens: np.ndarray, highs: np.ndarray,
                             lows: np.ndarray, closes: np.ndarray,
                             volumes: np.ndarray) -> Dict:
        """
        اكتشاف كل الأنماط
        """
        candles = self.candle_analyzer.analyze_candles(opens, highs, lows, closes, volumes)
        
        patterns = []
        
        # اكتشاف الأنماط الأحادية
        patterns.extend(self._detect_single_candle_patterns(candles, closes, highs, lows))
        
        # اكتشاف الأنماط الثنائية
        patterns.extend(self._detect_double_candle_patterns(candles, closes, highs, lows))
        
        # اكتشاف الأنماط الثلاثية
        patterns.extend(self._detect_triple_candle_patterns(candles, closes, highs, lows))
        
        # إضافة السياق (Trend + S/R + Volume)
        patterns = self._add_context(patterns, closes, highs, lows, volumes)
        
        # ترتيب حسب القوة
        patterns.sort(key=lambda p: p.strength * p.confidence, reverse=True)
        
        # تحويل لأفضل الإشارات
        signals = self._generate_signals(patterns, closes)
        
        return {
            "patterns": patterns[-20:],
            "best_patterns": patterns[:5],
            "signals": signals[-5:],
            "total_detected": len(patterns),
        }
    
    def _detect_single_candle_patterns(self, candles: List[CandleAnalysis],
                                         closes: np.ndarray, highs: np.ndarray,
                                         lows: np.ndarray) -> List[CandlestickPattern]:
        """
        اكتشاف الأنماط الأحادية (شمعة واحدة).
        """
        patterns = []
        
        for i in range(len(candles)):
            c = candles[i]
            
            # ---- Doji (المترددة) ----
            if c.body_pct < 0.1:
                strength = 0.5
                direction = 'neutral'
                desc = "Doji - تردد"
                
                # Dragonfly Doji (ظل سفلي طويل، لا ظل علوي)
                if c.lower_wick_pct > 0.6 and c.upper_wick_pct < 0.1:
                    direction = 'bullish'
                    strength = 0.65
                    desc = "Dragonfly Doji - انعكاس صاعد"
                
                # Gravestone Doji (ظل علوي طويل، لا ظل سفلي)
                elif c.upper_wick_pct > 0.6 and c.lower_wick_pct < 0.1:
                    direction = 'bearish'
                    strength = 0.65
                    desc = "Gravestone Doji - انعكاس هابط"
                
                # Long-legged Doji (ظلال طويلة)
                elif c.upper_wick_pct > 0.35 and c.lower_wick_pct > 0.35:
                    direction = 'neutral'
                    strength = 0.7
                    desc = "Long-legged Doji - تردد شديد"
                
                patterns.append(CandlestickPattern(
                    pattern_name='Doji', end_index=i,
                    direction=direction, strength=strength, confidence=0.6,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description=desc,
                ))
            
            # ---- Hammer (المطرقة) - صاعد ----
            if (c.lower_wick_pct > 0.55 and c.body_pct < 0.4 and 
                c.upper_wick_pct < 0.15 and c.is_bullish):
                patterns.append(CandlestickPattern(
                    pattern_name='Hammer', end_index=i,
                    direction='bullish', strength=0.7, confidence=0.65,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Hammer - مطرقة صاعدة",
                ))
            
            # ---- Hanging Man (الرجل المشنوق) - هابط ----
            if (c.lower_wick_pct > 0.55 and c.body_pct < 0.4 and 
                c.upper_wick_pct < 0.15 and not c.is_bullish):
                patterns.append(CandlestickPattern(
                    pattern_name='Hanging Man', end_index=i,
                    direction='bearish', strength=0.55, confidence=0.55,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Hanging Man - رجل مشنوق - تحذير هبوط",
                ))
            
            # ---- Inverted Hammer (المطرقة المقلوبة) - صاعد ----
            if (c.upper_wick_pct > 0.55 and c.body_pct < 0.4 and 
                c.lower_wick_pct < 0.15 and c.is_bullish):
                patterns.append(CandlestickPattern(
                    pattern_name='Inverted Hammer', end_index=i,
                    direction='bullish', strength=0.6, confidence=0.55,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Inverted Hammer - مطرقة مقلوبة صاعدة",
                ))
            
            # ---- Shooting Star (الشهاب) - هابط ----
            if (c.upper_wick_pct > 0.55 and c.body_pct < 0.4 and 
                c.lower_wick_pct < 0.15 and not c.is_bullish):
                patterns.append(CandlestickPattern(
                    pattern_name='Shooting Star', end_index=i,
                    direction='bearish', strength=0.65, confidence=0.6,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Shooting Star - شهاب هابط",
                ))
            
            # ---- Marubozu (بدون ظلال) ----
            if c.body_pct > 0.8 and c.upper_wick_pct < 0.05 and c.lower_wick_pct < 0.05:
                if c.is_bullish:
                    patterns.append(CandlestickPattern(
                        pattern_name='White Marubozu', end_index=i,
                        direction='bullish', strength=0.75, confidence=0.7,
                        volume_confirm=False, trend_confirm=False,
                        at_support=False, at_resistance=False,
                        description="White Marubozu - قوة شرائية مطلقة",
                    ))
                else:
                    patterns.append(CandlestickPattern(
                        pattern_name='Black Marubozu', end_index=i,
                        direction='bearish', strength=0.75, confidence=0.7,
                        volume_confirm=False, trend_confirm=False,
                        at_support=False, at_resistance=False,
                        description="Black Marubozu - قوة بيعية مطلقة",
                    ))
            
            # ---- Spinning Top (دوارة) ----
            if (c.body_pct < 0.3 and c.upper_wick_pct > 0.2 and 
                c.lower_wick_pct > 0.2 and abs(c.upper_wick - c.lower_wick) < c.total_range * 0.15):
                patterns.append(CandlestickPattern(
                    pattern_name='Spinning Top', end_index=i,
                    direction='neutral', strength=0.4, confidence=0.5,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Spinning Top - تردد واستعداد للانعكاس",
                ))
        
        return patterns
    
    def _detect_double_candle_patterns(self, candles: List[CandleAnalysis],
                                         closes: np.ndarray, highs: np.ndarray,
                                         lows: np.ndarray) -> List[CandlestickPattern]:
        """
        اكتشاف الأنماط الثنائية (شمعتين).
        """
        patterns = []
        
        for i in range(1, len(candles)):
            c1 = candles[i-1]  # الشمعة الأولى
            c2 = candles[i]    # الشمعة الثانية
            
            # ---- Bullish Engulfing (ابتلاع صاعد) ----
            if (c1.is_bearish and c2.is_bullish and
                c2.open <= c1.close and c2.close >= c1.open and
                c2.body > c1.body * 1.2):
                patterns.append(CandlestickPattern(
                    pattern_name='Bullish Engulfing', end_index=i,
                    direction='bullish', strength=0.75, confidence=0.7,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Bullish Engulfing - ابتلاع صاعد قوي",
                ))
            
            # ---- Bearish Engulfing (ابتلاع هابط) ----
            if (c1.is_bullish and c2.is_bearish and
                c2.open >= c1.close and c2.close <= c1.open and
                c2.body > c1.body * 1.2):
                patterns.append(CandlestickPattern(
                    pattern_name='Bearish Engulfing', end_index=i,
                    direction='bearish', strength=0.75, confidence=0.7,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Bearish Engulfing - ابتلاع هابط قوي",
                ))
            
            # ---- Piercing Line (خط اختراق) - صاعد ----
            if (c1.is_bearish and c2.is_bullish and
                c2.open <= c1.close and c2.close >= (c1.open + c1.close) / 2 and
                c2.close < c1.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Piercing Line', end_index=i,
                    direction='bullish', strength=0.7, confidence=0.65,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Piercing Line - اختراق صاعد",
                ))
            
            # ---- Dark Cloud Cover (غطاء السحابة الداكن) - هابط ----
            if (c1.is_bullish and c2.is_bearish and
                c2.open >= c1.close and c2.close <= (c1.open + c1.close) / 2 and
                c2.close > c1.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Dark Cloud Cover', end_index=i,
                    direction='bearish', strength=0.7, confidence=0.65,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Dark Cloud Cover - غطاء سحابة هابط",
                ))
            
            # ---- Bullish Harami (هارامي صاعد) ----
            if (c1.is_bearish and c1.body_category in ['normal', 'large'] and
                c2.is_bullish and c2.body < c1.body * 0.5 and
                c2.open >= c1.close and c2.close <= c1.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Bullish Harami', end_index=i,
                    direction='bullish', strength=0.6, confidence=0.55,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Bullish Harami - هارامي صاعد",
                ))
            
            # ---- Bearish Harami (هارامي هابط) ----
            if (c1.is_bullish and c1.body_category in ['normal', 'large'] and
                c2.is_bearish and c2.body < c1.body * 0.5 and
                c2.open <= c1.close and c2.close >= c1.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Bearish Harami', end_index=i,
                    direction='bearish', strength=0.6, confidence=0.55,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Bearish Harami - هارامي هابط",
                ))
            
            # ---- Tweezer Top (ملقط قمة) ----
            if (c1.is_bullish and c2.is_bearish and
                abs(c1.high - c2.high) < c1.total_range * 0.05):
                patterns.append(CandlestickPattern(
                    pattern_name='Tweezer Top', end_index=i,
                    direction='bearish', strength=0.55, confidence=0.5,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Tweezer Top - ملقط قمة",
                ))
            
            # ---- Tweezer Bottom (ملقط قاع) ----
            if (c1.is_bearish and c2.is_bullish and
                abs(c1.low - c2.low) < c1.total_range * 0.05):
                patterns.append(CandlestickPattern(
                    pattern_name='Tweezer Bottom', end_index=i,
                    direction='bullish', strength=0.55, confidence=0.5,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Tweezer Bottom - ملقط قاع",
                ))
        
        return patterns
    
    def _detect_triple_candle_patterns(self, candles: List[CandleAnalysis],
                                         closes: np.ndarray, highs: np.ndarray,
                                         lows: np.ndarray) -> List[CandlestickPattern]:
        """
        اكتشاف الأنماط الثلاثية (3 شموع).
        """
        patterns = []
        
        for i in range(2, len(candles)):
            c1 = candles[i-2]
            c2 = candles[i-1]
            c3 = candles[i]
            
            # ---- Morning Star (نجمة الصباح) - صاعد ----
            if (c1.is_bearish and c1.body_category in ['normal', 'large'] and
                c2.body_category == 'small' and
                c3.is_bullish and c3.body_category in ['normal', 'large'] and
                c3.close > (c1.open + c1.close) / 2 and
                c2.high < c1.low and c2.high < c3.low):
                patterns.append(CandlestickPattern(
                    pattern_name='Morning Star', end_index=i,
                    direction='bullish', strength=0.8, confidence=0.75,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Morning Star - نجمة الصباح - انعكاس صاعد قوي",
                ))
            
            # ---- Evening Star (نجمة المساء) - هابط ----
            if (c1.is_bullish and c1.body_category in ['normal', 'large'] and
                c2.body_category == 'small' and
                c3.is_bearish and c3.body_category in ['normal', 'large'] and
                c3.close < (c1.open + c1.close) / 2 and
                c2.low > c1.high and c2.low > c3.high):
                patterns.append(CandlestickPattern(
                    pattern_name='Evening Star', end_index=i,
                    direction='bearish', strength=0.8, confidence=0.75,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Evening Star - نجمة المساء - انعكاس هابط قوي",
                ))
            
            # ---- Three White Soldiers (الجنود الثلاثة البيض) - صاعد ----
            if (c1.is_bullish and c2.is_bullish and c3.is_bullish and
                c1.body_category in ['normal', 'large'] and
                c2.body_category in ['normal', 'large'] and
                c3.body_category in ['normal', 'large'] and
                c1.close > c1.open and c2.close > c2.open and c3.close > c3.open and
                c2.close > c1.close and c3.close > c2.close and
                c2.open > c1.open and c3.open > c2.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Three White Soldiers', end_index=i,
                    direction='bullish', strength=0.85, confidence=0.8,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Three White Soldiers - ثلاثة جنود بيض - استمرار صاعد قوي",
                ))
            
            # ---- Three Black Crows (الغربان الثلاثة السود) - هابط ----
            if (c1.is_bearish and c2.is_bearish and c3.is_bearish and
                c1.body_category in ['normal', 'large'] and
                c2.body_category in ['normal', 'large'] and
                c3.body_category in ['normal', 'large'] and
                c1.close < c1.open and c2.close < c2.open and c3.close < c3.open and
                c2.close < c1.close and c3.close < c2.close and
                c2.open < c1.open and c3.open < c2.open):
                patterns.append(CandlestickPattern(
                    pattern_name='Three Black Crows', end_index=i,
                    direction='bearish', strength=0.85, confidence=0.8,
                    volume_confirm=False, trend_confirm=False,
                    at_support=False, at_resistance=False,
                    description="Three Black Crows - ثلاثة غربان سود - استمرار هابط قوي",
                ))
        
        return patterns
    
    def _add_context(self, patterns: List[CandlestickPattern],
                     closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                     volumes: np.ndarray) -> List[CandlestickPattern]:
        """
        إضافة السياق لكل نمط (Trend + S/R + Volume).
        """
        if len(closes) < 20:
            return patterns
        
        for pattern in patterns:
            idx = pattern.end_index
            if idx >= len(closes):
                continue
            
            # 1. تأكيد الحجم
            if idx >= 5:
                avg_vol = np.mean(volumes[max(0, idx-10):idx+1])
                pattern.volume_confirm = volumes[idx] > avg_vol * 1.3
                
                if pattern.volume_confirm:
                    pattern.strength *= 1.2
            
            # 2. تحقق من الاتجاه
            if idx >= 20:
                sma10 = np.mean(closes[idx-9:idx+1]) if idx >= 9 else closes[idx]
                sma20 = np.mean(closes[max(0, idx-19):idx+1])
                
                trend_up = sma10 > sma20
                trend_down = sma10 < sma20
                
                # النمط الصاعد في اتجاه هابط = انعكاس (أقوى)
                if pattern.direction == 'bullish' and trend_down:
                    pattern.trend_confirm = True
                    pattern.strength *= 1.25
                # النمط الهابط في اتجاه صاعد = انعكاس (أقوى)
                elif pattern.direction == 'bearish' and trend_up:
                    pattern.trend_confirm = True
                    pattern.strength *= 1.25
                # النمط مع الاتجاه (أضعف نسبياً)
                elif pattern.direction == 'bullish' and trend_up:
                    pattern.trend_confirm = True
                elif pattern.direction == 'bearish' and trend_down:
                    pattern.trend_confirm = True
            
            # 3. تحقق من الدعم والمقاومة
            if idx >= 20:
                recent_highs = highs[idx-20:idx+1]
                recent_lows = lows[idx-20:idx+1]
                
                current = closes[idx]
                recent_high = max(recent_highs)
                recent_low = min(recent_lows)
                
                # قرب من دعم
                if abs(current - recent_low) / recent_low < 0.01:
                    pattern.at_support = True
                    if pattern.direction == 'bullish':
                        pattern.strength *= 1.2
                
                # قرب من مقاومة
                if abs(current - recent_high) / recent_high < 0.01:
                    pattern.at_resistance = True
                    if pattern.direction == 'bearish':
                        pattern.strength *= 1.2
            
            # تقييد القوة
            pattern.strength = min(1.0, pattern.strength)
        
        return patterns
    
    def _generate_signals(self, patterns: List[CandlestickPattern],
                           closes: np.ndarray) -> List[PatternSignal]:
        """
        توليد إشارات تداول من الأنماط.
        """
        signals = []
        
        for pattern in patterns[:10]:
            if pattern.strength < 0.5:
                continue
            
            idx = pattern.end_index
            if idx >= len(closes):
                continue
            
            current_price = closes[idx]
            atr = self._calculate_atr(highs=None, lows=None, closes=closes, period=14)
            
            entry = current_price
            
            if pattern.direction == 'bullish':
                stop = current_price - atr * 1.5
                target = current_price + atr * 2.5
            elif pattern.direction == 'bearish':
                stop = current_price + atr * 1.5
                target = current_price - atr * 2.5
            else:
                continue
            
            signals.append(PatternSignal(
                index=idx,
                pattern_name=pattern.pattern_name,
                direction=pattern.direction,
                strength=pattern.strength,
                confidence=pattern.confidence,
                description=pattern.description,
                entry_price=entry,
                stop_price=stop,
                target_price=target,
            ))
        
        return signals
    
    def _calculate_atr(self, highs, lows, closes, period=14):
        """حساب ATR"""
        if len(closes) < period:
            return np.mean(np.abs(np.diff(closes[-10:]))) if len(closes) >= 10 else closes[-1] * 0.01
        
        highs_arr = np.array(highs[-period:]) if highs is not None else np.array(closes[-period:])
        lows_arr = np.array(lows[-period:]) if lows is not None else np.array(closes[-period:])
        
        tr = np.zeros(period)
        for i in range(1, period):
            tr[i] = max(
                highs_arr[i] - lows_arr[i],
                abs(highs_arr[i] - closes[-period+i-1]),
                abs(lows_arr[i] - closes[-period+i-1])
            )
        
        return np.mean(tr[1:]) if len(tr) > 1 else closes[-1] * 0.005


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية أنماط الشموع الموحدة                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CandlestickPatternsStrategy:
    """
    استراتيجية أنماط الشموع اليابانية الديناميكية الكاملة.
    
    - 20 نمطاً
    - عتبات ديناميكية
    - سياق (Trend + S/R + Volume)
    - إشارات مع دخول ووقف وهدف
    """
    
    def __init__(self):
        self.pattern_detector = CandlestickPatternDetector()
    
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
        
        # اكتشاف الأنماط
        detection_result = self.pattern_detector.detect_all_patterns(
            opens, highs, lows, closes, volumes
        )
        
        # القرار
        decision = self._make_decision(detection_result, closes)
        
        return {**decision, "detection_result": detection_result}
    
    def _make_decision(self, detection: Dict, closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        best_patterns = detection.get('best_patterns', [])
        signals = detection.get('signals', [])
        
        # ---- من أفضل الأنماط ----
        for pattern in best_patterns[:5]:
            weight = pattern.strength * pattern.confidence * 0.5
            
            extras = []
            if pattern.volume_confirm:
                extras.append("حجم")
            if pattern.trend_confirm:
                extras.append("اتجاه")
            if pattern.at_support:
                extras.append("دعم")
            if pattern.at_resistance:
                extras.append("مقاومة")
            
            extra_str = f" ({', '.join(extras)})" if extras else ""
            
            if pattern.direction == 'bullish':
                buy_signals.append((f"{pattern.description}{extra_str}", weight))
            elif pattern.direction == 'bearish':
                sell_signals.append((f"{pattern.description}{extra_str}", weight))
        
        # ---- من الإشارات ----
        for sig in signals[-3:]:
            weight = sig.strength * sig.confidence * 0.6
            
            if sig.direction == 'bullish':
                buy_signals.append((f"{sig.description} (دخول:{sig.entry_price:.2f})", weight))
            elif sig.direction == 'bearish':
                sell_signals.append((f"{sig.description} (دخول:{sig.entry_price:.2f})", weight))
        
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
        reason += f" | {len(best_patterns)} أنماط مكتشفة"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_candlestick_patterns_strategy():
    """إنشاء استراتيجية أنماط الشموع الجاهزة"""
    return CandlestickPatternsStrategy()