import json, urllib.request, urllib.error, sys

def post_json(url, payload, headers=None):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.getcode(), r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)

if __name__ == '__main__':
    login_payload = {"email": "normal_test_user@example.com", "password": "normalPassword123!"}
    code, login_res = post_json('http://127.0.0.1:8000/api/auth/login', login_payload, {'Content-Type':'application/json'})
    print('LOGIN:', code, login_res[:200])
    try:
        token = json.loads(login_res).get('access_token')
    except Exception as e:
        print('Failed to parse token', e)
        sys.exit(1)

    payload = {"market":"XAUUSD","timeframe":"1d","start_date":"2026-05-01","end_date":"2026-05-10"}
    headers = {'Content-Type':'application/json', 'Authorization':'Bearer ' + token}
    code, res = post_json('http://127.0.0.1:8000/api/backtest/run', payload, headers)
    print('BACKTEST:', code, res[:1000])
