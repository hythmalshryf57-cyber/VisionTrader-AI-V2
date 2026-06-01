import requests
BASE='http://127.0.0.1:8000'
email='testuser@example.com'
password='TestPass123!'

r=requests.post(f'{BASE}/api/auth/login', json={'email':email,'password':password})
print('login', r.status_code, r.text)
if r.status_code!=200:
    raise SystemExit(1)
tok=r.json().get('access_token')
headers={'Authorization':f'Bearer {tok}'}
for path in ['/api/analysis/latest', '/api/analysis/1']:
    r=requests.get(BASE+path, headers=headers)
    print(path, r.status_code)
    print(r.text)
