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
    payload = {'url': 'https://www.tradingview.com/chart/?symbol=OANDA%3AXAUUSD'}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(origin + '/api/tradingview/fetch', data=data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        print('FETCH_STATUS', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('FETCH_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
    raise
except Exception as e:
    print('FETCH_ERR', e)
    raise
