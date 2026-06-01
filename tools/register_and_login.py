import requests
BASE='http://127.0.0.1:8000'
email='testuser@example.com'
password='TestPass123!'

r = requests.post(f"{BASE}/api/auth/register", json={'email': email, 'password': password})
print('register status', r.status_code, r.text)
if r.status_code == 200:
    token = r.json().get('access_token')
    print('access_token:', token)
else:
    # try login
    r2 = requests.post(f"{BASE}/api/auth/login", json={'email': email, 'password': password})
    print('login status', r2.status_code, r2.text)
    if r2.status_code==200:
        print('access_token:', r2.json().get('access_token'))
