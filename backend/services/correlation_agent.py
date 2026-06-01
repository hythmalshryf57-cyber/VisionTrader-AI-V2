from typing import Any, Dict, List

class CorrelationAgent:
    def __init__(self):
        self.name = "Correlation Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        relations = data.get("correlations") or []
        strong_pairs = []
        inverse_pairs = []
        for rel in relations:
            symbol = rel.get("symbol") or rel.get("pair") or "unknown"
            corr = float(rel.get("correlation") or 0)
            if corr >= 0.8:
                strong_pairs.append(symbol)
            if corr <= -0.8:
                inverse_pairs.append(symbol)

        if strong_pairs:
            report = f"أسواق مترابطة قوية: {', '.join(strong_pairs)}."
        else:
            report = "لا توجد علاقات قوية إيجابية واضحة."
        if inverse_pairs:
            report += f" علاقات عكسية قوية: {', '.join(inverse_pairs)}."

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60,
            "report": report,
            "strong_pairs": strong_pairs,
            "inverse_pairs": inverse_pairs,
        }
