import json
import urllib.request
import urllib.parse

LOGIN_URL = 'http://127.0.0.1:8000/api/auth/login'
AGENT_URL = 'http://127.0.0.1:8000/api/ai/agent'

login_data = json.dumps({'email': 'admin@example.com', 'password': 'ChangeThisAdminPassword2026!'}).encode('utf-8')
req = urllib.request.Request(LOGIN_URL, data=login_data, headers={'Content-Type': 'application/json'})
print('Logging in...')
with urllib.request.urlopen(req, timeout=20) as resp:
    body = json.loads(resp.read().decode('utf-8'))
    print('login status', resp.status)
    print(body)
    token = body.get('access_token')

if not token:
    raise RuntimeError('No access token returned')

post_data = urllib.parse.urlencode({'question': 'حلل الذهب'}).encode('utf-8')
req2 = urllib.request.Request(AGENT_URL, data=post_data, headers={
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': f'Bearer {token}'
})
print('Calling agent endpoint...')
with urllib.request.urlopen(req2, timeout=40) as resp:
    print('agent status', resp.status)
    print(resp.read().decode('utf-8'))
