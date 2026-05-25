import json
import urllib.request
from urllib.error import HTTPError

base = 'http://127.0.0.1:8000'
login_data = json.dumps({
    'email': 'copilot_test_user@local.example',
    'password': 'TestPassword123!'
}).encode('utf-8')
req = urllib.request.Request(base + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_data = json.loads(resp.read().decode('utf-8'))
        print('login', token_data)
except HTTPError as e:
    print('login error', e.code, e.read().decode('utf-8'))
    raise

headers = {'Authorization': 'Bearer ' + token_data['access_token']}
req = urllib.request.Request(base + '/api/admin/users', headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('admin users status', resp.status)
        print(resp.read().decode('utf-8')[:1000])
except HTTPError as e:
    print('admin users error', e.code, e.read().decode('utf-8'))
