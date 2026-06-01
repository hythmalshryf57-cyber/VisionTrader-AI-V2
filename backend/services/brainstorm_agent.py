from typing import Any, Dict, List

class BrainstormAgent:
    def __init__(self):
        self.name = "Brainstorm Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        themes = data.get("market_themes") or []
        ideas = []
        for theme in themes[:3]:
            ideas.append(f"جرب اختبار {theme} مع وقف أوسع وقدرة تحمل.")

        if not ideas:
            ideas.append("ضيف فكرة تداول جديدة مستخدماً نماذج الاتجاه والمحافظة على المخاطرة.")

        backtests = data.get("backtest_results") or []
        best_backtest = max(backtests, key=lambda x: float(x.get("sharpe") or 0), default=None)
        report = f"أفكار عصف ذهني: {'; '.join(ideas)}"
        if best_backtest:
            report += f" أفضل نتيجة اختبار: {best_backtest.get('strategy','?')} مع Sharpe {best_backtest.get('sharpe')}."

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 55,
            "report": report,
            "ideas": ideas,
            "best_backtest": best_backtest,
        }
