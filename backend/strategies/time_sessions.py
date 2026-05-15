"""
═══════════════════════════════════════════════════════════════════════════════
DYNAMIC TIME SESSIONS STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة التاسعة عشرة: تحليل الجلسات الزمنية الديناميكي - طبقة الذكاء الزمني
═══════════════════════════════════════════════════════════════════════════════

الوقت ليس مجرد ساعات. الوقت هو "مضاعف القوة" لكل إشارة تداولية.

هذه النسخة ديناميكية بالكامل - معاد بناؤها من الصفر:
- لا تحلل الوقت منفصلاً عن السعر والحجم
- الوقت = طبقة ذكاء تضاعف أو تضعف الإشارات الأخرى
- Opening Range حي لكل جلسة
- Actual Kill Zone Analysis (ما حدث فعلاً، ليس فقط التعريف)
- Live Session Character (شخصية السوق الآن)
- مصفوفة: الجلسة × نوع الإشارة = الاحتمالية
- No-Trade Zones ديناميكية
- تكامل كامل مع VSA و Wyckoff

الفلسفة الجديدة:
Shakeout في افتتاح لندن ≠ Shakeout في منتصف آسيا.
نفس الإشارة، قوة مختلفة تماماً بسبب الوقت.
الوقت هو "معامل الضرب" لكل قرار تداولي.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المعاد بناؤها                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class LiveSession:
    """شخصية الجلسة الحية - تحلل ما يحدث الآن، ليس ما هو ثابت"""
    name: str
    start_idx: int
    end_idx: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    range_size: float
    total_volume: float
    direction: str
    volatility: float
    trend_strength: float  # 0-1 مدى اتجاهية الجلسة
    manipulation_score: float  # 0-1 احتمال التلاعب
    opening_range_high: float  # 🟡 تعديل 7: نطاق أول ساعة
    opening_range_low: float
    opening_range_broken: str  # 'up', 'down', 'none'
    last_hour_close_position: float  # 🟢 تعديل 13: موقع إغلاق آخر ساعة
    actual_kill_zone_events: List[Dict]  # 🟡 تعديل 9: أحداث مناطق القتل الفعلية
    session_multiplier: float  # معامل قوة الإشارات في هذه الجلسة


@dataclass
class ActualKillZone:
    """منطقة قتل فعلية - ما حدث فيها حقيقة"""
    name: str
    start_idx: int
    end_idx: int
    range_size: float
    volume: float
    manipulation_detected: bool
    reversal_occurred: bool
    volatility_multiplier: float  # كم مرة أكثر تقلباً من المتوسط
    price_action: str  # وصف ما حدث
    fake_break_direction: Optional[str]  # اتجاه الاختراق الوهمي


@dataclass
class OpeningRange:
    """نطاق الافتتاح"""
    session_name: str
    start_idx: int
    end_idx: int
    high: float
    low: float
    breakout_idx: Optional[int]
    breakout_direction: Optional[str]
    success: bool  # هل أدى الاختراق إلى اتجاه مستمر؟
    bars_in_range: int


@dataclass
class TimeWeightedSignal:
    """إشارة مرجحة زمنياً"""
    original_signal_type: str
    original_strength: float
    time_multiplier: float
    final_strength: float
    session: str
    reason: str
    is_no_trade_zone: bool


@dataclass
class NoTradeZone:
    """منطقة محظورة للتداول"""
    session: str
    start_hour: float
    end_hour: float
    reason: str
    risk_level: str  # 'high', 'medium', 'low'
    historical_loss_rate: float  # نسبة الخسائر التاريخية في هذه المنطقة


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل الجلسات الحي (Live Session Analyzer)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class LiveSessionAnalyzer:
    """
    يحلل الجلسات بشكل حي وديناميكي.
    
    🟡 تعديل 6: Live Session Character
    🟡 تعديل 7: Opening Range حي
    🟡 تعديل 8: News Impact حقيقي من البيانات
    🟡 تعديل 9: Actual Kill Zone Analysis
    🟡 تعديل 10: تصنيف تداخل الجلسات الحقيقي
    """
    
    def __init__(self):
        self.session_history = defaultdict(lambda: defaultdict(list))
        self.hourly_volatility = defaultdict(list)
        self.no_trade_zones = []
        self._initialize_no_trade_zones()
    
    def _initialize_no_trade_zones(self):
        """🟢 تعديل 15: مناطق محظورة ديناميكية"""
        self.no_trade_zones = [
            NoTradeZone('Asian', 0, 1, 'أول ساعة آسيا - سيولة منخفضة', 'high', 0.45),
            NoTradeZone('NewYork', 21, 22, 'آخر ساعة نيويورك - تصفية مراكز', 'medium', 0.35),
            NoTradeZone('London', 8, 8.5, 'أول 30 دقيقة لندن - فوضى', 'high', 0.40),
            NoTradeZone('Overlap', 16, 16.5, 'أول 30 دقيقة أمريكا - فوضى', 'high', 0.38),
        ]
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray,
                times: Optional[List[datetime]] = None,
                sr_levels: List = None) -> Dict:
        """
        تحليل الجلسات الحية
        
        🔴 تعديل 1: بدون أوقات حقيقية = تحليل حي فقط (لا جلسات وهمية)
        """
        result = {
            "has_real_times": times is not None and len(times) > 0,
            "live_character": None,
            "current_session": "unknown",
            "sessions": [],
            "opening_ranges": [],
            "kill_zones": [],
            "time_multipliers": {},
            "no_trade_now": False,
        }
        
        # 🟡 تعديل 6: شخصية السوق الحية (دائماً متاحة)
        result["live_character"] = self._analyze_live_character(
            highs, lows, closes, volumes, opens
        )
        
        if times is None or len(times) == 0:
            # 🔴 تعديل 1: لا أوقات = لا تحليل جلسات وهمي
            result["current_session"] = "unknown"
            result["time_multipliers"] = self._get_default_multipliers()
            return result
        
        # تحليل مع أوقات حقيقية
        current_time = times[-1]
        current_hour = current_time.hour + current_time.minute / 60.0
        
        result["current_session"] = self._determine_session(current_hour)
        
        # تحليل الجلسات
        result["sessions"] = self._analyze_all_sessions(
            highs, lows, closes, volumes, opens, times
        )
        
        # 🟡 تعديل 7: Opening Ranges
        result["opening_ranges"] = self._analyze_opening_ranges(
            highs, lows, closes, volumes, times, result["sessions"]
        )
        
        # 🟡 تعديل 9: Actual Kill Zones
        result["kill_zones"] = self._analyze_actual_kill_zones(
            highs, lows, closes, volumes, times
        )
        
        # 🟡 تعديل 10: تصنيف التداخل
        result["overlap_analysis"] = self._analyze_overlap(
            highs, lows, closes, volumes, times, current_hour
        )
        
        # مضاعفات الوقت
        result["time_multipliers"] = self._calculate_time_multipliers(
            result["current_session"], current_hour, result["live_character"]
        )
        
        # 🟢 تعديل 15: هل نحن في منطقة محظورة؟
        result["no_trade_now"] = self._check_no_trade_zone(
            result["current_session"], current_hour
        )
        
        # تحديث التاريخ للتحليل المستقبلي
        self._update_history(result["sessions"], result["kill_zones"], times)
        
        return result
    
    def _analyze_live_character(self, highs: np.ndarray, lows: np.ndarray,
                                 closes: np.ndarray, volumes: np.ndarray,
                                 opens: np.ndarray) -> Dict:
        """
        🟡 تعديل 6: شخصية السوق الحية
        
        يحلل آخر 8 ساعات، 4 ساعات، ساعة واحدة
        هذا متاح حتى بدون أوقات حقيقية
        """
        n = len(closes)
        
        if n < 5:
            return {"status": "بيانات غير كافية"}
        
        # تحديد عدد الشموع لكل فترة (افتراض: شمعة = 15 دقيقة إذا لم تكن الأوقات متاحة)
        bars_per_hour = 4  # افتراضي: 4 شموع في الساعة (15 دقيقة)
        
        recent_1h = min(bars_per_hour, n)
        recent_4h = min(bars_per_hour * 4, n)
        recent_8h = min(bars_per_hour * 8, n)
        
        def analyze_window(length):
            if length < 2:
                return None
            h = highs[-length:]
            l = lows[-length:]
            c = closes[-length:]
            v = volumes[-length:]
            
            return {
                "high": max(h),
                "low": min(l),
                "range": max(h) - min(l),
                "direction": "up" if c[-1] > c[0] else "down",
                "volatility": np.std(c) / np.mean(c) if np.mean(c) > 0 else 0,
                "volume_trend": "increasing" if np.mean(v[-length//2:]) > np.mean(v[:length//2]) else "decreasing",
                "momentum": (c[-1] - c[0]) / c[0] if c[0] > 0 else 0,
                "efficiency": abs(c[-1] - c[0]) / (max(h) - min(l)) if max(h) > min(l) else 0,
            }
        
        char_8h = analyze_window(recent_8h)
        char_4h = analyze_window(recent_4h)
        char_1h = analyze_window(recent_1h)
        
        # تحديد الشخصية
        if char_8h and char_1h:
            # هل هناك تسارع؟
            if char_1h["efficiency"] > 0.7 and char_8h["efficiency"] < 0.3:
                character = "اختراق حي"
            elif char_1h["volatility"] > char_8h["volatility"] * 2:
                character = "تقلب متزايد"
            elif char_1h["volume_trend"] == "decreasing" and char_8h["volume_trend"] == "decreasing":
                character = "جفاف حجم"
            elif abs(char_1h["momentum"]) < 0.001:
                character = "تماسك حي"
            else:
                character = "طبيعي"
        else:
            character = "غير محدد"
        
        return {
            "character": character,
            "last_8h": char_8h,
            "last_4h": char_4h,
            "last_1h": char_1h,
        }
    
    def _determine_session(self, current_hour: float) -> str:
        """تحديد الجلسة الحالية من الساعة"""
        if 0 <= current_hour < 8:
            return 'Asian'
        elif 8 <= current_hour < 13:
            return 'London'
        elif 13 <= current_hour < 16:
            return 'Overlap'  # 🟡 تعديل 10: تداخل لندن ونيويورك
        elif 16 <= current_hour < 21:
            return 'NewYork'
        else:
            return 'Asian_Late'
    
    def _analyze_all_sessions(self, highs: np.ndarray, lows: np.ndarray,
                               closes: np.ndarray, volumes: np.ndarray,
                               opens: np.ndarray,
                               times: List[datetime]) -> List[LiveSession]:
        """
        تحليل جميع الجلسات في البيانات المتاحة
        """
        sessions = []
        
        # تعريف الجلسات
        session_defs = {
            'Asian': (0, 8),
            'London': (8, 16),
            'NewYork': (13, 21),
            'Overlap': (13, 16),
        }
        
        for name, (start_h, end_h) in session_defs.items():
            # جمع الشموع لهذه الجلسة عبر الأيام
            session_indices = []
            for i, t in enumerate(times):
                hour = t.hour + t.minute / 60.0
                if start_h <= hour < end_h:
                    session_indices.append(i)
            
            if not session_indices:
                continue
            
            # تجميع الشموع حسب الأيام
            day_groups = defaultdict(list)
            for idx in session_indices:
                day_key = times[idx].strftime('%Y-%m-%d')
                day_groups[day_key].append(idx)
            
            # تحليل آخر جلسة كاملة
            if day_groups:
                last_day = list(day_groups.keys())[-1]
                indices = day_groups[last_day]
                
                if indices:
                    s = self._create_session_from_indices(
                        name, indices, highs, lows, closes, volumes, opens, times
                    )
                    if s:
                        sessions.append(s)
        
        return sessions
    
    def _create_session_from_indices(self, name: str, indices: List[int],
                                      highs: np.ndarray, lows: np.ndarray,
                                      closes: np.ndarray, volumes: np.ndarray,
                                      opens: np.ndarray,
                                      times: List[datetime]) -> Optional[LiveSession]:
        """إنشاء كائن جلسة من مجموعة مؤشرات"""
        if not indices:
            return None
        
        h = highs[indices]
        l = lows[indices]
        c = closes[indices]
        v = volumes[indices]
        o = opens[indices]
        
        # نطاق الافتتاح (أول ساعة)
        first_hour_indices = []
        first_idx_time = times[indices[0]]
        for idx in indices:
            t = times[idx]
            if (t - first_idx_time).total_seconds() <= 3600:
                first_hour_indices.append(idx)
        
        if first_hour_indices:
            or_high = max(highs[first_hour_indices])
            or_low = min(lows[first_hour_indices])
        else:
            or_high = max(h)
            or_low = min(l)
        
        # هل انكسر نطاق الافتتاح؟
        current = c[-1]
        if current > or_high:
            or_broken = 'up'
        elif current < or_low:
            or_broken = 'down'
        else:
            or_broken = 'none'
        
        # موقع الإغلاق في آخر ساعة
        last_hour_indices = []
        last_idx_time = times[indices[-1]]
        for idx in reversed(indices):
            t = times[idx]
            if (last_idx_time - t).total_seconds() <= 3600:
                last_hour_indices.append(idx)
        
        if last_hour_indices and max(h) > min(l):
            last_hour_close_pos = (c[-1] - min(l)) / (max(h) - min(l))
        else:
            last_hour_close_pos = 0.5
        
        # كشف التلاعب المحسن
        manipulation_score = self._detect_real_manipulation(
            h, l, c, v, or_high, or_low
        )
        
        # 🟢 تعديل 11: معامل الجلسة
        session_mult = self._get_session_multiplier(name)
        
        return LiveSession(
            name=name,
            start_idx=indices[0],
            end_idx=indices[-1],
            open_price=o[0],
            high_price=max(h),
            low_price=min(l),
            close_price=c[-1],
            range_size=max(h) - min(l),
            total_volume=sum(v),
            direction='up' if c[-1] > o[0] else 'down',
            volatility=np.std(c) / np.mean(c) if np.mean(c) > 0 else 0,
            trend_strength=abs(c[-1] - o[0]) / (max(h) - min(l)) if max(h) > min(l) else 0,
            manipulation_score=manipulation_score,
            opening_range_high=or_high,
            opening_range_low=or_low,
            opening_range_broken=or_broken,
            last_hour_close_position=last_hour_close_pos,
            actual_kill_zone_events=[],
            session_multiplier=session_mult,
        )
    
    def _detect_real_manipulation(self, highs: np.ndarray, lows: np.ndarray,
                                    closes: np.ndarray, volumes: np.ndarray,
                                    or_high: float, or_low: float) -> float:
        """
        🔴 تعديل 4: كشف التلاعب الحقيقي
        
        ليس مجرد انعكاس، بل:
        - كسر مستوى مهم (نطاق الافتتاح أو دعم/مقاومة)
        - حجم مرتفع
        - ارتداد فوري
        """
        score = 0.0
        
        if len(closes) < 10:
            return 0.0
        
        # فحص كسر نطاق الافتتاح مع ارتداد
        for i in range(1, len(closes)):
            # كسر وهمي لأعلى
            if highs[i] > or_high * 1.002 and closes[i] < or_high:
                if volumes[i] > np.mean(volumes) * 1.3:
                    score += 0.3
            
            # كسر وهمي لأسفل
            if lows[i] < or_low * 0.998 and closes[i] > or_low:
                if volumes[i] > np.mean(volumes) * 1.3:
                    score += 0.3
        
        # فحص انعكاس منتصف الجلسة مع حجم
        mid = len(closes) // 2
        first_half_dir = closes[mid-1] - closes[0]
        second_half_dir = closes[-1] - closes[mid]
        
        if first_half_dir * second_half_dir < 0:  # انعكاس
            if abs(first_half_dir) > (max(highs) - min(lows)) * 0.4:
                if np.mean(volumes[mid:]) > np.mean(volumes[:mid]) * 1.2:
                    score += 0.25
        
        return min(1.0, score)
    
    def _analyze_opening_ranges(self, highs: np.ndarray, lows: np.ndarray,
                                 closes: np.ndarray, volumes: np.ndarray,
                                 times: List[datetime],
                                 sessions: List[LiveSession]) -> List[OpeningRange]:
        """
        🟡 تعديل 7: تحليل نطاقات الافتتاح
        
        أول ساعة من كل جلسة = المؤشر الأقوى
        """
        opening_ranges = []
        
        for session in sessions:
            # نطاق الافتتاح = أول ساعة
            or_high = session.opening_range_high
            or_low = session.opening_range_low
            
            # هل حدث اختراق؟
            breakout_idx = None
            breakout_dir = None
            success = False
            
            # البحث عن اختراق
            for i in range(session.start_idx + 4, session.end_idx + 1):  # بعد أول ساعة
                if closes[i] > or_high:
                    breakout_idx = i
                    breakout_dir = 'up'
                    break
                elif closes[i] < or_low:
                    breakout_idx = i
                    breakout_dir = 'down'
                    break
            
            if breakout_idx:
                # هل استمر الاختراق؟
                post_breakout = closes[breakout_idx:session.end_idx+1]
                if breakout_dir == 'up':
                    success = post_breakout[-1] > or_high
                else:
                    success = post_breakout[-1] < or_low
            
            opening_ranges.append(OpeningRange(
                session_name=session.name,
                start_idx=session.start_idx,
                end_idx=session.start_idx + 3,  # تقريبي: أول ساعة
                high=or_high,
                low=or_low,
                breakout_idx=breakout_idx,
                breakout_direction=breakout_dir,
                success=success,
                bars_in_range=4,
            ))
        
        return opening_ranges
    
    def _analyze_actual_kill_zones(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, volumes: np.ndarray,
                                     times: List[datetime]) -> List[ActualKillZone]:
        """
        🟡 تعديل 9: تحليل مناطق القتل الفعلية
        
        يحلل ما حدث في مناطق القتل فعلاً، وليس فقط تعريفها
        """
        kill_zones = []
        
        # تعريف مناطق القتل
        kz_defs = {
            'Asian_Kill': (0, 2),
            'London_Open': (8, 10),
            'NY_Open': (13, 15),
            'London_Close': (16, 17),
        }
        
        avg_range = np.mean(highs[-50:] - lows[-50:]) if len(highs) >= 50 else 0
        
        for name, (start_h, end_h) in kz_defs.items():
            # جمع الشموع في هذه المنطقة عبر آخر 5 أيام
            kz_indices = []
            for i, t in enumerate(times[-200:]):  # آخر 200 شمعة
                hour = t.hour + t.minute / 60.0
                if start_h <= hour < end_h:
                    kz_indices.append(len(times) - 200 + i)
            
            if len(kz_indices) < 3:
                continue
            
            # تحليل آخر ظهور
            last_kz_indices = [i for i in kz_indices if i >= kz_indices[-1] - 10]
            
            if last_kz_indices:
                kz_high = max(highs[last_kz_indices])
                kz_low = min(lows[last_kz_indices])
                kz_range = kz_high - kz_low
                kz_vol = sum(volumes[last_kz_indices])
                
                # هل كان هناك تلاعب؟
                manipulation = False
                fake_break_dir = None
                
                # فحص كسر وهمي
                prev_level = np.mean(closes[last_kz_indices[0]-5:last_kz_indices[0]]) if last_kz_indices[0] >= 5 else 0
                for idx in last_kz_indices:
                    if highs[idx] > prev_level * 1.003 and closes[idx] < prev_level:
                        manipulation = True
                        fake_break_dir = 'up'
                    if lows[idx] < prev_level * 0.997 and closes[idx] > prev_level:
                        manipulation = True
                        fake_break_dir = 'down'
                
                # التقلب الفعلي
                vol_mult = kz_range / avg_range if avg_range > 0 else 1.0
                
                # هل حدث انعكاس؟
                first_price = closes[last_kz_indices[0]]
                last_price = closes[last_kz_indices[-1]]
                
                # وصف ما حدث
                if manipulation:
                    price_action = f"تلاعب: كسر وهمي {fake_break_dir}"
                elif abs(last_price - first_price) > kz_range * 0.7:
                    price_action = "اتجاه قوي"
                elif kz_range < avg_range * 0.5:
                    price_action = "هادئ"
                else:
                    price_action = "طبيعي"
                
                kill_zones.append(ActualKillZone(
                    name=name,
                    start_idx=last_kz_indices[0],
                    end_idx=last_kz_indices[-1],
                    range_size=kz_range,
                    volume=kz_vol,
                    manipulation_detected=manipulation,
                    reversal_occurred=first_price * last_price < 0 if first_price * last_price != 0 else False,
                    volatility_multiplier=vol_mult,
                    price_action=price_action,
                    fake_break_direction=fake_break_dir,
                ))
        
        return kill_zones
    
    def _analyze_overlap(self, highs: np.ndarray, lows: np.ndarray,
                          closes: np.ndarray, volumes: np.ndarray,
                          times: List[datetime], current_hour: float) -> Dict:
        """
        🟡 تعديل 10: تصنيف تداخل الجلسات الحقيقي
        """
        # هل نحن في تداخل؟
        in_overlap = 13 <= current_hour < 16
        
        if not in_overlap:
            return {"active": False}
        
        # تحليل التداخل الحالي
        overlap_indices = []
        for i, t in enumerate(times[-100:]):
            hour = t.hour + t.minute / 60.0
            if 13 <= hour < 16:
                overlap_indices.append(len(times) - 100 + i)
        
        if not overlap_indices:
            return {"active": True, "character": "غير معروف"}
        
        overlap_range = max(highs[overlap_indices]) - min(lows[overlap_indices])
        overlap_vol = sum(volumes[overlap_indices])
        overlap_volatility = np.std(closes[overlap_indices]) / np.mean(closes[overlap_indices]) if np.mean(closes[overlap_indices]) > 0 else 0
        
        # تصنيف التداخل
        avg_range = np.mean(highs[-50:] - lows[-50:]) if len(highs) >= 50 else overlap_range
        
        if overlap_volatility > 0.005:
            character = "عنيف"
        elif overlap_range > avg_range * 1.5:
            character = "واسع النطاق"
        elif overlap_range < avg_range * 0.5:
            character = "هادئ"
        else:
            character = "طبيعي"
        
        return {
            "active": True,
            "character": character,
            "range": overlap_range,
            "volume": overlap_vol,
            "volatility": overlap_volatility,
        }
    
    def _get_session_multiplier(self, session_name: str) -> float:
        """
        🟢 تعديل 11: معامل الجلسة (مصفوفة: جلسة × نوع الإشارة)
        
        London = أقوى الجلسات للاختراقات
        Asian = جلسة تجميع/توزيع
        NewYork = استمرار أو انعكاس
        Overlap = أقوى وقت في اليوم
        """
        multipliers = {
            'Asian': 0.7,
            'London': 1.4,
            'NewYork': 1.2,
            'Overlap': 1.6,
            'Asian_Late': 0.6,
        }
        return multipliers.get(session_name, 1.0)
    
    def _calculate_time_multipliers(self, session: str, current_hour: float,
                                     live_char: Dict) -> Dict:
        """
        حساب مضاعفات الوقت لكل أنواع الإشارات
        
        🟢 تعديل 14: وقت × VSA = قوة مضاعفة
        """
        base_mult = self._get_session_multiplier(session)
        
        # تعديل حسب شخصية السوق
        char_mult = 1.0
        if live_char.get("character") == "اختراق حي":
            char_mult = 1.3
        elif live_char.get("character") == "جفاف حجم":
            char_mult = 0.7
        
        # تعديل حسب وقت الجلسة (افتتاح = أقوى)
        hour_in_session = current_hour % 8  # تقريبي
        if hour_in_session < 1:
            time_mult = 1.4  # أول ساعة = قوية
        elif hour_in_session > 6:
            time_mult = 0.8  # آخر ساعة = أضعف
        else:
            time_mult = 1.0
        
        final_mult = base_mult * char_mult * time_mult
        
        return {
            "session_multiplier": base_mult,
            "character_multiplier": char_mult,
            "time_multiplier": time_mult,
            "final_multiplier": final_mult,
            "session": session,
            "character": live_char.get("character", "غير محدد"),
        }
    
    def _get_default_multipliers(self) -> Dict:
        """مضاعفات افتراضية عند عدم توفر أوقات"""
        return {
            "session_multiplier": 1.0,
            "character_multiplier": 1.0,
            "time_multiplier": 1.0,
            "final_multiplier": 1.0,
            "session": "unknown",
            "character": "غير محدد",
        }
    
    def _check_no_trade_zone(self, session: str, current_hour: float) -> bool:
        """
        🟢 تعديل 15: فحص المنطقة المحظورة
        """
        for zone in self.no_trade_zones:
            if zone.session == session or zone.session == 'All':
                if zone.start_hour <= current_hour < zone.end_hour:
                    return True
        return False
    
    def _update_history(self, sessions: List[LiveSession], 
                         kill_zones: List[ActualKillZone],
                         times: List[datetime]):
        """تحديث التاريخ للتحليل المستقبلي"""
        for session in sessions:
            self.session_history[session.name]['volatility'].append(session.volatility)
            self.session_history[session.name]['range'].append(session.range_size)
        
        for kz in kill_zones:
            hour_key = int(kz.start_idx)
            self.hourly_volatility[hour_key].append(kz.volatility_multiplier)
    
    def get_time_weight_for_signal(self, signal_type: str, direction: str,
                                     session_data: Dict) -> TimeWeightedSignal:
        """
        🟢 تعديل 14: ترجيح أي إشارة تداولية بالوقت
        
        هذه هي الوظيفة الأساسية - تستخدمها الاستراتيجيات الأخرى
        """
        multipliers = session_data.get("time_multipliers", {})
        session = session_data.get("current_session", "unknown")
        is_no_trade = session_data.get("no_trade_now", False)
        
        # الإشارات القوية في أوقات قوية = أقوى
        # الإشارات الضعيفة في أوقات ضعيفة = أضعف
        signal_strength_map = {
            'shakeout': 0.9,
            'spring': 0.85,
            'upthrust': 0.85,
            'stopping_volume': 0.8,
            'climax': 0.8,
            'no_demand': 0.6,
            'no_supply': 0.6,
            'test': 0.55,
            'effort_divergence': 0.7,
        }
        
        base_strength = signal_strength_map.get(signal_type, 0.5)
        final_mult = multipliers.get("final_multiplier", 1.0)
        
        # في مناطق محظورة، القوة = 0
        if is_no_trade:
            final_mult = 0.0
        
        return TimeWeightedSignal(
            original_signal_type=signal_type,
            original_strength=base_strength,
            time_multiplier=final_mult,
            final_strength=base_strength * final_mult,
            session=session,
            reason=f"{session} × {multipliers.get('character', 'عادي')} = {final_mult:.1f}x",
            is_no_trade_zone=is_no_trade,
        )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: كاشف الدورات الزمنية (محسن)                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class TimeCycleDetector:
    """
    يكتشف الدورات الزمنية في السوق.
    """
    
    def analyze(self, closes: np.ndarray, times: Optional[List[datetime]] = None) -> Dict:
        """اكتشاف الدورات الزمنية"""
        cycles = self._find_cycles(closes)
        
        # 🟢 تعديل 13: تحليل آخر ساعة من كل يوم
        if times and len(times) > 24:
            last_hour_pattern = self._analyze_last_hour_pattern(closes, times)
        else:
            last_hour_pattern = None
        
        return {
            "cycles": cycles,
            "dominant_cycle": cycles[0] if cycles else None,
            "next_turn_date": self._predict_next_turn(cycles, len(closes)),
            "last_hour_pattern": last_hour_pattern,
        }
    
    def _find_cycles(self, closes: np.ndarray) -> List[Dict]:
        """إيجاد الدورات الزمنية"""
        cycles = []
        
        if len(closes) < 30:
            return cycles
        
        peaks = []
        for i in range(5, len(closes) - 5):
            if closes[i] > closes[i-1] and closes[i] > closes[i-2] and \
               closes[i] > closes[i+1] and closes[i] > closes[i+2]:
                peaks.append(i)
        
        if len(peaks) < 3:
            return cycles
        
        distances = []
        for i in range(1, len(peaks)):
            distances.append(peaks[i] - peaks[i-1])
        
        if not distances:
            return cycles
        
        avg_cycle = np.mean(distances)
        std_cycle = np.std(distances) if len(distances) > 1 else 0
        
        cycles.append({
            "length": int(avg_cycle),
            "std": std_cycle,
            "type": "peak_to_peak",
            "phase": (len(closes) - peaks[-1]) / avg_cycle if avg_cycle > 0 else 0,
        })
        
        return cycles
    
    def _analyze_last_hour_pattern(self, closes: np.ndarray,
                                     times: List[datetime]) -> Dict:
        """
        🟢 تعديل 13: تحليل آخر ساعة من كل يوم
        
        آخر ساعة تكشف نية المؤسسات لليوم التالي
        """
        if len(times) < 50:
            return None
        
        # تجميع آخر ساعة لكل يوم
        day_last_hours = defaultdict(list)
        
        for i, t in enumerate(times[:-4]):
            next_t = times[i+1] if i+1 < len(times) else t
            # إذا كانت هذه آخر شمعة في الساعة 21-22 (آخر ساعة تداول)
            hour = t.hour + t.minute / 60.0
            if 21 <= hour < 22:
                day_key = t.strftime('%Y-%m-%d')
                day_last_hours[day_key].append({
                    'close': closes[i],
                    'index': i,
                })
        
        if not day_last_hours:
            return None
        
        # تحليل العلاقة بين إغلاق آخر ساعة وافتتاح اليوم التالي
        correlations = []
        days = list(day_last_hours.keys())
        
        for i in range(len(days) - 1):
            today_close = day_last_hours[days[i]][-1]['close'] if day_last_hours[days[i]] else 0
            tomorrow_open_idx = day_last_hours[days[i+1]][0]['index'] + 1 if day_last_hours[days[i+1]] else 0
            
            if tomorrow_open_idx < len(closes):
                tomorrow_open = closes[tomorrow_open_idx]
                if today_close > 0:
                    change = (tomorrow_open - today_close) / today_close
                    correlations.append(change)
        
        if correlations:
            avg_next_day_change = np.mean(correlations)
            pattern = "صاعد" if avg_next_day_change > 0.001 else "هابط" if avg_next_day_change < -0.001 else "محايد"
        else:
            pattern = "غير معروف"
        
        return {
            "pattern": pattern,
            "avg_next_day_change": avg_next_day_change if correlations else 0,
            "days_analyzed": len(correlations),
        }
    
    def _predict_next_turn(self, cycles: List[Dict], current_idx: int) -> Optional[Dict]:
        """توقع نقطة التحول التالية"""
        if not cycles:
            return None
        
        cycle = cycles[0]
        bars_until = cycle["length"] - int(cycle["length"] * cycle.get("phase", 0))
        
        return {
            "bars_until": max(1, bars_until),
            "cycle_length": cycle["length"],
            "confidence": 0.6 if cycle["std"] < cycle["length"] * 0.3 else 0.3,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الجلسات الزمنية الموحدة               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class TimeSessionsStrategy:
    """
    استراتيجية تحليل الجلسات الزمنية - طبقة الذكاء الزمني (الإصدار 2.0)
    
    لم تعد "محلل جلسات" فقط.
    الآن هي "طبقة ذكاء" يمكن دمجها مع أي استراتيجية أخرى.
    
    الوظيفة الأساسية: time_weight = get_time_weight(signal_type)
    تعطي أي إشارة تداولية وزناً زمنياً يضاعف أو يضعف قوتها.
    """
    
    def __init__(self):
        self.session_analyzer = LiveSessionAnalyzer()
        self.cycle_detector = TimeCycleDetector()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        times = chart_data.get('times', None)
        
        if len(closes) < 24:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 24 شمعة على الأقل"}
        
        # 1. تحليل الجلسات الحية
        session_data = self.session_analyzer.analyze(
            highs, lows, closes, volumes, opens, times
        )
        
        # 2. الدورات الزمنية
        cycle_data = self.cycle_detector.analyze(closes, times)
        
        # 3. القرار
        decision = self._make_decision(session_data, cycle_data, closes)
        
        return {
            **decision,
            "session_data": session_data,
            "cycle_data": cycle_data,
            "time_multipliers": session_data.get("time_multipliers", {}),
        }
    
    def _make_decision(self, session_data: Dict, cycle_data: Dict,
                       closes: np.ndarray) -> Dict:
        """
        اتخاذ القرار بالاعتماد على الوقت كعامل مضاعف
        """
        buy_signals = []
        sell_signals = []
        warnings = []
        
        time_mult = session_data.get("time_multipliers", {})
        live_char = session_data.get("live_character", {})
        sessions = session_data.get("sessions", [])
        kill_zones = session_data.get("kill_zones", [])
        opening_ranges = session_data.get("opening_ranges", [])
        is_no_trade = session_data.get("no_trade_now", False)
        
        current_session = session_data.get("current_session", "unknown")
        
        # 🟢 تعديل 15: منطقة محظورة
        if is_no_trade:
            warnings.append("منطقة محظورة - لا تتداول الآن")
            return {
                "recommendation": "محايد",
                "confidence": 5,
                "reason": "منطقة محظورة للتداول - انتظر",
                "buy_signals": [],
                "sell_signals": [],
                "warnings": warnings,
            }
        
        # ---- من شخصية السوق الحية ----
        char_8h = live_char.get("last_8h", {})
        char_1h = live_char.get("last_1h", {})
        
        if live_char.get("character") == "اختراق حي":
            if char_1h and char_1h.get("direction") == "up":
                buy_signals.append(("اختراق حي صاعد", 0.6 * time_mult.get("final_multiplier", 1.0)))
            elif char_1h and char_1h.get("direction") == "down":
                sell_signals.append(("اختراق حي هابط", 0.6 * time_mult.get("final_multiplier", 1.0)))
        
        if live_char.get("character") == "جفاف حجم":
            warnings.append("جفاف حجم - انفجار قادم - انتظر الاختراق")
        
        # ---- من الجلسات ----
        for session in sessions:
            mult = session.session_multiplier
            
            # 🟡 تعديل 7: نطاق الافتتاح
            if session.opening_range_broken == 'up':
                buy_signals.append((
                    f"{session.name}: كسر نطاق الافتتاح لأعلى (×{mult:.1f})",
                    0.65 * mult
                ))
            elif session.opening_range_broken == 'down':
                sell_signals.append((
                    f"{session.name}: كسر نطاق الافتتاح لأسفل (×{mult:.1f})",
                    0.65 * mult
                ))
            
            # 🟢 تعديل 13: آخر ساعة
            if session.last_hour_close_position > 0.8:
                buy_signals.append((
                    f"{session.name}: إغلاق قوي عند القمة - استمرار صعود",
                    0.5 * mult
                ))
            elif session.last_hour_close_position < 0.2:
                sell_signals.append((
                    f"{session.name}: إغلاق قوي عند القاع - استمرار هبوط",
                    0.5 * mult
                ))
            
            # تلاعب
            if session.manipulation_score > 0.5:
                if session.direction == 'up':
                    sell_signals.append((
                        f"{session.name}: تلاعب صاعد (درجة:{session.manipulation_score:.0%})",
                        0.55 * mult
                    ))
                else:
                    buy_signals.append((
                        f"{session.name}: تلاعب هابط (درجة:{session.manipulation_score:.0%})",
                        0.55 * mult
                    ))
        
        # ---- من مناطق القتل الفعلية ----
        for kz in kill_zones:
            if kz.manipulation_detected:
                if kz.fake_break_direction == 'up':
                    sell_signals.append((
                        f"KZ {kz.name}: تلاعب - كسر وهمي لأعلى",
                        0.7
                    ))
                elif kz.fake_break_direction == 'down':
                    buy_signals.append((
                        f"KZ {kz.name}: تلاعب - كسر وهمي لأسفل",
                        0.7
                    ))
        
        # ---- من تداخل الجلسات ----
        overlap = session_data.get("overlap_analysis", {})
        if overlap.get("active") and overlap.get("character") == "عنيف":
            warnings.append("تداخل لندن-نيويورك عنيف - حذر من الانعكاسات")
        
        # ---- من الدورات الزمنية ----
        next_turn = cycle_data.get("next_turn_date")
        if next_turn and next_turn.get("confidence", 0) > 0.5:
            if next_turn.get("bars_until", 99) < 3:
                warnings.append(f"نقطة تحول زمني قريبة ({next_turn.get('bars_until')} شموع)")
        
        # ---- من الجلسة الحالية ----
        if current_session == 'London':
            buy_signals.append(("جلسة لندن - أفضل وقت للاختراقات", 0.3))
        elif current_session == 'Overlap':
            warnings.append("تداخل الجلسات - أعلى سيولة وأعلى خطر تلاعب")
        
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
        reason += f" | جلسة:{current_session}"
        reason += f" | شخصية:{live_char.get('character', 'عادي')}"
        
        if warnings:
            reason += " | ⚠️ " + " | ".join(warnings[:2])
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "warnings": warnings,
        }


def create_time_sessions_strategy():
    """إنشاء استراتيجية الجلسات الزمنية الجاهزة (الإصدار 2.0)"""
    return TimeSessionsStrategy()