import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

class PerformanceAnalyst:
    def __init__(self):
        self.name = "Performance Analyst"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        trades = data.get("trade_history") or []
        by_day = defaultdict(list)
        by_symbol = defaultdict(list)
        for trade in trades:
            pnl = float(trade.get("pnl") or 0)
            symbol = trade.get("symbol") or trade.get("market") or "unknown"
            ts = trade.get("timestamp") or trade.get("time")
            if ts:
                try:
                    dt = datetime.fromtimestamp(int(ts)) if isinstance(ts, (int, float)) else datetime.fromisoformat(str(ts))
                    day = dt.date().isoformat()
                except Exception:
                    day = "unknown"
            else:
                day = "unknown"
            by_day[day].append(pnl)
            by_symbol[symbol].append(pnl)

        best_day = max(by_day.items(), key=lambda kv: sum(kv[1]), default=("-", []))[0]
        worst_day = min(by_day.items(), key=lambda kv: sum(kv[1]), default=("-", []))[0]
        best_symbol = max(by_symbol.items(), key=lambda kv: sum(kv[1]), default=("-", []))[0]
        worst_symbol = min(by_symbol.items(), key=lambda kv: sum(kv[1]), default=("-", []))[0]

        suggestions = []
        if len(trades) >= 10:
            avg_pnl = statistics.mean([float(t.get("pnl") or 0) for t in trades])
            if avg_pnl < 0:
                suggestions.append("حاول توسيع الوقف 5 نقاط في الصفقات الضعيفة وتحسين إدارة الاتجاه.")
            else:
                suggestions.append("استمر في التركيز على الصفقات التي تظهر قوة واضحة وتجنب الضجيج.")
        else:
            suggestions.append("لم يتوفر عدد كافٍ من الصفقات لتحديد نمط أداء قوي.")

        summary = (
            f"أفضل يوم: {best_day}, أسوأ يوم: {worst_day}. أفضل زوج: {best_symbol}, أسوأ زوج: {worst_symbol}."
        )
        if suggestions:
            summary += " " + " ".join(suggestions)

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 50,
            "report": summary,
            "best_day": best_day,
            "worst_day": worst_day,
            "best_symbol": best_symbol,
            "worst_symbol": worst_symbol,
            "suggestions": suggestions,
        }
