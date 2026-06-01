from typing import Any, Dict

class ChallengeAgent:
    def __init__(self):
        self.name = "Challenge Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        goals = data.get("weekly_goals") or {}
        progress = data.get("goal_progress") or {}
        pending = []
        for goal, target in goals.items():
            done = progress.get(goal, 0)
            if done < target:
                pending.append(f"{goal}: {done}/{target}")

        if pending:
            report = f"تحديات الأسبوع الحالية: {' ; '.join(pending)}. "
            signal = "neutral"
            confidence = 65
        else:
            report = "جميع تحديات الأسبوع على المسار الصحيح."
            signal = "buy"
            confidence = 75

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": report,
            "pending_goals": pending,
        }
