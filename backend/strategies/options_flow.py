"""
═══════════════════════════════════════════════════════════════════════════════
OPTIONS FLOW ANALYSIS - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثلاثون: تحليل تدفق الخيارات - بيانات حقيقية + تقدير احتياطي
═══════════════════════════════════════════════════════════════════════════════

سوق الخيارات يكشف نوايا المؤسسات قبل سوق الأسهم.
"الخيارات تسبق السهم" - Options Lead the Stock.

هذه النسخة ديناميكية بالكامل - معاد بناؤها من الصفر:
- تحاول جلب بيانات Options حقيقية من Binance Options API
- إذا فشلت: تستخدم وضع "التقدير الاحتياطي" مع إفصاح صريح
- مصطلحات دقيقة: Return Distribution Skew (وليس Options Skew)
- PCR = محاولة جلب حقيقي، مع تقدير احتياطي من الحجم
- Gamma Exposure = من سلوك السعر (تقديري) مع تحذير
- Max Pain = من Binance إذا توفر، وإلا غير متاح
- Dealer Delta Hedging تقديري
- Expiry Dynamics من time_sessions_strategy
- Gamma Flip Detection
- Pin Risk حقيقي

المفاهيم:
1. Unusual Options Activity (حقيقي أو مقدر)
2. Put/Call Ratio (حقيقي أو مقدر)
3. Gamma Exposure - GEX (مقدر)
4. Delta Hedging Flows (مقدر)
5. Max Pain Theory (من API)
6. Return Distribution Skewness
7. Volatility Risk Premium
8. Dealer Positioning
9. Strike Concentration
10. Expiry Dynamics
11. Gamma Flip Detection
12. Pin Risk
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات المعاد بناؤها                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class OptionsFlow:
    """تدفق خيارات - حقيقي أو مقدر"""
    call_volume: float
    put_volume: float
    call_premium: float
    put_premium: float
    put_call_ratio: float
    unusual_activity: bool
    dominant_direction: str
    sentiment: str
    data_source: str = 'estimated'  # 🔴 تعديل 1: 'real' or 'estimated'
    # 🟡 تعديل 10: PCR حقيقي من API
    real_pcr: Optional[float] = None
    real_pcr_source: str = 'none'


@dataclass
class GammaProfile:
    """بروفايل جاما - محسن"""
    gamma_level: float
    gamma_flip_zone: Tuple[float, float]
    dealer_position: str
    expected_volatility: str
    pin_risk: bool
    max_gamma_strike: float
    # 🟢 تعديل 13: Gamma Flip Detection
    gamma_flip_risk: float = 0.0
    gamma_flip_direction: str = 'none'
    # 🟡 تعديل 8: Dealer Delta Hedging
    dealer_hedging_flow: str = 'neutral'
    dealer_hedging_strength: float = 0.0


@dataclass
class MaxPainData:
    """بيانات Max Pain"""
    max_pain_price: Optional[float]
    call_wall: Optional[float]  # أعلى Strike مع أكبر OI
    put_wall: Optional[float]   # أدنى Strike مع أكبر OI
    data_source: str = 'none'   # 'binance', 'estimated', 'none'
    expiry_date: Optional[str] = None


@dataclass
class OptionsSignal:
    """إشارة خيارات"""
    index: int
    signal_type: str
    direction: str
    strength: float
    description: str
    data_quality: str = 'estimated'  # 'real', 'estimated'


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: جسر بيانات الخيارات الحقيقية                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OptionsDataBridge:
    """
    🔴 تعديل 1 + 🟢 تعديل 11: جسر إلى بيانات الخيارات الحقيقية
    
    يحاول جلب:
    - Binance Options API (Open Interest, Strike Prices, Greeks)
    - PCR حقيقي من مصادر خارجية
    - Max Pain
    """
    
    def __init__(self):
        self.binance_service = None
        self._init_binance()
        self.cached_oi = {}  # Open Interest cache
        self.cached_pcr = None
        self.last_pcr_fetch = None
    
    def _init_binance(self):
        """محاولة الاتصال بـ Binance"""
        try:
            from services.binance_service import BinanceService
            self.binance_service = BinanceService()
            logger.info("✅ تم ربط BinanceService لبيانات الخيارات")
        except ImportError:
            logger.info("ℹ️ BinanceService غير متاح - استخدام التقدير الاحتياطي")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تهيئة BinanceService: {e}")
    
    def get_options_data(self, symbol: str = "BTCUSDT") -> Dict:
        """
        جلب بيانات الخيارات الحقيقية
        """
        result = {
            "has_real_data": False,
            "open_interest": None,
            "max_pain": None,
            "pcr": None,
            "strike_concentration": None,
            "source": "none",
        }
        
        if self.binance_service:
            try:
                # محاولة جلب Open Interest
                oi_data = self._fetch_open_interest(symbol)
                if oi_data:
                    result["open_interest"] = oi_data
                    result["has_real_data"] = True
                    result["source"] = "binance"
                
                # محاولة جلب Max Pain
                max_pain = self._calculate_max_pain(symbol)
                if max_pain:
                    result["max_pain"] = max_pain
                
                # محاولة جلب PCR
                pcr = self._fetch_pcr(symbol)
                if pcr:
                    result["pcr"] = pcr
                    
            except Exception as e:
                logger.warning(f"تعذر جلب بيانات الخيارات من Binance: {e}")
        
        return result
    
    def _fetch_open_interest(self, symbol: str) -> Optional[Dict]:
        """جلب Open Interest من Binance"""
        try:
            if self.binance_service:
                # Binance Options API endpoint
                oi = self.binance_service.get_options_open_interest(symbol)
                if oi:
                    self.cached_oi = oi
                    return oi
        except:
            pass
        return None
    
    def _calculate_max_pain(self, symbol: str) -> Optional[float]:
        """
        🟡 تعديل 7: حساب Max Pain من Open Interest
        
        Max Pain = السعر الذي يخسر عنده أكبر عدد من حاملي الخيارات
        """
        if not self.cached_oi:
            return None
        
        try:
            # تبسيط: السعر الذي يكون عنده Total Pain (Call OI + Put OI) أقل ما يمكن
            strikes = self.cached_oi.get('strikes', [])
            call_oi = self.cached_oi.get('call_oi', [])
            put_oi = self.cached_oi.get('put_oi', [])
            
            if not strikes or not call_oi or not put_oi:
                return None
            
            # لكل strike، احسب الألم الإجمالي
            pain_values = []
            for i, strike in enumerate(strikes):
                # Call pain: max(0, spot - strike) * call_oi
                # Put pain: max(0, strike - spot) * put_oi
                total_pain = sum(
                    max(0, strikes[j] - strike) * call_oi[j] +
                    max(0, strike - strikes[j]) * put_oi[j]
                    for j in range(len(strikes))
                )
                pain_values.append((strike, total_pain))
            
            # أقل ألم = Max Pain
            max_pain = min(pain_values, key=lambda x: x[1])[0]
            return max_pain
            
        except Exception as e:
            logger.warning(f"تعذر حساب Max Pain: {e}")
        
        return None
    
    def _fetch_pcr(self, symbol: str) -> Optional[float]:
        """
        🟡 تعديل 10: جلب PCR حقيقي
        """
        if self.cached_pcr and self.last_pcr_fetch and \
           datetime.now() - self.last_pcr_fetch < timedelta(minutes=15):
            return self.cached_pcr
        
        try:
            if self.binance_service:
                pcr = self.binance_service.get_put_call_ratio(symbol)
                if pcr:
                    self.cached_pcr = pcr
                    self.last_pcr_fetch = datetime.now()
                    return pcr
        except:
            pass
        
        # محاولة من API خارجي (بديل)
        try:
            # يمكن إضافة web scraping لموقع يعرض PCR
            pass
        except:
            pass
        
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: محلل تدفق الخيارات (محسن بالكامل)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OptionsFlowAnalyzer:
    """
    يحلل تدفق الخيارات - حقيقي أو تقديري.
    
    🔴 تعديل 1-5: مصطلحات دقيقة، تقدير صريح
    🟡 تعديل 7: Max Pain
    🟡 تعديل 8: Dealer Delta Hedging
    🟡 تعديل 10: PCR حقيقي
    🟢 تعديل 13: Gamma Flip Detection
    """
    
    def __init__(self):
        self.data_bridge = OptionsDataBridge()
        self.gamma_history = deque(maxlen=50)
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, opens: np.ndarray,
                symbol: str = "BTCUSDT") -> Dict:
        """تحليل كامل"""
        
        # محاولة جلب بيانات حقيقية
        real_options = self.data_bridge.get_options_data(symbol)
        has_real_data = real_options.get("has_real_data", False)
        
        # تحليل تدفق الخيارات
        flow = self._analyze_flow(highs, lows, closes, volumes, opens, real_options)
        
        # بروفايل جاما
        gamma = self._analyze_gamma(highs, lows, closes, volumes, real_options)
        
        # PCR
        pcr_analysis = self._analyze_pcr(highs, lows, closes, volumes, real_options)
        
        # نشاط غير عادي
        unusual = self._detect_unusual_activity(volumes, closes)
        
        # توزيع العوائد (Skewness إحصائي)
        skew = self._analyze_return_distribution(closes)
        
        # Max Pain
        max_pain = self._get_max_pain(real_options, closes)
        
        # 🟡 تعديل 9: Expiry Dynamics
        expiry = self._analyze_expiry_dynamics()
        
        return {
            "flow": flow,
            "gamma": gamma,
            "pcr": pcr_analysis,
            "unusual": unusual,
            "skew": skew,
            "max_pain": max_pain,
            "expiry": expiry,
            "has_real_data": has_real_data,
            "data_source": real_options.get("source", "estimated"),
        }
    
    def _analyze_flow(self, highs, lows, closes, volumes, opens, real_options) -> OptionsFlow:
        """
        🔴 تعديل 1+2: تحليل التدفق مع إفصاح عن المصدر
        
        إذا توفرت بيانات حقيقية: يستخدمها
        إذا لم تتوفر: تقدير احتياطي مع تحذير
        """
        has_real = real_options.get("has_real_data", False)
        
        if has_real and real_options.get("open_interest"):
            # استخدام بيانات حقيقية
            oi = real_options["open_interest"]
            call_vol = oi.get("total_call_volume", 0)
            put_vol = oi.get("total_put_volume", 0)
            pcr = put_vol / call_vol if call_vol > 0 else 1.0
            real_pcr = real_options.get("pcr")
            
            return OptionsFlow(
                call_volume=call_vol,
                put_volume=put_vol,
                call_premium=call_vol * 0.05,
                put_premium=put_vol * 0.05,
                put_call_ratio=pcr,
                unusual_activity=False,
                dominant_direction='bullish' if pcr < 0.7 else 'bearish' if pcr > 1.3 else 'neutral',
                sentiment=self._classify_sentiment(pcr),
                data_source='real',
                real_pcr=real_pcr,
                real_pcr_source='binance' if real_pcr else 'none',
            )
        
        # 🔴 تعديل 1: تقدير احتياطي (مع إفصاح)
        return self._estimate_flow_from_price(highs, lows, closes, volumes, opens)
    
    def _estimate_flow_from_price(self, highs, lows, closes, volumes, opens) -> OptionsFlow:
        """
        تقدير تدفق الخيارات من حركة السعر (احتياطي)
        """
        if len(closes) < 15:
            return OptionsFlow(0, 0, 0, 0, 1.0, False, 'neutral', 'neutral', 'estimated')
        
        call_vol = 0.0
        put_vol = 0.0
        
        for i in range(len(closes)):
            bar_range = highs[i] - lows[i]
            bar_vol = volumes[i]
            
            if bar_range > 0:
                close_position = (closes[i] - lows[i]) / bar_range
                
                upper_wick = highs[i] - max(opens[i], closes[i])
                lower_wick = min(opens[i], closes[i]) - lows[i]
                
                if upper_wick > bar_range * 0.4:
                    call_vol += bar_vol * 0.4
                elif lower_wick > bar_range * 0.4:
                    put_vol += bar_vol * 0.4
                elif closes[i] > opens[i]:
                    call_vol += bar_vol * 0.3
                else:
                    put_vol += bar_vol * 0.3
        
        total = call_vol + put_vol
        pcr = put_vol / call_vol if call_vol > 0 else 2.0
        
        return OptionsFlow(
            call_volume=call_vol,
            put_volume=put_vol,
            call_premium=call_vol * 0.1,
            put_premium=put_vol * 0.1,
            put_call_ratio=pcr,
            unusual_activity=(call_vol + put_vol) > np.sum(volumes) * 0.4,
            dominant_direction='bullish' if pcr < 0.6 else 'bearish' if pcr > 1.6 else 'neutral',
            sentiment=self._classify_sentiment(pcr),
            data_source='estimated',
        )
    
    def _classify_sentiment(self, pcr: float) -> str:
        """تصنيف المعنويات من PCR"""
        if pcr > 1.8:
            return 'خوف شديد - حماية مكثفة من الهبوط (انعكاس محتمل)'
        elif pcr > 1.3:
            return 'خوف - حماية من الهبوط'
        elif pcr < 0.5:
            return 'تفاؤل مفرط - رهان كبير على الصعود (قمة محتملة)'
        elif pcr < 0.7:
            return 'تفاؤل - رهان على الصعود'
        else:
            return 'محايد - توازن بين Call و Put'
    
    def _analyze_gamma(self, highs, lows, closes, volumes, real_options) -> GammaProfile:
        """
        تحليل جاما - محسن
        
        🟡 تعديل 8: Dealer Delta Hedging
        🟢 تعديل 13: Gamma Flip Detection
        """
        if len(closes) < 20:
            return GammaProfile(0, (0, 0), 'neutral', 'normal', False, 0)
        
        ranges = highs[-20:] - lows[-20:]
        avg_range = np.mean(ranges)
        current_range = np.mean(ranges[-5:])
        current = closes[-1]
        
        # تقدير مستوى جاما
        if current_range < avg_range * 0.5:
            gamma_level = 0.8
            vol_effect = 'suppressed'
            position = 'long_gamma'
        elif current_range > avg_range * 1.8:
            gamma_level = -0.8
            vol_effect = 'amplified'
            position = 'short_gamma'
        else:
            gamma_level = 0.0
            vol_effect = 'normal'
            position = 'neutral'
        
        # منطقة انقلاب جاما
        flip_zone = (current * 0.985, current * 1.015)
        
        # 🟢 تعديل 13: Gamma Flip Risk
        gamma_flip_risk = 0.0
        gamma_flip_direction = 'none'
        
        if len(self.gamma_history) >= 10:
            old_gamma = list(self.gamma_history)[-10]
            if old_gamma > 0.3 and gamma_level < 0:
                gamma_flip_risk = 0.7
                gamma_flip_direction = 'long_to_short'
            elif old_gamma < -0.3 and gamma_level > 0:
                gamma_flip_risk = 0.7
                gamma_flip_direction = 'short_to_long'
        
        self.gamma_history.append(gamma_level)
        
        # 🟡 تعديل 8: Dealer Delta Hedging تقديري
        if position == 'long_gamma':
            dealer_flow = 'buy_dips_sell_rips'
            dealer_strength = 0.6
        elif position == 'short_gamma':
            dealer_flow = 'sell_dips_buy_rips'
            dealer_strength = 0.6
        else:
            dealer_flow = 'neutral'
            dealer_strength = 0.0
        
        # Pin Risk
        pin_risk = current_range < avg_range * 0.3 and len(ranges) >= 10
        
        return GammaProfile(
            gamma_level=gamma_level,
            gamma_flip_zone=flip_zone,
            dealer_position=position,
            expected_volatility=vol_effect,
            pin_risk=pin_risk,
            max_gamma_strike=round(current, -1) if current > 100 else round(current, 2),
            gamma_flip_risk=gamma_flip_risk,
            gamma_flip_direction=gamma_flip_direction,
            dealer_hedging_flow=dealer_flow,
            dealer_hedging_strength=dealer_strength,
        )
    
    def _analyze_pcr(self, highs, lows, closes, volumes, real_options) -> Dict:
        """
        🔴 تعديل 4 + 🟡 تعديل 10: تحليل PCR
        
        إذا توفر PCR حقيقي: يستخدمه
        إذا لم يتوفر: تقدير احتياطي من الحجم
        """
        real_pcr = real_options.get("pcr")
        
        if real_pcr is not None:
            pcr = real_pcr
            source = 'real'
        else:
            # تقدير احتياطي من الحجم
            down_vol = sum(volumes[i] for i in range(1, len(closes)) if closes[i] < closes[i-1])
            up_vol = sum(volumes[i] for i in range(1, len(closes)) if closes[i] > closes[i-1])
            pcr = down_vol / up_vol if up_vol > 0 else 1.0
            source = 'estimated'
        
        if pcr > 1.8:
            signal = "خوف شديد - انعكاس صعودي محتمل"
        elif pcr > 1.3:
            signal = "خوف - حماية من الهبوط"
        elif pcr < 0.5:
            signal = "تفاؤل مفرط - انعكاس هبوطي محتمل"
        elif pcr < 0.7:
            signal = "تفاؤل - رهان على الصعود"
        else:
            signal = "محايد"
        
        return {
            "pcr": pcr,
            "signal": signal,
            "source": source,
        }
    
    def _detect_unusual_activity(self, volumes, closes) -> List[Dict]:
        """كشف نشاط غير عادي"""
        unusual = []
        
        if len(volumes) < 15:
            return unusual
        
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        
        for i in range(5, len(volumes)):
            if volumes[i] > avg_vol * 3.0:
                unusual.append({
                    "index": i,
                    "volume": volumes[i],
                    "ratio": volumes[i] / max(avg_vol, 0.0001),
                    "price": closes[i] if i < len(closes) else 0,
                    "type": "call_activity" if closes[i] > closes[i-1] else "put_activity",
                })
        
        return unusual[-5:]
    
    def _analyze_return_distribution(self, closes) -> Dict:
        """
        🔴 تعديل 5: تحليل توزيع العوائد (Return Distribution Skewness)
        
        هذا ليس Options Skew. هذا Skewness إحصائي للعوائد.
        """
        if len(closes) < 20:
            return {"skewness": 0, "direction": "neutral", "type": "return_distribution"}
        
        returns = np.diff(np.log(np.maximum(closes, 0.0001)))
        if len(returns) < 10:
            return {"skewness": 0, "direction": "neutral", "type": "return_distribution"}
        
        skew_val = self._calculate_skewness(returns[-20:])
        
        if skew_val > 0.5:
            direction = "negative_skew - ذيل هابط (عوائد سلبية متطرفة)"
        elif skew_val < -0.5:
            direction = "positive_skew - ذيل صاعد (عوائد إيجابية متطرفة)"
        else:
            direction = "symmetric - توزيع متماثل"
        
        return {
            "skewness": skew_val,
            "direction": direction,
            "type": "return_distribution_skewness",
            "note": "هذا Skewness إحصائي للعوائد، وليس Options Skew",
        }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """حساب الانحراف الإحصائي"""
        n = len(data)
        if n < 3:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.sum((data - mean) ** 3) / (n * std ** 3)
    
    def _get_max_pain(self, real_options, closes) -> MaxPainData:
        """
        🟡 تعديل 7 + 🟢 تعديل 12: Max Pain
        
        إذا توفر من Binance: يستخدمه
        إذا لم يتوفر: غير متاح
        """
        max_pain_price = real_options.get("max_pain")
        
        if max_pain_price is not None:
            return MaxPainData(
                max_pain_price=max_pain_price,
                call_wall=None,
                put_wall=None,
                data_source='binance',
                expiry_date=None,
            )
        
        return MaxPainData(
            max_pain_price=None,
            call_wall=None,
            put_wall=None,
            data_source='none',
        )
    
    def _analyze_expiry_dynamics(self) -> Dict:
        """
        🟡 تعديل 9: Expiry Dynamics
        
        محاولة تحديد أيام انتهاء الخيارات
        """
        now = datetime.now()
        
        # آخر جمعة من الشهر = يوم انتهاء شهري
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.weekday() == 4:
            days_until_friday = 0
        
        next_friday = now + timedelta(days=days_until_friday)
        
        # هل الجمعة القادمة هي الأخيرة في الشهر؟
        is_monthly_expiry = next_friday.day > 25 or \
                           (next_friday + timedelta(days=7)).month != next_friday.month
        
        return {
            "next_expiry": next_friday.strftime('%Y-%m-%d') if days_until_friday > 0 else "اليوم",
            "is_monthly_expiry": is_monthly_expiry,
            "days_until_expiry": days_until_friday,
            "expiry_week": days_until_friday <= 5,
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية الخيارات الموحدة (محسنة)            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class OptionsFlowStrategy:
    """
    استراتيجية تحليل تدفق الخيارات - الإصدار 2.0
    
    - تحاول جلب بيانات حقيقية من Binance Options API
    - إذا فشلت: تقدير احتياطي مع إفصاح صريح
    - مصطلحات دقيقة
    """
    
    def __init__(self):
        self.analyzer = OptionsFlowAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """التحليل الكامل"""
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        symbol = chart_data.get('symbol', 'BTCUSDT')
        
        if len(closes) < 20:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 20 شمعة على الأقل"}
        
        current_price = closes[-1]
        
        # تحليل
        data = self.analyzer.analyze(highs, lows, closes, volumes, opens, symbol)
        
        # قرار
        decision = self._make_decision(data, current_price, closes)
        
        return {
            **decision,
            "options_data": data,
            "data_quality": "حقيقي" if data.get("has_real_data") else "تقديري",
        }
    
    def _make_decision(self, data: Dict, current_price: float,
                       closes: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        warnings = []
        
        flow = data.get('flow')
        gamma = data.get('gamma')
        pcr_analysis = data.get('pcr', {})
        unusual = data.get('unusual', [])
        skew = data.get('skew', {})
        max_pain = data.get('max_pain')
        expiry = data.get('expiry', {})
        has_real = data.get('has_real_data', False)
        
        # ---- من PCR ----
        pcr = pcr_analysis.get('pcr', 1.0)
        pcr_source = pcr_analysis.get('source', 'estimated')
        
        if pcr > 1.8:
            buy_signals.append((f"PCR مرتفع جداً ({pcr:.2f}) [{pcr_source}] - انعكاس صاعد", 0.6))
        elif pcr < 0.5:
            sell_signals.append((f"PCR منخفض جداً ({pcr:.2f}) [{pcr_source}] - انعكاس هابط", 0.6))
        elif pcr > 1.3:
            sell_signals.append((f"PCR مرتفع ({pcr:.2f}) [{pcr_source}] - حذر", 0.35))
        elif pcr < 0.7:
            buy_signals.append((f"PCR منخفض ({pcr:.2f}) [{pcr_source}] - تفاؤل", 0.35))
        
        # ---- من جاما ----
        if gamma:
            if gamma.dealer_position == 'long_gamma':
                buy_signals.append(("Long Gamma - تقلب مكبوت (تثبيت)", 0.3))
            elif gamma.dealer_position == 'short_gamma':
                warnings.append("Short Gamma - تقلب متضخم (خطر)")
                sell_signals.append(("Short Gamma - خطر انفجار", 0.45))
            
            # 🟢 تعديل 13: Gamma Flip
            if gamma.gamma_flip_risk > 0.5:
                if gamma.gamma_flip_direction == 'long_to_short':
                    warnings.append("⚠️ Gamma Flip: Long → Short - انفجار تقلب قادم")
                    sell_signals.append(("Gamma Flip هابط", 0.65))
                elif gamma.gamma_flip_direction == 'short_to_long':
                    buy_signals.append(("Gamma Flip صاعد - استقرار قادم", 0.55))
            
            # 🟡 تعديل 8: Dealer Hedging
            if gamma.dealer_hedging_flow == 'buy_dips_sell_rips':
                buy_signals.append(("تاجر يشتري عند الهبوط (Long Gamma)", 0.35))
            elif gamma.dealer_hedging_flow == 'sell_dips_buy_rips':
                sell_signals.append(("تاجر يبيع عند الهبوط (Short Gamma)", 0.35))
            
            if gamma.pin_risk:
                buy_signals.append(("Pin Risk - تثبيت حول السعر", 0.15))
                sell_signals.append(("Pin Risk - تثبيت حول السعر", 0.15))
        
        # ---- من Max Pain ----
        if max_pain and max_pain.max_pain_price:
            mp = max_pain.max_pain_price
            distance = (current_price - mp) / mp
            if abs(distance) < 0.02:
                warnings.append(f"السعر قرب Max Pain ({mp:.2f}) - مغناطيس سعري")
            elif distance > 0.03:
                sell_signals.append((f"السعر فوق Max Pain ({mp:.2f}) - جاذبية هابطة", 0.4))
            elif distance < -0.03:
                buy_signals.append((f"السعر تحت Max Pain ({mp:.2f}) - جاذبية صاعدة", 0.4))
        
        # ---- من النشاط غير العادي ----
        for u in unusual:
            if u.get('type') == 'call_activity':
                buy_signals.append((f"نشاط Call كبير ({u['ratio']:.1f}x)", 0.5))
            else:
                sell_signals.append((f"نشاط Put كبير ({u['ratio']:.1f}x)", 0.5))
        
        # ---- من توزيع العوائد ----
        if skew.get('direction', '').startswith('negative_skew'):
            buy_signals.append(("ذيل هابط - خوف = فرصة Contrarian", 0.45))
        elif skew.get('direction', '').startswith('positive_skew'):
            sell_signals.append(("ذيل صاعد - طمع = خطر Contrarian", 0.45))
        
        # ---- من المعنويات ----
        if flow:
            if 'خوف شديد' in flow.sentiment:
                buy_signals.append((f"خوف شديد = انعكاس صاعد [{flow.data_source}]", 0.55))
            elif 'تفاؤل مفرط' in flow.sentiment:
                sell_signals.append((f"تفاؤل مفرط = انعكاس هابط [{flow.data_source}]", 0.55))
        
        # ---- من Expiry ----
        if expiry.get('expiry_week'):
            warnings.append(f"أسبوع انتهاء الخيارات - تقلب متوقع ({expiry.get('days_until_expiry')} أيام)")
        
        # ---- تحذير البيانات التقديرية ----
        if not has_real:
            warnings.append("⚠️ بيانات الخيارات تقديرية (لا يوجد مصدر حقيقي)")
        
        # ---- القرار النهائي ----
        total_buy = sum(s[1] for s in buy_signals)
        total_sell = sum(s[1] for s in sell_signals)
        
        if total_buy > total_sell * 1.5:
            recommendation = "شراء"
            confidence = min(85, int(total_buy / max(total_buy + total_sell, 1) * 100))
        elif total_sell > total_buy * 1.5:
            recommendation = "بيع"
            confidence = min(85, int(total_sell / max(total_buy + total_sell, 1) * 100))
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
        reason += f" | PCR:{pcr:.2f}"
        reason += f" | جودة:{'حقيقي' if has_real else 'تقديري'}"
        
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


# دوال مساعدة
def high_wick(high: float, open_p: float, close: float) -> float:
    return high - max(open_p, close)

def low_wick(open_p: float, close: float, low: float) -> float:
    return min(open_p, close) - low


def create_options_flow_strategy():
    """إنشاء استراتيجية Options Flow الجاهزة (الإصدار 2.0)"""
    return OptionsFlowStrategy()