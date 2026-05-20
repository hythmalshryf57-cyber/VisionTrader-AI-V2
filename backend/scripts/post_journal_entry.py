import json, urllib.request, urllib.error, sys

def request(method, url, payload=None, token=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode('utf-8')
            try:
                return r.getcode(), json.loads(txt)
            except Exception:
                return r.getcode(), txt
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8')
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, txt
    except Exception as e:
        return 0, str(e)

if __name__ == '__main__':
    base = 'http://127.0.0.1:8000'
    # login
    code, res = request('POST', base + '/api/auth/login', {'email':'normal_test_user@example.com','password':'normalPassword123!'})
    if code != 200:
        print('Login failed', code, res)
        sys.exit(1)
    token = res.get('access_token')
    print('Logged in, token truncated:', token[:20] + '...')

    # post journal entry
    payload = {'market':'XAUUSD','recommendation':'شراء','result':'ربح','pnl':12.5,'notes':'اختبار إدخال دفتر يوميات'}
    code, resp = request('POST', base + '/api/journal', payload, token)
    print('POST /api/journal', code, resp)

    # get journal
    code, journal = request('GET', base + '/api/journal', token=token)
    print('GET /api/journal', code, 'count=', len(journal) if isinstance(journal, list) else 'n/a')
    if isinstance(journal, list):
        print('Latest entry sample:', json.dumps(journal[0], ensure_ascii=False)[:500])
