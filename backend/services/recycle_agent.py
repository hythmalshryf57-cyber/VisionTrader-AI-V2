from typing import Any, Dict, List

class RecycleAgent:
    def __init__(self):
        self.name = "Recycle Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        matches = data.get("historical_matches") or []
        similar = [m for m in matches if float(m.get("score") or 0) >= 0.7]
        report = (
            f"وجدت {len(similar)} حالة تاريخية مشابهة." if similar else "لا توجد حالات تاريخية مشابهة قوية."
        )
        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60 if similar else 35,
            "report": report,
            "similar_patterns": [m.get("pattern") or m.get("name") for m in similar],
        }
