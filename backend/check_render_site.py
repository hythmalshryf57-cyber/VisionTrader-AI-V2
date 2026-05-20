import urllib.request
import urllib.error
import ssl
from urllib.parse import urljoin

base = 'https://visiontrader-ai-v2.onrender.com'
pages = [
    '/', '/frontend/login.html', '/frontend/register.html', '/frontend/dashboard.html',
    '/frontend/upload.html', '/frontend/result.html', '/frontend/history.html',
    '/frontend/calendar.html', '/frontend/settings.html', '/frontend/backtest.html',
    '/frontend/journal.html', '/frontend/admin.html', '/frontend/strategy_factory.html',
    '/frontend/strategy-battle.html', '/frontend/ask-ai.html', '/frontend/heatmap.html',
    '/frontend/academy.html', '/frontend/service-health.html'
]
apis = [
    '/api/health', '/api/system/pulse', '/api/system/strategies', '/api/system/personality',
    '/api/market/session', '/api/calendar/events', '/api/protection/status',
    '/api/daily-limits/status', '/api/market/countdown'
]

ctx = ssl.create_default_context()
ctx.check_hostname = True
ctx.verify_mode = ssl.CERT_REQUIRED

for path in pages + apis:
    url = urljoin(base, path)
    print('PATH:', path)
    print('URL:', url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            status = resp.getcode()
            content_type = resp.headers.get('Content-Type', '')
            raw = resp.read(4096)
            body = raw.decode('utf-8', errors='replace').strip().replace('\n', ' ')[:300]
            print('STATUS:', status)
            print('CONTENT-TYPE:', content_type)
            print('BODY:', body)
    except urllib.error.HTTPError as e:
        raw = e.read(4096)
        body = raw.decode('utf-8', errors='replace').strip().replace('\n', ' ')[:300] if raw else ''
        print('STATUS:', e.code)
        print('ERROR: HTTPError', e.reason)
        print('BODY:', body)
    except Exception as e:
        print('ERROR:', repr(e))
    print('---')
