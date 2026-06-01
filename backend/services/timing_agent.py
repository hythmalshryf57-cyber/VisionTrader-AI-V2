from typing import Any, Dict, List

class TimingAgent:
    def __init__(self):
        self.name = "Timing Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sessions = data.get("session_performance") or []
        good_times = []
        weak_times = []
        for entry in sessions:
            session = entry.get("session") or "unknown"
            score = float(entry.get("score") or 0)
            if score >= 0.7:
                good_times.append(session)
            if score <= 0.3:
                weak_times.append(session)

        if good_times:
            signal = "buy"
            confidence = 70
            report = f"أفضل أوقات الدخول: {', '.join(good_times)}."
        else:
            signal = "neutral"
            confidence = 40
            report = "لا يوجد وقت دخول مفضل واضح؛ تجنب الصفقات في الأوقات الضعيفة."
        if weak_times:
            report += f" أوقات السيولة الضعيفة: {', '.join(weak_times)}."

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": report,
            "good_times": good_times,
            "weak_times": weak_times,
        }
