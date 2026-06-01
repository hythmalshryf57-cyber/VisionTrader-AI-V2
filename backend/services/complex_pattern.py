from typing import Any, Dict, List

class ComplexPattern:
    def __init__(self):
        self.name = "Complex Pattern Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        patterns = data.get("pattern_signals") or []
        found = []
        for pattern in patterns:
            name = str(pattern.get("pattern") or pattern.get("name") or "unknown")
            score = float(pattern.get("confidence") or 0)
            if score >= 60:
                found.append(name)

        report = (
            f"اكتشف الأنماط التالية: {', '.join(found)}." if found else "لا توجد أنماط معقدة قوية حالياً."
        )
        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60 if found else 40,
            "report": report,
            "patterns_found": found,
        }
