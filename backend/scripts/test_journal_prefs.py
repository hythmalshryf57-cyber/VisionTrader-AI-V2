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
        with urllib.request.urlopen(req, timeout=60) as r:
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
    print('Logging in as admin...')
    code, res = request('POST', base + '/api/auth/login', {'email':'hythmalshryf57@gmail.com','password':'hytham774790416m'})
    print('LOGIN', code)
    if code != 200:
        print('Login failed:', res)
        sys.exit(1)
    token = res.get('access_token')
    if not token:
        print('No token in login response')
        sys.exit(1)
    print('Token obtained (truncated):', token[:20] + '...')

    print('\nGET /api/journal')
    code, journal = request('GET', base + '/api/journal', token=token)
    print('Status:', code)
    try:
        print('Entries count:', len(journal) if isinstance(journal, list) else 'not-list')
        if isinstance(journal, list) and journal:
            print('First entry sample:', json.dumps(journal[0], ensure_ascii=False)[:1000])
    except Exception as e:
        print('Journal response:', journal)

    print('\nGET /api/user/preferences (before)')
    code, prefs_before = request('GET', base + '/api/user/preferences', token=token)
    print('Status:', code, 'Prefs:', prefs_before)

    print('\nPOST /api/user/preferences -> set theme=light, language=en')
    new_prefs = {'theme':'light','language':'en'}
    code, post_res = request('POST', base + '/api/user/preferences', new_prefs, token=token)
    print('Status:', code, 'Response:', post_res)

    print('\nGET /api/user/preferences (after)')
    code, prefs_after = request('GET', base + '/api/user/preferences', token=token)
    print('Status:', code, 'Prefs:', prefs_after)
