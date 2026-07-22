import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')

base = 'http://localhost:8000'

# Step 1: Login
print('=== Step 1: Login ===')
login_data = {
    'email': 'test102030m@gmail.com',
    'password': 'DevAdminPass!2026_ZuENK5cAZIg'
}
r = requests.post(f'{base}/api/auth/login', json=login_data, timeout=10)
print(f'Login status: {r.status_code}')
if r.status_code != 200:
    print('Login failed:', r.text[:500])
    sys.exit(1)

token = r.json().get('access_token')
print(f'Token received: {token[:30]}...')

headers = {'Authorization': f'Bearer {token}'}

# Step 2: Send analysis request for XAUUSD (Gold)
print()
print('=== Step 2: Sending XAUUSD Analysis ===')
analysis_payload = {
    'market': 'XAUUSD',
    'visual_description': 'Gold chart showing uptrend on H4, price above 200 EMA, RSI at 62, support at 2380',
    'chart_data': {
        'closes': [2350, 2355, 2360, 2368, 2375, 2380, 2385, 2390],
        'highs':  [2355, 2360, 2365, 2375, 2382, 2388, 2392, 2396],
        'lows':   [2348, 2352, 2358, 2362, 2370, 2375, 2380, 2385],
        'volumes': [1200, 1300, 1100, 1400, 1500, 1600, 1450, 1550],
        'trend': 'bullish',
        'support_levels': [2360, 2375],
        'resistance_levels': [2400, 2420],
        'candle_patterns': ['bullish_engulfing', 'hammer'],
    },
    'images': []
}

r = requests.post(
    f'{base}/api/analysis/process',
    json=analysis_payload,
    headers=headers,
    timeout=30
)
print(f'Analysis HTTP status: {r.status_code}')
result = r.json()

# Print results
print()
print('=' * 50)
print('       ANALYSIS RESULT - XAUUSD (Gold)')
print('=' * 50)
print(f'Recommendation : {result.get("recommendation", "N/A")}')
print(f'Confidence     : {result.get("confidence", "N/A")}%')
print(f'Strength       : {result.get("strength", "N/A")}')
reason = result.get("reason") or result.get("explanation") or "N/A"
print(f'Reason         : {str(reason)[:400]}')
if result.get('entry_zone'):
    print(f'Entry Zone     : {result.get("entry_zone")}')
if result.get('dynamic_targets'):
    print(f'Targets        : {result.get("dynamic_targets")}')
if result.get('cluster_breakdown'):
    print(f'Clusters       : {result.get("cluster_breakdown")}')
print()

# Step 3: Test EURUSD
print('=== Step 3: Sending EURUSD Analysis ===')
analysis_payload2 = {
    'market': 'EURUSD',
    'visual_description': 'EURUSD showing bearish pattern, price below 50 EMA, RSI at 38, resistance at 1.085',
    'chart_data': {
        'closes': [1.092, 1.090, 1.088, 1.086, 1.084, 1.083, 1.082, 1.080],
        'highs':  [1.094, 1.092, 1.090, 1.088, 1.086, 1.085, 1.084, 1.082],
        'lows':   [1.090, 1.088, 1.086, 1.084, 1.082, 1.081, 1.080, 1.078],
        'volumes': [900, 850, 1100, 1200, 950, 1050, 980, 1300],
        'trend': 'bearish',
        'support_levels': [1.075, 1.070],
        'resistance_levels': [1.085, 1.090],
        'candle_patterns': ['bearish_engulfing'],
    },
    'images': []
}
r2 = requests.post(
    f'{base}/api/analysis/process',
    json=analysis_payload2,
    headers=headers,
    timeout=30
)
result2 = r2.json()
print(f'HTTP: {r2.status_code}')
print(f'Recommendation : {result2.get("recommendation", "N/A")}')
print(f'Confidence     : {result2.get("confidence", "N/A")}%')
print()
print('ALL TESTS DONE!')
