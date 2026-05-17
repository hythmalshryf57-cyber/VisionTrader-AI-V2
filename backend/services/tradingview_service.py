import requests
import base64
from typing import Optional, Dict
from config import settings


class TradingViewService:
    SCREENSHOT_PROVIDER = "https://image.thum.io/get/width/1200/crop/700/"
    GEMINI_ENDPOINT = getattr(settings, 'GEMINI_API_URL', 'https://api.gemini.com/v1/vision/analyze')

    def fetch_chart_snapshot(self, url: str) -> bytes:
        if not url:
            raise ValueError("TradingView URL is required")
        snapshot_url = self.SCREENSHOT_PROVIDER + url
        response = requests.get(snapshot_url, timeout=25)
        response.raise_for_status()
        return response.content

    def analyze_with_gemini(self, image_bytes: bytes) -> Dict:
        if not getattr(settings, 'GEMINI_API_KEY', None):
            return {
                "analysis": {
                    "recommendation": "محايد",
                    "confidence": 40,
                    "note": "Gemini API key غير مضبوطة. تم إرجاع تحليل احتياطي." 
                },
                "source": "fallback"
            }
        payload = {
            "image_base64": base64.b64encode(image_bytes).decode('utf-8'),
            "instructions": "حلل لقطة شاشة TradingView وقدم توصية سوقية، مستويات دعم ومقاومة، واتجاه عام."
        }
        # Use API key as query parameter to match authentication method requested
        url = f"{self.GEMINI_ENDPOINT}?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return {"analysis": response.json(), "source": "gemini"}
        except Exception as e:
            return {
                "analysis": {
                    "recommendation": "محايد",
                    "confidence": 40,
                    "note": f"فشل الاتصال بـ Gemini: {e}. تم استخدام تحليل احتياطي."
                },
                "source": "fallback"
            }

    def fetch_and_analyze(self, url: str) -> Dict:
        image_bytes = self.fetch_chart_snapshot(url)
        return self.analyze_with_gemini(image_bytes)

    def detect_chart_details(self, image_bytes: bytes) -> Dict:
        if not getattr(settings, 'GEMINI_API_KEY', None):
            return {
                "pair": "UNKNOWN",
                "timeframe": "UNKNOWN",
                "confidence": 0,
                "note": "Gemini API key غير مضبوطة."
            }

        payload = {
            "image_base64": base64.b64encode(image_bytes).decode('utf-8'),
            "instructions": "حلل هذه الصورة للشارت واستخرج: الزوج التجاري (مثل XAU/USD, EUR/USD), الفريم الزمني (مثل 1H, 4H, Daily). أعد الإجابة بتنسيق JSON فقط."
        }
        url = f"{self.GEMINI_ENDPOINT}?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            # Assume result has pair, timeframe, confidence
            return {
                "pair": result.get("pair", "UNKNOWN"),
                "timeframe": result.get("timeframe", "UNKNOWN"),
                "confidence": result.get("confidence", 50)
            }
        except Exception as e:
            return {
                "pair": "UNKNOWN",
                "timeframe": "UNKNOWN",
                "confidence": 0,
                "note": f"فشل التعرف: {e}"
            }
