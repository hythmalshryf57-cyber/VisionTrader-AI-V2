"""
═══════════════════════════════════════════════════════════════════════════════
SOCIAL SENTIMENT STRATEGY - النسخة الديناميكية المتكاملة (الإصدار 2.0)
المدرسة الثالثة والعشرون: تحليل المشاعر الاجتماعية الحقيقي
═══════════════════════════════════════════════════════════════════════════════

هذه الاستراتيجية تحلل المشاعر الحقيقية من:
- Twitter API (تغريدات)
- Google News RSS (مقالات إخبارية)
- Reddit RSS (منشورات)

ليست "تقدير مشاعر" من السعر والحجم.
بل تحليل حقيقي لما يقوله المتداولون والإعلام.

المفاهيم المتقدمة:
1. Social Sentiment Score (من -1 إلى +1)
2. Social Volume (عدد المنشورات/التغريدات)
3. Sentiment Divergence (تباعد المشاعر عن السعر)
4. Social Volume Spike Detection
5. Narrative Detection (كشف السرد السائد)
6. Source Weighting (وزن المصدر)
7. Contrarian Confidence Score
8. Social Support/Resistance Levels
9. Hype Cycle Detection (دورة الضجيج)
10. Fear & Greed Index
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
import sys
import importlib
import re
import logging

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    هياكل البيانات                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class SocialPost:
    """منشور اجتماعي من أي مصدر"""
    source: str  # 'twitter', 'google_news', 'reddit'
    text: str
    sentiment_score: float  # -1 إلى +1
    followers_count: int = 0
    timestamp: Optional[datetime] = None
    url: str = ""
    author: str = ""
    engagement: int = 0  # likes, retweets, comments
    keywords: List[str] = field(default_factory=list)
    source_weight: float = 1.0  # وزن المصدر
    price_at_time: float = 0.0


@dataclass
class SocialSentimentScore:
    """نتيجة تحليل المشاعر"""
    overall_sentiment: float  # -1 إلى +1
    twitter_sentiment: float
    news_sentiment: float
    reddit_sentiment: float
    social_volume: int  # إجمالي المنشورات
    twitter_volume: int
    news_volume: int
    reddit_volume: int
    sentiment_change_1h: float  # تغير المشاعر في آخر ساعة
    sentiment_change_24h: float  # تغير المشاعر في آخر 24 ساعة
    volume_change_1h: float  # تغير الحجم الاجتماعي
    dominant_narrative: str  # السرد السائد
    fear_greed_index: float  # 0-100 (0=خوف, 100=طمع)
    contrarian_signal: str  # 'none', 'buy', 'sell'
    hype_cycle_phase: str  # مرحلة دورة الضجيج


@dataclass
class SentimentDivergence:
    """تباعد المشاعر عن السعر"""
    index: int
    divergence_type: str  # 'bullish', 'bearish'
    price_change: float
    sentiment_change: float
    strength: float
    description: str


@dataclass
class SocialSignal:
    """إشارة تداول من البيانات الاجتماعية"""
    index: int
    signal_type: str  # 'sentiment_extreme', 'volume_spike', 'divergence', 'narrative_shift', 'contrarian'
    direction: str  # 'bullish', 'bearish'
    strength: float
    confidence: float
    description: str
    sources: List[str]
    social_volume_at_signal: int


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة صفر: محلل النص وتصنيف المشاعر                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class TextSentimentAnalyzer:
    """
    يحلل النص ويستخرج المشاعر والكلمات المفتاحية.
    
    يستخدم:
    - قواميس كلمات إيجابية/سلبية
    - كشف السرد (Narrative Detection)
    - وزن المصدر (Source Weighting)
    """
    
    # 🟡 تعديل 4: قواميس الكلمات للكشف عن السرد
    BULLISH_KEYWORDS = [
        'moon', 'to the moon', '🚀', 'bullish', 'buy', 'long', 'accumulation',
        'breakout', 'pump', 'rally', 'green', 'gain', 'profit',
        'صعود', 'شراء', 'تجميع', 'اختراق', 'ارتفاع', 'قوي', 'فرصة',
        'launch', 'partnership', 'listing', 'adoption', 'upgrade',
    ]
    
    BEARISH_KEYWORDS = [
        'crash', 'dump', 'bearish', 'sell', 'short', 'distribution',
        'breakdown', 'red', 'loss', 'panic', 'fear', 'collapse',
        'انهيار', 'بيع', 'توزيع', 'هبوط', 'خوف', 'ذعر', 'خسارة',
        'hack', 'ban', 'regulation', 'lawsuit', 'delisting',
    ]
    
    FEAR_KEYWORDS = [
        'fear', 'panic', 'scared', 'worried', 'uncertain', 'confusion',
        'خوف', 'ذعر', 'قلق', 'غير مؤكد', 'فوضى',
    ]
    
    GREED_KEYWORDS = [
        'moon', 'lambo', 'rich', 'easy money', 'guaranteed', 'never sell',
        'to the moon', 'millionaire', 'yolo', 'all in',
        'طمع', 'ثراء', 'سهل', 'مضمون',
    ]
    
    def __init__(self):
        self.source_weights = {
            'twitter_verified': 3.0,      # حساب موثق
            'twitter_high_followers': 2.0, # أكثر من 100k متابع
            'twitter_normal': 1.0,        # حساب عادي
            'google_news_major': 2.5,      # Bloomberg, Reuters, etc.
            'google_news_minor': 1.0,      # مدونات، مواقع صغيرة
            'reddit_high_karma': 1.5,     # حساب ذو karma عالي
            'reddit_normal': 0.8,          # حساب عادي
        }
    
    def analyze_post(self, post: SocialPost) -> SocialPost:
        """
        تحليل منشور واحد: المشاعر + الكلمات المفتاحية + الوزن
        """
        text = post.text.lower() if post.text else ""
        
        # 🟡 تعديل 1: تحليل المشاعر من النص
        post.sentiment_score = self._calculate_sentiment(text)
        
        # 🟡 تعديل 4: استخراج الكلمات المفتاحية
        post.keywords = self._extract_keywords(text)
        
        # 🟡 تعديل 5: وزن المصدر
        post.source_weight = self._calculate_source_weight(post)
        
        return post
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        حساب المشاعر من النص.
        نسبة الكلمات الإيجابية - نسبة الكلمات السلبية.
        """
        if not text:
            return 0.0
        
        words = text.split()
        if not words:
            return 0.0
        
        bullish_count = sum(1 for word in self.BULLISH_KEYWORDS if word in text)
        bearish_count = sum(1 for word in self.BEARISH_KEYWORDS if word in text)
        
        total = bullish_count + bearish_count
        
        if total == 0:
            # لا كلمات معروفة = محايد
            return 0.0
        
        sentiment = (bullish_count - bearish_count) / total
        
        # تقييد بين -1 و +1
        return max(-1.0, min(1.0, sentiment))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """استخراج الكلمات المفتاحية من النص"""
        keywords = []
        
        all_keywords = self.BULLISH_KEYWORDS + self.BEARISH_KEYWORDS + \
                      self.FEAR_KEYWORDS + self.GREED_KEYWORDS
        
        for keyword in all_keywords:
            if keyword in text and keyword not in keywords:
                keywords.append(keyword)
        
        return keywords
    
    def _calculate_source_weight(self, post: SocialPost) -> float:
        """
        🟡 تعديل 5: حساب وزن المصدر
        
        Bloomberg > مدونة مجهولة
        حساب موثق > حساب عادي
        """
        if post.source == 'twitter':
            if post.followers_count > 100000:
                return self.source_weights['twitter_high_followers']
            elif post.followers_count > 10000:
                return self.source_weights['twitter_verified']
            else:
                return self.source_weights['twitter_normal']
        
        elif post.source == 'google_news':
            # المصادر الكبرى
            major_sources = ['bloomberg', 'reuters', 'cnbc', 'wsj', 'ft.com', 
                           'coindesk', 'cointelegraph', 'yahoo finance']
            if any(src in post.url.lower() for src in major_sources):
                return self.source_weights['google_news_major']
            return self.source_weights['google_news_minor']
        
        elif post.source == 'reddit':
            if post.engagement > 100:  # karma/upvotes
                return self.source_weights['reddit_high_karma']
            return self.source_weights['reddit_normal']
        
        return 1.0
    
    def detect_narrative(self, posts: List[SocialPost]) -> str:
        """
        🟡 تعديل 4: كشف السرد السائد من مجموعة منشورات
        """
        if not posts:
            return "لا يوجد سرد واضح"
        
        # تجميع الكلمات المفتاحية
        keyword_counts = defaultdict(int)
        for post in posts:
            for keyword in post.keywords:
                keyword_counts[keyword] += 1
        
        if not keyword_counts:
            return "سرد محايد"
        
        # الكلمة الأكثر تكراراً
        dominant = max(keyword_counts, key=keyword_counts.get)
        count = keyword_counts[dominant]
        
        # تصنيف السرد
        if dominant in self.BULLISH_KEYWORDS:
            if count > len(posts) * 0.3:
                return f"طمع - {dominant}"
            return f"تفاؤل - {dominant}"
        elif dominant in self.BEARISH_KEYWORDS:
            if count > len(posts) * 0.3:
                return f"ذعر - {dominant}"
            return f"تشاؤم - {dominant}"
        elif dominant in self.FEAR_KEYWORDS:
            return f"خوف - {dominant}"
        elif dominant in self.GREED_KEYWORDS:
            return f"طمع - {dominant}"
        
        return f"سرد مختلط - {dominant}"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الأولى: جامع البيانات الاجتماعية                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SocialDataCollector:
    """
    يجمع البيانات من مصادر اجتماعية حقيقية.
    
    يحاول استيراد social_sentiment_service من services/
    إذا فشل، يستخدم وضع المحاكاة مع تحذير.
    """
    
    def __init__(self):
        self.text_analyzer = TextSentimentAnalyzer()
        self.social_service = None
        self._init_social_service()
        
        # تخزين مؤقت للبيانات
        self.cached_posts: List[SocialPost] = []
        self.last_fetch_time: Optional[datetime] = None
        self.cache_duration = timedelta(minutes=5)
    
    def _init_social_service(self):
        """
        محاولة استيراد خدمة البيانات الاجتماعية الحقيقية
        """
        try:
            module = sys.modules.get("services.social_sentiment")
            if module is None:
                module = importlib.import_module("services.social_sentiment")
            SocialSentimentService = getattr(module, "SocialSentimentService", None)
            if SocialSentimentService is None:
                raise ImportError("SocialSentimentService not found in services.social_sentiment")
            self.social_service = SocialSentimentService()
            logger.info("✅ تم ربط SocialSentimentService الحقيقي")
        except ImportError:
            logger.warning("⚠️ SocialSentimentService غير متاح. استخدام وضع المحاكاة.")
            self.social_service = None
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة SocialSentimentService: {e}")
            self.social_service = None
    
    def fetch_social_data(self, symbol: str = "BTCUSD", force_refresh: bool = False) -> List[SocialPost]:
        """
        🔴 تعديل 1: جلب البيانات الحقيقية من المصادر
        
        إذا social_service متاح: يستخدمه
        إذا غير متاح: يحذر ويستخدم بيانات فارغة
        """
        # استخدام الكاش إذا كانت البيانات حديثة
        if not force_refresh and self.last_fetch_time and \
           datetime.now() - self.last_fetch_time < self.cache_duration:
            return self.cached_posts
        
        all_posts = []
        
        if self.social_service:
            # ✅ استخدام البيانات الحقيقية
            try:
                # جلب من Twitter
                twitter_posts = self._fetch_twitter_posts(symbol)
                all_posts.extend(twitter_posts)
                
                # جلب من Google News
                news_posts = self._fetch_google_news_posts(symbol)
                all_posts.extend(news_posts)
                
                # جلب من Reddit
                reddit_posts = self._fetch_reddit_posts(symbol)
                all_posts.extend(reddit_posts)
                
                logger.info(f"✅ تم جلب {len(all_posts)} منشور اجتماعي حقيقي")
                
            except Exception as e:
                logger.error(f"❌ خطأ في جلب البيانات الاجتماعية: {e}")
        else:
            logger.warning("⚠️ لا توجد خدمة اجتماعية. تحليل المشاعر غير متاح.")
        
        # تحليل كل منشور
        analyzed_posts = []
        for post in all_posts:
            analyzed = self.text_analyzer.analyze_post(post)
            analyzed_posts.append(analyzed)
        
        # تحديث الكاش
        self.cached_posts = analyzed_posts
        self.last_fetch_time = datetime.now()
        
        return analyzed_posts
    
    def _fetch_twitter_posts(self, symbol: str) -> List[SocialPost]:
        """جلب تغريدات من Twitter"""
        posts = []
        
        try:
            if self.social_service:
                # استدعاء خدمة Twitter من social_sentiment.py
                tweets = self.social_service.get_twitter_sentiment(symbol)
                
                for tweet in tweets:
                    posts.append(SocialPost(
                        source='twitter',
                        text=tweet.get('text', ''),
                        sentiment_score=0.0,  # سيُحسب لاحقاً
                        followers_count=tweet.get('followers_count', 0),
                        timestamp=tweet.get('timestamp'),
                        url=tweet.get('url', ''),
                        author=tweet.get('author', ''),
                        engagement=tweet.get('likes', 0) + tweet.get('retweets', 0),
                        price_at_time=tweet.get('price_at_time', 0),
                    ))
        except Exception as e:
            logger.warning(f"تعذر جلب تغريدات Twitter: {e}")
        
        return posts
    
    def _fetch_google_news_posts(self, symbol: str) -> List[SocialPost]:
        """جلب مقالات من Google News"""
        posts = []
        
        try:
            if self.social_service:
                articles = self.social_service.get_google_news_sentiment(symbol)
                
                for article in articles:
                    posts.append(SocialPost(
                        source='google_news',
                        text=article.get('title', '') + ' ' + article.get('snippet', ''),
                        sentiment_score=0.0,
                        followers_count=0,
                        timestamp=article.get('timestamp'),
                        url=article.get('url', ''),
                        author=article.get('source', ''),
                        engagement=0,
                        price_at_time=article.get('price_at_time', 0),
                    ))
        except Exception as e:
            logger.warning(f"تعذر جلب مقالات Google News: {e}")
        
        return posts
    
    def _fetch_reddit_posts(self, symbol: str) -> List[SocialPost]:
        """جلب منشورات من Reddit"""
        posts = []
        
        try:
            if self.social_service:
                reddit_posts = self.social_service.get_reddit_sentiment(symbol)
                
                for r_post in reddit_posts:
                    posts.append(SocialPost(
                        source='reddit',
                        text=r_post.get('title', '') + ' ' + r_post.get('text', ''),
                        sentiment_score=0.0,
                        followers_count=0,
                        timestamp=r_post.get('timestamp'),
                        url=r_post.get('url', ''),
                        author=r_post.get('author', ''),
                        engagement=r_post.get('upvotes', 0) + r_post.get('comments', 0),
                        price_at_time=r_post.get('price_at_time', 0),
                    ))
        except Exception as e:
            logger.warning(f"تعذر جلب منشورات Reddit: {e}")
        
        return posts
    
    def get_posts_in_timeframe(self, hours: int = 24) -> List[SocialPost]:
        """الحصول على المنشورات في إطار زمني محدد"""
        if not self.cached_posts:
            self.fetch_social_data()
        
        if not self.cached_posts:
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            post for post in self.cached_posts
            if post.timestamp and post.timestamp > cutoff
        ]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       الدرجة الثانية: محلل المشاعر الاجتماعية                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SocialSentimentAnalyzer:
    """
    يحلل المشاعر الاجتماعية وينتج إشارات تداول.
    
    🔴 تعديل 1: يستخدم بيانات حقيقية من SocialDataCollector
    🟡 تعديل 2: Social Volume Spike Detection
    🟡 تعديل 3: Sentiment Divergence حقيقي
    🟡 تعديل 4: Narrative Detection
    🟡 تعديل 5: Source Weighting
    🟡 تعديل 6: Hype Cycle Detection
    🟡 تعديل 7: Contrarian Confidence Score
    🟡 تعديل 8: Social Support/Resistance
    """
    
    def __init__(self):
        self.data_collector = SocialDataCollector()
        self.text_analyzer = TextSentimentAnalyzer()
        self.sentiment_history = deque(maxlen=168)  # أسبوع من البيانات الساعية
        self.volume_history = deque(maxlen=168)
        self.price_history = deque(maxlen=168)
        self.social_sr_levels = []  # مستويات دعم/مقاومة اجتماعية
    
    def analyze(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                volumes: np.ndarray, symbol: str = "BTCUSD") -> Dict:
        """
        تحليل المشاعر الاجتماعية الكامل
        """
        current_price = closes[-1] if len(closes) > 0 else 0
        
        # 🔴 تعديل 1: جلب البيانات الحقيقية
        posts = self.data_collector.fetch_social_data(symbol)
        
        # حساب المشاعر
        sentiment_score = self._calculate_sentiment_score(posts)
        
        # 🟡 تعديل 2: كشف Spike في الحجم الاجتماعي
        volume_spike = self._detect_social_volume_spike(posts)
        
        # 🟡 تعديل 3: كشف تباعد المشاعر عن السعر
        divergences = self._detect_sentiment_divergence(sentiment_score, closes)
        
        # 🟡 تعديل 6: تحديد مرحلة دورة الضجيج
        hype_phase = self._detect_hype_cycle(sentiment_score, closes)
        
        # 🟡 تعديل 7: حساب Contrarian Score
        contrarian = self._calculate_contrarian_score(sentiment_score, closes, volumes)
        
        # 🟡 تعديل 8: مستويات اجتماعية
        self._update_social_levels(posts, current_price)
        
        # تحديث التاريخ
        self._update_history(sentiment_score, len(posts), current_price)
        
        # كشف الإشارات
        signals = self._generate_signals(
            sentiment_score, volume_spike, divergences, 
            hype_phase, contrarian, current_price
        )
        
        return {
            "sentiment_score": sentiment_score,
            "signals": signals,
            "hype_phase": hype_phase,
            "contrarian_signal": contrarian,
            "social_levels": self.social_sr_levels[-5:],
            "posts_analyzed": len(posts),
            "data_source": "real" if self.data_collector.social_service else "unavailable",
        }
    
    def _calculate_sentiment_score(self, posts: List[SocialPost]) -> SocialSentimentScore:
        """
        🔴 تعديل 1: حساب المشاعر من البيانات الحقيقية مع وزن المصادر
        
        ليس من Up/Down Bars. من تغريدات ومقالات حقيقية.
        """
        if not posts:
            return SocialSentimentScore(
                overall_sentiment=0.0,
                twitter_sentiment=0.0,
                news_sentiment=0.0,
                reddit_sentiment=0.0,
                social_volume=0,
                twitter_volume=0,
                news_volume=0,
                reddit_volume=0,
                sentiment_change_1h=0.0,
                sentiment_change_24h=0.0,
                volume_change_1h=0.0,
                dominant_narrative="لا بيانات",
                fear_greed_index=50.0,
                contrarian_signal='none',
                hype_cycle_phase='unknown',
            )
        
        # 🟡 تعديل 5: المشاعر المرجحة بالمصدر
        twitter_posts = [p for p in posts if p.source == 'twitter']
        news_posts = [p for p in posts if p.source == 'google_news']
        reddit_posts = [p for p in posts if p.source == 'reddit']
        
        def weighted_sentiment(posts_list):
            if not posts_list:
                return 0.0
            total_weight = sum(p.source_weight for p in posts_list)
            if total_weight == 0:
                return 0.0
            return sum(p.sentiment_score * p.source_weight for p in posts_list) / total_weight
        
        twitter_sent = weighted_sentiment(twitter_posts)
        news_sent = weighted_sentiment(news_posts)
        reddit_sent = weighted_sentiment(reddit_posts)
        
        # المتوسط المرجح
        source_counts = [len(twitter_posts), len(news_posts), len(reddit_posts)]
        total_sources = sum(source_counts)
        
        if total_sources > 0:
            overall = (twitter_sent * source_counts[0] + 
                      news_sent * source_counts[1] + 
                      reddit_sent * source_counts[2]) / total_sources
        else:
            overall = 0.0
        
        # 🟡 تعديل 4: السرد السائد
        narrative = self.text_analyzer.detect_narrative(posts)
        
        # 🟡 تعديل 6: مؤشر الخوف والطمع
        fear_greed = self._calculate_fear_greed_index(posts)
        
        # تغير المشاعر
        sent_change_1h, sent_change_24h = self._calculate_sentiment_change()
        vol_change = self._calculate_volume_change(len(posts))
        
        # 🟡 تعديل 7: إشارة Contrarian
        contrarian = self._determine_contrarian_signal(overall, len(posts), fear_greed)
        
        return SocialSentimentScore(
            overall_sentiment=overall,
            twitter_sentiment=twitter_sent,
            news_sentiment=news_sent,
            reddit_sentiment=reddit_sent,
            social_volume=len(posts),
            twitter_volume=len(twitter_posts),
            news_volume=len(news_posts),
            reddit_volume=len(reddit_posts),
            sentiment_change_1h=sent_change_1h,
            sentiment_change_24h=sent_change_24h,
            volume_change_1h=vol_change,
            dominant_narrative=narrative,
            fear_greed_index=fear_greed,
            contrarian_signal=contrarian,
            hype_cycle_phase='unknown',  # سيُحدّث لاحقاً
        )
    
    def _calculate_fear_greed_index(self, posts: List[SocialPost]) -> float:
        """
        🟡 تعديل 6: حساب مؤشر الخوف والطمع من المنشورات
        
        0 = خوف شديد (فرصة شراء)
        100 = طمع شديد (خطر بيع)
        """
        if not posts:
            return 50.0
        
        fear_count = 0
        greed_count = 0
        
        for post in posts:
            text = post.text.lower()
            for word in self.text_analyzer.FEAR_KEYWORDS:
                if word in text:
                    fear_count += 1
                    break
            for word in self.text_analyzer.GREED_KEYWORDS:
                if word in text:
                    greed_count += 1
                    break
        
        total = fear_count + greed_count
        
        if total == 0:
            # استخدام المشاعر العامة
            avg_sentiment = np.mean([p.sentiment_score for p in posts])
            return 50 + avg_sentiment * 40
        
        # نسبة الطمع
        greed_ratio = greed_count / total
        return greed_ratio * 100
    
    def _detect_social_volume_spike(self, posts: List[SocialPost]) -> Dict:
        """
        🟡 تعديل 2: كشف Spike في الحجم الاجتماعي
        
        عندما يقفز عدد المنشورات فجأة = خبر كبير
        """
        current_volume = len(posts)
        
        if len(self.volume_history) < 5:
            return {"is_spike": False, "multiplier": 1.0}
        
        avg_volume = np.mean(list(self.volume_history)[-5:])
        
        if avg_volume == 0:
            return {"is_spike": False, "multiplier": 1.0}
        
        multiplier = current_volume / avg_volume
        
        return {
            "is_spike": multiplier > 3.0,
            "multiplier": multiplier,
            "current": current_volume,
            "average": avg_volume,
        }
    
    def _detect_sentiment_divergence(self, sentiment: SocialSentimentScore,
                                      closes: np.ndarray) -> List[SentimentDivergence]:
        """
        🟡 تعديل 3: تباعد المشاعر عن السعر (حقيقي)
        
        السعر يصعد + المشاعر تتحول للسلبية = انعكاس هبوطي
        السعر يهبط + المشاعر تتحول للإيجابية = انعكاس صعودي
        """
        divergences = []
        
        if len(closes) < 10 or len(self.sentiment_history) < 5:
            return divergences
        
        # تغير السعر في آخر 10 شموع
        price_change = (closes[-1] - closes[-10]) / closes[-10] * 100 if closes[-10] > 0 else 0
        
        # تغير المشاعر
        old_sentiment = np.mean(list(self.sentiment_history)[-5:])
        new_sentiment = sentiment.overall_sentiment
        
        sentiment_change = new_sentiment - old_sentiment
        
        # تباعد هابط: سعر يصعد + مشاعر تتحول للسلبية
        if price_change > 2.0 and sentiment_change < -0.3:
            divergences.append(SentimentDivergence(
                index=len(closes) - 1,
                divergence_type='bearish',
                price_change=price_change,
                sentiment_change=sentiment_change,
                strength=min(1.0, abs(sentiment_change)),
                description=f"تباعد هابط: سعر +{price_change:.1f}% لكن المشاعر {sentiment_change:.2f}",
            ))
        
        # تباعد صاعد: سعر يهبط + مشاعر تتحول للإيجابية
        if price_change < -2.0 and sentiment_change > 0.3:
            divergences.append(SentimentDivergence(
                index=len(closes) - 1,
                divergence_type='bullish',
                price_change=price_change,
                sentiment_change=sentiment_change,
                strength=min(1.0, abs(sentiment_change)),
                description=f"تباعد صاعد: سعر {price_change:.1f}% لكن المشاعر +{sentiment_change:.2f}",
            ))
        
        return divergences
    
    def _detect_hype_cycle(self, sentiment: SocialSentimentScore,
                            closes: np.ndarray) -> str:
        """
        🟡 تعديل 6: تحديد مرحلة دورة الضجيج من البيانات الحقيقية
        
        Stealth: حجم اجتماعي منخفض + سعر مستقر
        Awareness: حجم يبدأ يرتفع + سعر يتحرك
        Mania: حجم في أعلى 10% + سعر في قمة
        Blow-off: حجم يبدأ ينخفض + سعر ينهار
        """
        if len(self.volume_history) < 20:
            return 'unknown'
        
        vol_history = list(self.volume_history)
        price_history = list(self.price_history)
        
        current_vol = sentiment.social_volume
        avg_vol = np.mean(vol_history[-20:])
        vol_percentile = sum(1 for v in vol_history if v < current_vol) / len(vol_history)
        
        current_price = closes[-1] if len(closes) > 0 else 0
        price_20_high = max(price_history[-20:]) if len(price_history) >= 20 else current_price
        price_20_low = min(price_history[-20:]) if len(price_history) >= 20 else current_price
        
        if price_20_high > price_20_low:
            price_position = (current_price - price_20_low) / (price_20_high - price_20_low)
        else:
            price_position = 0.5
        
        # Stealth: حجم منخفض + سعر في الأسفل
        if vol_percentile < 0.3 and price_position < 0.4:
            return 'stealth'
        
        # Awareness: حجم متوسط + سعر يتحرك
        if 0.3 <= vol_percentile < 0.6:
            return 'awareness'
        
        # Mania: حجم عالي + سعر في القمة
        if vol_percentile > 0.7 and price_position > 0.7:
            return 'mania'
        
        # Blow-off: حجم يبدأ ينخفض + سعر ينهار
        if vol_percentile > 0.5 and price_position < 0.3 and current_vol < avg_vol:
            return 'blow_off'
        
        return 'transition'
    
    def _calculate_contrarian_score(self, sentiment: SocialSentimentScore,
                                      closes: np.ndarray, volumes: np.ndarray) -> Dict:
        """
        🟡 تعديل 7: Contrarian Confidence Score
        
        لا تبيع لمجرد مشاعر إيجابية.
        انتظر 3 شروط: مشاعر متطرفة + حجم اجتماعي عالي + سعر عند مقاومة
        """
        score = 0.0
        signal = 'none'
        conditions_met = []
        
        # شرط 1: مشاعر متطرفة (> 0.7 أو < -0.7)
        if sentiment.overall_sentiment > 0.7:
            score += 0.3
            conditions_met.append("مشاعر إيجابية متطرفة")
        elif sentiment.overall_sentiment < -0.7:
            score += 0.3
            conditions_met.append("مشاعر سلبية متطرفة")
        
        # شرط 2: حجم اجتماعي في أعلى 20%
        if len(self.volume_history) >= 20:
            vol_percentile = sum(1 for v in self.volume_history if v < sentiment.social_volume) / len(self.volume_history)
            if vol_percentile > 0.8:
                score += 0.3
                conditions_met.append(f"حجم اجتماعي في أعلى {vol_percentile:.0%}")
        
        # شرط 3: السعر عند مقاومة/دعم
        if len(closes) >= 50:
            highs_50 = max(closes[-50:])
            lows_50 = min(closes[-50:])
            range_50 = highs_50 - lows_50
            if range_50 > 0:
                price_pos = (closes[-1] - lows_50) / range_50
                if price_pos > 0.8 and sentiment.overall_sentiment > 0.5:
                    score += 0.2
                    conditions_met.append("سعر عند مقاومة")
                elif price_pos < 0.2 and sentiment.overall_sentiment < -0.5:
                    score += 0.2
                    conditions_met.append("سعر عند دعم")
        
        if score > 0.6:
            if sentiment.overall_sentiment > 0.5:
                signal = 'sell'  # contrarian بيع عند الطمع
            elif sentiment.overall_sentiment < -0.5:
                signal = 'buy'  # contrarian شراء عند الخوف
        
        return {
            "signal": signal,
            "score": score,
            "conditions": conditions_met,
        }
    
    def _update_social_levels(self, posts: List[SocialPost], current_price: float):
        """
        🟡 تعديل 8: تحديث مستويات الدعم/المقاومة الاجتماعية
        
        السعر الذي كان عنده أعلى حجم منشورات = مستوى اجتماعي
        """
        if not posts:
            return
        
        # تجميع المنشورات حسب السعر
        price_buckets = defaultdict(int)
        for post in posts:
            if post.price_at_time > 0:
                # تقريب لأقرب مستوى
                bucket = round(post.price_at_time / current_price * 100) * current_price / 100
                price_buckets[bucket] += 1
        
        if price_buckets:
            # أعلى تركيز للمنشورات
            max_price = max(price_buckets, key=price_buckets.get)
            max_count = price_buckets[max_price]
            
            level = {
                "price": max_price,
                "post_count": max_count,
                "timestamp": datetime.now(),
            }
            
            # إضافة إذا كان جديداً
            if not self.social_sr_levels or \
               abs(max_price - self.social_sr_levels[-1]['price']) / current_price > 0.01:
                self.social_sr_levels.append(level)
        
        # اقتصاص
        if len(self.social_sr_levels) > 20:
            self.social_sr_levels = self.social_sr_levels[-20:]
    
    def _calculate_sentiment_change(self) -> Tuple[float, float]:
        """حساب تغير المشاعر في آخر ساعة و24 ساعة"""
        if len(self.sentiment_history) < 2:
            return 0.0, 0.0
        
        current = self.sentiment_history[-1]
        
        # آخر ساعة (آخر قيمة)
        one_hour_ago = self.sentiment_history[-2] if len(self.sentiment_history) >= 2 else current
        
        # آخر 24 ساعة
        idx_24h = max(0, len(self.sentiment_history) - 24)
        twenty_four_hours_ago = self.sentiment_history[idx_24h]
        
        return current - one_hour_ago, current - twenty_four_hours_ago
    
    def _calculate_volume_change(self, current_volume: int) -> float:
        """حساب تغير الحجم الاجتماعي"""
        if len(self.volume_history) < 2:
            return 0.0
        
        prev = self.volume_history[-2]
        if prev == 0:
            return 1.0 if current_volume > 0 else 0.0
        
        return (current_volume - prev) / prev
    
    def _determine_contrarian_signal(self, sentiment: float, volume: int,
                                      fear_greed: float) -> str:
        """تحديد إشارة Contrarian"""
        if fear_greed > 85 and sentiment > 0.6 and volume > 50:
            return 'sell'
        elif fear_greed < 15 and sentiment < -0.6 and volume > 50:
            return 'buy'
        return 'none'
    
    def _update_history(self, sentiment: SocialSentimentScore, volume: int, price: float):
        """تحديث التاريخ"""
        self.sentiment_history.append(sentiment.overall_sentiment)
        self.volume_history.append(volume)
        self.price_history.append(price)
    
    def _generate_signals(self, sentiment: SocialSentimentScore,
                           volume_spike: Dict, divergences: List[SentimentDivergence],
                           hype_phase: str, contrarian: Dict,
                           current_price: float) -> List[SocialSignal]:
        """توليد إشارات التداول"""
        signals = []
        idx = 0  # سيُملأ من السياق الخارجي
        
        # 🟡 تعديل 2: Spike في الحجم الاجتماعي
        if volume_spike.get("is_spike"):
            # اتجاه السعر يحدد الاتجاه
            if sentiment.overall_sentiment > 0.3:
                signals.append(SocialSignal(
                    index=idx,
                    signal_type='volume_spike',
                    direction='bullish',
                    strength=0.7,
                    confidence=0.65,
                    description=f"انفجار حجم اجتماعي (×{volume_spike['multiplier']:.1f}) + مشاعر إيجابية",
                    sources=['twitter', 'google_news', 'reddit'],
                    social_volume_at_signal=sentiment.social_volume,
                ))
            elif sentiment.overall_sentiment < -0.3:
                signals.append(SocialSignal(
                    index=idx,
                    signal_type='volume_spike',
                    direction='bearish',
                    strength=0.7,
                    confidence=0.65,
                    description=f"انفجار حجم اجتماعي (×{volume_spike['multiplier']:.1f}) + مشاعر سلبية",
                    sources=['twitter', 'google_news', 'reddit'],
                    social_volume_at_signal=sentiment.social_volume,
                ))
        
        # 🟡 تعديل 3: تباعد المشاعر
        for div in divergences:
            signals.append(SocialSignal(
                index=idx,
                signal_type='divergence',
                direction=div.divergence_type,
                strength=div.strength,
                confidence=0.7,
                description=div.description,
                sources=['twitter', 'google_news', 'reddit'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        
        # 🟡 تعديل 6: مرحلة الضجيج
        if hype_phase == 'stealth':
            signals.append(SocialSignal(
                index=idx,
                signal_type='narrative_shift',
                direction='bullish',
                strength=0.5,
                confidence=0.5,
                description="مرحلة التخفي - تجميع هادئ",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        elif hype_phase == 'mania':
            signals.append(SocialSignal(
                index=idx,
                signal_type='narrative_shift',
                direction='bearish',
                strength=0.7,
                confidence=0.6,
                description="مرحلة الهوس - خطر انفجار الفقاعة",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        
        # 🟡 تعديل 7: Contrarian
        if contrarian.get("signal") == 'buy':
            signals.append(SocialSignal(
                index=idx,
                signal_type='contrarian',
                direction='bullish',
                strength=0.85,
                confidence=contrarian.get("score", 0.6),
                description=f"شراء Contrarian: {', '.join(contrarian.get('conditions', []))}",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        elif contrarian.get("signal") == 'sell':
            signals.append(SocialSignal(
                index=idx,
                signal_type='contrarian',
                direction='bearish',
                strength=0.85,
                confidence=contrarian.get("score", 0.6),
                description=f"بيع Contrarian: {', '.join(contrarian.get('conditions', []))}",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        
        # مشاعر متطرفة
        if sentiment.fear_greed_index > 85:
            signals.append(SocialSignal(
                index=idx,
                signal_type='sentiment_extreme',
                direction='bearish',
                strength=0.65,
                confidence=0.6,
                description=f"طمع شديد (FG:{sentiment.fear_greed_index:.0f}) - حذر من التصحيح",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        elif sentiment.fear_greed_index < 15:
            signals.append(SocialSignal(
                index=idx,
                signal_type='sentiment_extreme',
                direction='bullish',
                strength=0.65,
                confidence=0.6,
                description=f"خوف شديد (FG:{sentiment.fear_greed_index:.0f}) - فرصة شراء",
                sources=['all'],
                social_volume_at_signal=sentiment.social_volume,
            ))
        
        return signals


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           الدرجة النهائية: استراتيجية المشاعر الاجتماعية الموحدة           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SocialSentimentStrategy:
    """
    استراتيجية تحليل المشاعر الاجتماعية الحقيقية (الإصدار 2.0)
    
    تستخدم بيانات حقيقية من:
    - Twitter API
    - Google News RSS
    - Reddit RSS
    
    لم تعد تخترع مشاعر من السعر.
    """
    
    def __init__(self):
        self.sentiment_analyzer = SocialSentimentAnalyzer()
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        التحليل الكامل
        """
        opens = np.array(chart_data.get('opens', []))
        highs = np.array(chart_data.get('highs', []))
        lows = np.array(chart_data.get('lows', []))
        closes = np.array(chart_data.get('closes', []))
        volumes = np.array(chart_data.get('volumes', []))
        symbol = chart_data.get('symbol', 'BTCUSD')
        
        if len(closes) < 10:
            return {"recommendation": "محايد", "confidence": 10,
                    "reason": "تحتاج 10 شموع على الأقل"}
        
        # تحليل المشاعر الحقيقية
        sentiment_data = self.sentiment_analyzer.analyze(
            highs, lows, closes, volumes, symbol
        )
        
        # القرار
        decision = self._make_decision(sentiment_data, closes)
        
        return {
            **decision,
            "sentiment_data": sentiment_data,
        }
    
    def _make_decision(self, sentiment_data: Dict, closes: np.ndarray) -> Dict:
        """اتخاذ القرار"""
        buy_signals = []
        sell_signals = []
        
        sentiment_score = sentiment_data.get("sentiment_score")
        signals = sentiment_data.get("signals", [])
        
        # ---- من المشاعر ----
        if sentiment_score:
            if sentiment_score.overall_sentiment > 0.6:
                buy_signals.append((f"مشاعر إيجابية ({sentiment_score.overall_sentiment:.2f})", 0.4))
            elif sentiment_score.overall_sentiment < -0.6:
                sell_signals.append((f"مشاعر سلبية ({sentiment_score.overall_sentiment:.2f})", 0.4))
            
            # Contrarian
            if sentiment_score.contrarian_signal == 'buy':
                buy_signals.append(("إشارة Contrarian شراء", 0.75))
            elif sentiment_score.contrarian_signal == 'sell':
                sell_signals.append(("إشارة Contrarian بيع", 0.75))
            
            # Fear & Greed
            if sentiment_score.fear_greed_index > 80:
                sell_signals.append((f"طمع شديد ({sentiment_score.fear_greed_index:.0f})", 0.55))
            elif sentiment_score.fear_greed_index < 20:
                buy_signals.append((f"خوف شديد ({sentiment_score.fear_greed_index:.0f})", 0.55))
            
            # حجم اجتماعي
            if sentiment_score.volume_change_1h > 2.0:
                buy_signals.append((f"انفجار حجم اجتماعي (×{sentiment_score.volume_change_1h:.1f})", 0.5))
        
        # ---- من الإشارات ----
        for sig in signals[-5:]:
            weight = sig.strength * 0.7
            if sig.signal_type == 'contrarian':
                weight = sig.strength * 0.9
            elif sig.signal_type == 'divergence':
                weight = sig.strength * 0.75
            
            if sig.direction == 'bullish':
                buy_signals.append((sig.description, weight))
            else:
                sell_signals.append((sig.description, weight))
        
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
        
        if sentiment_score:
            reason += f" | Sent:{sentiment_score.overall_sentiment:.2f}"
            reason += f" | Vol:{sentiment_score.social_volume}"
            reason += f" | FG:{sentiment_score.fear_greed_index:.0f}"
        
        data_source = sentiment_data.get("data_source", "unavailable")
        if data_source == "unavailable":
            reason += " | ⚠️ بيانات اجتماعية غير متاحة"
        else:
            reason += " | ✅ بيانات حقيقية"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }


def create_social_sentiment_strategy():
    """إنشاء استراتيجية المشاعر الاجتماعية الجاهزة (الإصدار 2.0)"""
    return SocialSentimentStrategy()