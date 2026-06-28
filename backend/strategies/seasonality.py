"""
═══════════════════════════════════════════════════════════════════════════════
SEASONALITY ANALYSIS - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثالثة والعشرون: تحليل الموسمية - طبقة المرشح الذكي
═══════════════════════════════════════════════════════════════════════════════

الأسواق لها دورات موسمية. بعض الشهور أفضل من غيرها.
"بيع في مايو واذهب بعيداً" - Sell in May and Go Away.

هذه النسخة ديناميكية بالكامل - معاد بناؤها كطبقة مرشحة:
- الموسمية = مرشح (Filter) وليست سبباً للدخول
- الأنماط تتعلم من تاريخ السوق الفعلي
- الفترات الخاصة تُحسب من البيانات وليس من جداول ثابتة
- Seasonal Shift Detection
- Month-over-Month Momentum
- Holiday Calendar حقيقي
- Quarter Effects
- تتكامل مع: Wyckoff, VSA, VPIN, ICT, Time Sessions

الفلسفة الجديدة:
إشارة شراء من Wyckoff + موسمية صاعدة = قوة ×1.3
إشارة شراء من Wyckoff + موسمية هابطة = قوة ×0.7
الموسمية مرشح يضاعف أو يضعف، ولا يتخذ القرار وحده.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المعاد بناؤها                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class SeasonalPattern:
    """نمط موسمي - نسخة محسنة"""
    period: str
    period_key: str
    avg_return: float
    win_rate: float
    strength: float
    consistency: float
    return_range: Tuple[float, float]  # 🔴 تعديل 1: مدى العوائد
    positive_years_ratio: float  # 🔴 تعديل 1: نسبة السنوات الموجبة
    excess_return: float = 0.0  # 🟡 تعديل 8: العائد الزائد عن السوق
    current_phase: str = 'inactive'
    anomaly_detected: bool = False
    recent_trend: str = 'stable'  # 🟡 تعديل 7: اتجاه آخر 3 سنوات
    shift_detected: bool = False  # 🟡 تعديل 7: تحول موسمي


@dataclass
class SeasonalityProfile:
    """بروفايل الموسمية الكامل - نسخة محسنة"""
    current_month: str
    current_week_of_month: int  # 🟡 تعديل 9
    current_quarter: int  # 🟡 تعديل 10
    monthly_patterns: List[SeasonalPattern]
    weekly_patterns: List[SeasonalPattern]
    special_periods: List[SeasonalPattern]
    quarter_patterns: List[SeasonalPattern]  # 🟡 تعديل 10
    seasonal_bias: str
    seasonal_strength: float
    seasonal_filter_multiplier: float  # 🔴 تعديل 2: معامل المرشح
    anomaly_score: float  # 0-1
    momentum_score: float  # 🟢 تعديل 14


@dataclass
class HolidayInfo:
    """معلومات عطلة"""
    name: str
    date: datetime
    country: str
    historical_impact: float  # متوسط التأثير
    affected_sessions: List[str]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: تقويم العطل (Holiday Calendar)                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class HolidayCalendar:
    """
    🟢 تعديل 15: تقويم عطل حقيقي مع تأثير تاريخي
    """
    
    # العطل الرئيسية (قابلة للتوسيع)
    MAJOR_HOLIDAYS = [
        {"name": "رأس السنة الميلادية", "month": 1, "day": 1, "countries": ["US", "UK", "EU", "Global"]},
        {"name": "عيد العمال", "month": 5, "day": 1, "countries": ["Global"]},
        {"name": "عيد الاستقلال الأمريكي", "month": 7, "day": 4, "countries": ["US"]},
        {"name": "عيد العمال الأمريكي", "month": 9, "day": 1, "weekday": 0, "countries": ["US"]},
        {"name": "عيد الشكر", "month": 11, "day": 1, "weekday": 3, "countries": ["US"]},
        {"name": "عيد الميلاد", "month": 12, "day": 25, "countries": ["Global"]},
        {"name": "نهاية السنة", "month": 12, "day": 31, "countries": ["Global"]},
    ]
    
    def __init__(self):
        self.holiday_impact_history = defaultdict(list)
    
    def get_upcoming_holidays(self, current_date: datetime, days_ahead: int = 7) -> List[HolidayInfo]:
        """الحصول على العطل القادمة"""
        upcoming = []
        
        for i in range(days_ahead):
            check_date = current_date + timedelta(days=i)
            
            for holiday in self.MAJOR_HOLIDAYS:
                if self._is_holiday(holiday, check_date):
                    avg_impact = self._get_historical_impact(holiday['name'])
                    upcoming.append(HolidayInfo(
                        name=holiday['name'],
                        date=check_date,
                        country=', '.join(holiday['countries']),
                        historical_impact=avg_impact,
                        affected_sessions=['Asian', 'London'] if 'US' in holiday['countries'] else ['All'],
                    ))
        
        return upcoming
    
    def _is_holiday(self, holiday: Dict, date: datetime) -> bool:
        """فحص هل التاريخ يوافق العطلة"""
        if date.month != holiday['month']:
            return False
        
        if 'weekday' in holiday:
            # عطلة في يوم معين من الأسبوع (مثلاً: أول اثنين من سبتمبر)
            if date.weekday() == holiday['weekday']:
                week_num = (date.day - 1) // 7 + 1
                target_week = holiday.get('week_of_month', 1)
                return week_num == target_week
            return False
        
        return date.day == holiday['day']
    
    def _get_historical_impact(self, holiday_name: str) -> float:
        """الحصول على التأثير التاريخي للعطلة من البيانات المسجلة"""
        if holiday_name in self.holiday_impact_history:
            impacts = self.holiday_impact_history[holiday_name]
            if impacts:
                return np.mean(impacts)
        
        # قيم افتراضية
        default_impacts = {
            "رأس السنة الميلادية": 0.003,
            "عيد العمال": 0.001,
            "عيد الشكر": -0.002,
            "عيد الميلاد": 0.005,
        }
        return default_impacts.get(holiday_name, 0.0)
    
    def record_holiday_impact(self, holiday_name: str, impact: float):
        """تسجيل تأثير عطلة للتعلم المستقبلي"""
        self.holiday_impact_history[holiday_name].append(impact)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل الموسمية الديناميكي (معاد بناؤه)                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class DynamicSeasonalityAnalyzer:
    """
    يحلل الموسمية كطبقة مرشحة ذكية.
    
    🔴 تعديل 1: مدى العوائد ونسبة السنوات الموجبة
    🔴 تعديل 2: الموسمية = مرشح، ليست إشارة مستقلة
    🔴 تعديل 3: الشذوذ يحتاج سياقاً سعرياً
    🔴 تعديل 4: حجم الشهر ديناميكي
    🔴 تعديل 5: الفترات الخاصة تتعلم من البيانات
    🟡 تعديل 7: Seasonal Shift Detection
    🟡 تعديل 8: العائد الزائد
    🟡 تعديل 9: Week of Month
    🟡 تعديل 10: Quarter Effects
    🟢 تعديل 13: False Seasonality Break
    🟢 تعديل 14: Month-over-Month Momentum
    """
    
    MONTHS_AR = ["يناير", "فبراير", "مارس", "إبريل", "مايو", "يونيو",
                  "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    
    DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
    
    QUARTERS = {1: "الربع الأول", 2: "الربع الثاني", 3: "الربع الثالث", 4: "الربع الرابع"}
    
    def __init__(self):
        self.holiday_calendar = HolidayCalendar()
        self.seasonal_history = defaultdict(lambda: defaultdict(list))
    
    def analyze(self, closes: np.ndarray, volumes: np.ndarray,
                dates: Optional[List[datetime]] = None,
                external_signals: Dict = None) -> Dict:
        """
        تحليل الموسمية الكامل
        
        external_signals: إشارات من استراتيجيات أخرى لتضخيمها/تصفيتها
        """
        if len(closes) < 50:
            return self._empty_result()
        
        # بناء البروفايل
        profile = self._build_profile(closes, volumes, dates)
        
        # حساب معامل المرشح
        filter_multiplier = self._calculate_filter_multiplier(profile, closes, dates)
        
        # 🟢 تعديل 11: إذا كانت هناك إشارات خارجية، طبق المرشح
        weighted_signals = None
        if external_signals:
            weighted_signals = self._apply_seasonal_filter(external_signals, filter_multiplier)
        
        # كشف الشذوذ مع سياق
        anomalies = self._detect_anomalies_with_context(closes, profile, dates)
        
        # 🟢 تعديل 13: False Seasonality Break
        false_breaks = self._detect_false_seasonality_breaks(closes, profile)
        
        # العطل القادمة
        upcoming_holidays = []
        if dates and len(dates) > 0:
            upcoming_holidays = self.holiday_calendar.get_upcoming_holidays(dates[-1])
        
        return {
            "profile": profile,
            "filter_multiplier": filter_multiplier,
            "weighted_signals": weighted_signals,
            "anomalies": anomalies,
            "false_breaks": false_breaks,
            "upcoming_holidays": upcoming_holidays,
            "recommendation": "مرشح",  # لا توصية مستقلة
            "confidence": 0,  # الموسمية لا تقرر وحدها
            "reason": f"معامل المرشح الموسمي: {filter_multiplier:.2f}x",
        }
    
    def _empty_result(self) -> Dict:
        """نتيجة فارغة"""
        return {
            "profile": None,
            "filter_multiplier": 1.0,
            "weighted_signals": None,
            "anomalies": [],
            "false_breaks": [],
            "upcoming_holidays": [],
            "recommendation": "محايد",
            "confidence": 0,
            "reason": "بيانات غير كافية",
        }
    
    def get_seasonal_filter(self, closes: np.ndarray, volumes: np.ndarray,
                            dates: List[datetime] = None) -> float:
        """
        🔴 تعديل 2: دالة المرشح الموسمي
        
        تستخدمها الاستراتيجيات الأخرى للحصول على معامل التضخيم/التضعيف
        """
        profile = self._build_profile(closes, volumes, dates)
        return self._calculate_filter_multiplier(profile, closes, dates)
    
    def _build_profile(self, closes: np.ndarray, volumes: np.ndarray,
                       dates: Optional[List[datetime]]) -> SeasonalityProfile:
        """بناء بروفايل الموسمية الكامل"""
        
        # تحليل الأنماط
        monthly = self._analyze_monthly_patterns(closes, dates)
        weekly = self._analyze_weekly_patterns(closes, dates)
        specials = self._analyze_special_periods(closes, dates)  # 🔴 تعديل 5
        quarters = self._analyze_quarter_patterns(closes, dates)  # 🟡 تعديل 10
        
        # تحديد الزمن الحالي
        current_month = 4  # مايو افتراضي
        current_week_of_month = 2
        current_quarter = 2
        
        if dates and len(dates) > 0:
            try:
                last_date = dates[-1]
                current_month = last_date.month - 1
                current_week_of_month = (last_date.day - 1) // 7 + 1
                current_quarter = (last_date.month - 1) // 3 + 1
            except:
                pass
        
        # التحيز الموسمي
        seasonal_bias = 'neutral'
        seasonal_strength = 0.0
        
        active_monthly = [p for p in monthly if p.period_key == self.MONTHS_AR[current_month]]
        if active_monthly:
            pattern = active_monthly[0]
            if pattern.avg_return > 0.003:
                seasonal_bias = 'bullish'
                seasonal_strength = pattern.strength
            elif pattern.avg_return < -0.003:
                seasonal_bias = 'bearish'
                seasonal_strength = pattern.strength
        
        # 🟢 تعديل 14: زخم شهري
        momentum_score = self._calculate_monthly_momentum(monthly, current_month)
        
        # معامل المرشح
        filter_multiplier = self._calculate_filter_multiplier_from_parts(
            seasonal_bias, seasonal_strength, momentum_score, specials, quarters, current_quarter
        )
        
        # شذوذ
        anomaly_score = self._calculate_anomaly_score(closes, profile=None)
        
        return SeasonalityProfile(
            current_month=self.MONTHS_AR[current_month],
            current_week_of_month=current_week_of_month,
            current_quarter=current_quarter,
            monthly_patterns=monthly,
            weekly_patterns=weekly,
            special_periods=specials,
            quarter_patterns=quarters,
            seasonal_bias=seasonal_bias,
            seasonal_strength=seasonal_strength,
            seasonal_filter_multiplier=filter_multiplier,
            anomaly_score=anomaly_score,
            momentum_score=momentum_score,
        )
    
    def _analyze_monthly_patterns(self, closes: np.ndarray,
                                    dates: Optional[List[datetime]]) -> List[SeasonalPattern]:
        """
        🔴 تعديل 1: تحليل الأنماط الشهرية مع مدى العوائد ونسبة السنوات الموجبة
        🔴 تعديل 4: حجم الشهر ديناميكي
        🟡 تعديل 7: Seasonal Shift Detection
        🟡 تعديل 8: العائد الزائد
        """
        patterns = []
        
        if dates is None or len(dates) < 30:
            return self._estimate_monthly_from_data(closes)
        
        # 🔴 تعديل 4: حجم الشهر ديناميكي
        date_range = (dates[-1] - dates[0]).days if hasattr(dates[-1], 'days') else len(dates)
        months_of_data = max(1, date_range / 30)
        bars_per_month = int(len(closes) / months_of_data) if months_of_data > 0 else 21
        
        # تجميع العوائد حسب الشهر والسنة
        monthly_data = defaultdict(lambda: defaultdict(list))
        
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                month = dates[i].month - 1
                year = dates[i].year
                monthly_data[month][year].append(ret)
        
        # عائد السوق الكلي للعائد الزائد
        total_return = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        annualized_return = total_return / max(1, months_of_data / 12)
        monthly_market_return = annualized_return / 12
        
        for month_idx, years_data in monthly_data.items():
            all_returns = []
            yearly_returns = []
            
            for year, returns in years_data.items():
                year_return = np.sum(returns) if returns else 0
                yearly_returns.append(year_return)
                all_returns.extend(returns)
            
            if len(yearly_returns) >= 2:
                avg_ret = np.mean(yearly_returns)
                win_rate = sum(1 for r in yearly_returns if r > 0) / len(yearly_returns)
                
                # 🔴 تعديل 1: مدى العوائد
                return_range = (np.min(yearly_returns), np.max(yearly_returns))
                positive_years_ratio = win_rate
                
                # 🟡 تعديل 8: العائد الزائد
                excess_return = avg_ret - monthly_market_return
                
                # 🟡 تعديل 7: Seasonal Shift Detection
                recent_years = yearly_returns[-3:] if len(yearly_returns) >= 3 else yearly_returns
                older_years = yearly_returns[:-3] if len(yearly_returns) > 3 else yearly_returns
                
                recent_trend = 'stable'
                shift_detected = False
                
                if len(recent_years) >= 2 and len(older_years) >= 2:
                    recent_avg = np.mean(recent_years)
                    older_avg = np.mean(older_years)
                    
                    if older_avg > 0 and recent_avg < 0:
                        recent_trend = 'turning_bearish'
                        shift_detected = True
                    elif older_avg < 0 and recent_avg > 0:
                        recent_trend = 'turning_bullish'
                        shift_detected = True
                    elif recent_avg > older_avg * 1.5:
                        recent_trend = 'strengthening'
                    elif recent_avg < older_avg * 0.5:
                        recent_trend = 'weakening'
                
                strength = min(1.0, abs(avg_ret) * 50)
                consistency = 1 - np.std(yearly_returns) / max(abs(np.mean(yearly_returns)), 0.0001)
                
                patterns.append(SeasonalPattern(
                    period='monthly',
                    period_key=self.MONTHS_AR[month_idx],
                    avg_return=avg_ret,
                    win_rate=win_rate,
                    strength=min(1.0, max(0, strength)),
                    consistency=min(1.0, max(0, consistency)),
                    return_range=return_range,
                    positive_years_ratio=positive_years_ratio,
                    excess_return=excess_return,
                    current_phase='active' if month_idx == dates[-1].month - 1 else 'inactive',
                    recent_trend=recent_trend,
                    shift_detected=shift_detected,
                ))
        
        return patterns
    
    def _estimate_monthly_from_data(self, closes: np.ndarray) -> List[SeasonalPattern]:
        """
        🔴 تعديل 4: تقدير الموسمية بحجم ديناميكي
        """
        patterns = []
        
        if len(closes) < 50:
            return patterns
        
        # حجم الشهر = إجمالي البيانات / 12
        bars_per_month = max(5, len(closes) // 12)
        
        for i in range(min(12, len(closes) // bars_per_month)):
            start = i * bars_per_month
            end = min((i + 1) * bars_per_month, len(closes))
            
            if end - start < 3:
                continue
            
            segment = closes[start:end]
            if segment[0] > 0:
                avg_ret = (segment[-1] - segment[0]) / segment[0]
            else:
                avg_ret = 0
            
            patterns.append(SeasonalPattern(
                period='monthly',
                period_key=f"شهر_{i+1}",
                avg_return=avg_ret,
                win_rate=0.5,
                strength=min(1.0, abs(avg_ret) * 10),
                consistency=0.5,
                return_range=(avg_ret * 0.5, avg_ret * 1.5),
                positive_years_ratio=0.5,
                current_phase='inactive',
                shift_detected=False,
            ))
        
        return patterns
    
    def _analyze_weekly_patterns(self, closes: np.ndarray,
                                   dates: Optional[List[datetime]]) -> List[SeasonalPattern]:
        """تحليل الأنماط الأسبوعية"""
        patterns = []
        
        if dates is None:
            return patterns
        
        daily_returns = defaultdict(list)
        
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                day = dates[i].weekday()
                daily_returns[day].append(ret)
        
        for day, returns in daily_returns.items():
            if len(returns) >= 5:
                avg_ret = np.mean(returns)
                win_rate = sum(1 for r in returns if r > 0) / len(returns)
                
                patterns.append(SeasonalPattern(
                    period='weekly',
                    period_key=self.DAYS_AR[day],
                    avg_return=avg_ret,
                    win_rate=win_rate,
                    strength=min(1.0, abs(avg_ret) * 100),
                    consistency=0.7,
                    return_range=(np.min(returns), np.max(returns)),
                    positive_years_ratio=win_rate,
                    current_phase='active' if day == dates[-1].weekday() else 'inactive',
                ))
        
        return patterns
    
    def _analyze_special_periods(self, closes: np.ndarray,
                                   dates: Optional[List[datetime]]) -> List[SeasonalPattern]:
        """
        🔴 تعديل 5: الفترات الخاصة تتعلم من البيانات الفعلية
        """
        specials = []
        
        if dates is None or len(dates) < 60:
            return specials
        
        last_date = dates[-1]
        
        # تحليل الأداء الفعلي لكل فترة خاصة من التاريخ
        special_periods_checks = {
            'نهاية الشهر': lambda d: d.day >= 25,
            'بداية الشهر': lambda d: d.day <= 5,
            'تأثير يناير': lambda d: d.month == 1,
            'رالي ديسمبر': lambda d: d.month == 12,
            'البيع في مايو': lambda d: d.month == 5,
        }
        
        for period_name, check_func in special_periods_checks.items():
            # جمع العوائد في هذه الفترة عبر التاريخ
            period_returns = []
            
            for i in range(1, len(closes)):
                if closes[i-1] > 0 and check_func(dates[i]):
                    ret = (closes[i] - closes[i-1]) / closes[i-1]
                    period_returns.append(ret)
            
            if len(period_returns) >= 5:
                avg_ret = np.mean(period_returns)
                win_rate = sum(1 for r in period_returns if r > 0) / len(period_returns)
                strength = min(1.0, abs(avg_ret) * 100)
                
                is_active = check_func(last_date)
                
                specials.append(SeasonalPattern(
                    period='special',
                    period_key=period_name,
                    avg_return=avg_ret,
                    win_rate=win_rate,
                    strength=min(1.0, max(0, strength)),
                    consistency=0.6,
                    return_range=(np.min(period_returns), np.max(period_returns)),
                    positive_years_ratio=win_rate,
                    current_phase='active' if is_active else 'inactive',
                ))
        
        return specials
    
    def _analyze_quarter_patterns(self, closes: np.ndarray,
                                    dates: Optional[List[datetime]]) -> List[SeasonalPattern]:
        """
        🟡 تعديل 10: Quarter Effects
        """
        patterns = []
        
        if dates is None or len(dates) < 90:
            return patterns
        
        quarter_returns = defaultdict(list)
        
        for i in range(1, len(closes)):
            if closes[i-1] > 0 and i < len(dates):
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                quarter = (dates[i].month - 1) // 3 + 1
                quarter_returns[quarter].append(ret)
        
        for q, returns in quarter_returns.items():
            if len(returns) >= 10:
                avg_ret = np.mean(returns)
                win_rate = sum(1 for r in returns if r > 0) / len(returns)
                
                patterns.append(SeasonalPattern(
                    period='quarter',
                    period_key=self.QUARTERS[q],
                    avg_return=avg_ret,
                    win_rate=win_rate,
                    strength=min(1.0, abs(avg_ret) * 30),
                    consistency=0.6,
                    return_range=(np.min(returns), np.max(returns)),
                    positive_years_ratio=win_rate,
                    current_phase='active' if q == (dates[-1].month - 1) // 3 + 1 else 'inactive',
                ))
        
        return patterns
    
    def _calculate_filter_multiplier(self, profile: SeasonalityProfile,
                                      closes: np.ndarray,
                                      dates: Optional[List[datetime]]) -> float:
        """
        🔴 تعديل 2: معامل المرشح الموسمي
        
        يستخدم كمضاعف لإشارات الاستراتيجيات الأخرى
        1.0 = لا تأثير
        > 1.0 = تعزيز
        < 1.0 = تضعيف
        """
        multiplier = 1.0
        
        # 1. التحيز الموسمي
        if profile.seasonal_bias == 'bullish':
            multiplier += profile.seasonal_strength * 0.3
        elif profile.seasonal_bias == 'bearish':
            multiplier -= profile.seasonal_strength * 0.3
        
        # 2. الزخم الشهري
        multiplier += (profile.momentum_score - 0.5) * 0.2
        
        # 3. الفترات الخاصة النشطة
        active_specials = [p for p in profile.special_periods if p.current_phase == 'active']
        for special in active_specials:
            if special.avg_return > 0.003:
                multiplier += 0.1
            elif special.avg_return < -0.003:
                multiplier -= 0.1
        
        # 4. Quarter Effects
        active_quarter = [p for p in profile.quarter_patterns if p.current_phase == 'active']
        for q in active_quarter:
            multiplier += q.avg_return * 5  # تطبيع
        
        # 5. شذوذ
        if profile.anomaly_score > 0.7:
            multiplier *= 0.8  # تضعيف في حالة الشذوذ
        
        # 6. تحول موسمي
        active_monthly = [p for p in profile.monthly_patterns if p.current_phase == 'active']
        if active_monthly and active_monthly[0].shift_detected:
            if active_monthly[0].recent_trend == 'turning_bearish':
                multiplier -= 0.15
            elif active_monthly[0].recent_trend == 'turning_bullish':
                multiplier += 0.15
        
        # تقييد
        return max(0.5, min(1.5, multiplier))
    
    def _calculate_filter_multiplier_from_parts(self, seasonal_bias, seasonal_strength,
                                                  momentum_score, specials, quarters,
                                                  current_quarter) -> float:
        """حساب معامل المرشح من الأجزاء"""
        multiplier = 1.0
        
        if seasonal_bias == 'bullish':
            multiplier += seasonal_strength * 0.3
        elif seasonal_bias == 'bearish':
            multiplier -= seasonal_strength * 0.3
        
        multiplier += (momentum_score - 0.5) * 0.2
        
        active_specials = [p for p in specials if p.current_phase == 'active']
        for special in active_specials:
            if special.avg_return > 0.003:
                multiplier += 0.1
            elif special.avg_return < -0.003:
                multiplier -= 0.1
        
        active_quarter = [p for p in quarters if p.current_phase == 'active']
        for q in active_quarter:
            multiplier += q.avg_return * 5
        
        return max(0.5, min(1.5, multiplier))
    
    def _calculate_monthly_momentum(self, monthly_patterns: List[SeasonalPattern],
                                      current_month: int) -> float:
        """
        🟢 تعديل 14: Month-over-Month Momentum
        
        3 أشهر متتالية فوق متوسطها = زخم قوي
        """
        if len(monthly_patterns) < 3:
            return 0.5
        
        # آخر 3 أشهر (بما فيها الحالي)
        recent_months = []
        for i in range(3):
            month_idx = (current_month - i) % 12
            month_patterns = [p for p in monthly_patterns if p.period_key == self.MONTHS_AR[month_idx]]
            if month_patterns:
                recent_months.append(month_patterns[0])
        
        if len(recent_months) < 2:
            return 0.5
        
        # هل كلها في نفس الاتجاه؟
        all_positive = all(m.avg_return > 0 for m in recent_months)
        all_negative = all(m.avg_return < 0 for m in recent_months)
        
        # هل تتسارع؟
        if len(recent_months) >= 3:
            if all_positive and recent_months[0].avg_return > recent_months[1].avg_return:
                return 0.7
            elif all_negative and recent_months[0].avg_return < recent_months[1].avg_return:
                return 0.3
        
        if all_positive:
            return 0.6
        elif all_negative:
            return 0.4
        
        return 0.5
    
    def _calculate_anomaly_score(self, closes: np.ndarray,
                                   profile: SeasonalityProfile = None) -> float:
        """حساب درجة الشذوذ"""
        if len(closes) < 20:
            return 0.0
        
        recent_return = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
        
        # السوق يتحرك عكس الموسمية = شذوذ
        if profile and profile.seasonal_bias == 'bullish' and recent_return < -0.02:
            return min(1.0, abs(recent_return) * 20)
        elif profile and profile.seasonal_bias == 'bearish' and recent_return > 0.02:
            return min(1.0, abs(recent_return) * 20)
        
        return 0.0
    
    def _detect_anomalies_with_context(self, closes: np.ndarray,
                                         profile: SeasonalityProfile,
                                         dates: Optional[List[datetime]]) -> List[Dict]:
        """
        🔴 تعديل 3: الشذوذ يحتاج سياقاً سعرياً
        """
        anomalies = []
        
        if len(closes) < 20:
            return anomalies
        
        recent_return = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
        
        if profile.seasonal_bias == 'bullish' and recent_return < -0.02:
            # تحقق: هل هذا مجرد تصحيح أم انهيار حقيقي؟
            below_support = False
            if len(closes) >= 50:
                lows_50 = min(closes[-50:])
                below_support = closes[-1] < lows_50 * 1.01
            
            anomalies.append({
                "type": "موسمية معاكسة",
                "message": "السوق يهبط رغم موسمية صاعدة",
                "strength": 0.7 if below_support else 0.5,
                "context": "كسر دعم" if below_support else "تصحيح طبيعي",
                "requires_confirmation": not below_support,
            })
        elif profile.seasonal_bias == 'bearish' and recent_return > 0.02:
            above_resistance = False
            if len(closes) >= 50:
                highs_50 = max(closes[-50:])
                above_resistance = closes[-1] > highs_50 * 0.99
            
            anomalies.append({
                "type": "موسمية معاكسة",
                "message": "السوق يصعد رغم موسمية هابطة",
                "strength": 0.7 if above_resistance else 0.5,
                "context": "اختراق مقاومة" if above_resistance else "ارتداد طبيعي",
                "requires_confirmation": not above_resistance,
            })
        
        return anomalies
    
    def _detect_false_seasonality_breaks(self, closes: np.ndarray,
                                           profile: SeasonalityProfile) -> List[Dict]:
        """
        🟢 تعديل 13: False Seasonality Break
        
        السوق يكسر نمطه الموسمي = حدث كبير
        """
        breaks = []
        
        if len(closes) < 60:
            return breaks
        
        # مقارنة أداء هذا الشهر بأداء نفس الشهر تاريخياً
        active_monthly = [p for p in profile.monthly_patterns if p.current_phase == 'active']
        if not active_monthly:
            return breaks
        
        pattern = active_monthly[0]
        
        # أداء الشهر الحالي حتى الآن
        if len(closes) >= 20:
            month_return = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
            
            # كسر النمط
            if pattern.avg_return > 0.02 and month_return < -0.02:
                breaks.append({
                    "type": "False Seasonality Break",
                    "message": f"{pattern.period_key} يكسر نمطه الصاعد ({pattern.avg_return:.1%} → {month_return:.1%})",
                    "strength": 0.75,
                    "direction": "bearish",
                })
            elif pattern.avg_return < -0.02 and month_return > 0.02:
                breaks.append({
                    "type": "False Seasonality Break",
                    "message": f"{pattern.period_key} يكسر نمطه الهابط ({pattern.avg_return:.1%} → {month_return:.1%})",
                    "strength": 0.75,
                    "direction": "bullish",
                })
        
        return breaks
    
    def _apply_seasonal_filter(self, external_signals: Dict,
                                filter_multiplier: float) -> Dict:
        """
        🟢 تعديل 11: تطبيق المرشح الموسمي على إشارات خارجية
        
        يستخدم هذا من Wyckoff, VSA, ICT, إلخ
        """
        weighted = {"buy_signals": [], "sell_signals": [], "filter_multiplier": filter_multiplier}
        
        for signal in external_signals.get("buy_signals", []):
            weighted["buy_signals"].append({
                "original": signal[0] if isinstance(signal, tuple) else signal,
                "original_weight": signal[1] if isinstance(signal, tuple) else 0.5,
                "seasonal_weight": signal[1] * filter_multiplier if isinstance(signal, tuple) else 0.5 * filter_multiplier,
            })
        
        for signal in external_signals.get("sell_signals", []):
            weighted["sell_signals"].append({
                "original": signal[0] if isinstance(signal, tuple) else signal,
                "original_weight": signal[1] if isinstance(signal, tuple) else 0.5,
                "seasonal_weight": signal[1] * (2 - filter_multiplier) if isinstance(signal, tuple) else 0.5 * (2 - filter_multiplier),
            })
        
        return weighted


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: طبقة المرشح الموسمي الموحدة                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SeasonalityStrategy:
    """
    طبقة المرشح الموسمي (الإصدار 2.0)
    
    لم تعد استراتيجية مستقلة. هي طبقة مرشحة ذكية.
    
    الوظيفة الأساسية:
    seasonal_filter = seasonality.get_seasonal_filter(closes, volumes, dates)
    weighted_signal = original_signal × seasonal_filter
    """
    
    def __init__(self):
        self.analyzer = DynamicSeasonalityAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل (كطبقة مرشحة)
        """
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        dates = chart_data.get('dates', None)
        external_signals = chart_data.get('external_signals', None)
        
        if len(closes) < 30:
            return {"recommendation": "محايد", "confidence": 0,
                    "reason": "بيانات غير كافية للمرشح الموسمي"}
        
        result = self.analyzer.analyze(closes, volumes, dates, external_signals)
        
        # إذا كانت هناك إشارات خارجية، استخدمها
        if result.get("weighted_signals"):
            weighted = result["weighted_signals"]
            buy_total = sum(s["seasonal_weight"] for s in weighted["buy_signals"])
            sell_total = sum(s["seasonal_weight"] for s in weighted["sell_signals"])
            
            if buy_total > sell_total * 1.3:
                recommendation = "شراء (معدل موسمياً)"
                confidence = min(80, int(buy_total * 100))
            elif sell_total > buy_total * 1.3:
                recommendation = "بيع (معدل موسمياً)"
                confidence = min(80, int(sell_total * 100))
            else:
                recommendation = "محايد"
                confidence = 30
        else:
            # لا توجد إشارات خارجية - نُرجع نتيجة محايدة ذات ثقة منخفضة
            recommendation = "محايد"
            confidence = 20
        
        filter_mult = result.get("filter_multiplier", 1.0)
        
        return {
            **result,
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": f"معامل المرشح الموسمي: {filter_mult:.2f}x | " + \
                      f"تحيز: {result.get('profile', {}).seasonal_bias if result.get('profile') else 'غير معروف'}",
        }
    
    def get_filter(self, chart_data: Dict) -> float:
        """
        دالة سريعة للحصول على معامل المرشح فقط
        تستخدمها الاستراتيجيات الأخرى
        """
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        dates = chart_data.get('dates', None)
        
        if len(closes) < 30:
            return 1.0
        
        return self.analyzer.get_seasonal_filter(closes, volumes, dates)


def create_seasonality_strategy():
    """إنشاء طبقة المرشح الموسمي الجاهزة (الإصدار 2.0)"""
    return SeasonalityStrategy()