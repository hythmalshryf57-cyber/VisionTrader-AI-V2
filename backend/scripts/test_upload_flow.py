import json, urllib.request, urllib.error, sys

def post_json(url, payload, headers=None):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8')
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    login_payload = {"email": "normal_test_user@example.com", "password": "normalPassword123!"}
    print('Logging in as normal user...')
    login_res = post_json('http://127.0.0.1:8000/api/auth/login', login_payload, {'Content-Type':'application/json'})
    print('LOGIN RESPONSE:', login_res[:1000])
    try:
        token = json.loads(login_res).get('access_token')
    except Exception as e:
        print('Failed to parse login response:', e)
        sys.exit(1)

    print('Token obtained, calling /api/auth/me')
    me = post_json('http://127.0.0.1:8000/api/auth/me', {}, {'Authorization':'Bearer ' + token})
    print('ME:', me[:1000])

    print('Submitting analysis request...')
    # tiny 1x1 PNG in base64
    b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
    payload = {"market":"XAUUSD","images":[{"name":"test.png","data":"data:image/png;base64,"+b64}]}
    headers = {'Content-Type':'application/json', 'Authorization':'Bearer ' + token}
    analysis_res = post_json('http://127.0.0.1:8000/api/analysis/process', payload, headers)
    print('ANALYSIS RESPONSE:', analysis_res[:2000])
