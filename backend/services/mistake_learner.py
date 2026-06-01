from collections import Counter
from typing import Any, Dict, List

class MistakeLearner:
    def __init__(self):
        self.name = "Mistake Learner"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        trades = data.get("trade_history") or []
        losses = [t for t in trades if float(t.get("pnl") or 0) < 0]
        reasons = [str(t.get("mistake") or t.get("reason") or "غير محدد") for t in losses]
        counts = Counter(reasons)
        repeated = [reason for reason, count in counts.items() if count >= 3]

        details = []
        for reason, count in counts.most_common(3):
            details.append(f"{reason}: {count} مرات")

        if repeated:
            alert = f"تم تكرار نفس الخطأ {repeated[0]} ثلاث مرات أو أكثر؛ يجب مراجعة النظام بشكل عاجل."
        else:
            alert = "لا يوجد نمط خطأ مكرر جداً حتى الآن."

        advice = []
        for reason, count in counts.items():
            if "وقف" in reason or "stop" in reason.lower():
                advice.append("تحقق من إعدادات الوقف وتأكد من زيادة المساحة عند الضرورة.")
            elif "تأخر" in reason or "late" in reason.lower():
                advice.append("لا تدخل الصفقة متأخراً وحافظ على الانضباط الزمني.")
            elif "تحيز" in reason or "emotion" in reason.lower():
                advice.append("تجنب التداول بناءً على العواطف وابقَ على الخطة.")

        if not advice:
            advice.append("راجع الصفقات الخاسرة وحاول تحديد السبب الدقيق لكل منها.")

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 55,
            "report": f"صمم لتحليل الأخطاء المتكررة وتقديم نصائح مخصصة. {alert}",
            "loss_count": len(losses),
            "common_errors": details,
            "strong_alert": bool(repeated),
            "advice": advice,
        }
