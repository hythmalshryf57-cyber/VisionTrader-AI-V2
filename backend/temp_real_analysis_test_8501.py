import urllib.request
import urllib.error
import json

origin = 'http://127.0.0.1:8501'

try:
    login_data = json.dumps({'email': 'test@test.com', 'password': 'Test1234!'}).encode('utf-8')
    req = urllib.request.Request(origin + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        token = json.loads(r.read().decode())['access_token']
        print('LOGIN_OK')
except urllib.error.HTTPError as e:
    print('LOGIN_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
    raise
except Exception as e:
    print('LOGIN_ERR', e)
    raise

try:
    payload = {
        'market': 'XAUUSD',
        'visual_description': 'ذهب فريم ساعة، اتجاه صاعد، سعر 2685، شموع Bullish Engulfing، دعم 2678، مقاومة 2692، Bollinger يتوسع، RSI عند 62',
        'images': []
    }
    analysis_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(origin + '/api/analysis/process', data=analysis_data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        print('ANALYSIS_STATUS', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('ANALYSIS_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
    raise
except Exception as e:
    print('ANALYSIS_ERR', e)
    raise
