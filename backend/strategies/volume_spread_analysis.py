"""
═══════════════════════════════════════════════════════════════════════════════
VOLUME SPREAD ANALYSIS (VSA) - النسخة الديناميكية المتكاملة
المدرسة السادسة: تحليل الحجم والانتشار - بصمات المال الذكي
═══════════════════════════════════════════════════════════════════════════════

ريتشارد وايكوف (مرة أخرى) وتوم ويليامز طوروا VSA.
الفكرة: الحجم يكشف نوايا المؤسسات. السعر بدون حجم = نصف الحقيقة.

هذه النسخة ديناميكية بالكامل:
- لا عتبات ثابتة للحجم المرتفع/المنخفض
- كل شيء نسبي للسياق المحيط
- الحجم يقرأ في علاقته مع الانتشار (Spread)
- الإغلاق في الشمعة أهم من أي شيء آخر
- السوق يخبرك بقصته من خلال الحجم والانتشار معاً

المبادئ الأساسية:
1. الحجم + الانتشار + الإغلاق = البصمة الكاملة
2. جهد (حجم) كبير + انتشار ضيق = انعكاس قريب
3. جهد كبير + انتشار واسع + إغلاق في الاتجاه = استمرار
4. جهد منخفض + انتشار واسع = حركة سهلة (لا مقاومة)
5. ذروة بيع/شراء = نهاية اتجاه

العلامات الخاصة التي يكتشفها:
- Stopping Volume (حجم التوقف)
- No Demand (غياب الطلب)
- No Supply (غياب العرض)
- Effort vs Result (الجهد مقابل النتيجة)
- Upthrust / Reverse Upthrust
- Shakeout (الهزة)
- Test (اختبار)
- Absorption (امتصاص)
- Distribution (توزيع)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSASignalType(Enum):
    """أنواع إشارات VSA"""
    STOPPING_VOLUME = "حجم توقف - نهاية اتجاه"
    NO_DEMAND = "غياب طلب - ضعف صعود"
    NO_SUPPLY = "غياب عرض - ضعف هبوط"
    EFFORT_BULLISH = "جهد صاعد - توافق"
    EFFORT_BEARISH = "جهد هابط - توافق"
    EFFORT_DIVERGENCE_BULLISH = "انحراف صاعد - جهد بلا نتيجة"
    EFFORT_DIVERGENCE_BEARISH = "انحراف هابط - جهد بلا نتيجة"
    UPTHRUST = "دفع علوي - فخ صاعد"
    REVERSE_UPTHRUST = "دفع علوي معكوس"
    SHAKEOUT = "هزة - طرد ضعاف القلوب"
    TEST = "اختبار - تأكيد المنطقة"
    ABSORPTION = "امتصاص - تجميع/توزيع"
    CLIMAX_BUYING = "ذروة شراء"
    CLIMAX_SELLING = "ذروة بيع"
    PUSH_THROUGH = "اختراق بقوة"
    END_OF_RISING = "نهاية صعود"
    BAG_HOLDING = "توزيع على المتأخرين"


@dataclass
class VolumeBar:
    """تحليل شمعة واحدة من منظور VSA"""
    index: int
    open: float
    high: float
    low: float
    close: float
    spread: float           # الانتشار (High - Low)
    volume: float           # الحجم
    relative_volume: float  # الحجم النسبي (مقارنة بالمتوسط)
    spread_category: str    # 'narrow', 'normal', 'wide', 'ultra_wide'
    volume_category: str    # 'low', 'normal', 'high', 'ultra_high', 'climax'
    close_position: float   # 0=أسفل, 0.5=وسط, 1=أعلى
    is_up_bar: bool
    is_down_bar: bool
    body: float             # حجم الجسم


@dataclass
class VSASignal:
    """إشارة VSA مكتشفة"""
    index: int
    signal_type: VSASignalType
    direction: str          # 'bullish', 'bearish', 'neutral'
    strength: float         # 0-1
    confidence: float       # 0-1
    description: str
    price_level: float
    volume_bar: VolumeBar
    context: str            # سياق الإشارة


@dataclass
class VolumeTrend:
    """اتجاه الحجم"""
    trend_type: str         # 'increasing', 'decreasing', 'stable', 'spiking', 'drying'
    intensity: float        # 0-1
    duration: int           # عدد الشموع
    significance: str       # 'important', 'normal', 'weak'


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: محلل الشمعة الواحدة (Bar-by-Bar VSA Analyzer)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BarByBarVSAAnalyzer:
    """
    يحلل كل شمعة على حدة من منظور VSA.
    الحجم + الانتشار + الإغلاق = القصة الكاملة.
    
    ديناميكي: العتبات تتكيف مع ظروف السوق الحالية.
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        تحليل VSA لكل شمعة
        """
        # تصنيف كل شمعة
        bars = []
        for i in range(len(closes)):
            bar = self._analyze_single_bar(opens[i], highs[i], lows[i], closes[i],
                                           volumes[i], volumes, i)
            bars.append(bar)
        
        # اكتشاف الإشارات من الشموع
        signals = self._detect_signals_from_bars(bars, highs, lows, closes, volumes)
        
        # تجميع الإشارات
        recent_signals = signals[-20:] if len(signals) >= 20 else signals
        
        return {
            "recent_bars": bars[-20:],
            "all_signals": signals[-50:],
            "recent_signals": recent_signals,
            "current_signal": recent_signals[-1] if recent_signals else None,
            "signal_summary": self._summarize_signals(recent_signals),
        }
    
    def _analyze_single_bar(self, open_p: float, high: float, low: float,
                             close: float, volume: float, all_volumes: np.ndarray,
                             index: int) -> VolumeBar:
        """
        تحليل شمعة واحدة تحليلاً كاملاً.
        """
        spread = high - low
        body = abs(close - open_p)
        is_up = close > open_p
        is_down = close < open_p
        
        # الحجم النسبي (ديناميكي)
        if index >= 15:
            avg_vol = np.mean(all_volumes[max(0, index-15):index])
            std_vol = np.std(all_volumes[max(0, index-15):index]) if index >= 5 else avg_vol * 0.2
        else:
            avg_vol = volume if volume > 0 else 1.0
            std_vol = avg_vol * 0.2
        
        if avg_vol > 0:
            relative_vol = volume / avg_vol
        else:
            relative_vol = 1.0
        
        # تصنيف الحجم (ديناميكي)
        if relative_vol > 3.5:
            volume_category = 'climax'
        elif relative_vol > 2.0:
            volume_category = 'ultra_high'
        elif relative_vol > 1.3:
            volume_category = 'high'
        elif relative_vol < 0.35:
            volume_category = 'low'
        else:
            volume_category = 'normal'
        
        # تصنيف الانتشار (ديناميكي)
        if index >= 10:
            avg_spread = np.mean(highs[max(0,index-10):index+1] - lows[max(0,index-10):index+1])
        else:
            avg_spread = spread if spread > 0 else 0.0001
        
        if avg_spread > 0:
            spread_ratio = spread / avg_spread
        else:
            spread_ratio = 1.0
        
        if spread_ratio > 2.5:
            spread_category = 'ultra_wide'
        elif spread_ratio > 1.5:
            spread_category = 'wide'
        elif spread_ratio < 0.4:
            spread_category = 'narrow'
        else:
            spread_category = 'normal'
        
        # موقع الإغلاق
        if spread > 0:
            close_position = (close - low) / spread
        else:
            close_position = 0.5
        
        return VolumeBar(
            index=index,
            open=open_p,
            high=high,
            low=low,
            close=close,
            spread=spread,
            volume=volume,
            relative_volume=relative_vol,
            spread_category=spread_category,
            volume_category=volume_category,
            close_position=close_position,
            is_up_bar=is_up,
            is_down_bar=is_down,
            body=body,
        )
    
    def _detect_signals_from_bars(self, bars: List[VolumeBar], highs: np.ndarray,
                                   lows: np.ndarray, closes: np.ndarray,
                                   volumes: np.ndarray) -> List[VSASignal]:
        """
        اكتشاف إشارات VSA من تسلسل الشموع
        """
        signals = []
        
        for i in range(len(bars)):
            bar = bars[i]
            
            # ---- حجم توقف (Stopping Volume) ----
            if self._is_stopping_volume(bar, bars, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.STOPPING_VOLUME,
                    direction='bullish' if bar.is_down_bar else 'bearish',
                    strength=0.85,
                    confidence=0.8,
                    description="حجم مرتفع على شمعة بانتشار واسع تعكس الاتجاه - المؤسسات تتدخل",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="نهاية اتجاه",
                ))
            
            # ---- غياب الطلب (No Demand) ----
            if self._is_no_demand(bar, bars, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.NO_DEMAND,
                    direction='bearish',
                    strength=0.7,
                    confidence=0.7,
                    description="شمعة صاعدة بانتشار ضيق وحجم منخفض - لا يوجد مشترين حقيقيين",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف الصعود",
                ))
            
            # ---- غياب العرض (No Supply) ----
            if self._is_no_supply(bar, bars, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.NO_SUPPLY,
                    direction='bullish',
                    strength=0.7,
                    confidence=0.7,
                    description="شمعة هابطة بانتشار ضيق وحجم منخفض - لا يوجد بائعين حقيقيين",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف الهبوط",
                ))
            
            # ---- توافق/انحراف الجهد ----
            effort_signal = self._analyze_effort_result(bar, bars, closes, i)
            if effort_signal:
                signals.append(effort_signal)
            
            # ---- دفع علوي (Upthrust) ----
            if self._is_upthrust(bar, bars, highs, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.UPTHRUST,
                    direction='bearish',
                    strength=0.8,
                    confidence=0.75,
                    description="اختراق وهمي للأعلى بظل طويل وحجم مرتفع - فخ للمشترين",
                    price_level=bar.high,
                    volume_bar=bar,
                    context="فخ صاعد",
                ))
            
            # ---- هزة (Shakeout) ----
            if self._is_shakeout(bar, bars, lows, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.SHAKEOUT,
                    direction='bullish',
                    strength=0.9,
                    confidence=0.85,
                    description="كسر وهمي للأسفل بحجم مرتفع وارتداد قوي - طرد الضعفاء",
                    price_level=bar.low,
                    volume_bar=bar,
                    context="تجميع عنيف",
                ))
            
            # ---- اختبار (Test) ----
            if self._is_test(bar, bars, lows, closes, volumes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.TEST,
                    direction='bullish',
                    strength=0.65,
                    confidence=0.65,
                    description="اختبار منطقة بحجم منخفض - تأكيد عدم وجود بائعين",
                    price_level=bar.low,
                    volume_bar=bar,
                    context="تأكيد الدعم",
                ))
            
            # ---- ذروة شراء/بيع ----
            if self._is_climax(bar, bars, closes, i):
                direction = 'bearish' if bar.is_up_bar else 'bullish'
                sig_type = VSASignalType.CLIMAX_BUYING if bar.is_up_bar else VSASignalType.CLIMAX_SELLING
                signals.append(VSASignal(
                    index=i,
                    signal_type=sig_type,
                    direction=direction,
                    strength=0.75,
                    confidence=0.7,
                    description=f"ذروة {'شراء' if bar.is_up_bar else 'بيع'} - نهاية الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="نهاية اتجاه",
                ))
            
            # ---- امتصاص (Absorption) ----
            if self._is_absorption(bar, bars, closes, i):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.ABSORPTION,
                    direction='neutral',
                    strength=0.6,
                    confidence=0.6,
                    description="حجم مرتفع مع انتشار ضيق - المؤسسات تمتص الأوامر",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="تجميع/توزيع صامت",
                ))
        
        return signals
    
    def _is_stopping_volume(self, bar: VolumeBar, bars: List[VolumeBar],
                            closes: np.ndarray, index: int) -> bool:
        """
        كشف حجم التوقف.
        حجم مرتفع جداً على شمعة تعكس الاتجاه السابق.
        """
        if bar.volume_category not in ['ultra_high', 'climax']:
            return False
        
        if bar.spread_category not in ['wide', 'ultra_wide']:
            return False
        
        # الاتجاه السابق
        if index >= 10:
            trend_up = closes[index-1] > closes[index-5] and closes[index-5] > closes[index-10]
            trend_down = closes[index-1] < closes[index-5] and closes[index-5] < closes[index-10]
            
            # شمعة هابطة بحجم مرتفع بعد اتجاه هابط = وقف الهبوط
            if bar.is_down_bar and trend_down and bar.close_position > 0.4:
                return True
            
            # شمعة صاعدة بحجم مرتفع بعد اتجاه صاعد = وقف الصعود
            if bar.is_up_bar and trend_up and bar.close_position < 0.6:
                return True
        
        return False
    
    def _is_no_demand(self, bar: VolumeBar, bars: List[VolumeBar],
                      closes: np.ndarray, index: int) -> bool:
        """
        كشف غياب الطلب.
        شمعة صاعدة بانتشار ضيق وحجم منخفض.
        """
        if not bar.is_up_bar:
            return False
        
        if bar.volume_category != 'low':
            return False
        
        if bar.spread_category != 'narrow':
            return False
        
        # يحدث في قمة أو بعد صعود
        if index >= 10:
            if closes[index] > np.mean(closes[max(0,index-20):index]):
                return True
        
        return False
    
    def _is_no_supply(self, bar: VolumeBar, bars: List[VolumeBar],
                      closes: np.ndarray, index: int) -> bool:
        """
        كشف غياب العرض.
        شمعة هابطة بانتشار ضيق وحجم منخفض.
        """
        if not bar.is_down_bar:
            return False
        
        if bar.volume_category != 'low':
            return False
        
        if bar.spread_category != 'narrow':
            return False
        
        if index >= 10:
            if closes[index] < np.mean(closes[max(0,index-20):index]):
                return True
        
        return False
    
    def _analyze_effort_result(self, bar: VolumeBar, bars: List[VolumeBar],
                                closes: np.ndarray, index: int) -> Optional[VSASignal]:
        """
        تحليل الجهد مقابل النتيجة.
        """
        if bar.volume_category not in ['high', 'ultra_high', 'climax']:
            return None
        
        if bar.spread_category == 'narrow':
            # جهد كبير + انتشار ضيق = انحراف
            if bar.is_up_bar and bar.close_position < 0.4:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_DIVERGENCE_BULLISH,
                    direction='bearish',
                    strength=0.7,
                    confidence=0.7,
                    description="جهد صاعد كبير لكن السعر لم يتحرك - البائعون يمنعون الصعود",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف خفي",
                )
            elif bar.is_down_bar and bar.close_position > 0.6:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_DIVERGENCE_BEARISH,
                    direction='bullish',
                    strength=0.7,
                    confidence=0.7,
                    description="جهد هابط كبير لكن السعر لم يتحرك - المشترون يمنعون الهبوط",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="قوة خفية",
                )
        
        elif bar.spread_category in ['wide', 'ultra_wide']:
            # جهد كبير + انتشار واسع = توافق
            if bar.is_up_bar and bar.close_position > 0.7:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_BULLISH,
                    direction='bullish',
                    strength=0.6,
                    confidence=0.65,
                    description="توافق صاعد - الحجم يؤكد الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="استمرار",
                )
            elif bar.is_down_bar and bar.close_position < 0.3:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_BEARISH,
                    direction='bearish',
                    strength=0.6,
                    confidence=0.65,
                    description="توافق هابط - الحجم يؤكد الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="استمرار",
                )
        
        return None
    
    def _is_upthrust(self, bar: VolumeBar, bars: List[VolumeBar],
                     highs: np.ndarray, closes: np.ndarray, index: int) -> bool:
        """
        كشف الدفع العلوي.
        شمعة تخترق مقاومة للأعلى ثم تعود تحتها.
        """
        if bar.volume_category not in ['high', 'ultra_high']:
            return False
        
        # ظل علوي طويل
        if bar.spread > 0:
            upper_wick = bar.high - max(bar.open, bar.close)
            if upper_wick < bar.spread * 0.5:
                return False
        else:
            return False
        
        # الإغلاق في النصف السفلي
        if bar.close_position > 0.4:
            return False
        
        # تجاوز مستوى مقاومة سابق
        if index >= 10:
            prev_high = max(highs[index-10:index])
            if bar.high > prev_high and bar.close < prev_high:
                return True
        
        return False
    
    def _is_shakeout(self, bar: VolumeBar, bars: List[VolumeBar],
                     lows: np.ndarray, closes: np.ndarray, index: int) -> bool:
        """
        كشف الهزة (Shakeout).
        كسر وهمي للأسفل بحجم مرتفع وارتداد فوري.
        """
        if bar.volume_category not in ['high', 'ultra_high', 'climax']:
            return False
        
        # ظل سفلي طويل
        if bar.spread > 0:
            lower_wick = min(bar.open, bar.close) - bar.low
            if lower_wick < bar.spread * 0.5:
                return False
        else:
            return False
        
        # الإغلاق في النصف العلوي
        if bar.close_position < 0.6:
            return False
        
        # كسر مستوى دعم سابق
        if index >= 10:
            prev_low = min(lows[index-10:index])
            if bar.low < prev_low and bar.close > prev_low:
                return True
        
        return False
    
    def _is_test(self, bar: VolumeBar, bars: List[VolumeBar],
                 lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
                 index: int) -> bool:
        """
        كشف الاختبار.
        السعر يعود لمنطقة سابقة بحجم منخفض جداً.
        """
        if bar.volume_category != 'low':
            return False
        
        if index < 10:
            return False
        
        # السعر يختبر قاعاً سابقاً
        prev_low = min(lows[index-10:index])
        if bar.low <= prev_low * 1.005 and bar.low >= prev_low * 0.995:
            return True
        
        return False
    
    def _is_climax(self, bar: VolumeBar, bars: List[VolumeBar],
                   closes: np.ndarray, index: int) -> bool:
        """
        كشف ذروة الشراء/البيع.
        """
        if bar.volume_category != 'climax':
            return False
        
        if bar.spread_category not in ['wide', 'ultra_wide']:
            return False
        
        # ذروة شراء: شمعة صاعدة بحجم هائل وانتشار واسع
        if bar.is_up_bar and bar.close_position > 0.8:
            if index >= 15 and closes[index] > np.max(closes[index-15:index]):
                return True
        
        # ذروة بيع: شمعة هابطة بحجم هائل وانتشار واسع
        if bar.is_down_bar and bar.close_position < 0.2:
            if index >= 15 and closes[index] < np.min(closes[index-15:index]):
                return True
        
        return False
    
    def _is_absorption(self, bar: VolumeBar, bars: List[VolumeBar],
                       closes: np.ndarray, index: int) -> bool:
        """
        كشف الامتصاص.
        حجم مرتفع مع انتشار ضيق = المؤسسات تمتص.
        """
        if bar.volume_category not in ['high', 'ultra_high']:
            return False
        
        if bar.spread_category != 'narrow':
            return False
        
        if 0.35 < bar.close_position < 0.65:
            return True
        
        return False
    
    def _summarize_signals(self, signals: List[VSASignal]) -> Dict:
        """
        تلخيص الإشارات الحديثة
        """
        if not signals:
            return {"dominant": "لا إشارات", "bias": "محايد"}
        
        bullish_count = sum(1 for s in signals if s.direction == 'bullish')
        bearish_count = sum(1 for s in signals if s.direction == 'bearish')
        
        avg_strength_bullish = np.mean([s.strength for s in signals if s.direction == 'bullish']) if bullish_count > 0 else 0
        avg_strength_bearish = np.mean([s.strength for s in signals if s.direction == 'bearish']) if bearish_count > 0 else 0
        
        bullish_power = bullish_count * avg_strength_bullish
        bearish_power = bearish_count * avg_strength_bearish
        
        if bullish_power > bearish_power * 1.5:
            bias = "صاعد"
        elif bearish_power > bullish_power * 1.5:
            bias = "هابط"
        else:
            bias = "محايد"
        
        return {
            "dominant": "صاعد" if bullish_power > bearish_power else "هابط" if bearish_power > bullish_power else "متوازن",
            "bias": bias,
            "bullish_power": bullish_power,
            "bearish_power": bearish_power,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: محلل اتجاه الحجم (Volume Trend Analyzer)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VolumeTrendAnalyzer:
    """
    يحلل اتجاه الحجم عبر الزمن.
    الحجم يسبق السعر - تغير الحجم ينذر بتغير الاتجاه.
    """
    
    def analyze(self, volumes: np.ndarray, closes: np.ndarray) -> Dict:
        """
        تحليل اتجاهات الحجم
        """
        # الاتجاه العام للحجم
        overall_trend = self._analyze_overall_trend(volumes)
        
        # علاقة الحجم بالسعر
        volume_price_relationship = self._analyze_volume_price(volumes, closes)
        
        # تباعد الحجم عن السعر
        divergences = self._detect_volume_price_divergence(volumes, closes)
        
        return {
            "overall_trend": overall_trend,
            "volume_price": volume_price_relationship,
            "divergences": divergences[-5:],
        }
    
    def _analyze_overall_trend(self, volumes: np.ndarray) -> VolumeTrend:
        """
        تحليل الاتجاه العام للحجم
        """
        if len(volumes) < 20:
            return VolumeTrend(trend_type='stable', intensity=0.3, duration=0, significance='normal')
        
        # مقارنة الحجم الأخير بالقديم
        recent = volumes[-10:]
        older = volumes[-20:-10]
        
        avg_recent = np.mean(recent)
        avg_older = np.mean(older)
        
        if avg_older == 0:
            ratio = 1.0
        else:
            ratio = avg_recent / avg_older
        
        if ratio > 1.5:
            trend_type = 'increasing'
            intensity = min(1.0, ratio / 3)
            significance = 'important' if ratio > 2.0 else 'normal'
        elif ratio < 0.5:
            trend_type = 'drying'
            intensity = min(1.0, 1 - ratio)
            significance = 'important' if ratio < 0.3 else 'normal'
        elif np.std(recent) > np.mean(recent) * 0.5:
            trend_type = 'spiking'
            intensity = 0.6
            significance = 'important'
        else:
            trend_type = 'stable'
            intensity = 0.3
            significance = 'normal'
        
        return VolumeTrend(
            trend_type=trend_type,
            intensity=intensity,
            duration=len(volumes),
            significance=significance,
        )
    
    def _analyze_volume_price(self, volumes: np.ndarray, closes: np.ndarray) -> Dict:
        """
        تحليل علاقة الحجم بالسعر
        """
        if len(closes) < 20:
            return {"relationship": "غير كافٍ"}
        
        # في آخر 20 شمعة
        recent_closes = closes[-20:]
        recent_volumes = volumes[-20:]
        
        up_bars_vol = []
        down_bars_vol = []
        
        for i in range(1, len(recent_closes)):
            if recent_closes[i] > recent_closes[i-1]:
                up_bars_vol.append(recent_volumes[i])
            else:
                down_bars_vol.append(recent_volumes[i])
        
        avg_up_vol = np.mean(up_bars_vol) if up_bars_vol else 0
        avg_down_vol = np.mean(down_bars_vol) if down_bars_vol else 0
        
        if avg_down_vol > 0:
            vol_ratio = avg_up_vol / avg_down_vol
        else:
            vol_ratio = 1.0
        
        if vol_ratio > 1.3:
            relationship = "حجم الصعود أعلى - اهتمام بالشراء"
        elif vol_ratio < 0.7:
            relationship = "حجم الهبوط أعلى - اهتمام بالبيع"
        else:
            relationship = "متوازن"
        
        return {
            "relationship": relationship,
            "up_volume_avg": avg_up_vol,
            "down_volume_avg": avg_down_vol,
            "ratio": vol_ratio,
        }
    
    def _detect_volume_price_divergence(self, volumes: np.ndarray, 
                                         closes: np.ndarray) -> List[Dict]:
        """
        اكتشاف تباعد الحجم عن السعر
        """
        divergences = []
        
        if len(closes) < 15:
            return divergences
        
        # فحص كل 5 شموع
        for i in range(10, len(closes) - 5):
            price_change = closes[i+5] - closes[i]
            vol_change = np.mean(volumes[i+1:i+6]) - np.mean(volumes[i-4:i+1])
            
            if price_change > 0 and vol_change < 0 and abs(vol_change) > np.mean(volumes) * 0.3:
                divergences.append({
                    "index": i,
                    "type": "bearish_divergence",
                    "description": "سعر يصعد وحجم ينخفض - ضعف الصعود",
                    "strength": 0.65,
                })
            
            if price_change < 0 and vol_change < 0 and abs(vol_change) > np.mean(volumes) * 0.3:
                divergences.append({
                    "index": i,
                    "type": "bullish_divergence",
                    "description": "سعر ينخفض وحجم ينخفض - ضعف الهبوط",
                    "strength": 0.65,
                })
        
        return divergences


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الثالثة: مراحل السوق من منظور VSA                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSAMarketPhaseAnalyzer:
    """
    يحدد مرحلة السوق من خلال تحليل VSA.
    تجميع، توزيع، اتجاه، قمة، قاع.
    """
    
    def analyze(self, signals: List[VSASignal], bars: List[VolumeBar],
                closes: np.ndarray) -> Dict:
        """
        تحديد مرحلة السوق
        """
        phase = self._determine_phase(signals, bars, closes)
        
        return {
            "current_phase": phase,
            "phase_confidence": self._phase_confidence(phase, signals),
            "phase_description": self._describe_phase(phase),
        }
    
    def _determine_phase(self, signals: List[VSASignal], bars: List[VolumeBar],
                         closes: np.ndarray) -> str:
        """
        تحديد المرحلة الحالية
        """
        if not signals:
            return "غير محدد"
        
        # عد الإشارات حسب النوع
        signal_counts = {}
        for s in signals[-20:]:
            key = s.signal_type.value
            signal_counts[key] = signal_counts.get(key, 0) + 1
        
        # تحليل اتجاه السعر
        if len(closes) >= 20:
            trend = "up" if closes[-1] > closes[-10] else "down" if closes[-1] < closes[-10] else "sideways"
        else:
            trend = "unknown"
        
        # قمة: ذروة شراء + Upthrusts + No Demand
        climax_buying = signal_counts.get(VSASignalType.CLIMAX_BUYING.value, 0)
        upthrusts = signal_counts.get(VSASignalType.UPTHRUST.value, 0)
        no_demand = signal_counts.get(VSASignalType.NO_DEMAND.value, 0)
        
        if climax_buying >= 1 or upthrusts >= 1 or no_demand >= 2:
            if trend == "up" or closes[-1] > np.mean(closes[-50:]):
                return "توزيع - قمة محتملة"
        
        # قاع: ذروة بيع + Shakeout + No Supply + Stopping Volume
        climax_selling = signal_counts.get(VSASignalType.CLIMAX_SELLING.value, 0)
        shakeouts = signal_counts.get(VSASignalType.SHAKEOUT.value, 0)
        no_supply = signal_counts.get(VSASignalType.NO_SUPPLY.value, 0)
        stopping = signal_counts.get(VSASignalType.STOPPING_VOLUME.value, 0)
        
        if climax_selling >= 1 or shakeouts >= 1 or no_supply >= 2 or stopping >= 1:
            if trend == "down" or closes[-1] < np.mean(closes[-50:]):
                return "تجميع - قاع محتمل"
        
        # اتجاه: توافق الجهد
        effort_bullish = signal_counts.get(VSASignalType.EFFORT_BULLISH.value, 0)
        effort_bearish = signal_counts.get(VSASignalType.EFFORT_BEARISH.value, 0)
        
        if effort_bullish > effort_bearish:
            return "اتجاه صاعد - حجم يؤكد"
        elif effort_bearish > effort_bullish:
            return "اتجاه هابط - حجم يؤكد"
        
        # امتصاص = تجميع/توزيع صامت
        absorption = signal_counts.get(VSASignalType.ABSORPTION.value, 0)
        if absorption >= 3:
            return "امتصاص - تجميع أو توزيع"
        
        return "غير محدد"
    
    def _phase_confidence(self, phase: str, signals: List[VSASignal]) -> float:
        """ثقة تحديد المرحلة"""
        if phase == "غير محدد":
            return 0.2
        
        if not signals:
            return 0.3
        
        recent = signals[-20:]
        strong_signals = [s for s in recent if s.strength > 0.7]
        
        return min(0.9, 0.4 + len(strong_signals) * 0.1)
    
    def _describe_phase(self, phase: str) -> str:
        """وصف المرحلة بالعربية"""
        descriptions = {
            "توزيع - قمة محتملة": "السوق يظهر علامات توزيع. الحجم على الصعود يضعف. كن حذراً من انعكاس هابط.",
            "تجميع - قاع محتمل": "السوق يظهر علامات تجميع. الحجم على الهبوط يضعف. فرصة صعود قريبة.",
            "اتجاه صاعد - حجم يؤكد": "الحجم يؤكد الصعود. المؤسسات تشتري. استمر مع الاتجاه.",
            "اتجاه هابط - حجم يؤكد": "الحجم يؤكد الهبوط. المؤسسات تبيع. استمر مع الاتجاه.",
            "امتصاص - تجميع أو توزيع": "المؤسسات تمتص الأوامر بهدوء. راقب الاختراق القادم.",
        }
        return descriptions.get(phase, "المرحلة غير واضحة، انتظر تأكيداً.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية VSA الموحدة                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSAStrategy:
    """
    استراتيجية تحليل الحجم والانتشار الكاملة.
    
    تجمع:
    - تحليل كل شمعة (Bar-by-Bar)
    - اتجاهات الحجم
    - مراحل السوق
    
    في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.bar_analyzer = BarByBarVSAAnalyzer()
        self.trend_analyzer = VolumeTrendAnalyzer()
        self.phase_analyzer = VSAMarketPhaseAnalyzer()
    
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
        
        # 1. تحليل الشموع
        bar_data = self.bar_analyzer.analyze(opens, highs, lows, closes, volumes)
        
        # 2. تحليل اتجاه الحجم
        trend_data = self.trend_analyzer.analyze(volumes, closes)
        
        # 3. مرحلة السوق
        recent_signals = bar_data.get('recent_signals', [])
        recent_bars = bar_data.get('recent_bars', [])
        phase_data = self.phase_analyzer.analyze(recent_signals, recent_bars, closes)
        
        # 4. القرار
        decision = self._make_decision(bar_data, trend_data, phase_data)
        
        return {
            **decision,
            "bar_data": bar_data,
            "trend_data": trend_data,
            "phase_data": phase_data,
        }
    
    def _make_decision(self, bar_data: Dict, trend_data: Dict,
                       phase_data: Dict) -> Dict:
        """
        اتخاذ القرار
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من الإشارات الحديثة ----
        recent_signals = bar_data.get('recent_signals', [])
        signal_summary = bar_data.get('signal_summary', {})
        
        for s in recent_signals[-10:]:
            weight = s.strength * s.confidence * 0.5
            
            if s.direction == 'bullish':
                buy_signals.append((s.description[:50], weight))
            elif s.direction == 'bearish':
                sell_signals.append((s.description[:50], weight))
        
        # ---- من اتجاه الحجم ----
        overall_trend = trend_data.get('overall_trend', VolumeTrend('stable', 0, 0, 'normal'))
        vol_price = trend_data.get('volume_price', {})
        
        if overall_trend.trend_type == 'drying' and overall_trend.significance == 'important':
            # حجم يجف = تغير قادم
            if len(closes) >= 10 and closes[-1] < closes[-10]:
                buy_signals.append(("حجم يجف على هبوط - انعكاس صعودي قريب", 0.5))
            elif len(closes) >= 10 and closes[-1] > closes[-10]:
                sell_signals.append(("حجم يجف على صعود - انعكاس هبوطي قريب", 0.5))
        
        if vol_price.get('relationship') == "حجم الصعود أعلى - اهتمام بالشراء":
            buy_signals.append(("حجم يصب في صالح الصعود", 0.4))
        elif vol_price.get('relationship') == "حجم الهبوط أعلى - اهتمام بالبيع":
            sell_signals.append(("حجم يصب في صالح الهبوط", 0.4))
        
        # ---- من المرحلة ----
        current_phase = phase_data.get('current_phase', 'غير محدد')
        
        if current_phase == "تجميع - قاع محتمل":
            buy_signals.append(("VSA: مرحلة تجميع", 0.65))
        elif current_phase == "توزيع - قمة محتملة":
            sell_signals.append(("VSA: مرحلة توزيع", 0.65))
        elif current_phase == "اتجاه صاعد - حجم يؤكد":
            buy_signals.append(("VSA: اتجاه صاعد مؤكد", 0.6))
        elif current_phase == "اتجاه هابط - حجم يؤكد":
            sell_signals.append(("VSA: اتجاه هابط مؤكد", 0.6))
        
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
            confidence = 40 + int(total_buy - total_sell) * 15
        elif total_sell > total_buy:
            recommendation = "بيع ضعيف"
            confidence = 40 + int(total_sell - total_buy) * 15
        else:
            recommendation = "محايد"
            confidence = 25
        
        top_signals = sorted(buy_signals + sell_signals, key=lambda x: x[1], reverse=True)[:5]
        reason = " | ".join([s[0] for s in top_signals])
        reason += f" | المرحلة: {current_phase}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "phase": current_phase,
        }


def create_vsa_strategy():
    """إنشاء استراتيجية VSA الجاهزة"""
    return VSAStrategy()"""
═══════════════════════════════════════════════════════════════════════════════
VOLUME SPREAD ANALYSIS (VSA) - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة السادسة: تحليل الحجم والانتشار - بصمات المال الذكي
═══════════════════════════════════════════════════════════════════════════════

ريتشارد وايكوف (مرة أخرى) وتوم ويليامز طوروا VSA.
الفكرة: الحجم يكشف نوايا المؤسسات. السعر بدون حجم = نصف الحقيقة.

هذه النسخة ديناميكية بالكامل - معدلة بـ 15 تحسيناً تداولياً:
- لا عتبات ثابتة للحجم المرتفع/المنخفض
- كل شيء نسبي للسياق المحيط
- تحليل تسلسل الإشارات (Signal Sequencing)
- تصنيف الخلفية (Background Classification)
- ذاكرة الإشارات مع عامل الاضمحلال (Decay Factor)
- عتبات انتشار متكيفة مع التقلب (ATR)
- Cumulative Effort vs Result
- Volume-Weighted Close Position

التعديلات الجوهرية:
🔴 5 أخطاء تداولية تم إصلاحها
🟡 5 تحسينات ذكاء تداولي
🟢 5 فرص قوية غير مستغلة تم تفعيلها

المبادئ الأساسية:
1. الحجم + الانتشار + الإغلاق = البصمة الكاملة
2. السياق يحكم تفسير كل إشارة
3. تسلسل الإشارات أهم من الإشارة المفردة
4. الإشارات تفقد قوتها مع الزمن
5. الدعم والمقاومة يضاعفان قوة الإشارات
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSASignalType(Enum):
    """أنواع إشارات VSA"""
    STOPPING_VOLUME = "حجم توقف - نهاية اتجاه"
    NO_DEMAND = "غياب طلب - ضعف صعود"
    NO_SUPPLY = "غياب عرض - ضعف هبوط"
    EFFORT_BULLISH = "جهد صاعد - توافق"
    EFFORT_BEARISH = "جهد هابط - توافق"
    EFFORT_DIVERGENCE_BULLISH = "انحراف صاعد - جهد بلا نتيجة"
    EFFORT_DIVERGENCE_BEARISH = "انحراف هابط - جهد بلا نتيجة"
    UPTHRUST = "دفع علوي - فخ صاعد"
    REVERSE_UPTHRUST = "دفع علوي معكوس"
    SHAKEOUT = "هزة - طرد ضعاف القلوب"
    TEST = "اختبار - تأكيد المنطقة"
    ABSORPTION = "امتصاص - تجميع/توزيع"
    ABSORPTION_ACCUMULATION = "امتصاص تجميعي"
    ABSORPTION_DISTRIBUTION = "امتصاص توزيعي"
    CLIMAX_BUYING = "ذروة شراء"
    CLIMAX_SELLING = "ذروة بيع"
    VOLUME_CLIMAX = "ذروة حجم - تحذير انعكاس"
    PUSH_THROUGH_SUPPLY = "اختراق عرض - قوة حقيقية"
    PUSH_THROUGH_DEMAND = "اختراق طلب - ضعف حقيقي"
    VOLUME_DRY_UP = "جفاف حجم - انفجار قادم"
    END_OF_RISING = "نهاية صعود"
    BAG_HOLDING = "توزيع على المتأخرين"


class MarketBackground(Enum):
    """تصنيف خلفية السوق"""
    AT_MAJOR_BOTTOM = "قاع رئيسي"
    AT_MINOR_BOTTOM = "قاع فرعي"
    AT_MAJOR_TOP = "قمة رئيسية"
    AT_MINOR_TOP = "قمة فرعية"
    IN_UPTREND = "وسط اتجاه صاعد"
    IN_DOWNTREND = "وسط اتجاه هابط"
    IN_RANGE_LOW = "أسفل نطاق"
    IN_RANGE_HIGH = "أعلى نطاق"
    IN_RANGE_MID = "وسط نطاق"
    UNKNOWN = "غير محدد"


@dataclass
class VolumeBar:
    """تحليل شمعة واحدة من منظور VSA - نسخة محسنة"""
    index: int
    open: float
    high: float
    low: float
    close: float
    spread: float
    volume: float
    relative_volume: float
    spread_category: str
    volume_category: str
    close_position: float
    is_up_bar: bool
    is_down_bar: bool
    body: float
    vw_close_position: float = 0.5  # 🟢 تعديل 14
    spread_atr_ratio: float = 1.0  # 🟢 تعديل 15


@dataclass
class VSASignal:
    """إشارة VSA مكتشفة - نسخة محسنة"""
    index: int
    signal_type: VSASignalType
    direction: str
    strength: float
    confidence: float
    description: str
    price_level: float
    volume_bar: VolumeBar
    context: str
    background: MarketBackground = MarketBackground.UNKNOWN  # 🔴 تعديل 2
    decay_factor: float = 1.0  # 🟡 تعديل 10
    at_support_resistance: bool = False  # 🟢 تعديل 11
    sr_strength_multiplier: float = 1.0  # 🟢 تعديل 11
    sequence_boost: float = 0.0  # 🔴 تعديل 1


@dataclass
class VolumeTrend:
    """اتجاه الحجم"""
    trend_type: str
    intensity: float
    duration: int
    significance: str


@dataclass
class SupportResistanceLevel:
    """مستوى دعم/مقاومة"""
    price: float
    level_type: str  # 'support' or 'resistance'
    strength: float  # 0-1
    touches: int
    age: int
    is_major: bool


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║    الدرجة صفر: محلل مستويات الدعم والمقاومة (لربط VSA بالسياق)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SupportResistanceAnalyzer:
    """
    يكتشف مستويات الدعم والمقاومة لربطها مع إشارات VSA.
    🟢 تعديل 11: دمج VSA مع مستويات الدعم والمقاومة
    """
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> List[SupportResistanceLevel]:
        """اكتشاف المستويات الرئيسية"""
        levels = []
        
        if len(closes) < 50:
            return levels
        
        # اكتشاف القمم والقيعان
        peaks = []
        valleys = []
        
        for i in range(10, len(closes) - 10):
            if all(highs[i] >= highs[i-j] for j in range(1, 11)) and \
               all(highs[i] >= highs[i+j] for j in range(1, 11)):
                peaks.append({'price': highs[i], 'index': i})
            if all(lows[i] <= lows[i-j] for j in range(1, 11)) and \
               all(lows[i] <= lows[i+j] for j in range(1, 11)):
                valleys.append({'price': lows[i], 'index': i})
        
        # تجميع المستويات المتقاربة
        support_groups = self._cluster_levels(valleys, closes)
        resistance_groups = self._cluster_levels(peaks, closes)
        
        # إنشاء مستويات الدعم
        for group in support_groups:
            touches = len(group['items'])
            age = len(closes) - group['items'][-1]['index']
            is_major = touches >= 3 or age > 100
            
            levels.append(SupportResistanceLevel(
                price=group['avg_price'],
                level_type='support',
                strength=min(1.0, touches * 0.3 + (1 if is_major else 0) * 0.3),
                touches=touches,
                age=age,
                is_major=is_major,
            ))
        
        # إنشاء مستويات المقاومة
        for group in resistance_groups:
            touches = len(group['items'])
            age = len(closes) - group['items'][-1]['index']
            is_major = touches >= 3 or age > 100
            
            levels.append(SupportResistanceLevel(
                price=group['avg_price'],
                level_type='resistance',
                strength=min(1.0, touches * 0.3 + (1 if is_major else 0) * 0.3),
                touches=touches,
                age=age,
                is_major=is_major,
            ))
        
        return levels
    
    def _cluster_levels(self, points: List[Dict], closes: np.ndarray) -> List[Dict]:
        """تجميع النقاط المتقاربة"""
        if not points:
            return []
        
        avg_price = np.mean(closes[-50:]) if len(closes) >= 50 else np.mean(closes)
        threshold = avg_price * 0.005
        
        sorted_points = sorted(points, key=lambda x: x['price'])
        groups = []
        current_group = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i]['price'] - current_group[-1]['price'] < threshold:
                current_group.append(sorted_points[i])
            else:
                groups.append(current_group)
                current_group = [sorted_points[i]]
        
        groups.append(current_group)
        
        return [
            {
                'avg_price': np.mean([p['price'] for p in group]),
                'items': group,
            }
            for group in groups
        ]
    
    def is_near_level(self, price: float, levels: List[SupportResistanceLevel], 
                      atr: float = 0) -> Tuple[bool, float]:
        """
        فحص هل السعر قريب من مستوى دعم/مقاومة رئيسي
        🟢 تعديل 11
        """
        if atr == 0:
            proximity = price * 0.005
        else:
            proximity = atr * 0.5
        
        for level in levels:
            if abs(price - level.price) < proximity:
                return True, level.strength
        
        return False, 1.0


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║      الدرجة الأولى: محلل الشمعة الواحدة (Bar-by-Bar VSA Analyzer)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BarByBarVSAAnalyzer:
    """
    يحلل كل شمعة على حدة من منظور VSA.
    الحجم + الانتشار + الإغلاق = القصة الكاملة.
    
    ديناميكي: العتبات تتكيف مع ظروف السوق الحالية.
    🟢 تعديل 14: Volume-Weighted Close Position
    🟢 تعديل 15: عتبات انتشار متكيفة مع ATR
    """
    
    def analyze(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray, volumes: np.ndarray,
                sr_levels: List[SupportResistanceLevel] = None) -> Dict:
        """
        تحليل VSA لكل شمعة
        """
        # حساب ATR للعتبات المتكيفة
        atr = self._calculate_atr(highs, lows, closes)
        
        # تصنيف كل شمعة
        bars = []
        for i in range(len(closes)):
            bar = self._analyze_single_bar(opens[i], highs[i], lows[i], closes[i],
                                           volumes[i], volumes, i, atr)
            bars.append(bar)
        
        # اكتشاف الإشارات من الشموع
        signals = self._detect_signals_from_bars(bars, highs, lows, closes, volumes, sr_levels)
        
        # 🔴 تعديل 1: تحليل تسلسل الإشارات
        signals = self._apply_signal_sequencing(signals)
        
        # 🟡 تعديل 10: تطبيق عامل الاضمحلال
        signals = self._apply_decay_factors(signals, len(closes))
        
        # تجميع الإشارات
        recent_signals = [s for s in signals if s.index >= len(closes) - 20]
        
        return {
            "recent_bars": bars[-20:],
            "all_signals": signals[-50:],
            "recent_signals": recent_signals,
            "current_signal": recent_signals[-1] if recent_signals else None,
            "signal_summary": self._summarize_signals(recent_signals),
        }
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """حساب متوسط المدى الحقيقي"""
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
    
    def _analyze_single_bar(self, open_p: float, high: float, low: float,
                             close: float, volume: float, all_volumes: np.ndarray,
                             index: int, atr: float = 0) -> VolumeBar:
        """
        تحليل شمعة واحدة تحليلاً كاملاً - نسخة محسنة
        """
        spread = high - low
        body = abs(close - open_p)
        is_up = close > open_p
        is_down = close < open_p
        
        # الحجم النسبي (ديناميكي)
        if index >= 15:
            avg_vol = np.mean(all_volumes[max(0, index-15):index])
            std_vol = np.std(all_volumes[max(0, index-15):index]) if index >= 5 else avg_vol * 0.2
        else:
            avg_vol = volume if volume > 0 else 1.0
            std_vol = avg_vol * 0.2
        
        if avg_vol > 0:
            relative_vol = volume / avg_vol
        else:
            relative_vol = 1.0
        
        # تصنيف الحجم (ديناميكي)
        if relative_vol > 3.5:
            volume_category = 'climax'
        elif relative_vol > 2.0:
            volume_category = 'ultra_high'
        elif relative_vol > 1.3:
            volume_category = 'high'
        elif relative_vol < 0.35:
            volume_category = 'low'
        else:
            volume_category = 'normal'
        
        # 🟢 تعديل 15: عتبات انتشار متكيفة مع ATR
        if index >= 10:
            avg_spread = np.mean(highs[max(0,index-10):index+1] - lows[max(0,index-10):index+1])
        else:
            avg_spread = spread if spread > 0 else 0.0001
        
        if avg_spread > 0:
            spread_ratio = spread / avg_spread
        else:
            spread_ratio = 1.0
        
        # نسبة الانتشار إلى ATR
        spread_atr_ratio = spread / atr if atr > 0 else 1.0
        
        # 🟢 تعديل 15: عتبات ديناميكية ترتبط بـ ATR
        if atr > 0:
            narrow_threshold = max(0.3, 0.4 - (atr / avg_spread) * 0.1) if avg_spread > 0 else 0.4
            wide_threshold = min(2.0, 1.5 + (atr / avg_spread) * 0.2) if avg_spread > 0 else 1.5
            ultra_wide_threshold = min(3.0, 2.5 + (atr / avg_spread) * 0.3) if avg_spread > 0 else 2.5
        else:
            narrow_threshold = 0.4
            wide_threshold = 1.5
            ultra_wide_threshold = 2.5
        
        if spread_ratio > ultra_wide_threshold:
            spread_category = 'ultra_wide'
        elif spread_ratio > wide_threshold:
            spread_category = 'wide'
        elif spread_ratio < narrow_threshold:
            spread_category = 'narrow'
        else:
            spread_category = 'normal'
        
        # موقع الإغلاق
        if spread > 0:
            close_position = (close - low) / spread
        else:
            close_position = 0.5
        
        # 🟢 تعديل 14: Volume-Weighted Close Position
        vw_close_position = close_position * min(relative_vol, 3.0) / 3.0
        
        return VolumeBar(
            index=index,
            open=open_p,
            high=high,
            low=low,
            close=close,
            spread=spread,
            volume=volume,
            relative_volume=relative_vol,
            spread_category=spread_category,
            volume_category=volume_category,
            close_position=close_position,
            is_up_bar=is_up,
            is_down_bar=is_down,
            body=body,
            vw_close_position=vw_close_position,
            spread_atr_ratio=spread_atr_ratio,
        )
    
    def _classify_background(self, closes: np.ndarray, highs: np.ndarray, 
                              lows: np.ndarray, index: int) -> MarketBackground:
        """
        🔴 تعديل 2: تصنيف خلفية السوق
        
        يحدد "أين نحن" في الصورة الكبيرة قبل تفسير أي إشارة
        """
        if index < 50:
            return MarketBackground.UNKNOWN
        
        current = closes[index]
        
        # المدى طويل الأجل
        lookback = min(200, index)
        all_time_high = max(highs[max(0,index-lookback):index+1])
        all_time_low = min(lows[max(0,index-lookback):index+1])
        total_range = all_time_high - all_time_low
        
        if total_range > 0:
            position = (current - all_time_low) / total_range
        else:
            position = 0.5
        
        # تحديد الاتجاه
        if index >= 50:
            sma20 = np.mean(closes[index-19:index+1])
            sma50 = np.mean(closes[max(0,index-49):index+1])
            trend_up = sma20 > sma50 and closes[index] > closes[index-20]
            trend_down = sma20 < sma50 and closes[index] < closes[index-20]
        else:
            trend_up = closes[index] > closes[max(0,index-10)]
            trend_down = closes[index] < closes[max(0,index-10)]
        
        # هل نحن في نطاق؟
        recent_high = max(highs[max(0,index-20):index+1])
        recent_low = min(lows[max(0,index-20):index+1])
        recent_range = recent_high - recent_low
        
        in_range = recent_range < total_range * 0.3 if total_range > 0 else False
        
        # التصنيف
        if position < 0.2:
            if all_time_low == recent_low:
                return MarketBackground.AT_MAJOR_BOTTOM
            return MarketBackground.AT_MINOR_BOTTOM
        elif position > 0.8:
            if all_time_high == recent_high:
                return MarketBackground.AT_MAJOR_TOP
            return MarketBackground.AT_MINOR_TOP
        elif in_range:
            if position < 0.35:
                return MarketBackground.IN_RANGE_LOW
            elif position > 0.65:
                return MarketBackground.IN_RANGE_HIGH
            else:
                return MarketBackground.IN_RANGE_MID
        elif trend_up:
            return MarketBackground.IN_UPTREND
        elif trend_down:
            return MarketBackground.IN_DOWNTREND
        
        return MarketBackground.UNKNOWN
    
    def _detect_signals_from_bars(self, bars: List[VolumeBar], highs: np.ndarray,
                                   lows: np.ndarray, closes: np.ndarray,
                                   volumes: np.ndarray,
                                   sr_levels: List[SupportResistanceLevel] = None) -> List[VSASignal]:
        """
        اكتشاف إشارات VSA من تسلسل الشموع - نسخة محسنة
        """
        signals = []
        
        for i in range(len(bars)):
            bar = bars[i]
            
            # 🔴 تعديل 2: تصنيف الخلفية
            background = self._classify_background(closes, highs, lows, i)
            
            # 🟢 تعديل 11: فحص القرب من دعم/مقاومة
            at_sr, sr_strength = False, 1.0
            if sr_levels:
                sr_analyzer = SupportResistanceAnalyzer()
                at_sr, sr_strength = sr_analyzer.is_near_level(
                    bar.close, sr_levels, 
                    self._calculate_atr(highs[:i+1], lows[:i+1], closes[:i+1])
                )
            
            # ---- حجم توقف (Stopping Volume) ----
            if self._is_stopping_volume(bar, bars, closes, highs, lows, i, background):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.STOPPING_VOLUME,
                    direction='bullish' if bar.is_down_bar else 'bearish',
                    strength=0.85 * sr_strength,
                    confidence=0.8,
                    description="حجم مرتفع على شمعة بانتشار واسع تعكس الاتجاه - المؤسسات تتدخل",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="نهاية اتجاه",
                    background=background,
                    at_support_resistance=at_sr,
                    sr_strength_multiplier=sr_strength,
                ))
            
            # ---- غياب الطلب (No Demand) ----
            if self._is_no_demand(bar, bars, closes, i, background):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.NO_DEMAND,
                    direction='bearish',
                    strength=0.7,
                    confidence=0.7,
                    description="شمعة صاعدة بانتشار ضيق وحجم منخفض - لا يوجد مشترين حقيقيين",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف الصعود",
                    background=background,
                ))
            
            # ---- غياب العرض (No Supply) ----
            if self._is_no_supply(bar, bars, closes, i, background):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.NO_SUPPLY,
                    direction='bullish',
                    strength=0.7,
                    confidence=0.7,
                    description="شمعة هابطة بانتشار ضيق وحجم منخفض - لا يوجد بائعين حقيقيين",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف الهبوط",
                    background=background,
                ))
            
            # ---- توافق/انحراف الجهد ----
            effort_signal = self._analyze_effort_result(bar, bars, closes, i, background)
            if effort_signal:
                signals.append(effort_signal)
            
            # ---- دفع علوي (Upthrust) ----
            if self._is_upthrust(bar, bars, highs, closes, i, background):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.UPTHRUST,
                    direction='bearish',
                    strength=0.8 * sr_strength,
                    confidence=0.75,
                    description="اختراق وهمي للأعلى بظل طويل وحجم مرتفع - فخ للمشترين",
                    price_level=bar.high,
                    volume_bar=bar,
                    context="فخ صاعد",
                    background=background,
                    at_support_resistance=at_sr,
                    sr_strength_multiplier=sr_strength,
                ))
            
            # ---- هزة (Shakeout) ----
            shakeout_result = self._is_shakeout(bar, bars, lows, closes, i, background)
            if shakeout_result:
                quality = shakeout_result  # 🟢 تعديل 12: جودة Shakeout
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.SHAKEOUT,
                    direction='bullish',
                    strength=0.9 * quality * sr_strength,
                    confidence=0.85 * quality,
                    description=f"كسر وهمي للأسفل بحجم مرتفع وارتداد قوي - طرد الضعفاء (جودة:{quality:.0%})",
                    price_level=bar.low,
                    volume_bar=bar,
                    context="تجميع عنيف",
                    background=background,
                    at_support_resistance=at_sr,
                    sr_strength_multiplier=sr_strength,
                ))
            
            # ---- اختبار (Test) ----
            if self._is_test(bar, bars, lows, closes, volumes, i, background, signals):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.TEST,
                    direction='bullish',
                    strength=0.65,
                    confidence=0.65,
                    description="اختبار منطقة بحجم منخفض - تأكيد عدم وجود بائعين",
                    price_level=bar.low,
                    volume_bar=bar,
                    context="تأكيد الدعم",
                    background=background,
                ))
            
            # ---- ذروة شراء/بيع ----
            if self._is_climax(bar, bars, closes, highs, lows, i, background):
                direction = 'bearish' if bar.is_up_bar else 'bullish'
                sig_type = VSASignalType.CLIMAX_BUYING if bar.is_up_bar else VSASignalType.CLIMAX_SELLING
                signals.append(VSASignal(
                    index=i,
                    signal_type=sig_type,
                    direction=direction,
                    strength=0.75,
                    confidence=0.7,
                    description=f"ذروة {'شراء' if bar.is_up_bar else 'بيع'} - نهاية الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="نهاية اتجاه",
                    background=background,
                ))
            
            # ---- ذروة حجم (Volume Climax) ----
            if self._is_volume_climax(bar, bars, closes, volumes, i, background):
                signals.append(VSASignal(
                    index=i,
                    signal_type=VSASignalType.VOLUME_CLIMAX,
                    direction='neutral',
                    strength=0.6,
                    confidence=0.6,
                    description="ذروة حجم - أعلى حجم في 50 شمعة - تحذير من انعكاس قريب",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="تحذير انعكاس",
                    background=background,
                ))
            
            # ---- امتصاص (Absorption) ----
            absorption_signal = self._is_absorption(bar, bars, closes, i, background)
            if absorption_signal:
                signals.append(absorption_signal)
            
            # ---- اختراق عرض/طلب (Push Through) ----
            push_signal = self._is_push_through(bar, bars, highs, lows, closes, i, background)
            if push_signal:
                signals.append(push_signal)
        
        # 🟡 تعديل 8: كشف جفاف الحجم
        dry_up_signals = self._detect_volume_dry_up(bars, volumes, closes)
        signals.extend(dry_up_signals)
        
        # 🟢 تعديل 13: Cumulative Effort vs Result
        cumulative_signals = self._analyze_cumulative_effort(bars, closes, volumes)
        signals.extend(cumulative_signals)
        
        # ترتيب الإشارات حسب index
        signals.sort(key=lambda x: x.index)
        
        return signals
    
    def _is_stopping_volume(self, bar: VolumeBar, bars: List[VolumeBar],
                            closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                            index: int, background: MarketBackground) -> bool:
        """
        🔴 تعديل 3: كشف حجم التوقف مع سياق محسن
        
        - يحدث بعد حركة هابطة طويلة ومستمرة
        - يفضل أن يكون على دعم رئيسي
        - يستخدم الموقع النسبي في المدى طويل الأجل
        """
        if bar.volume_category not in ['ultra_high', 'climax']:
            return False
        
        if bar.spread_category not in ['wide', 'ultra_wide']:
            return False
        
        if index < 20:
            return False
        
        # 🔴 تعديل 3: عدد الشموع الهابطة المتتالية
        consecutive_down = 0
        for j in range(index-1, max(0, index-30), -1):
            if closes[j] < closes[j-1]:
                consecutive_down += 1
            else:
                break
        
        consecutive_up = 0
        for j in range(index-1, max(0, index-30), -1):
            if closes[j] > closes[j-1]:
                consecutive_up += 1
            else:
                break
        
        # 🔴 تعديل 3: الموقع النسبي في المدى طويل الأجل
        lookback = min(100, index)
        long_term_high = max(highs[max(0,index-lookback):index+1])
        long_term_low = min(lows[max(0,index-lookback):index+1])
        long_term_range = long_term_high - long_term_low
        
        if long_term_range > 0:
            position = (bar.close - long_term_low) / long_term_range
        else:
            position = 0.5
        
        # شمعة هابطة بحجم مرتفع بعد اتجاه هابط = وقف الهبوط
        if bar.is_down_bar and consecutive_down >= 5 and bar.close_position > 0.4:
            # أقوى إذا كان في أسفل المدى
            if position < 0.3:
                return True
            return consecutive_down >= 10
        
        # شمعة صاعدة بحجم مرتفع بعد اتجاه صاعد = وقف الصعود
        if bar.is_up_bar and consecutive_up >= 5 and bar.close_position < 0.6:
            if position > 0.7:
                return True
            return consecutive_up >= 10
        
        return False
    
    def _is_no_demand(self, bar: VolumeBar, bars: List[VolumeBar],
                      closes: np.ndarray, index: int, 
                      background: MarketBackground) -> bool:
        """
        🔴 تعديل 2: غياب الطلب مع خلفية
        
        No Demand في قمة = خطير جداً
        No Demand في منتصف اتجاه صاعد = تحذير
        No Demand في قاع = أقل خطورة
        """
        if not bar.is_up_bar:
            return False
        
        if bar.volume_category != 'low':
            return False
        
        if bar.spread_category != 'narrow':
            return False
        
        # 🟢 تعديل 14: استخدام VW Close Position
        if bar.vw_close_position < 0.4:
            return False
        
        # 🔴 تعديل 2: الخلفية تؤثر
        if background in [MarketBackground.AT_MAJOR_TOP, MarketBackground.AT_MINOR_TOP]:
            return True  # No Demand في قمة = خطير
        
        if background == MarketBackground.IN_UPTREND:
            if index >= 20 and closes[index] > np.mean(closes[max(0,index-20):index]):
                return True
        
        return False
    
    def _is_no_supply(self, bar: VolumeBar, bars: List[VolumeBar],
                      closes: np.ndarray, index: int,
                      background: MarketBackground) -> bool:
        """
        🔴 تعديل 2: غياب العرض مع خلفية
        
        No Supply في قاع = فرصة
        No Supply في منتصف اتجاه هابط = أقل أهمية
        """
        if not bar.is_down_bar:
            return False
        
        if bar.volume_category != 'low':
            return False
        
        if bar.spread_category != 'narrow':
            return False
        
        if bar.vw_close_position > 0.6:
            return False
        
        # 🔴 تعديل 2: الخلفية تؤثر
        if background in [MarketBackground.AT_MAJOR_BOTTOM, MarketBackground.AT_MINOR_BOTTOM]:
            return True
        
        if background == MarketBackground.IN_DOWNTREND:
            if index >= 20 and closes[index] < np.mean(closes[max(0,index-20):index]):
                return True
        
        return False
    
    def _analyze_effort_result(self, bar: VolumeBar, bars: List[VolumeBar],
                                closes: np.ndarray, index: int,
                                background: MarketBackground) -> Optional[VSASignal]:
        """
        تحليل الجهد مقابل النتيجة مع خلفية
        """
        if bar.volume_category not in ['high', 'ultra_high', 'climax']:
            return None
        
        if bar.spread_category == 'narrow':
            if bar.is_up_bar and bar.vw_close_position < 0.4:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_DIVERGENCE_BULLISH,
                    direction='bearish',
                    strength=0.7,
                    confidence=0.7,
                    description="جهد صاعد كبير لكن السعر لم يتحرك - البائعون يمنعون الصعود",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="ضعف خفي",
                    background=background,
                )
            elif bar.is_down_bar and bar.vw_close_position > 0.6:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_DIVERGENCE_BEARISH,
                    direction='bullish',
                    strength=0.7,
                    confidence=0.7,
                    description="جهد هابط كبير لكن السعر لم يتحرك - المشترون يمنعون الهبوط",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="قوة خفية",
                    background=background,
                )
        
        elif bar.spread_category in ['wide', 'ultra_wide']:
            if bar.is_up_bar and bar.vw_close_position > 0.7:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_BULLISH,
                    direction='bullish',
                    strength=0.6,
                    confidence=0.65,
                    description="توافق صاعد - الحجم يؤكد الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="استمرار",
                    background=background,
                )
            elif bar.is_down_bar and bar.vw_close_position < 0.3:
                return VSASignal(
                    index=index,
                    signal_type=VSASignalType.EFFORT_BEARISH,
                    direction='bearish',
                    strength=0.6,
                    confidence=0.65,
                    description="توافق هابط - الحجم يؤكد الحركة",
                    price_level=bar.close,
                    volume_bar=bar,
                    context="استمرار",
                    background=background,
                )
        
        return None
    
    def _is_upthrust(self, bar: VolumeBar, bars: List[VolumeBar],
                     highs: np.ndarray, closes: np.ndarray, index: int,
                     background: MarketBackground) -> bool:
        """كشف الدفع العلوي مع خلفية"""
        if bar.volume_category not in ['high', 'ultra_high']:
            return False
        
        if bar.spread > 0:
            upper_wick = bar.high - max(bar.open, bar.close)
            if upper_wick < bar.spread * 0.5:
                return False
        else:
            return False
        
        if bar.close_position > 0.4:
            return False
        
        if index >= 10:
            prev_high = max(highs[index-10:index])
            if bar.high > prev_high and bar.close < prev_high:
                # أقوى في القمم
                if background in [MarketBackground.AT_MAJOR_TOP, MarketBackground.AT_MINOR_TOP,
                                  MarketBackground.IN_RANGE_HIGH]:
                    return True
                return True
        
        return False
    
    def _is_shakeout(self, bar: VolumeBar, bars: List[VolumeBar],
                     lows: np.ndarray, closes: np.ndarray, index: int,
                     background: MarketBackground) -> float:
        """
        كشف الهزة (Shakeout) مع تقييم الجودة
        
        🟢 تعديل 12: Shakeout Quality Score
        """
        if bar.volume_category not in ['high', 'ultra_high', 'climax']:
            return 0.0
        
        if bar.spread > 0:
            lower_wick = min(bar.open, bar.close) - bar.low
            if lower_wick < bar.spread * 0.5:
                return 0.0
        else:
            return 0.0
        
        if bar.close_position < 0.6:
            return 0.0
        
        if index < 10:
            return 0.0
        
        prev_low = min(lows[index-10:index])
        if not (bar.low < prev_low and bar.close > prev_low):
            return 0.0
        
        # 🟢 تعديل 12: حساب جودة Shakeout
        quality = 0.5
        
        # الحجم: climax = جودة أعلى
        if bar.volume_category == 'climax':
            quality += 0.2
        elif bar.volume_category == 'ultra_high':
            quality += 0.1
        
        # سرعة الارتداد: close_position عالي = جودة أعلى
        if bar.close_position > 0.8:
            quality += 0.2
        elif bar.close_position > 0.7:
            quality += 0.1
        
        # الموقع: في قاع = جودة أعلى
        if background in [MarketBackground.AT_MAJOR_BOTTOM, MarketBackground.AT_MINOR_BOTTOM]:
            quality += 0.15
        
        return min(1.0, quality)
    
    def _is_test(self, bar: VolumeBar, bars: List[VolumeBar],
                 lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
                 index: int, background: MarketBackground,
                 recent_signals: List[VSASignal]) -> bool:
        """
        🔴 تعديل 4: اختبار يجب أن يكون على منطقة "مهمة"
        
        - منطقة سبق أن ارتد منها السعر بقوة
        - منطقة Shakeout سابقة
        - منطقة امتصاص
        """
        if bar.volume_category != 'low':
            return False
        
        if index < 15:
            return False
        
        # 🔴 تعديل 4: البحث عن مناطق مهمة قريبة
        # 1. قاع سابق مهم (ارتداد قوي)
        for j in range(max(0, index-30), index-5):
            if lows[j] < np.mean(lows[max(0,j-5):j]) and \
               closes[j] > lows[j] * 1.005 and \
               abs(bar.low - lows[j]) / lows[j] < 0.01:
                return True
        
        # 2. منطقة Shakeout سابقة
        for sig in recent_signals[-10:]:
            if sig.signal_type == VSASignalType.SHAKEOUT and \
               abs(bar.low - sig.price_level) / sig.price_level < 0.01:
                return True
        
        return False
    
    def _is_climax(self, bar: VolumeBar, bars: List[VolumeBar],
                   closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                   index: int, background: MarketBackground) -> bool:
        """
        🔴 تعديل 5: ذروة شراء/بيع بمقارنة 50-100 شمعة
        
        Climax = قمة/قاع سعري + قمة حجمية في نفس الوقت
        """
        if bar.volume_category != 'climax':
            return False
        
        if bar.spread_category not in ['wide', 'ultra_wide']:
            return False
        
        if index < 50:
            return False
        
        # 🔴 تعديل 5: مقارنة بآخر 50 شمعة على الأقل
        lookback = min(100, index)
        
        # ذروة شراء: أعلى سعر + أعلى حجم في فترة طويلة
        if bar.is_up_bar and bar.close_position > 0.7:
            period_high = max(highs[index-lookback:index])
            period_max_vol = max(volumes[index-lookback:index])
            
            is_price_climax = bar.close >= period_high * 0.995
            is_volume_climax = bar.volume >= period_max_vol * 0.9
            
            if is_price_climax and is_volume_climax:
                return True
        
        # ذروة بيع: أدنى سعر + أعلى حجم في فترة طويلة
        if bar.is_down_bar and bar.close_position < 0.3:
            period_low = min(lows[index-lookback:index])
            period_max_vol = max(volumes[index-lookback:index])
            
            is_price_climax = bar.close <= period_low * 1.005
            is_volume_climax = bar.volume >= period_max_vol * 0.9
            
            if is_price_climax and is_volume_climax:
                return True
        
        return False
    
    def _is_volume_climax(self, bar: VolumeBar, bars: List[VolumeBar],
                          closes: np.ndarray, volumes: np.ndarray, index: int,
                          background: MarketBackground) -> bool:
        """
        🟡 تعديل 6: Volume Climax منفصل عن Stopping Volume
        
        أعلى حجم في 50 شمعة دون انعكاس فوري = تحذير من انعكاس قريب
        """
        if index < 50:
            return False
        
        if bar.volume_category not in ['ultra_high', 'climax']:
            return False
        
        # أعلى حجم في 50 شمعة
        period_max_vol = max(volumes[max(0,index-50):index+1])
        
        if bar.volume >= period_max_vol * 0.95:
            return True
        
        return False
    
    def _is_absorption(self, bar: VolumeBar, bars: List[VolumeBar],
                       closes: np.ndarray, index: int,
                       background: MarketBackground) -> Optional[VSASignal]:
        """
        🟡 تعديل 7: تمييز Absorption تجميعي عن توزيعي
        
        Absorption في أسفل النطاق = تجميع
        Absorption في أعلى النطاق = توزيع
        """
        if bar.volume_category not in ['high', 'ultra_high']:
            return None
        
        if bar.spread_category != 'narrow':
            return None
        
        if not (0.35 < bar.close_position < 0.65):
            return None
        
        # 🟡 تعديل 7: تحديد النوع حسب الموقع
        if background in [MarketBackground.AT_MAJOR_BOTTOM, MarketBackground.AT_MINOR_BOTTOM,
                          MarketBackground.IN_RANGE_LOW]:
            sig_type = VSASignalType.ABSORPTION_ACCUMULATION
            direction = 'bullish'
            desc = "امتصاص تجميعي - المؤسسات تشتري في القاع"
        elif background in [MarketBackground.AT_MAJOR_TOP, MarketBackground.AT_MINOR_TOP,
                            MarketBackground.IN_RANGE_HIGH]:
            sig_type = VSASignalType.ABSORPTION_DISTRIBUTION
            direction = 'bearish'
            desc = "امتصاص توزيعي - المؤسسات تبيع في القمة"
        else:
            sig_type = VSASignalType.ABSORPTION
            direction = 'neutral'
            desc = "امتصاص - تجميع/توزيع صامت"
        
        return VSASignal(
            index=index,
            signal_type=sig_type,
            direction=direction,
            strength=0.6,
            confidence=0.6,
            description=desc,
            price_level=bar.close,
            volume_bar=bar,
            context="تجميع/توزيع صامت",
            background=background,
        )
    
    def _is_push_through(self, bar: VolumeBar, bars: List[VolumeBar],
                         highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                         index: int, background: MarketBackground) -> Optional[VSASignal]:
        """
        🟡 تعديل 9: Pushing Through Supply/Demand
        
        اختراق مستوى بحجم مرتفع وانتشار واسع وإغلاق قوي
        """
        if bar.volume_category not in ['high', 'ultra_high', 'climax']:
            return None
        
        if bar.spread_category not in ['wide', 'ultra_wide']:
            return None
        
        if index < 15:
            return None
        
        # اختراق مقاومة للأعلى
        prev_high = max(highs[index-15:index])
        if bar.close > prev_high and bar.is_up_bar and bar.close_position > 0.7:
            return VSASignal(
                index=index,
                signal_type=VSASignalType.PUSH_THROUGH_SUPPLY,
                direction='bullish',
                strength=0.75,
                confidence=0.7,
                description="اختراق عرض بحجم مرتفع - قوة شرائية حقيقية",
                price_level=bar.close,
                volume_bar=bar,
                context="اختراق حقيقي",
                background=background,
            )
        
        # كسر دعم للأسفل
        prev_low = min(lows[index-15:index])
        if bar.close < prev_low and bar.is_down_bar and bar.close_position < 0.3:
            return VSASignal(
                index=index,
                signal_type=VSASignalType.PUSH_THROUGH_DEMAND,
                direction='bearish',
                strength=0.75,
                confidence=0.7,
                description="كسر طلب بحجم مرتفع - قوة بيعية حقيقية",
                price_level=bar.close,
                volume_bar=bar,
                context="كسر حقيقي",
                background=background,
            )
        
        return None
    
    def _detect_volume_dry_up(self, bars: List[VolumeBar], volumes: np.ndarray,
                               closes: np.ndarray) -> List[VSASignal]:
        """
        🟡 تعديل 8: كشف جفاف الحجم التدريجي
        
        الحجم ينخفض تدريجياً على 10-15 شمعة = انفجار قادم
        """
        signals = []
        
        if len(volumes) < 15:
            return signals
        
        # فحص آخر 15 شمعة
        recent_vols = volumes[-15:]
        
        if len(recent_vols) < 10:
            return signals
        
        # حساب معدل الانحدار
        x = np.arange(len(recent_vols))
        slope = np.polyfit(x, recent_vols, 1)[0]
        
        avg_vol = np.mean(volumes[-50:]) if len(volumes) >= 50 else np.mean(volumes)
        
        if avg_vol == 0:
            return signals
        
        # هل الحجم ينخفض تدريجياً؟
        slope_normalized = slope / avg_vol
        
        if slope_normalized < -0.02:  # انحدار سلبي ملحوظ
            # تأكيد: الحجم في النصف الثاني أقل من النصف الأول
            first_half = np.mean(recent_vols[:len(recent_vols)//2])
            second_half = np.mean(recent_vols[len(recent_vols)//2:])
            
            if first_half > 0 and second_half / first_half < 0.7:
                bar = bars[-1]
                signals.append(VSASignal(
                    index=len(closes) - 1,
                    signal_type=VSASignalType.VOLUME_DRY_UP,
                    direction='neutral',
                    strength=0.55,
                    confidence=0.6,
                    description=f"جفاف حجم تدريجي ({len(recent_vols)} شمعة) - انفجار قادم",
                    price_level=closes[-1],
                    volume_bar=bar,
                    context="استعداد للحركة",
                    background=MarketBackground.UNKNOWN,
                ))
        
        return signals
    
    def _analyze_cumulative_effort(self, bars: List[VolumeBar], closes: np.ndarray,
                                    volumes: np.ndarray) -> List[VSASignal]:
        """
        🟢 تعديل 13: Cumulative Effort vs Cumulative Result
        
        جمع الجهد والنتيجة عبر 5-10 شموع تراكمياً
        """
        signals = []
        
        if len(closes) < 10:
            return signals
        
        # آخر 8 شموع
        window = 8
        recent_bars = bars[-window:]
        recent_closes = closes[-window:]
        
        cumulative_volume = sum(b.volume for b in recent_bars)
        cumulative_price_change = abs(recent_closes[-1] - recent_closes[0])
        
        avg_vol = np.mean(volumes[-50:]) if len(volumes) >= 50 else np.mean(volumes)
        
        if avg_vol == 0:
            return signals
        
        expected_move = (cumulative_volume / (avg_vol * window)) * np.mean(highs[-window:] - lows[-window:])
        
        if expected_move > 0:
            effort_result_ratio = cumulative_price_change / expected_move
        else:
            effort_result_ratio = 1.0
        
        # جهد تراكمي كبير + نتيجة صغيرة = انعكاس
        if cumulative_volume > avg_vol * window * 1.3 and effort_result_ratio < 0.5:
            bar = bars[-1]
            direction = 'bearish' if closes[-1] > closes[-window] else 'bullish'
            signals.append(VSASignal(
                index=len(closes) - 1,
                signal_type=VSASignalType.EFFORT_DIVERGENCE_BULLISH if direction == 'bearish' else VSASignalType.EFFORT_DIVERGENCE_BEARISH,
                direction=direction,
                strength=0.75,
                confidence=0.7,
                description=f"جهد تراكمي كبير (×{cumulative_volume/(avg_vol*window):.1f}) بنتيجة ضئيلة - انعكاس",
                price_level=closes[-1],
                volume_bar=bar,
                context="انحراف تراكمي",
                background=MarketBackground.UNKNOWN,
            ))
        
        return signals
    
    def _apply_signal_sequencing(self, signals: List[VSASignal]) -> List[VSASignal]:
        """
        🔴 تعديل 1: تحليل تسلسل الإشارات (Signal Sequencing)
        
        يبحث عن أنماط من إشارتين أو ثلاث إشارات متتالية تعزز بعضها
        """
        if len(signals) < 2:
            return signals
        
        for i in range(1, len(signals)):
            current = signals[i]
            prev = signals[i-1]
            
            # المسافة بين الإشارات يجب أن تكون قريبة (خلال 5 شموع)
            if current.index - prev.index > 5:
                continue
            
            boost = 0.0
            
            # Shakeout + Test = تأكيد مزدوج
            if prev.signal_type == VSASignalType.SHAKEOUT and current.signal_type == VSASignalType.TEST:
                boost = 0.3
                current.description += " [تأكيد بعد Shakeout]"
            
            # No Supply + Stopping Volume = انعكاس قوي
            elif prev.signal_type == VSASignalType.NO_SUPPLY and current.signal_type == VSASignalType.STOPPING_VOLUME:
                boost = 0.25
                current.description += " [تأكيد انعكاس]"
            
            # Upthrust + No Demand = توزيع مؤكد
            elif prev.signal_type == VSASignalType.UPTHRUST and current.signal_type == VSASignalType.NO_DEMAND:
                boost = 0.35
                current.description += " [توزيع مؤكد]"
            
            # Volume Climax + Effort Divergence = انعكاس عنيف
            elif prev.signal_type == VSASignalType.VOLUME_CLIMAX and \
                 current.signal_type in [VSASignalType.EFFORT_DIVERGENCE_BULLISH, VSASignalType.EFFORT_DIVERGENCE_BEARISH]:
                boost = 0.3
                current.description += " [ذروة + انحراف]"
            
            # Absorption Accumulation + Push Through Supply = تجميع ثم انطلاق
            elif prev.signal_type in [VSASignalType.ABSORPTION_ACCUMULATION, VSASignalType.ABSORPTION] and \
                 current.signal_type == VSASignalType.PUSH_THROUGH_SUPPLY:
                boost = 0.3
                current.description += " [تجميع ثم انطلاق]"
            
            # Cumulative Effort + Stopping Volume = تأكيد قوي
            elif prev.signal_type in [VSASignalType.EFFORT_DIVERGENCE_BULLISH, VSASignalType.EFFORT_DIVERGENCE_BEARISH] and \
                 current.signal_type == VSASignalType.STOPPING_VOLUME:
                boost = 0.25
                current.description += " [انحراف + توقف]"
            
            if boost > 0:
                current.strength = min(1.0, current.strength + boost)
                current.confidence = min(1.0, current.confidence + boost)
                current.sequence_boost = boost
        
        return signals
    
    def _apply_decay_factors(self, signals: List[VSASignal], data_length: int) -> List[VSASignal]:
        """
        🟡 تعديل 10: تطبيق عامل الاضمحلال (Shelf Life)
        
        - Shakeout: يفقد 5% كل 5 شموع، يستمر 30 شمعة
        - No Demand/No Supply: يفقد 8% كل 5 شموع، يستمر 15 شمعة
        - Stopping Volume: يفقد 5% كل 5 شموع، يستمر 25 شمعة
        - Test: يفقد 10% كل 5 شموع، يستمر 10 شموع
        """
        for signal in signals:
            bars_since = data_length - signal.index
            
            if bars_since <= 0:
                signal.decay_factor = 1.0
                continue
            
            # كل نوع إشارة له عمر افتراضي مختلف
            if signal.signal_type in [VSASignalType.SHAKEOUT, VSASignalType.STOPPING_VOLUME]:
                decay_per_5_bars = 0.05
                max_life = 30
            elif signal.signal_type in [VSASignalType.CLIMAX_BUYING, VSASignalType.CLIMAX_SELLING,
                                         VSASignalType.VOLUME_CLIMAX]:
                decay_per_5_bars = 0.06
                max_life = 25
            elif signal.signal_type in [VSASignalType.NO_DEMAND, VSASignalType.NO_SUPPLY]:
                decay_per_5_bars = 0.08
                max_life = 15
            elif signal.signal_type == VSASignalType.TEST:
                decay_per_5_bars = 0.10
                max_life = 10
            elif signal.signal_type == VSASignalType.UPTHRUST:
                decay_per_5_bars = 0.05
                max_life = 20
            elif signal.signal_type in [VSASignalType.ABSORPTION, VSASignalType.ABSORPTION_ACCUMULATION,
                                         VSASignalType.ABSORPTION_DISTRIBUTION]:
                decay_per_5_bars = 0.04
                max_life = 35
            elif signal.signal_type in [VSASignalType.PUSH_THROUGH_SUPPLY, VSASignalType.PUSH_THROUGH_DEMAND]:
                decay_per_5_bars = 0.07
                max_life = 20
            elif signal.signal_type == VSASignalType.VOLUME_DRY_UP:
                decay_per_5_bars = 0.06
                max_life = 15
            else:
                decay_per_5_bars = 0.06
                max_life = 20
            
            periods = bars_since // 5
            decay = decay_per_5_bars * periods
            
            if bars_since > max_life:
                signal.decay_factor = 0.0
            else:
                signal.decay_factor = max(0.1, 1.0 - decay)
            
            # تطبيق الاضمحلال على القوة
            signal.strength *= signal.decay_factor
            signal.confidence *= signal.decay_factor
        
        return signals
    
    def _summarize_signals(self, signals: List[VSASignal]) -> Dict:
        """تلخيص الإشارات الحديثة مع مراعاة الاضمحلال"""
        if not signals:
            return {"dominant": "لا إشارات", "bias": "محايد"}
        
        # الإشارات التي ما زالت "حية"
        active_signals = [s for s in signals if s.decay_factor > 0.2]
        
        if not active_signals:
            return {"dominant": "الإشارات منتهية الصلاحية", "bias": "محايد"}
        
        bullish_count = sum(1 for s in active_signals if s.direction == 'bullish')
        bearish_count = sum(1 for s in active_signals if s.direction == 'bearish')
        
        avg_strength_bullish = np.mean([s.strength for s in active_signals if s.direction == 'bullish']) if bullish_count > 0 else 0
        avg_strength_bearish = np.mean([s.strength for s in active_signals if s.direction == 'bearish']) if bearish_count > 0 else 0
        
        bullish_power = bullish_count * avg_strength_bullish
        bearish_power = bearish_count * avg_strength_bearish
        
        if bullish_power > bearish_power * 1.5:
            bias = "صاعد"
        elif bearish_power > bullish_power * 1.5:
            bias = "هابط"
        else:
            bias = "محايد"
        
        return {
            "dominant": "صاعد" if bullish_power > bearish_power else "هابط" if bearish_power > bullish_power else "متوازن",
            "bias": bias,
            "bullish_power": bullish_power,
            "bearish_power": bearish_power,
            "active_signals": len(active_signals),
            "expired_signals": len(signals) - len(active_signals),
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: محلل اتجاه الحجم (Volume Trend Analyzer)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VolumeTrendAnalyzer:
    """
    يحلل اتجاه الحجم عبر الزمن.
    الحجم يسبق السعر - تغير الحجم ينذر بتغير الاتجاه.
    """
    
    def analyze(self, volumes: np.ndarray, closes: np.ndarray) -> Dict:
        """
        تحليل اتجاهات الحجم
        """
        overall_trend = self._analyze_overall_trend(volumes)
        volume_price_relationship = self._analyze_volume_price(volumes, closes)
        divergences = self._detect_volume_price_divergence(volumes, closes)
        
        return {
            "overall_trend": overall_trend,
            "volume_price": volume_price_relationship,
            "divergences": divergences[-5:],
        }
    
    def _analyze_overall_trend(self, volumes: np.ndarray) -> VolumeTrend:
        """تحليل الاتجاه العام للحجم"""
        if len(volumes) < 20:
            return VolumeTrend(trend_type='stable', intensity=0.3, duration=0, significance='normal')
        
        recent = volumes[-10:]
        older = volumes[-20:-10]
        
        avg_recent = np.mean(recent)
        avg_older = np.mean(older)
        
        if avg_older == 0:
            ratio = 1.0
        else:
            ratio = avg_recent / avg_older
        
        if ratio > 1.5:
            trend_type = 'increasing'
            intensity = min(1.0, ratio / 3)
            significance = 'important' if ratio > 2.0 else 'normal'
        elif ratio < 0.5:
            trend_type = 'drying'
            intensity = min(1.0, 1 - ratio)
            significance = 'important' if ratio < 0.3 else 'normal'
        elif np.std(recent) > np.mean(recent) * 0.5:
            trend_type = 'spiking'
            intensity = 0.6
            significance = 'important'
        else:
            trend_type = 'stable'
            intensity = 0.3
            significance = 'normal'
        
        return VolumeTrend(
            trend_type=trend_type,
            intensity=intensity,
            duration=len(volumes),
            significance=significance,
        )
    
    def _analyze_volume_price(self, volumes: np.ndarray, closes: np.ndarray) -> Dict:
        """تحليل علاقة الحجم بالسعر"""
        if len(closes) < 20:
            return {"relationship": "غير كافٍ"}
        
        recent_closes = closes[-20:]
        recent_volumes = volumes[-20:]
        
        up_bars_vol = []
        down_bars_vol = []
        
        for i in range(1, len(recent_closes)):
            if recent_closes[i] > recent_closes[i-1]:
                up_bars_vol.append(recent_volumes[i])
            else:
                down_bars_vol.append(recent_volumes[i])
        
        avg_up_vol = np.mean(up_bars_vol) if up_bars_vol else 0
        avg_down_vol = np.mean(down_bars_vol) if down_bars_vol else 0
        
        if avg_down_vol > 0:
            vol_ratio = avg_up_vol / avg_down_vol
        else:
            vol_ratio = 1.0
        
        if vol_ratio > 1.3:
            relationship = "حجم الصعود أعلى - اهتمام بالشراء"
        elif vol_ratio < 0.7:
            relationship = "حجم الهبوط أعلى - اهتمام بالبيع"
        else:
            relationship = "متوازن"
        
        return {
            "relationship": relationship,
            "up_volume_avg": avg_up_vol,
            "down_volume_avg": avg_down_vol,
            "ratio": vol_ratio,
        }
    
    def _detect_volume_price_divergence(self, volumes: np.ndarray, 
                                         closes: np.ndarray) -> List[Dict]:
        """اكتشاف تباعد الحجم عن السعر"""
        divergences = []
        
        if len(closes) < 15:
            return divergences
        
        for i in range(10, len(closes) - 5):
            price_change = closes[i+5] - closes[i]
            vol_change = np.mean(volumes[i+1:i+6]) - np.mean(volumes[i-4:i+1])
            
            if price_change > 0 and vol_change < 0 and abs(vol_change) > np.mean(volumes) * 0.3:
                divergences.append({
                    "index": i,
                    "type": "bearish_divergence",
                    "description": "سعر يصعد وحجم ينخفض - ضعف الصعود",
                    "strength": 0.65,
                })
            
            if price_change < 0 and vol_change < 0 and abs(vol_change) > np.mean(volumes) * 0.3:
                divergences.append({
                    "index": i,
                    "type": "bullish_divergence",
                    "description": "سعر ينخفض وحجم ينخفض - ضعف الهبوط",
                    "strength": 0.65,
                })
        
        return divergences


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         الدرجة الثالثة: مراحل السوق من منظور VSA                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSAMarketPhaseAnalyzer:
    """
    يحدد مرحلة السوق من خلال تحليل VSA.
    تجميع، توزيع، اتجاه، قمة، قاع.
    """
    
    def analyze(self, signals: List[VSASignal], bars: List[VolumeBar],
                closes: np.ndarray) -> Dict:
        """
        تحديد مرحلة السوق
        """
        phase = self._determine_phase(signals, bars, closes)
        
        return {
            "current_phase": phase,
            "phase_confidence": self._phase_confidence(phase, signals),
            "phase_description": self._describe_phase(phase),
        }
    
    def _determine_phase(self, signals: List[VSASignal], bars: List[VolumeBar],
                         closes: np.ndarray) -> str:
        """تحديد المرحلة الحالية"""
        if not signals:
            return "غير محدد"
        
        # الإشارات النشطة فقط
        active = [s for s in signals[-30:] if s.decay_factor > 0.2]
        
        if not active:
            return "غير محدد"
        
        signal_counts = {}
        for s in active:
            key = s.signal_type.value
            signal_counts[key] = signal_counts.get(key, 0) + 1
        
        if len(closes) >= 20:
            trend = "up" if closes[-1] > closes[-10] else "down" if closes[-1] < closes[-10] else "sideways"
        else:
            trend = "unknown"
        
        # قمة: ذروة شراء + Upthrusts + No Demand + Absorption Distribution
        climax_buying = signal_counts.get(VSASignalType.CLIMAX_BUYING.value, 0)
        upthrusts = signal_counts.get(VSASignalType.UPTHRUST.value, 0)
        no_demand = signal_counts.get(VSASignalType.NO_DEMAND.value, 0)
        abs_dist = signal_counts.get(VSASignalType.ABSORPTION_DISTRIBUTION.value, 0)
        
        if climax_buying >= 1 or upthrusts >= 1 or no_demand >= 2 or abs_dist >= 1:
            if trend == "up" or closes[-1] > np.mean(closes[-50:]):
                return "توزيع - قمة محتملة"
        
        # قاع: ذروة بيع + Shakeout + No Supply + Stopping Volume + Absorption Accumulation
        climax_selling = signal_counts.get(VSASignalType.CLIMAX_SELLING.value, 0)
        shakeouts = signal_counts.get(VSASignalType.SHAKEOUT.value, 0)
        no_supply = signal_counts.get(VSASignalType.NO_SUPPLY.value, 0)
        stopping = signal_counts.get(VSASignalType.STOPPING_VOLUME.value, 0)
        abs_acc = signal_counts.get(VSASignalType.ABSORPTION_ACCUMULATION.value, 0)
        
        if climax_selling >= 1 or shakeouts >= 1 or no_supply >= 2 or stopping >= 1 or abs_acc >= 1:
            if trend == "down" or closes[-1] < np.mean(closes[-50:]):
                return "تجميع - قاع محتمل"
        
        # اتجاه: توافق الجهد
        effort_bullish = signal_counts.get(VSASignalType.EFFORT_BULLISH.value, 0)
        effort_bearish = signal_counts.get(VSASignalType.EFFORT_BEARISH.value, 0)
        push_supply = signal_counts.get(VSASignalType.PUSH_THROUGH_SUPPLY.value, 0)
        push_demand = signal_counts.get(VSASignalType.PUSH_THROUGH_DEMAND.value, 0)
        
        if effort_bullish + push_supply > effort_bearish + push_demand:
            return "اتجاه صاعد - حجم يؤكد"
        elif effort_bearish + push_demand > effort_bullish + push_supply:
            return "اتجاه هابط - حجم يؤكد"
        
        # امتصاص = تجميع/توزيع صامت
        absorption = signal_counts.get(VSASignalType.ABSORPTION.value, 0)
        if absorption >= 3:
            return "امتصاص - تجميع أو توزيع"
        
        # جفاف حجم = انفجار قادم
        dry_up = signal_counts.get(VSASignalType.VOLUME_DRY_UP.value, 0)
        if dry_up >= 1:
            return "جفاف حجم - انفجار قادم"
        
        return "غير محدد"
    
    def _phase_confidence(self, phase: str, signals: List[VSASignal]) -> float:
        """ثقة تحديد المرحلة"""
        if phase == "غير محدد":
            return 0.2
        
        if not signals:
            return 0.3
        
        active = [s for s in signals[-20:] if s.decay_factor > 0.3]
        strong_signals = [s for s in active if s.strength > 0.7]
        
        return min(0.9, 0.4 + len(strong_signals) * 0.1)
    
    def _describe_phase(self, phase: str) -> str:
        """وصف المرحلة بالعربية"""
        descriptions = {
            "توزيع - قمة محتملة": "السوق يظهر علامات توزيع. الحجم على الصعود يضعف. كن حذراً من انعكاس هابط.",
            "تجميع - قاع محتمل": "السوق يظهر علامات تجميع. الحجم على الهبوط يضعف. فرصة صعود قريبة.",
            "اتجاه صاعد - حجم يؤكد": "الحجم يؤكد الصعود. المؤسسات تشتري. استمر مع الاتجاه.",
            "اتجاه هابط - حجم يؤكد": "الحجم يؤكد الهبوط. المؤسسات تبيع. استمر مع الاتجاه.",
            "امتصاص - تجميع أو توزيع": "المؤسسات تمتص الأوامر بهدوء. راقب الاختراق القادم.",
            "جفاف حجم - انفجار قادم": "الحجم يجف تدريجياً. انفجار سعري قريب. استعد للحركة.",
        }
        return descriptions.get(phase, "المرحلة غير واضحة، انتظر تأكيداً.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║              الدرجة النهائية: استراتيجية VSA الموحدة                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class VSAStrategy:
    """
    استراتيجية تحليل الحجم والانتشار الكاملة (الإصدار 2.0)
    
    تجمع:
    - تحليل كل شمعة (Bar-by-Bar) مع خلفية وتسلسل
    - اتجاهات الحجم
    - مراحل السوق
    - مستويات الدعم والمقاومة
    
    في قرار تداولي واحد.
    """
    
    def __init__(self):
        self.bar_analyzer = BarByBarVSAAnalyzer()
        self.trend_analyzer = VolumeTrendAnalyzer()
        self.phase_analyzer = VSAMarketPhaseAnalyzer()
        self.sr_analyzer = SupportResistanceAnalyzer()
    
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
        
        # 0. مستويات الدعم والمقاومة
        sr_levels = self.sr_analyzer.analyze(highs, lows, closes)
        
        # 1. تحليل الشموع
        bar_data = self.bar_analyzer.analyze(opens, highs, lows, closes, volumes, sr_levels)
        
        # 2. تحليل اتجاه الحجم
        trend_data = self.trend_analyzer.analyze(volumes, closes)
        
        # 3. مرحلة السوق
        recent_signals = bar_data.get('recent_signals', [])
        recent_bars = bar_data.get('recent_bars', [])
        phase_data = self.phase_analyzer.analyze(recent_signals, recent_bars, closes)
        
        # 4. القرار
        decision = self._make_decision(bar_data, trend_data, phase_data, closes)
        
        return {
            **decision,
            "bar_data": bar_data,
            "trend_data": trend_data,
            "phase_data": phase_data,
            "sr_levels": [
                {"price": l.price, "type": l.level_type, "strength": l.strength, "is_major": l.is_major}
                for l in sr_levels[-10:]
            ],
        }
    
    def _make_decision(self, bar_data: Dict, trend_data: Dict,
                       phase_data: Dict, closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار مع مراعاة الاضمحلال والتسلسل
        """
        buy_signals = []
        sell_signals = []
        
        # ---- من الإشارات الحديثة (النشطة فقط) ----
        recent_signals = bar_data.get('recent_signals', [])
        signal_summary = bar_data.get('signal_summary', {})
        
        for s in recent_signals[-15:]:
            if s.decay_factor < 0.3:
                continue  # إشارة منتهية الصلاحية
            
            weight = s.strength * s.confidence * s.decay_factor * 0.5
            
            # 🟢 تعديل 11: مضاعفة الوزن عند دعم/مقاومة
            if s.at_support_resistance:
                weight *= s.sr_strength_multiplier * 1.3
            
            # 🔴 تعديل 1: مضاعفة الوزن إذا كان هناك تسلسل
            if s.sequence_boost > 0:
                weight *= 1.3
            
            if s.direction == 'bullish':
                buy_signals.append((f"{s.description[:50]} [عمر:{s.decay_factor:.0%}]", weight))
            elif s.direction == 'bearish':
                sell_signals.append((f"{s.description[:50]} [عمر:{s.decay_factor:.0%}]", weight))
        
        # ---- من اتجاه الحجم ----
        overall_trend = trend_data.get('overall_trend', VolumeTrend('stable', 0, 0, 'normal'))
        vol_price = trend_data.get('volume_price', {})
        
        if overall_trend.trend_type == 'drying' and overall_trend.significance == 'important':
            if len(closes) >= 10 and closes[-1] < closes[-10]:
                buy_signals.append(("حجم يجف على هبوط - انعكاس صعودي قريب", 0.5))
            elif len(closes) >= 10 and closes[-1] > closes[-10]:
                sell_signals.append(("حجم يجف على صعود - انعكاس هبوطي قريب", 0.5))
        
        if vol_price.get('relationship') == "حجم الصعود أعلى - اهتمام بالشراء":
            buy_signals.append(("حجم يصب في صالح الصعود", 0.4))
        elif vol_price.get('relationship') == "حجم الهبوط أعلى - اهتمام بالبيع":
            sell_signals.append(("حجم يصب في صالح الهبوط", 0.4))
        
        # ---- من المرحلة ----
        current_phase = phase_data.get('current_phase', 'غير محدد')
        
        if current_phase == "تجميع - قاع محتمل":
            buy_signals.append(("VSA: مرحلة تجميع", 0.65))
        elif current_phase == "توزيع - قمة محتملة":
            sell_signals.append(("VSA: مرحلة توزيع", 0.65))
        elif current_phase == "اتجاه صاعد - حجم يؤكد":
            buy_signals.append(("VSA: اتجاه صاعد مؤكد", 0.6))
        elif current_phase == "اتجاه هابط - حجم يؤكد":
            sell_signals.append(("VSA: اتجاه هابط مؤكد", 0.6))
        elif current_phase == "جفاف حجم - انفجار قادم":
            buy_signals.append(("جفاف حجم - ترقب صعود", 0.45))
            sell_signals.append(("جفاف حجم - ترقب هبوط", 0.45))
        
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
        reason += f" | المرحلة: {current_phase}"
        reason += f" | نشط:{signal_summary.get('active_signals', 0)}"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "phase": current_phase,
        }


def create_vsa_strategy():
    """إنشاء استراتيجية VSA الجاهزة (الإصدار 2.0 المعدل)"""
    return VSAStrategy()