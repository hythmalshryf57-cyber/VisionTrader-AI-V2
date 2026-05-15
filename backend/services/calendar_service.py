"""
Calendar Service - خدمة التقويم الاقتصادي
"""

from typing import List, Dict
from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET

class CalendarService:
    """خدمة لجلب البيانات الاقتصادية والأحداث المؤثرة من Forex Factory"""

    def __init__(self):
        self.feed_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        self.cache = {
            "updated": datetime.min,
            "events": []
        }
        self.cache_ttl = timedelta(minutes=15)

    def _refresh_cache(self):
        now = datetime.utcnow()
        if now - self.cache["updated"] < self.cache_ttl:
            return

        try:
            response = requests.get(self.feed_url, timeout=3)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            events = []

            for node in root.findall('.//event'):
                timestamp = node.get('timestamp')
                if not timestamp:
                    continue
                try:
                    event_time = datetime.utcfromtimestamp(int(timestamp))
                except ValueError:
                    continue

                events.append({
                    "title": node.get('title') or node.get('eventName') or "غير معروف",
                    "currency": node.get('currency') or node.get('country') or "N/A",
                    "impact": node.get('impact') or node.get('importance') or "low",
                    "time": event_time,
                    "actual": node.get('actual'),
                    "forecast": node.get('forecast'),
                    "previous": node.get('previous'),
                    "importance": node.get('importance') or node.get('impact') or "low"
                })

            self.cache["events"] = sorted(events, key=lambda e: e["time"])
            self.cache["updated"] = now
        except Exception:
            self.cache["updated"] = now
            pass

    def get_upcoming_events(self, hours: int = 24) -> List[Dict]:
        """
        جلب الأحداث الاقتصادية القادمة

        Args:
            hours: عدد الساعات القادمة للبحث

        Returns:
            قائمة بالأحداث
        """

        self._refresh_cache()
        now = datetime.utcnow()
        return [
            {**event, "time_until": event["time"] - now}
            for event in self.cache["events"]
            if event["time"] > now and (event["time"] - now).total_seconds() / 3600 <= hours
        ]

    def get_today_events(self) -> List[Dict]:
        self._refresh_cache()
        today = datetime.utcnow().date()
        return [
            {
                **event,
                "time_iso": event["time"].isoformat() + "Z",
                "minutes_until": max(0, int((event["time"] - datetime.utcnow()).total_seconds() / 60))
            }
            for event in self.cache["events"]
            if event["time"].date() == today
        ]

    def get_high_impact_soon(self, minutes: int = 15) -> List[Dict]:
        now = datetime.utcnow()
        return [
            {**event, "minutes_until": max(0, int((event["time"] - now).total_seconds() / 60))}
            for event in self.get_today_events()
            if event.get("impact") == "high" and 0 <= (event["time"] - now).total_seconds() / 60 <= minutes
        ]

    def get_market_specific_events(self, market: str) -> List[Dict]:
        currency = "USD"
        if market.startswith("XAU"):
            currency = "USD"
        elif market.endswith("USD"):
            currency = market[:3]

        return [
            event for event in self.get_today_events()
            if event.get("currency") in [currency, "USD", "EUR", "GBP", "AUD", "JPY"]
        ]

# إنشاء instance عالمي
calendar_service = CalendarService()