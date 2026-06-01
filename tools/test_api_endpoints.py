import requests

BASE='http://127.0.0.1:8000'

user = {'email':'testuser@example.com','password':'TestPass123!'}
admin = {'email':'hythmalshryf57@gmail.com','password':'admin123!'}

# Helper

def auth_token(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    print('login', creds['email'], r.status_code)
    if r.status_code != 200:
        print(r.text)
        return None
    return r.json().get('access_token')

user_token = auth_token(user)
admin_token = auth_token(admin)

headers = {'Authorization': f'Bearer {user_token}'} if user_token else {}
admin_headers = {'Authorization': f'Bearer {admin_token}'} if admin_token else {}

endpoints = [
    ('health', '/api/health', {}),
    ('pulse', '/api/system/pulse', {}),
    ('latest', '/api/analysis/latest', headers),
    ('journal', '/api/journal', headers),
    ('prefs', '/api/user/preferences', headers),
    ('strategies', '/api/system/strategies', {}),
    ('calendar', '/api/calendar/events?hours=24', headers),
    ('market_session', '/api/market/session', headers),
    ('trade_active', '/api/trade/active', headers),
    ('protection', '/api/protection/status', headers),
    ('daily_limits', '/api/daily-limits/status', headers),
    ('scanner_status', '/api/scanner/status', headers),
    ('debug_integration', '/api/debug/integration', {}),
]

for name, path, hdr in endpoints:
    try:
        h = hdr or {}
        if path.startswith('/api/analysis/process'):
            r = requests.post(BASE+path, json={'market':'XAUUSD'}, headers=h, timeout=20)
        else:
            r = requests.get(BASE+path, headers=h, timeout=20)
        print(name, path, r.status_code, r.text[:200])
    except Exception as e:
        print('ERR', name, path, e)

# backtest
if admin_headers:
    bt = requests.post(BASE+'/api/backtest/run', json={'market':'XAUUSD','timeframe':'1H','start_date':'2024-01-01','end_date':'2024-01-10'}, headers=admin_headers, timeout=30)
    print('backtest', bt.status_code, bt.text[:400])

# static pages
for page in ['academy.html','admin-engine.html','admin.html','dashboard.html','upload.html']:
    try:
        r = requests.get(BASE+'/'+page, timeout=20)
        print('page', page, r.status_code, 'len', len(r.text))
    except Exception as e:
        print('page_err', page, e)
