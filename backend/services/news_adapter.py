"""
╔══════════════════════════════════════════════════════════════╗
║        News-Responsive Adaptation – VisionTrader AI         ║
║  يراقب الأخبار الاقتصادية ويكيف الاستراتيجيات تلقائياً     ║
╚══════════════════════════════════════════════════════════════╝

المصادر:
  - ForexFactory (اقتصادية)
  - Google News RSS
  - Twitter/X (محاكاة)

مستويات التأثير:
  CRITICAL  → أزمة/حرب   → وضع الحماية الكامل
  HIGH      → خبر قوي    → تخفيض أحجام + توسيع وقف
  POSITIVE  → خبر إيجابي → زيادة وزن Momentum
  NEGATIVE  → خبر سلبي  → زيادة وزن Power (تحوط)
  NEUTRAL   → عادي       → لا تغيير
"""

import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import threading

import requests

# ───────────────────────── إعداد الـ Logger ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NewsAdapter")

# ───────────────────────── استيراد خدمات المشروع ─────────────────────
try:
    from config import settings
    TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN
    ADMIN_CHAT_ID  = settings.ADMIN_CHAT_ID
    DEEPSEEK_KEY   = settings.DEEPSEEK_API_KEY
except Exception:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_CHAT_ID  = os.getenv("ADMIN_CHAT_ID", "")
    DEEPSEEK_KEY   = os.getenv("DEEPSEEK_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════
#  Enums & Dataclasses
# ══════════════════════════════════════════════════════════════════════

class ImpactLevel(str, Enum):
    CRITICAL = "CRITICAL"   # أزمة / حرب
    HIGH     = "HIGH"       # خبر اقتصادي قوي
    POSITIVE = "POSITIVE"   # خبر إيجابي للسوق
    NEGATIVE = "NEGATIVE"   # خبر سلبي للسوق
    NEUTRAL  = "NEUTRAL"    # لا تأثير كبير


@dataclass
class NewsItem:
    title:       str
    source:      str
    published:   str
    url:         str
    impact:      ImpactLevel = ImpactLevel.NEUTRAL
    confidence:  float       = 0.0
    currencies:  List[str]   = field(default_factory=list)
    keywords:    List[str]   = field(default_factory=list)
    summary:     str         = ""


@dataclass
class AdaptationAction:
    timestamp:          str
    impact_level:       ImpactLevel
    trigger_news:       str
    actions_taken:      List[str]
    strategy_weights:   Dict[str, float]
    trading_allowed:    bool
    risk_multiplier:    float
    stop_loss_factor:   float
    size_reduction:     float


@dataclass
class SystemState:
    trading_allowed:      bool  = True
    risk_multiplier:      float = 1.0
    stop_loss_factor:     float = 1.0
    size_reduction:       float = 0.0   # 0..1 → نسبة التخفيض
    momentum_weight:      float = 1.0
    power_weight:         float = 1.0
    geometric_weight:     float = 1.0
    high_risk_frozen:     bool  = False
    protection_mode:      bool  = False
    last_adaptation:      str   = ""
    adaptation_reason:    str   = ""


# ══════════════════════════════════════════════════════════════════════
#  Keyword Dictionaries (وزن الكلمات المفتاحية)
# ══════════════════════════════════════════════════════════════════════

CRISIS_KEYWORDS = [
    "war", "crisis", "invasion", "nuclear", "collapse", "default",
    "sanctions", "emergency", "pandemic", "crash", "black swan",
    "حرب", "أزمة", "انهيار", "طوارئ", "غزو", "انفجار",
    "martial law", "terror attack", "market halt", "circuit breaker",
]

HIGH_IMPACT_KEYWORDS = [
    "interest rate", "fed decision", "nonfarm", "nfp", "gdp", "cpi",
    "inflation", "unemployment", "fomc", "ecb", "boe", "rba",
    "rate hike", "rate cut", "quantitative easing", "tapering",
    "فائدة", "تضخم", "بطالة", "ناتج محلي",
]

POSITIVE_KEYWORDS = [
    "beat expectations", "beats expectations", "beats", "exceeded expectations",
    "record high", "strong growth", "surpasses", "surpass", "outpaced",
    "bullish", "recovery", "expansion", "outperform", "rally", "better than expected",
    "نمو قوي", "تجاوز التوقعات", "ارتفاع قياسي", "تعافي",
]

NEGATIVE_KEYWORDS = [
    "miss expectations", "recession", "contraction", "contracts", "slowdown",
    "bearish", "downgrade", "sell-off", "weak", "decline", "plunge",
    "fears grow", "concerns", "worries", "slump", "tumble",
    "ركود", "تراجع", "هبوط", "انخفاض", "تباطؤ",
]

CURRENCY_MAP = {
    "USD": ["dollar", "fed", "fomc", "dxy", "us economy", "nonfarm"],
    "EUR": ["euro", "ecb", "european", "eurozone"],
    "GBP": ["pound", "boe", "britain", "uk economy"],
    "JPY": ["yen", "boj", "japan", "japanese"],
    "XAU": ["gold", "safe haven", "precious metal"],
    "BTC": ["bitcoin", "crypto", "btc", "blockchain"],
}


# ══════════════════════════════════════════════════════════════════════
#  Telegram Helper
# ══════════════════════════════════════════════════════════════════════

def _send_telegram(message: str, urgent: bool = False) -> bool:
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("Telegram غير مُهيأ – رسالة لم تُرسل")
        return False
    prefix = "🚨🚨 *URGENT* 🚨🚨\n" if urgent else ""
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    ADMIN_CHAT_ID,
        "text":       prefix + message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("✅ رسالة Telegram أُرسلت بنجاح")
            return True
        logger.warning(f"Telegram أعاد كود {r.status_code}")
    except Exception as exc:
        logger.error(f"خطأ Telegram: {exc}")
    return False


# ══════════════════════════════════════════════════════════════════════
#  News Fetchers
# ══════════════════════════════════════════════════════════════════════

class ForexFactoryFetcher:
    """يجلب أخبار الاقتصاد من ForexFactory عبر RSS"""

    RSS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

    def fetch(self) -> List[NewsItem]:
        items: List[NewsItem] = []
        try:
            r = requests.get(self.RSS_URL, timeout=15, headers={"User-Agent": "VisionTrader/2.0"})
            if r.status_code != 200:
                logger.warning(f"ForexFactory RSS → {r.status_code}")
                return items
            root = ET.fromstring(r.content)
            for event in root.findall(".//event"):
                title    = (event.findtext("title") or "").strip()
                currency = (event.findtext("country") or "").upper()
                impact   = (event.findtext("impact") or "").lower()
                date_str = event.findtext("date") or ""

                if not title:
                    continue

                impact_level = ImpactLevel.NEUTRAL
                if impact in ("high",):
                    impact_level = ImpactLevel.HIGH

                items.append(NewsItem(
                    title=title,
                    source="ForexFactory",
                    published=date_str,
                    url=self.RSS_URL,
                    impact=impact_level,
                    currencies=[currency] if currency else [],
                ))
        except Exception as exc:
            logger.error(f"ForexFactory خطأ: {exc}")
        return items


class GoogleNewsFetcher:
    """يجلب أخبار السوق من Google News RSS"""

    FEEDS = [
        "https://news.google.com/rss/search?q=forex+economy+market&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=interest+rate+inflation+gdp&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=financial+crisis+war+economy&hl=en-US&gl=US&ceid=US:en",
    ]

    def fetch(self) -> List[NewsItem]:
        items: List[NewsItem] = []
        for feed_url in self.FEEDS:
            try:
                r = requests.get(feed_url, timeout=15, headers={"User-Agent": "VisionTrader/2.0"})
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for item_el in root.findall(".//item"):
                    title   = (item_el.findtext("title") or "").strip()
                    link    = (item_el.findtext("link") or "").strip()
                    pub     = (item_el.findtext("pubDate") or "").strip()
                    if not title:
                        continue
                    items.append(NewsItem(
                        title=title,
                        source="GoogleNews",
                        published=pub,
                        url=link,
                    ))
            except Exception as exc:
                logger.error(f"GoogleNews خطأ: {exc}")
        return items


class TwitterSimFetcher:
    """محاكاة بيانات Twitter/X (بسبب قيود API مدفوع)"""

    MOCK_TWEETS = [
        {"text": "FED signals possible rate cut next quarter #USD #Forex", "likes": 4200},
        {"text": "Gold surges as geopolitical tensions rise #XAU #SafeHaven", "likes": 8900},
        {"text": "Strong US jobs data beats expectations – dollar rallying", "likes": 3100},
        {"text": "Oil prices crash on demand concerns #recession", "likes": 2800},
        {"text": "Breaking: Central bank emergency meeting called #crisis", "likes": 15000},
    ]

    def fetch(self) -> List[NewsItem]:
        items: List[NewsItem] = []
        for tw in self.MOCK_TWEETS:
            items.append(NewsItem(
                title=tw["text"],
                source="Twitter/X",
                published=datetime.utcnow().isoformat(),
                url="https://twitter.com",
                confidence=min(tw["likes"] / 20000, 1.0),
            ))
        return items


# ══════════════════════════════════════════════════════════════════════
#  Impact Analyzer
# ══════════════════════════════════════════════════════════════════════

class ImpactAnalyzer:
    """يحلل تأثير الخبر محلياً + DeepSeek عند الحاجة"""

    def __init__(self):
        self.api_key  = DEEPSEEK_KEY
        self.base_url = "https://api.deepseek.com/v1"

    # ─── تحليل محلي سريع ───────────────────────────────────────────
    def _local_analyze(self, news: NewsItem) -> Tuple[ImpactLevel, float, List[str]]:
        text    = news.title.lower()
        all_keywords: List[str] = []

        # ── 1) أعلى أولوية: أزمة/حرب ────────────────────────────────
        crisis_found = [kw for kw in CRISIS_KEYWORDS if kw.lower() in text]
        if crisis_found:
            return ImpactLevel.CRITICAL, 0.92, crisis_found

        # ── 2) فحص كل الأصناف معاً ──────────────────────────────────
        high_found = [kw for kw in HIGH_IMPACT_KEYWORDS if kw.lower() in text]
        pos_found  = [kw for kw in POSITIVE_KEYWORDS    if kw.lower() in text]
        neg_found  = [kw for kw in NEGATIVE_KEYWORDS    if kw.lower() in text]

        all_keywords = high_found + pos_found + neg_found

        has_high = len(high_found) > 0
        pos_score = len(pos_found)
        neg_score = len(neg_found)

        # إذا كان خبر HIGH + إيجابي → POSITIVE (خبر اقتصادي إيجابي قوي)
        if has_high and pos_score > 0 and pos_score >= neg_score:
            return ImpactLevel.POSITIVE, 0.75, all_keywords

        # إذا كان خبر HIGH + سلبي → NEGATIVE (خبر اقتصادي سلبي قوي)
        if has_high and neg_score > 0 and neg_score > pos_score:
            return ImpactLevel.NEGATIVE, 0.75, all_keywords

        # خبر HIGH بدون توجه واضح
        if has_high:
            return ImpactLevel.HIGH, 0.80, all_keywords

        # ── 3) خبر إيجابي/سلبي بدون HIGH ───────────────────────────
        if pos_score > neg_score and pos_score > 0:
            return ImpactLevel.POSITIVE, 0.65, pos_found
        if neg_score > pos_score and neg_score > 0:
            return ImpactLevel.NEGATIVE, 0.65, neg_found

        return ImpactLevel.NEUTRAL, 0.50, []

    # ─── تحليل عميق عبر DeepSeek ───────────────────────────────────
    def _deepseek_analyze(self, news: NewsItem) -> Optional[Dict]:
        if not self.api_key or self.api_key.startswith("your-"):
            return None

        prompt = f"""
أنت محلل مالي متخصص في أسواق الفوركس. حلل الخبر التالي:

العنوان: {news.title}
المصدر: {news.source}
التاريخ: {news.published}

حدد:
1. مستوى التأثير: CRITICAL / HIGH / POSITIVE / NEGATIVE / NEUTRAL
2. درجة الثقة (0.0–1.0)
3. العملات المتأثرة (مثال: USD, EUR, XAU)
4. ملخص التأثير في جملة واحدة

أجب بـ JSON فقط:
{{
  "impact": "HIGH",
  "confidence": 0.85,
  "currencies": ["USD", "EUR"],
  "summary": "ملخص التأثير"
}}
"""
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       "deepseek-chat",
                    "messages":    [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens":  200,
                },
                timeout=10,
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                j_start = content.find("{")
                j_end   = content.rfind("}") + 1
                if j_start != -1 and j_end > j_start:
                    return json.loads(content[j_start:j_end])
        except Exception as exc:
            logger.warning(f"DeepSeek analyze خطأ: {exc}")
        return None

    # ─── تحليل شامل ────────────────────────────────────────────────
    def analyze(self, news: NewsItem) -> NewsItem:
        # أولاً: تحليل محلي
        local_impact, local_conf, keywords = self._local_analyze(news)
        news.impact     = local_impact
        news.confidence = local_conf
        news.keywords   = keywords

        # كشف العملات
        text_lower = news.title.lower()
        for currency, triggers in CURRENCY_MAP.items():
            if any(t in text_lower for t in triggers):
                if currency not in news.currencies:
                    news.currencies.append(currency)

        # ثانياً: DeepSeek إذا كان التأثير HIGH أو أعلى
        if local_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            ds_result = self._deepseek_analyze(news)
            if ds_result:
                try:
                    news.impact     = ImpactLevel(ds_result.get("impact", local_impact))
                    news.confidence = float(ds_result.get("confidence", local_conf))
                    news.currencies = ds_result.get("currencies", news.currencies)
                    news.summary    = ds_result.get("summary", "")
                    logger.info(f"✅ DeepSeek: {news.impact} | ثقة {news.confidence:.0%}")
                except Exception:
                    pass

        return news


# ══════════════════════════════════════════════════════════════════════
#  Main NewsAdapter
# ══════════════════════════════════════════════════════════════════════

class NewsAdapter:
    """
    نظام التكيف مع الأخبار – القلب الرئيسي

    الدورة:
      monitor_news() → analyze_impact() → adapt_system()
      وعند الأزمة → emergency_shutdown()
    """

    MONITOR_INTERVAL = 300      # كل 5 دقائق
    HISTORY_FILE     = "news_adaptation_history.json"

    def __init__(self):
        self.fetchers  = [ForexFactoryFetcher(), GoogleNewsFetcher(), TwitterSimFetcher()]
        self.analyzer  = ImpactAnalyzer()
        self.state     = SystemState()
        self.history:  List[Dict] = []
        self.seen_titles: set     = set()
        self._running  = False
        self._thread:  Optional[threading.Thread] = None

        self._load_history()
        logger.info("🌐 NewsAdapter جاهز")

    # ─── تحميل/حفظ التاريخ ─────────────────────────────────────────
    def _load_history(self):
        try:
            if os.path.exists(self.HISTORY_FILE):
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
                logger.info(f"📂 تاريخ محمل: {len(self.history)} سجل")
        except Exception:
            self.history = []

    def _save_history(self):
        try:
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[-500:], f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"خطأ حفظ التاريخ: {exc}")

    # ─── جلب الأخبار من جميع المصادر ──────────────────────────────
    def _fetch_all_news(self) -> List[NewsItem]:
        all_news: List[NewsItem] = []
        for fetcher in self.fetchers:
            try:
                batch = fetcher.fetch()
                logger.info(f"📰 {fetcher.__class__.__name__}: {len(batch)} خبر")
                all_news.extend(batch)
            except Exception as exc:
                logger.error(f"{fetcher.__class__.__name__} فشل: {exc}")

        # إزالة المكررات
        unique = []
        for item in all_news:
            if item.title not in self.seen_titles:
                self.seen_titles.add(item.title)
                unique.append(item)

        # الاحتفاظ بـ 500 عنوان فقط في الذاكرة
        if len(self.seen_titles) > 500:
            self.seen_titles = set(list(self.seen_titles)[-500:])

        return unique

    # ─── تحليل تأثير الخبر ─────────────────────────────────────────
    def analyze_impact(self, news: NewsItem) -> NewsItem:
        """يحلل تأثير خبر واحد ويرجعه مكتملاً"""
        return self.analyzer.analyze(news)

    # ─── تكيف النظام حسب مستوى التأثير ────────────────────────────
    def adapt_system(self, impact_level: ImpactLevel, trigger_news: str = "") -> AdaptationAction:
        """يعدّل إعدادات النظام بناءً على مستوى تأثير الخبر"""

        actions: List[str] = []

        if impact_level == ImpactLevel.CRITICAL:
            # ═══ أزمة / حرب → وضع الحماية الكامل ═══
            self.state.trading_allowed   = False
            self.state.protection_mode   = True
            self.state.risk_multiplier   = 0.0
            self.state.size_reduction    = 1.0   # إيقاف كامل
            self.state.stop_loss_factor  = 2.0
            self.state.high_risk_frozen  = True
            self.state.momentum_weight   = 0.0
            self.state.power_weight      = 1.5   # تحوط أقصى
            self.state.geometric_weight  = 0.3
            actions = [
                "🛑 إيقاف التداول التلقائي",
                "🔴 تفعيل وضع الحماية الكامل",
                "❄️  تجميد جميع الاستراتيجيات عالية المخاطر",
                "📊 زيادة وقف الخسارة ضعفين",
                "📩 إرسال تنبيه طارئ عاجل",
            ]
            logger.critical(f"🚨 CRITICAL – {trigger_news}")
            self.emergency_shutdown(f"أزمة/خبر خطير: {trigger_news}")

        elif impact_level == ImpactLevel.HIGH:
            # ═══ خبر اقتصادي قوي ═══
            self.state.trading_allowed   = True
            self.state.protection_mode   = False
            self.state.risk_multiplier   = 0.5
            self.state.size_reduction    = 0.5   # تخفيض 50%
            self.state.stop_loss_factor  = 1.5
            self.state.high_risk_frozen  = True
            self.state.momentum_weight   = 0.7
            self.state.power_weight      = 1.3
            self.state.geometric_weight  = 0.8
            actions = [
                "⚠️ تخفيض أحجام الصفقات 50%",
                "📏 توسيع الوقف 1.5×",
                "❄️  تجميد الاستراتيجيات عالية المخاطر",
                "⚖️ تقليل وزن Momentum",
            ]
            logger.warning(f"⚠️ HIGH impact – {trigger_news}")

        elif impact_level == ImpactLevel.POSITIVE:
            # ═══ خبر إيجابي ═══
            self.state.trading_allowed   = True
            self.state.protection_mode   = False
            self.state.risk_multiplier   = 1.1
            self.state.size_reduction    = 0.0
            self.state.stop_loss_factor  = 1.0
            self.state.high_risk_frozen  = False
            self.state.momentum_weight   = 1.4   # زيادة Momentum
            self.state.power_weight      = 0.8
            self.state.geometric_weight  = 1.1
            actions = [
                "📈 زيادة وزن Momentum +40%",
                "✅ السماح بأحجام صفقات طبيعية",
                "🚀 تفعيل استراتيجيات الاتجاه",
            ]
            logger.info(f"✅ POSITIVE – {trigger_news}")

        elif impact_level == ImpactLevel.NEGATIVE:
            # ═══ خبر سلبي ═══
            self.state.trading_allowed   = True
            self.state.protection_mode   = False
            self.state.risk_multiplier   = 0.7
            self.state.size_reduction    = 0.3   # تخفيض 30%
            self.state.stop_loss_factor  = 1.3
            self.state.high_risk_frozen  = False
            self.state.momentum_weight   = 0.6
            self.state.power_weight      = 1.5   # تعزيز Power/تحوط
            self.state.geometric_weight  = 0.9
            actions = [
                "🛡️ زيادة وزن Power (تحوط) +50%",
                "📉 تقليل Momentum -40%",
                "📏 تخفيض أحجام الصفقات 30%",
                "🔒 توسيع الوقف 1.3×",
            ]
            logger.info(f"📉 NEGATIVE – {trigger_news}")

        else:
            # ═══ NEUTRAL ═══
            self.state.trading_allowed   = True
            self.state.protection_mode   = False
            self.state.risk_multiplier   = 1.0
            self.state.size_reduction    = 0.0
            self.state.stop_loss_factor  = 1.0
            self.state.high_risk_frozen  = False
            self.state.momentum_weight   = 1.0
            self.state.power_weight      = 1.0
            self.state.geometric_weight  = 1.0
            actions = ["ℹ️ لا تغيير – الخبر محايد"]
            logger.info("ℹ️ NEUTRAL – لا تعديل على النظام")

        self.state.last_adaptation   = datetime.utcnow().isoformat()
        self.state.adaptation_reason = trigger_news

        action = AdaptationAction(
            timestamp       = self.state.last_adaptation,
            impact_level    = impact_level,
            trigger_news    = trigger_news,
            actions_taken   = actions,
            strategy_weights={
                "momentum": self.state.momentum_weight,
                "power":    self.state.power_weight,
                "geometric":self.state.geometric_weight,
            },
            trading_allowed = self.state.trading_allowed,
            risk_multiplier = self.state.risk_multiplier,
            stop_loss_factor= self.state.stop_loss_factor,
            size_reduction  = self.state.size_reduction,
        )

        # حفظ في التاريخ
        self.history.append(asdict(action))
        self._save_history()

        return action

    # ─── الإيقاف الطارئ ────────────────────────────────────────────
    def emergency_shutdown(self, reason: str):
        """إيقاف طارئ كامل مع إشعار Telegram عاجل"""
        logger.critical(f"🚨 EMERGENCY SHUTDOWN – {reason}")

        msg = (
            "🚨🚨 *EMERGENCY SHUTDOWN – VisionTrader AI* 🚨🚨\n\n"
            f"*السبب:* {reason}\n\n"
            "⛔ تم إيقاف التداول التلقائي فوراً\n"
            "🔴 وضع الحماية مُفعَّل\n"
            "❄️ جميع الاستراتيجيات مجمدة\n\n"
            "📌 يرجى مراجعة الوضع والتأكيد يدوياً قبل العودة للتداول.\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        _send_telegram(msg, urgent=True)

    # ─── حلقة المراقبة الرئيسية ────────────────────────────────────
    def monitor_news(self):
        """
        يراقب الأخبار بشكل مستمر – يعمل في خيط منفصل.
        استدعِ start() لتشغيله أو stop() لإيقافه.
        """
        logger.info(f"🔄 بدأت دورة مراقبة الأخبار (كل {self.MONITOR_INTERVAL}s)")

        while self._running:
            try:
                all_news = self._fetch_all_news()
                logger.info(f"📡 {len(all_news)} خبر جديد للتحليل")

                # نحلل كل خبر ونأخذ أعلى تأثير
                worst_impact = ImpactLevel.NEUTRAL
                worst_news   = ""
                worst_conf   = 0.0

                for item in all_news:
                    analyzed = self.analyze_impact(item)
                    level_rank = {
                        ImpactLevel.NEUTRAL:  0,
                        ImpactLevel.POSITIVE: 1,
                        ImpactLevel.NEGATIVE: 2,
                        ImpactLevel.HIGH:     3,
                        ImpactLevel.CRITICAL: 4,
                    }
                    if level_rank[analyzed.impact] > level_rank[worst_impact]:
                        if analyzed.confidence >= 0.55:   # حد الثقة
                            worst_impact = analyzed.impact
                            worst_news   = analyzed.title
                            worst_conf   = analyzed.confidence

                # تطبيق التكيف إذا كان التأثير أعلى من NEUTRAL
                if worst_impact != ImpactLevel.NEUTRAL:
                    logger.info(f"⚡ تكيف النظام ← {worst_impact} | {worst_news[:60]}")
                    action = self.adapt_system(worst_impact, worst_news)
                    self._log_action(action)
                else:
                    logger.info("✅ لا توجد أخبار ذات تأثير – النظام يعمل بوضعه الطبيعي")

            except Exception as exc:
                logger.error(f"خطأ في حلقة monitor_news: {exc}")

            # انتظر حتى الدورة القادمة
            for _ in range(self.MONITOR_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("⏹️ انتهت حلقة مراقبة الأخبار")

    def _log_action(self, action: AdaptationAction):
        logger.info("═" * 55)
        logger.info(f"📊 تكيف النظام – {action.impact_level}")
        logger.info(f"📰 الخبر: {action.trigger_news[:70]}")
        for a in action.actions_taken:
            logger.info(f"   {a}")
        logger.info(f"⚖️  أوزان: Momentum={action.strategy_weights['momentum']:.1f} | "
                    f"Power={action.strategy_weights['power']:.1f} | "
                    f"Geometric={action.strategy_weights['geometric']:.1f}")
        logger.info(f"📉 تخفيض الأحجام: {action.size_reduction*100:.0f}%")
        logger.info(f"📏 معامل الوقف: ×{action.stop_loss_factor}")
        logger.info(f"🟢 التداول: {'مسموح' if action.trading_allowed else 'موقوف'}")
        logger.info("═" * 55)

    # ─── تشغيل/إيقاف في خلفية ──────────────────────────────────────
    def start(self):
        if self._running:
            logger.warning("NewsAdapter يعمل بالفعل")
            return
        self._running = True
        self._thread  = threading.Thread(target=self.monitor_news, daemon=True)
        self._thread.start()
        logger.info("▶️ NewsAdapter شغّال في الخلفية")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("⏹️ NewsAdapter متوقف")

    # ─── حالة النظام الحالية ───────────────────────────────────────
    def get_state(self) -> Dict:
        return {
            "trading_allowed":   self.state.trading_allowed,
            "protection_mode":   self.state.protection_mode,
            "risk_multiplier":   self.state.risk_multiplier,
            "size_reduction_pct":f"{self.state.size_reduction*100:.0f}%",
            "stop_loss_factor":  self.state.stop_loss_factor,
            "strategy_weights": {
                "momentum":  self.state.momentum_weight,
                "power":     self.state.power_weight,
                "geometric": self.state.geometric_weight,
            },
            "last_adaptation":   self.state.last_adaptation,
            "adaptation_reason": self.state.adaptation_reason,
            "history_count":     len(self.history),
        }


# ══════════════════════════════════════════════════════════════════════
#  Singleton (للاستيراد في main.py أو routers)
# ══════════════════════════════════════════════════════════════════════
news_adapter = NewsAdapter()


# ══════════════════════════════════════════════════════════════════════
#  اختبار مباشر
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Fix Windows Unicode console encoding
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    print("\n" + "=" * 60)
    print("  [NEWS ADAPTER] News-Responsive Adaptation - Test")
    print("=" * 60 + "\n")

    adapter = NewsAdapter()

    # Test 1: Analyze news at different impact levels
    print("[TEST 1] Analyzing news at multiple impact levels")
    print("-" * 50)

    test_cases = [
        ("War breaks out: Global markets in crisis – emergency meeting called",
         ImpactLevel.CRITICAL),
        ("FED raises interest rate by 75bps – markets react sharply",
         ImpactLevel.HIGH),
        ("US GDP beats expectations – strong economic growth reported",
         ImpactLevel.POSITIVE),
        ("Recession fears grow as GDP contracts for second quarter",
         ImpactLevel.NEGATIVE),
        ("Bank announces minor branch updates across Europe",
         ImpactLevel.NEUTRAL),
    ]

    all_passed = True
    for title, expected in test_cases:
        item     = NewsItem(title=title, source="Test", published="now", url="")
        analyzed = adapter.analyze_impact(item)
        passed   = analyzed.impact == expected
        all_passed = all_passed and passed
        status   = "PASS" if passed else "FAIL"
        print(f"[{status}] {analyzed.impact:10s} (conf={analyzed.confidence:.0%}) | {title[:55]}")

    print()

    # Test 2: adapt_system for each impact level
    print("[TEST 2] System Adaptation per impact level")
    print("-" * 50)

    for level in [ImpactLevel.HIGH, ImpactLevel.POSITIVE, ImpactLevel.NEGATIVE, ImpactLevel.NEUTRAL]:
        action = adapter.adapt_system(level, f"Test news ({level})")
        print(f"\n[{level}]")
        print(f"   Trading: {'ALLOWED' if action.trading_allowed else 'STOPPED'}")
        print(f"   Size reduction: {action.size_reduction*100:.0f}%")
        print(f"   StopLoss factor: x{action.stop_loss_factor}")
        print(f"   Momentum={action.strategy_weights['momentum']:.1f} | "
              f"Power={action.strategy_weights['power']:.1f} | "
              f"Geometric={action.strategy_weights['geometric']:.1f}")
        print(f"   Actions: {len(action.actions_taken)} actions taken")

    print()

    # Test 3: System state
    print("[TEST 3] Current System State")
    print("-" * 50)
    state = adapter.get_state()
    for k, v in state.items():
        print(f"   {k}: {v}")

    print()

    # Test 4: Fetch live news from Google News RSS
    print("[TEST 4] Fetching news from Google News RSS")
    print("-" * 50)
    fetcher = GoogleNewsFetcher()
    try:
        news_list = fetcher.fetch()
        if news_list:
            print(f"   OK: Fetched {len(news_list)} news items")
            for n in news_list[:3]:
                analyzed = adapter.analyze_impact(n)
                print(f"   [{analyzed.impact:10s}] {analyzed.title[:65]}")
        else:
            print("   INFO: No news fetched (check network)")
    except Exception as exc:
        print(f"   WARNING: Failed to fetch: {exc}")

    print()

    # Summary
    print("=" * 60)
    result = "ALL TESTS PASSED" if all_passed else "SOME TESTS NEED REVIEW"
    print(f"  [{result}]")
    print(f"  History saved: {adapter.HISTORY_FILE}")
    print("=" * 60 + "\n")

    sys.exit(0 if all_passed else 1)
