from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

class NewsCalendarAgent:
    def __init__(self):
        self.name = "News Calendar Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        events = data.get("upcoming_news") or []
        strong_events = []
        summary_lines = []
        now = datetime.now(timezone.utc)
        for event in events:
            title = str(event.get("title") or event.get("headline") or "حدث").strip()
            time_value = event.get("time") or event.get("timestamp")
            if time_value:
                try:
                    event_time = datetime.fromtimestamp(int(time_value)) if isinstance(time_value, (int, float)) else datetime.fromisoformat(str(time_value))
                except Exception:
                    event_time = None
            else:
                event_time = None
            impact = str(event.get("impact") or event.get("importance") or "medium").lower()
            if impact in ["high", "strong", "كبير"]:
                strong_events.append(title)
            if event_time:
                minutes_to = int((event_time - now).total_seconds() / 60)
            else:
                minutes_to = None
            if minutes_to is not None and minutes_to <= 15 and impact in ["high", "strong", "كبير"]:
                summary_lines.append(f"تنبيه: {title} بعد {minutes_to} دقيقة.")

        overview = (
            f"يوجد {len(events)} حدثاً مقرراً اليوم. أهم الأحداث: {', '.join(str(e) for e in strong_events[:3]) or 'لا يوجد أحداث قوية حالياً'}."
        )
        if summary_lines:
            overview += " " + " ".join(summary_lines)

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60,
            "report": overview,
            "strong_events": strong_events,
            "morning_briefing": overview,
        }
