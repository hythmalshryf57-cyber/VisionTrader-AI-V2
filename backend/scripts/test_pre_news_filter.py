from datetime import datetime, timedelta, timezone
import sys, os

# Ensure backend package is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Stub heavy submodules (like ai_core) to avoid importing sklearn/scipy during this quick test
import types
fake_ai_core = types.ModuleType('services.ai_core')
fake_ai_core.ai_core_service = None
sys.modules['services.ai_core'] = fake_ai_core

from services.voting_engine import EnvironmentFilter

class FakeCalendar:
    def __init__(self, now, event_offset_minutes=None, past=False):
        self.now = now
        self.event_offset_minutes = event_offset_minutes
        self.past = past

    def get_upcoming_events(self, hours=4):
        events = []
        if self.event_offset_minutes is None:
            return events
        event_time = self.now + timedelta(minutes=self.event_offset_minutes)
        if not self.past and event_time > self.now:
            events.append({
                'title': 'Test High Impact',
                'currency': 'USD',
                'impact': 'high',
                'time': event_time,
                'time_until': event_time - self.now
            })
        return events

    def get_today_events(self):
        events = []
        if self.event_offset_minutes is None:
            return events
        event_time = self.now + timedelta(minutes=self.event_offset_minutes)
        events.append({
            'title': 'Test High Impact',
            'currency': 'USD',
            'impact': 'high',
            'time': event_time,
        })
        return events


def run_case(offset_minutes, description, past=False):
    now = datetime.now(timezone.utc)
    fake = FakeCalendar(now, event_offset_minutes=offset_minutes, past=past)
    ef = EnvironmentFilter()
    ef.calendar_service = fake
    res = ef.check_environment('EURUSD')
    print('---', description)
    print('offset_minutes:', offset_minutes)
    print('recommendation:', res.get('recommendation'))
    print('message:', res.get('message'))
    print('minutes_to_event:', res.get('minutes_to_event'))
    print('issues:', res.get('issues'))
    print()

if __name__ == '__main__':
    # Case 1: 12 minutes to event -> suspend (within 15)
    run_case(12, '12 minutes to event')

    # Case 2: 4 minutes to event -> suspend with close/tighten advice
    run_case(4, '4 minutes to event')

    # Case 3: event happened 5 minutes ago -> recent past within 10 -> resume
    run_case(-5, 'event occurred 5 minutes ago', past=True)
    # Case 4: event happened 11 minutes ago -> beyond 10 mins -> resume trading
    run_case(-11, 'event occurred 11 minutes ago', past=True)
