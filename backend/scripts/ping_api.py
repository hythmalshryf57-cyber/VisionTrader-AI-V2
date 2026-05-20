import urllib.request

URLS = [
    'http://127.0.0.1:8000/api/health',
    'http://127.0.0.1:8000/api/calendar/events',
    'http://127.0.0.1:8000/api/backtest/run',
]

for url in URLS:
    print('URL:', url)
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as r:
            print('status', r.status)
            print(r.read(1024).decode('utf-8', errors='replace'))
    except urllib.error.HTTPError as e:
        print('HTTPError', e.code)
        try:
            print(e.read().decode('utf-8', errors='replace'))
        except Exception as ex:
            print('body read failed', ex)
    except Exception as e:
        print('ERROR', type(e).__name__, e)
    print('---')
