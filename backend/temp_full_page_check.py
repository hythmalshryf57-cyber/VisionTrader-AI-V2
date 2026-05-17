import urllib.request
import urllib.error
import json

base = 'http://127.0.0.1:8000'
pages = {
    'index': '/frontend/index.html',
    'login': '/frontend/login.html',
    'dashboard': '/frontend/dashboard.html',
    'upload': '/frontend/upload.html',
    'result': '/frontend/result.html',
    'history': '/frontend/history.html',
    'calendar': '/frontend/calendar.html',
    'settings': '/frontend/settings.html',
    'backtest': '/frontend/backtest.html',
    'journal': '/frontend/journal.html',
    'admin': '/frontend/admin.html',
    'strategy_factory': '/frontend/strategy_factory.html',
    'strategy_battle': '/frontend/strategy-battle.html',
    'ask_ai': '/frontend/ask-ai.html',
    'academy': '/frontend/academy.html',
    'heatmap': '/frontend/heatmap.html',
    'service_health': '/frontend/service-health.html',
}

api_paths = [
    ('health','/api/health'),
    ('pulse','/api/system/pulse'),
    ('strategies','/api/system/strategies'),
    ('personality','/api/system/personality'),
    ('recommendation_quick_XAUUSD','/api/recommendation/quick/XAUUSD'),
    ('recommendation_quick_BTCUSDT','/api/recommendation/quick/BTCUSDT'),
    ('trade_active','/api/trade/active'),
    ('trade_history','/api/trade/history'),
    ('calendar_events','/api/calendar/events'),
    ('scanner_status','/api/scanner/status'),
    ('sentiment_scan_XAUUSD','/api/sentiment/scan?symbol=XAUUSD'),
]

def fetch(url):
    info = {'url': url, 'status': None, 'error': None, 'body': ''}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            info['status'] = r.getcode()
            info['body'] = r.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        info['status'] = e.code
        try:
            info['body'] = e.read().decode('utf-8', errors='ignore')
        except Exception:
            info['body'] = ''
        info['error'] = f'HTTP {e.code}'
    except Exception as e:
        info['status'] = 'ERR'
        info['error'] = repr(e)
    return info

results = {'pages': {}, 'apis': {}}
for name,path in pages.items():
    results['pages'][name] = fetch(base + path)
for name,path in api_paths:
    results['apis'][name] = fetch(base + path)
with open('page_api_check.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(json.dumps(results, indent=2, ensure_ascii=False))
