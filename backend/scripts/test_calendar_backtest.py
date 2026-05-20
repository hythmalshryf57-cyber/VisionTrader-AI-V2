import json
import urllib.request
import urllib.error
from urllib.parse import urljoin

BASE = 'http://127.0.0.1:8000/'


def request(method, path, token=None, data=None):
    url = urljoin(BASE, path.lstrip('/'))
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            content = res.read()
            ct = res.headers.get_content_type()
            return res.status, content.decode('utf-8', errors='replace'), dict(res.headers)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        return e.code, body, dict(e.headers)
    except Exception as e:
        return None, str(e), {}


def print_result(name, status, body, headers=None):
    print(f'=== {name} ===')
    print('status:', status)
    if body:
        print('body:', body[:1000])
    else:
        print('body: <empty>')
    if headers:
        print('headers:', {k: headers.get(k) for k in ['Content-Type', 'Content-Length', 'WWW-Authenticate', 'Allow'] if headers.get(k)})
    print()


if __name__ == '__main__':
    status, body, headers = request('GET', '/calendar.html')
    print_result('GET /calendar.html', status, body, headers)
    status, body, headers = request('GET', '/backtest.html')
    print_result('GET /backtest.html', status, body, headers)
    status, body, headers = request('GET', '/api/health')
    print_result('GET /api/health', status, body, headers)

    login_payload = {'email': 'normal_test_user@example.com', 'password': 'normalPassword123!'}
    status, body, headers = request('POST', '/api/auth/login', data=login_payload)
    print_result('POST /api/auth/login', status, body, headers)
    token = None
    if status == 200:
        try:
            token = json.loads(body).get('access_token')
        except Exception:
            token = None

    if token:
        status, body, headers = request('GET', '/api/calendar/events?hours=24', token=token)
        print_result('GET /api/calendar/events', status, body, headers)
        bt_payload = {'market': 'BTC/USDT', 'timeframe': '1h', 'start_date': '2023-01-01', 'end_date': '2023-02-01'}
        status, body, headers = request('POST', '/api/backtest/run', token=token, data=bt_payload)
        print_result('POST /api/backtest/run', status, body, headers)
    else:
        print('Login failed, skipping protected API tests.')
