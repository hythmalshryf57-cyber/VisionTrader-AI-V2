"""
═══════════════════════════════════════════════════════════════════════════════
PSYCHOLOGICAL ENGINEERING STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الرابعة والثلاثون: هندسة علم النفس في التداول
═══════════════════════════════════════════════════════════════════════════════

أكبر عدو للمتداول هو نفسه. هذه الاستراتيجية:
1. تحلل سيكولوجية السوق من السعر + البيانات الحقيقية
2. تكتشف مراحل العواطف في الشارت
3. تحدد "مناطق الألم النفسي" الحية
4. تقيس الاقتناع والتردد
5. تراقب "عتبات الألم" وتكسرها
6. تتكامل مع psychology_engine.py و social_sentiment_strategy.py

مراحل العواطف في السوق (دورة متكررة):
1. الاستسلام (Capitulation) - القاع
2. الاكتئاب (Depression) - لا أمل
3. الأمل (Hope) - بداية الحركة
4. التفاؤل (Optimism) - تأكيد الحركة
5. الإثارة (Excitement) - تسارع
6. النشوة (Euphoria) - القمة
7. القلق (Anxiety) - أول تراجع
8. الإنكار (Denial) - رفض التصديق
9. الخوف (Fear) - تسارع الهبوط
10. الذعر (Panic) - القاع

المفاهيم المتقدمة (الإصدار 2.0):
1. Emotional Cycle Detection (ديناميكي)
2. Real + Implied Sentiment Fusion
3. Commitment Analysis (اعتقاد vs فعل)
4. Hesitation Detection
5. Greed/Fear Oscillation
6. Pain Threshold Mapping (حي)
7. Psychological Support/Resistance
8. Investor Regret Zones (حية)
9. Emotional Divergence
10. Emotional Momentum (سرعة تغير المشاعر)
11. Emotional Cycle Completion Prediction
12. Pain Threshold Breach Detection
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المحسنة                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class EmotionalState:
    """حالة عاطفية للسوق - نسخة محسنة"""
    primary_emotion: str
    intensity: float
    cycle_position: float
    fomo_level: float
    capitulation_risk: float
    greed_index: float
    fear_index: float
    conviction: float
    hesitation: float
    pain_level: float
    # 🟡 تعديل 10: زخم عاطفي
    emotional_velocity: float = 0.0
    # 🟡 تعديل 8: تباعد عاطفي
    emotional_divergence: float = 0.0
    # 🔴 تعديل 1: مشاعر حقيقية (من psychology_engine)
    real_sentiment: float = 0.0
    real_sentiment_source: str = 'none'
    # مشاعر مدمجة
    fused_sentiment: float = 0.5


@dataclass
class PsychologicalZone:
    """منطقة نفسية - نسخة محسنة"""
    price: float
    zone_type: str
    strength: float
    emotional_weight: float
    description: str
    created_at_index: int
    last_touched_index: int = -1
    is_active: bool = True
    # 🟢 تعديل 12: هل السعر حالياً عند هذه المنطقة؟
    price_at_zone: bool = False


@dataclass
class PainThreshold:
    """عتبة ألم نفسي"""
    price: float
    pain_level: float
    volume: float
    breached: bool = False
    breach_index: int = -1
    recovery_index: int = -1


@dataclass
class EmotionalCycle:
    """دورة عاطفية كاملة"""
    cycle_number: int
    start_index: int
    end_index: int
    duration: int
    min_price: float
    max_price: float
    phases: List[Dict]  # قائمة المراحل التي مرت بها الدورة
    completed: bool


@dataclass
class PsychSignal:
    """إشارة نفسية"""
    index: int
    signal_type: str
    direction: str
    strength: float
    emotion: str
    description: str
    real_sentiment_confirm: bool = False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: جسر البيانات النفسية الحقيقية                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PsychologyDataBridge:
    """
    🔴 تعديل 1 + 🟡 تعديل 6: جسر إلى البيانات النفسية الحقيقية
    
    يحاول استيراد:
    - psychology_engine.py من services/
    - social_sentiment_strategy.py للحصول على مشاعر حقيقية
    """
    
    def __init__(self):
        self.psychology_engine = None
        self.social_sentiment_strategy = None
        self._init_connections()
    
    def _init_connections(self):
        """محاولة الاتصال بمصادر البيانات الحقيقية"""
        # محاولة استيراد psychology_engine
        try:
            from services.psychology_engine import PsychologyEngine
            self.psychology_engine = PsychologyEngine(user_id=None)
            logger.info("✅ تم ربط PsychologyEngine الحقيقي")
        except ImportError:
            logger.info("ℹ️ PsychologyEngine غير متاح - استخدام التحليل الضمني فقط")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تهيئة PsychologyEngine: {e}")
        
        # محاولة استيراد social_sentiment_strategy
        try:
            from strategies.social_sentiment_strategy import SocialSentimentStrategy
            self.social_sentiment_strategy = SocialSentimentStrategy()
            logger.info("✅ تم ربط SocialSentimentStrategy للحصول على مشاعر حقيقية")
        except ImportError:
            logger.info("ℹ️ SocialSentimentStrategy غير متاحة")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تهيئة SocialSentimentStrategy: {e}")
    
    def get_real_psychology_data(self, symbol: str = "BTCUSD") -> Dict:
        """
        جلب بيانات نفسية حقيقية من المصادر المتاحة
        """
        result = {
            "real_fear_greed": None,
            "real_sentiment": None,
            "trader_pain_index": None,
            "confidence_index": None,
            "source": "none",
        }
        
        # من psychology_engine
        if self.psychology_engine:
            try:
                psych_data = self.psychology_engine.get_current_state(symbol)
                if psych_data:
                    result["real_fear_greed"] = psych_data.get('fear_greed_index')
                    result["trader_pain_index"] = psych_data.get('pain_index')
                    result["confidence_index"] = psych_data.get('confidence')
                    result["source"] = 'psychology_engine'
            except Exception as e:
                logger.warning(f"تعذر جلب بيانات psychology_engine: {e}")
        
        # من social_sentiment_strategy (للحصول على مشاعر حقيقية)
        if self.social_sentiment_strategy:
            try:
                sentiment_result = self.social_sentiment_strategy.analyze({
                    'closes': [], 'highs': [], 'lows': [], 'volumes': [], 'symbol': symbol,
                })
                if sentiment_result and 'sentiment_data' in sentiment_result:
                    sent_data = sentiment_result['sentiment_data']
                    if sent_data and 'sentiment_score' in sent_data:
                        score = sent_data['sentiment_score']
                        if hasattr(score, 'overall_sentiment'):
                            result["real_sentiment"] = score.overall_sentiment
                        if hasattr(score, 'fear_greed_index'):
                            result["real_fear_greed"] = result["real_fear_greed"] or score.fear_greed_index
                        if not result["source"] or result["source"] == 'none':
                            result["source"] = 'social_sentiment'
            except Exception as e:
                logger.warning(f"تعذر جلب بيانات social_sentiment: {e}")
        
        return result


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل الحالة العاطفية (محسن بالكامل)                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class EmotionalStateAnalyzer:
    """
    يحلل الحالة العاطفية للسوق.
    
    🔴 تعديل 3: نطاق الدورة ديناميكي
    🔴 تعديل 4: فترات ديناميكية
    🟡 تعديل 8: Emotional Divergence
    🟡 تعديل 10: Emotional Momentum
    """
    
    EMOTIONS = [
        'استسلام', 'اكتئاب', 'أمل', 'تفاؤل', 'إثارة',
        'نشوة', 'قلق', 'إنكار', 'خوف', 'ذعر'
    ]
    
    def __init__(self):
        self.data_bridge = PsychologyDataBridge()
        self.emotion_history = deque(maxlen=200)
        self.pain_thresholds: List[PainThreshold] = []
        self.emotional_cycles: List[EmotionalCycle] = []
        self.cycle_counter = 0
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, symbol: str = "BTCUSD") -> Dict:
        """تحليل الحالة العاطفية الكامل"""
        
        if len(closes) < 30:
            return {"emotion": None, "error": "بيانات غير كافية"}
        
        # 🔴 تعديل 3: نطاق ديناميكي
        dynamic_window = self._calculate_dynamic_window(closes)
        
        # 🔴 تعديل 4: فترات ديناميكية
        periods = self._calculate_dynamic_periods(closes)
        
        # 🔴 تعديل 1: جلب بيانات نفسية حقيقية
        real_psych = self.data_bridge.get_real_psychology_data(symbol)
        
        # تحليل المشاعر الضمنية من السعر
        implied = self._analyze_implied_emotion(
            highs, lows, closes, volumes, dynamic_window, periods
        )
        
        # 🟢 تعديل 11: دمج المشاعر الحقيقية والضمنية
        fused = self._fuse_sentiments(implied, real_psych)
        
        # 🟡 تعديل 10: زخم عاطفي
        emotional_velocity = self._calculate_emotional_velocity(implied)
        
        # 🟡 تعديل 8: تباعد عاطفي
        emotional_divergence = self._calculate_emotional_divergence(
            closes, implied, dynamic_window
        )
        
        # بناء الحالة العاطفية
        emotion = EmotionalState(
            primary_emotion=implied['primary'],
            intensity=implied['intensity'],
            cycle_position=implied['cycle_position'],
            fomo_level=implied['fomo'],
            capitulation_risk=implied['capitulation'],
            greed_index=implied['greed'],
            fear_index=implied['fear'],
            conviction=implied['conviction'],
            hesitation=implied['hesitation'],
            pain_level=implied['pain'],
            emotional_velocity=emotional_velocity,
            emotional_divergence=emotional_divergence,
            real_sentiment=real_psych.get('real_sentiment', 0.0) or 0.0,
            real_sentiment_source=real_psych.get('source', 'none'),
            fused_sentiment=fused,
        )
        
        # تحديث التاريخ
        self.emotion_history.append(emotion)
        
        return {
            "emotion": emotion,
            "implied_metrics": implied,
            "real_psych_data": real_psych,
            "fused_sentiment": fused,
            "emotional_velocity": emotional_velocity,
            "emotional_divergence": emotional_divergence,
        }
    
    def _calculate_dynamic_window(self, closes: np.ndarray) -> int:
        """
        🔴 تعديل 3: نافذة ديناميكية للدورة العاطفية
        
        تستخدم متوسط مدة الموجات السابقة
        """
        if len(closes) < 60:
            return 30
        
        # حساب متوسط طول الموجات السابقة
        waves = self._detect_waves(closes)
        
        if len(waves) >= 3:
            avg_wave_length = np.mean([w['length'] for w in waves[-5:]])
            # النافذة = 2 × متوسط طول الموجة
            return max(20, min(100, int(avg_wave_length * 2)))
        
        return 30
    
    def _detect_waves(self, closes: np.ndarray) -> List[Dict]:
        """اكتشاف الموجات السعرية"""
        waves = []
        
        if len(closes) < 10:
            return waves
        
        # تبسيط: البحث عن تغيرات الاتجاه
        direction = 1 if closes[1] > closes[0] else -1
        wave_start = 0
        
        for i in range(2, len(closes)):
            current_dir = 1 if closes[i] > closes[i-1] else -1
            if current_dir != direction:
                wave_length = i - wave_start
                if wave_length >= 3:
                    waves.append({
                        'start': wave_start,
                        'end': i - 1,
                        'length': wave_length,
                        'direction': 'up' if direction == 1 else 'down',
                    })
                wave_start = i
                direction = current_dir
        
        return waves
    
    def _calculate_dynamic_periods(self, closes: np.ndarray) -> Dict:
        """
        🔴 تعديل 4: فترات ديناميكية
        
        change_3d و change_10d تصبح نسباً من متوسط مدة الموجات
        """
        waves = self._detect_waves(closes)
        
        if waves:
            avg_wave = np.mean([w['length'] for w in waves[-5:]])
        else:
            avg_wave = 10
        
        return {
            'short': max(2, int(avg_wave * 0.3)),
            'medium': max(4, int(avg_wave * 0.7)),
            'long': max(7, int(avg_wave * 1.5)),
        }
    
    def _analyze_implied_emotion(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, volumes: np.ndarray,
                                   window: int, periods: Dict) -> Dict:
        """تحليل المشاعر الضمنية من السعر"""
        
        recent = closes[-min(window, len(closes)):]
        all_time_high = max(highs[-window:]) if len(highs) >= window else max(highs)
        all_time_low = min(lows[-window:]) if len(lows) >= window else min(lows)
        
        current = closes[-1]
        range_total = max(all_time_high - all_time_low, 0.0001)
        
        # موقع السعر
        price_position = (current - all_time_low) / range_total
        
        # تغيرات ديناميكية
        short_period = periods.get('short', 3)
        medium_period = periods.get('medium', 8)
        long_period = periods.get('long', 15)
        
        idx_short = max(0, len(closes) - short_period - 1)
        idx_medium = max(0, len(closes) - medium_period - 1)
        idx_long = max(0, len(closes) - long_period - 1)
        
        change_short = (current - closes[idx_short]) / closes[idx_short] if closes[idx_short] > 0 else 0
        change_medium = (current - closes[idx_medium]) / closes[idx_medium] if closes[idx_medium] > 0 else 0
        change_long = (current - closes[idx_long]) / closes[idx_long] if closes[idx_long] > 0 else 0
        
        # التقلب
        returns = np.diff(np.log(np.maximum(recent, 0.0001)))
        volatility = np.std(returns) if len(returns) > 0 else 0
        
        # الحجم
        avg_vol = np.mean(volumes[-10:])
        long_avg_vol = np.mean(volumes[-min(50, len(volumes)):])
        vol_ratio = avg_vol / max(long_avg_vol, 0.0001)
        
        # تحديد الشعور الأساسي
        primary, intensity = self._classify_primary_emotion(
            price_position, change_short, change_medium, change_long, vol_ratio
        )
        
        # FOMO
        fomo = max(0, min(1.0, change_short * 8 + max(0, vol_ratio - 1) * 0.5))
        
        # Capitulation
        capitulation = max(0, min(1.0, abs(change_long) * 2.5 + max(0, vol_ratio - 1.3) * 0.5)) if change_long < 0 else 0
        
        # الجشع والخوف
        greed = min(1.0, price_position * 0.5 + max(0, change_short) * 8 * 0.3 + max(0, fomo) * 0.2)
        fear = min(1.0, (1 - price_position) * 0.5 + max(0, -change_short) * 8 * 0.3 + capitulation * 0.2)
        
        # الاقتناع
        direction_changes = sum(1 for i in range(2, len(recent))
                               if (recent[i] > recent[i-1] and recent[i-1] < recent[i-2]) or
                                  (recent[i] < recent[i-1] and recent[i-1] > recent[i-2]))
        conviction = 1 - (direction_changes / max(len(recent) - 2, 1) * 2)
        
        # التردد
        ranges = highs[-10:] - lows[-10:]
        avg_range = np.mean(ranges)
        if avg_range > 0:
            small_bars = sum(1 for r in ranges if r < avg_range * 0.5)
            hesitation = small_bars / len(ranges)
        else:
            hesitation = 0.5
        
        # الألم
        pain = max(0, (max(highs[-window:]) - current) / range_total) if price_position < 0.5 else \
               max(0, (current - min(lows[-window:])) / range_total) * 0.5
        
        return {
            'primary': primary,
            'intensity': intensity,
            'cycle_position': price_position,
            'fomo': fomo,
            'capitulation': capitulation,
            'greed': greed,
            'fear': fear,
            'conviction': conviction,
            'hesitation': hesitation,
            'pain': min(1.0, pain),
            'volatility': volatility,
            'vol_ratio': vol_ratio,
        }
    
    def _classify_primary_emotion(self, price_position: float, 
                                    change_short: float, change_medium: float,
                                    change_long: float, vol_ratio: float) -> Tuple[str, float]:
        """تصنيف الشعور الأساسي"""
        if price_position > 0.8 and change_short > 0.03:
            return 'نشوة', 0.8
        elif price_position > 0.6 and change_medium > 0.05:
            return 'إثارة', 0.7
        elif price_position > 0.5 and change_medium > 0.02:
            return 'تفاؤل', 0.6
        elif price_position < 0.2 and change_short < -0.03 and vol_ratio > 1.5:
            return 'ذعر', 0.85
        elif price_position < 0.3 and change_medium < -0.05:
            return 'خوف', 0.7
        elif price_position < 0.2 and change_short > 0.01:
            return 'أمل', 0.5
        elif change_long < -0.2:
            return 'استسلام', 0.9
        elif price_position > 0.7 and change_short < -0.02:
            return 'قلق', 0.55
        elif price_position > 0.5 and change_medium < -0.03:
            return 'إنكار', 0.5
        elif price_position < 0.25 and change_short < 0:
            return 'اكتئاب', 0.6
        else:
            return 'محايد', 0.4
    
    def _fuse_sentiments(self, implied: Dict, real_psych: Dict) -> float:
        """
        🟢 تعديل 11: دمج المشاعر الحقيقية والضمنية
        
        إذا توفرت بيانات حقيقية: true_sentiment × 0.6 + implied × 0.4
        إذا لم تتوفر: implied فقط
        """
        # حساب المشاعر الضمنية (من السعر)
        implied_sentiment = (implied['greed'] - implied['fear']) * 0.5 + 0.5
        
        real_sent = real_psych.get('real_sentiment')
        real_fg = real_psych.get('real_fear_greed')
        
        if real_sent is not None and real_sent != 0:
            # دمج مع المشاعر الحقيقية من تويتر/ريديت
            return real_sent * 0.6 + implied_sentiment * 0.4
        elif real_fg is not None and real_fg > 0:
            # استخدام Fear & Greed المعدل
            fg_normalized = real_fg / 100
            return fg_normalized * 0.6 + implied_sentiment * 0.4
        
        # لا توجد بيانات حقيقية
        return implied_sentiment
    
    def _calculate_emotional_velocity(self, implied: Dict) -> float:
        """
        🟡 تعديل 10: سرعة تغير المشاعر (Emotional Momentum)
        
        سرعة الانتقال من أمل إلى نشوة في 3 شموع ≠ الانتقال في 20 شمعة
        """
        if len(self.emotion_history) < 5:
            return 0.0
        
        # مقارنة شدة المشاعر الحالية بما كانت عليه قبل 5 فترات
        recent_emotions = list(self.emotion_history)[-5:]
        
        if len(recent_emotions) >= 5:
            old_intensity = recent_emotions[0].intensity
            current_intensity = implied['intensity']
            
            velocity = (current_intensity - old_intensity) / 5
            
            # هل تغيرت المشاعر؟
            old_emotion = recent_emotions[0].primary_emotion
            current_emotion = implied['primary']
            
            if old_emotion != current_emotion:
                velocity += 0.2  # تغير المشاعر = زخم إضافي
            
            return max(-1.0, min(1.0, velocity))
        
        return 0.0
    
    def _calculate_emotional_divergence(self, closes: np.ndarray, implied: Dict,
                                          window: int) -> float:
        """
        🟡 تعديل 8: تباعد عاطفي
        
        السعر يصعد لكن FOMO يهبط = القناعة تضعف
        السعر يهبط لكن Capitulation يهبط = البيع ينضب
        """
        if len(closes) < 10:
            return 0.0
        
        divergence = 0.0
        
        # السعر في آخر 10 شموع
        price_change = (closes[-1] - closes[-10]) / closes[-10] if closes[-10] > 0 else 0
        
        # تباعد 1: سعر صاعد + خوف مرتفع (ضعف خفي)
        if price_change > 0.03 and implied['fear'] > 0.5:
            divergence += 0.35
        
        # تباعد 2: سعر هابط + جشع مرتفع (قوة خفية)
        if price_change < -0.03 and implied['greed'] > 0.5:
            divergence += 0.35
        
        # تباعد 3: سعر صاعد + اقتناع منخفض (حركة بلا قناعة)
        if price_change > 0.02 and implied['conviction'] < 0.3:
            divergence += 0.3
        
        return min(1.0, divergence)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: رسام خرائط الألم النفسي (Pain Mapper) محسن          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PsychologicalZoneMapper:
    """
    يرسم مناطق الألم النفسي ويتتبعها.
    
    🔴 تعديل 2: مناطق ألم حية (current_pain_zone)
    🟡 تعديل 7: Psychological S/R
    🟡 تعديل 9: Pain Threshold Breach
    🟢 تعديل 12: Investor Regret Zones الحية
    """
    
    def __init__(self):
        self.pain_zones: List[PsychologicalZone] = []
        self.pain_thresholds: List[PainThreshold] = []
        self.max_pain_recorded = 0.0
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, current_price: float) -> Dict:
        """تحليل مناطق الألم النفسي"""
        
        # رسم مناطق الألم
        self._map_pain_zones(highs, lows, closes, volumes)
        
        # تحديث المناطق الحية
        self._update_active_zones(current_price, len(closes) - 1)
        
        # 🟡 تعديل 9: كشف كسر عتبات الألم
        pain_breach = self._detect_pain_breach(closes, volumes)
        
        # 🟢 تعديل 12: مناطق الندم الحية
        regret_zones = self._get_active_regret_zones(current_price)
        
        # 🟡 تعديل 7: دعم/مقاومة نفسي
        psych_sr = self._find_psychological_sr(current_price)
        
        return {
            "pain_zones": [z for z in self.pain_zones if z.is_active][-5:],
            "current_pain_zone": self._get_current_pain_zone(current_price),
            "pain_breach": pain_breach,
            "active_regret_zones": regret_zones,
            "psychological_sr": psych_sr,
            "max_pain_recorded": self.max_pain_recorded,
        }
    
    def _map_pain_zones(self, highs: np.ndarray, lows: np.ndarray,
                         closes: np.ndarray, volumes: np.ndarray):
        """رسم مناطق الألم النفسي من الحجم المرتفع"""
        
        if len(closes) < 20:
            return
        
        for i in range(10, len(closes) - 1):
            # حجم مرتفع = منطقة اهتمام نفسي
            avg_vol = np.mean(volumes[max(0, i-20):i])
            if avg_vol > 0 and volumes[i] > avg_vol * 2.0:
                
                # هل السعر كان في قمة أم قاع؟
                local_high = max(highs[max(0, i-10):i+1])
                local_low = min(lows[max(0, i-10):i+1])
                
                if closes[i] > closes[i-1] and closes[i] >= local_high * 0.98:
                    zone_type = 'regret_buy'  # اشتروا عند القمة = ندم
                    desc = f"منطقة ندم شراء عند {closes[i]:.2f}"
                elif closes[i] < closes[i-1] and closes[i] <= local_low * 1.02:
                    zone_type = 'regret_sell'  # باعوا عند القاع = ندم
                    desc = f"منطقة ندم بيع عند {closes[i]:.2f}"
                else:
                    zone_type = 'emotional_cluster'
                    desc = f"تجمع عاطفي عند {closes[i]:.2f}"
                
                # هل هذه المنطقة موجودة مسبقاً؟
                existing = [z for z in self.pain_zones 
                           if abs(z.price - closes[i]) / closes[i] < 0.01]
                
                if existing:
                    existing[0].emotional_weight += volumes[i] / max(avg_vol, 0.0001)
                    existing[0].strength = min(1.0, existing[0].strength + 0.1)
                    existing[0].last_touched_index = i
                else:
                    self.pain_zones.append(PsychologicalZone(
                        price=closes[i],
                        zone_type=zone_type,
                        strength=0.5,
                        emotional_weight=volumes[i] / max(avg_vol, 0.0001),
                        description=desc,
                        created_at_index=i,
                        last_touched_index=i,
                        is_active=True,
                    ))
        
        # تنظيف المناطق القديمة
        if len(self.pain_zones) > 50:
            self.pain_zones = sorted(self.pain_zones, 
                                     key=lambda z: z.emotional_weight, reverse=True)[:30]
    
    def _update_active_zones(self, current_price: float, current_index: int):
        """🔴 تعديل 2: تحديث المناطق الحية"""
        for zone in self.pain_zones:
            # المنطقة قريبة من السعر الحالي؟
            zone.price_at_zone = abs(current_price - zone.price) / current_price < 0.01
            
            # المنطقة قديمة جداً؟
            if current_index - zone.created_at_index > 100:
                zone.is_active = False
            
            # تم لمسها مؤخراً؟
            if current_index - zone.last_touched_index < 10:
                zone.is_active = True
                zone.strength = min(1.0, zone.strength + 0.05)
    
    def _get_current_pain_zone(self, current_price: float) -> Optional[PsychologicalZone]:
        """🔴 تعديل 2: هل السعر حالياً في منطقة ألم؟"""
        for zone in self.pain_zones:
            if zone.price_at_zone and zone.is_active:
                return zone
        return None
    
    def _detect_pain_breach(self, closes: np.ndarray, volumes: np.ndarray) -> Optional[Dict]:
        """
        🟡 تعديل 9: كسر عتبة الألم
        
        عندما يتجاوز الألم مستوى قياسياً سابقاً = حدث نفسي كبير
        """
        if len(closes) < 30:
            return None
        
        # حساب الألم الحالي
        highest = max(closes[-30:])
        current = closes[-1]
        pain = (highest - current) / highest if highest > 0 else 0
        
        # تحديث أعلى ألم مسجل
        if pain > self.max_pain_recorded:
            old_max = self.max_pain_recorded
            self.max_pain_recorded = pain
            
            if old_max > 0 and pain > old_max * 1.2:
                return {
                    "breached": True,
                    "old_max": old_max,
                    "new_max": pain,
                    "description": f"كسر عتبة الألم القياسية ({old_max:.1%} → {pain:.1%})",
                    "signal": "استسلام حقيقي" if pain > 0.3 else "ألم متزايد",
                }
        
        return None
    
    def _get_active_regret_zones(self, current_price: float) -> List[PsychologicalZone]:
        """
        🟢 تعديل 12: مناطق الندم الحية
        
        العودة لمنطقة ندم = فرصة (الناس يبيعون بخوف أو يشترون بطمع)
        """
        active = []
        for zone in self.pain_zones:
            if zone.is_active and zone.zone_type in ['regret_buy', 'regret_sell']:
                distance = abs(current_price - zone.price) / current_price
                if distance < 0.02:
                    active.append(zone)
        
        return active
    
    def _find_psychological_sr(self, current_price: float) -> Dict:
        """
        🟡 تعديل 7: دعم/مقاومة نفسي
        
        الأسعار التي تسبب ألماً = مستويات نفسية قوية
        """
        supports = []
        resistances = []
        
        for zone in self.pain_zones:
            if not zone.is_active:
                continue
            
            if zone.price < current_price and zone.emotional_weight > 2.0:
                supports.append({
                    "price": zone.price,
                    "strength": zone.strength,
                    "type": zone.zone_type,
                })
            elif zone.price > current_price and zone.emotional_weight > 2.0:
                resistances.append({
                    "price": zone.price,
                    "strength": zone.strength,
                    "type": zone.zone_type,
                })
        
        return {
            "psychological_supports": sorted(supports, key=lambda x: x['strength'], reverse=True)[:3],
            "psychological_resistances": sorted(resistances, key=lambda x: x['strength'], reverse=True)[:3],
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الهندسة النفسية الموحدة              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class PsychologicalEngineeringStrategy:
    """
    استراتيجية هندسة علم النفس - الإصدار 2.0
    
    تجمع:
    - تحليل المشاعر الضمنية من السعر
    - بيانات نفسية حقيقية من psychology_engine.py
    - مشاعر حقيقية من social_sentiment_strategy.py
    - مناطق الألم النفسي الحية
    - عتبات الألم وكسرها
    - دعم/مقاومة نفسي
    - زخم عاطفي وتباعد عاطفي
    """
    
    def __init__(self):
        self.emotion_analyzer = EmotionalStateAnalyzer()
        self.zone_mapper = PsychologicalZoneMapper()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        symbol = chart_data.get('symbol', 'BTCUSD')
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 30 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # 1. تحليل الحالة العاطفية
        emotion_data = self.emotion_analyzer.analyze(highs, lows, closes, volumes, symbol)
        emotion = emotion_data.get('emotion')
        
        # 2. مناطق الألم النفسي
        zone_data = self.zone_mapper.analyze(highs, lows, closes, volumes, current_price)
        
        # 3. القرار
        decision = self._make_decision(emotion_data, zone_data, current_price, closes)
        
        return {
            **decision,
            "emotion_data": emotion_data,
            "zone_data": zone_data,
        }
    
    def _make_decision(self, emotion_data: Dict, zone_data: Dict,
                       current_price: float, closes: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        emotion = emotion_data.get('emotion')
        implied = emotion_data.get('implied_metrics', {})
        
        if not emotion:
            return {"recommendation": "محايد", "confidence": 10, "reason": "غير محدد"}
        
        # ---- من الدورة العاطفية ----
        phase = emotion.primary_emotion
        
        buy_phases = ['استسلام', 'اكتئاب', 'ذعر']
        sell_phases = ['نشوة']
        caution_phases = ['قلق', 'إنكار', 'خوف']
        opportunity_phases = ['أمل', 'تفاؤل']
        
        if phase in buy_phases:
            buy_signals.append((f"دورة عاطفية: {phase} - وقت الشراء", 0.7))
        elif phase in sell_phases:
            sell_signals.append((f"دورة عاطفية: {phase} - وقت البيع", 0.7))
        elif phase in opportunity_phases:
            buy_signals.append((f"دورة عاطفية: {phase} - استمر بالشراء", 0.55))
        elif phase in caution_phases:
            sell_signals.append((f"دورة عاطفية: {phase} - استعد للبيع", 0.5))
        
        # ---- من FOMO ----
        if emotion.fomo_level > 0.6:
            sell_signals.append((f"FOMO مرتفع ({emotion.fomo_level:.0%}) - لا تشتر", 0.6))
        elif emotion.fomo_level < 0.2 and phase in buy_phases:
            buy_signals.append(("FOMO منخفض - لا أحد يشتري - فرصة", 0.55))
        
        # ---- من الاستسلام ----
        if emotion.capitulation_risk > 0.6:
            buy_signals.append((f"استسلام ({emotion.capitulation_risk:.0%}) - نهاية البيع", 0.65))
        
        # ---- من الاقتناع ----
        if emotion.conviction > 0.7:
            if phase in opportunity_phases:
                buy_signals.append(("اقتناع عالي + تفاؤل - قوة", 0.5))
            elif phase in caution_phases:
                sell_signals.append(("اقتناع عالي + خوف - استمرار هبوط", 0.5))
        
        if emotion.conviction < 0.3 and phase == 'نشوة':
            sell_signals.append(("اقتناع منخفض عند النشوة - بيع", 0.65))
        elif emotion.conviction < 0.3 and phase in buy_phases:
            buy_signals.append(("اقتناع منخفض عند الخوف - شراء", 0.6))
        
        # ---- من التردد ----
        if emotion.hesitation > 0.7:
            warnings.append("تردد عالي جداً - انتظر وضوح الرؤية")
        
        # ---- من الجشع والخوف ----
        if emotion.greed_index > 0.8:
            sell_signals.append(("جشع شديد - قمة", 0.65))
        if emotion.fear_index > 0.8:
            buy_signals.append(("خوف شديد - قاع", 0.65))
        
        # ---- من الألم ----
        if emotion.pain_level > 0.7:
            buy_signals.append(("ألم نفسي مرتفع - ارتداد قريب", 0.55))
        
        # ---- 🟡 تعديل 10: الزخم العاطفي ----
        if emotion.emotional_velocity > 0.4:
            if phase in buy_phases + opportunity_phases:
                buy_signals.append(("تسارع عاطفي إيجابي", 0.45))
            elif phase in sell_phases:
                sell_signals.append(("تسارع عاطفي سلبي", 0.45))
        
        # ---- 🟡 تعديل 8: التباعد العاطفي ----
        if emotion.emotional_divergence > 0.5:
            if phase in sell_phases:
                warnings.append("تباعد عاطفي - القناعة تضعف رغم الصعود")
            elif phase in buy_phases:
                buy_signals.append(("تباعد عاطفي إيجابي - البيع ينضب", 0.5))
        
        # ---- 🔴 تعديل 1: تأكيد من البيانات الحقيقية ----
        if emotion.real_sentiment_source != 'none':
            if emotion.real_sentiment < -0.5 and phase in buy_phases:
                buy_signals.append(("مشاعر حقيقية تؤكد الخوف - شراء", 0.6))
            elif emotion.real_sentiment > 0.5 and phase in sell_phases:
                sell_signals.append(("مشاعر حقيقية تؤكد الطمع - بيع", 0.6))
        
        # ---- من مناطق الألم ----
        current_pain_zone = zone_data.get('current_pain_zone')
        if current_pain_zone:
            warnings.append(f"السعر عند منطقة ألم نفسي: {current_pain_zone.description}")
        
        pain_breach = zone_data.get('pain_breach')
        if pain_breach and pain_breach.get('breached'):
            if 'استسلام' in pain_breach.get('signal', ''):
                buy_signals.append((pain_breach['description'], 0.7))
            warnings.append(pain_breach['description'])
        
        # ---- من مناطق الندم ----
        regret_zones = zone_data.get('active_regret_zones', [])
        if regret_zones:
            warnings.append(f"السعر عند {len(regret_zones)} منطقة ندم - فرصة نفسية")
            if phase in buy_phases:
                buy_signals.append((f"منطقة ندم ({len(regret_zones)}) + {phase} = شراء", 0.6))
        
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
        reason += f" | {emotion.primary_emotion}"
        
        if emotion.real_sentiment_source != 'none':
            reason += f" | حقيقي:{emotion.real_sentiment:.2f}"
        
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


def create_psychological_engineering_strategy():
    """إنشاء استراتيجية الهندسة النفسية الجاهزة (الإصدار 2.0)"""
    return PsychologicalEngineeringStrategy()