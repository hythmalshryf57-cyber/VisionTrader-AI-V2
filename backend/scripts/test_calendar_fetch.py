from importlib import import_module
import sys
sys.path.insert(0, '..')
try:
    mod = import_module('backend.services.calendar_service')
    svc = getattr(mod, 'calendar_service')
    events = svc.get_upcoming_events(48)
    print('Upcoming events:', len(events))
    for e in events[:10]:
        print('-', e.get('title'), e.get('time'))
except Exception as exc:
    print('ERROR', exc)
