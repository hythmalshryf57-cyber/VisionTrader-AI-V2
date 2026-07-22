import requests, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

base = 'http://localhost:8001'

# Login
r = requests.post(f'{base}/api/auth/login',
    json={'email': 'test102030m@gmail.com', 'password': 'DevAdminPass!2026_ZuENK5cAZIg'},
    timeout=10)
print('Login:', r.status_code)
if r.status_code != 200:
    print(r.text)
    sys.exit(1)

token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Analysis request
payload = {
    'market': 'XAUUSD',
    'visual_description': 'Gold uptrend H4, RSI 62, support at 2380',
    'chart_data': {
        'closes': [2350, 2360, 2370, 2380, 2390],
        'highs': [2355, 2365, 2375, 2385, 2396],
        'lows': [2348, 2358, 2368, 2378, 2385],
        'volumes': [1200, 1300, 1100, 1400, 1550],
        'trend': 'bullish',
        'support_levels': [2360, 2375],
        'resistance_levels': [2400, 2420],
        'candle_patterns': ['bullish_engulfing'],
    },
    'images': []
}

print('Sending analysis...')
try:
    r2 = requests.post(f'{base}/api/analysis/process',
        json=payload, headers=headers, timeout=30)
    print('Status:', r2.status_code)
    print('Headers:', dict(r2.headers))
    print('Body:', r2.text[:5000])
except Exception as e:
    print('Request error:', e)
