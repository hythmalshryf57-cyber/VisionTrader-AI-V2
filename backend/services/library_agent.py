from typing import Any, Dict, List

class LibraryAgent:
    def __init__(self):
        self.name = "Library Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        strategy = data.get("strategy_name") or data.get("strategy") or "استراتيجية عامة"
        examples = data.get("strategy_examples") or []
        explanation = data.get("strategy_description") or "شرح مبسط للاستراتيجية غير متوفر."
        demo = examples[:3] if isinstance(examples, list) else []

        report = f"شرح الاستراتيجية: {strategy}. {explanation}"
        if demo:
            report += f" أمثلة حية: {', '.join(str(x) for x in demo)}."

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60,
            "report": report,
            "strategy": strategy,
            "examples": demo,
        }
