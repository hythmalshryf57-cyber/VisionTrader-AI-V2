from typing import Any, Dict, List

class ResearchAgent:
    def __init__(self):
        self.name = "Research Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        news = data.get("research_news") or []
        discoveries = [item.get("headline") or item.get("title") for item in news[:5] if item]
        summary = data.get("weekly_summary") or "ملخص أسبوعي غير متوفر." 
        if not discoveries:
            discoveries = ["لا توجد اكتشافات جديدة حالياً."]

        report = (
            f"أهم 5 اكتشافات هذا الأسبوع: {', '.join(discoveries)}. "
            f"{summary}"
        )
        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 55,
            "report": report,
            "discoveries": discoveries,
            "summary": summary,
        }
