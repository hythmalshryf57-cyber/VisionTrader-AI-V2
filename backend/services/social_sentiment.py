from typing import Dict, Any, List

from .deep_market import DeepMarketScanner
try:
    from backend.strategies.social_sentiment import SocialSentimentStrategy
except ImportError:
    from strategies.social_sentiment import SocialSentimentStrategy


class SocialSentimentService:
    def __init__(self):
        self.market_scanner = DeepMarketScanner()
        self.strategy = SocialSentimentStrategy()

    def _build_chart_data(self, klines: List[List[Any]]) -> Dict[str, List[float]]:
        opens = [float(item[1]) for item in klines]
        highs = [float(item[2]) for item in klines]
        lows = [float(item[3]) for item in klines]
        closes = [float(item[4]) for item in klines]
        volumes = [float(item[5]) for item in klines]
        return {
            "opens": opens,
            "highs": highs,
            "lows": lows,
            "closes": closes,
            "volumes": volumes,
        }

    def analyze(self, symbol: str) -> Dict[str, Any]:
        klines = self.market_scanner._get_klines(symbol, interval="15m", limit=100)
        if not klines:
            return {
                "symbol": symbol,
                "available": False,
                "recommendation": "غير متاحة",
                "message": "لا توجد بيانات كافية لتحليل المشاعر الاجتماعية.",
            }

        chart_data = self._build_chart_data(klines)
        try:
            result = self.strategy.analyze(chart_data)
        except Exception as e:
            return {
                "symbol": symbol,
                "available": False,
                "recommendation": "خطأ",
                "message": f"فشل تحليل المشاعر: {e}",
            }

        sentiment_score = result.get("sentiment") or result.get("sentiment_score") or 0.0
        return {
            "symbol": symbol,
            "available": True,
            "recommendation": result.get("recommendation", "محايد"),
            "confidence": int(result.get("confidence", 0) if isinstance(result.get("confidence", 0), (int, float)) else 0),
            "sentiment_score": round(float(sentiment_score), 3),
            "detail": result,
            "message": "تم تحليل الاتجاهات الاجتماعية بناءً على بيانات السوق وسلوك الأسعار.",
        }


social_sentiment_service = SocialSentimentService()
