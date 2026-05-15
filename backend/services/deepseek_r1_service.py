"""
DeepSeek R1 Service - القاضي الذكي للتصويت
"""

import json
import logging
from typing import Dict, Optional
import requests
from config import settings

logger = logging.getLogger(__name__)

class DeepSeekR1Service:
    """خدمة DeepSeek R1 للتحليل المتقدم والقضاء على التناقضات"""

    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        self.base_url = "https://api.deepseek.com/v1"  # افتراضي
        self.model = "deepseek-r1"  # أو أي نموذج متاح

    def analyze_consensus(self, context: str) -> Dict:
        """
        تحليل توافق الاستراتيجيات وكشف التناقضات

        Args:
            context: سياق نتائج العناقيد

        Returns:
            قرار القاضي
        """

        if not self.api_key:
            return {
                "use_internal_judge": True,
                "approved": False,
                "confidence_boost": 0,
                "notes": "DeepSeek API key not configured; internal judge will validate cluster consensus."
            }

        prompt = f"""
        أنت قاضي ذكي في نظام تداول متقدم. لديك نتائج من 3 عناقيد استراتيجية:

        {context}

        مهمتك:
        1. تحليل ما إذا كانت النتائج متسقة منطقياً
        2. كشف أي تناقضات قاتلة
        3. منح boost للثقة إذا كان التوافق قوياً
        4. استخدام فيتو إذا وجدت تناقضاً خطيراً

        أجب بصيغة JSON فقط:
        {{
            "approved": true/false,
            "veto": true/false (إذا كان هناك تناقض قاتل),
            "veto_reason": "سبب الفيتو إذا وجد",
            "confidence_boost": عدد صحيح (0-20) زيادة في الثقة,
            "notes": "ملاحظات إضافية"
        }}
        """

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # منخفض للدقة
                    "max_tokens": 500
                },
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                try:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        parsed = json.loads(json_content)
                        return parsed
                except Exception as e:
                    logger.exception(f"Failed to parse DeepSeek response JSON: {e}")

            logger.warning("DeepSeek R1 service returned unexpected or invalid response")
            return {
                "use_internal_judge": True,
                "approved": False,
                "veto": False,
                "confidence_boost": 0,
                "notes": "Judge analysis could not be interpreted, internal judge will decide."
            }

        except Exception as e:
            logger.exception(f"DeepSeek R1 service error: {e}")
            return {
                "use_internal_judge": True,
                "approved": False,
                "veto": False,
                "confidence_boost": 0,
                "notes": f"Service error: {str(e)}"
            }

    def validate_market_logic(self, market: str, recommendation: str, cluster_details: Dict) -> Dict:
        """
        التحقق من منطق السوق

        Args:
            market: رمز السوق
            recommendation: التوصية
            cluster_details: تفاصيل العناقيد

        Returns:
            تقييم المنطق
        """

        prompt = f"""
        سوق: {market}
        التوصية: {recommendation}

        تفاصيل العناقيد:
        - القوة: {cluster_details.get('power', {}).get('direction', 'unknown')}
        - الهندسة: {cluster_details.get('geometric', {}).get('direction', 'unknown')}
        - الزخم: {cluster_details.get('momentum', {}).get('direction', 'unknown')}

        هل هذه التوصية منطقية للسوق المحدد؟ هل تتوافق مع اتجاهات السوق الحالية؟
        أجب بـ true/false وسبب مختصر.
        """

        # تنفيذ مشابه للدالة أعلاه
        # ... (يمكن إضافة لاحقاً)

        return {"logical": True, "reason": "Analysis pending"}

# إنشاء instance عالمي
deepseek_r1_service = DeepSeekR1Service()