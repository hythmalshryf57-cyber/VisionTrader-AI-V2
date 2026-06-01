import requests, base64, os
BASE='http://127.0.0.1:8000'
email='testuser@example.com'
password='TestPass123!'

s = requests.Session()
# login
r = s.post(f"{BASE}/api/auth/login", json={'email': email, 'password': password})
print('login', r.status_code)
if r.status_code!=200:
    print(r.text); raise SystemExit(1)
token = r.json().get('access_token')
headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

img_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'file.jpe')
if not os.path.exists(img_path):
    print('image not found', img_path)
    raise SystemExit(1)
with open(img_path, 'rb') as f:
    b = base64.b64encode(f.read()).decode('ascii')

payload = {
    'market': 'XAUUSD',
    'timeframe': '1H',
    'images': [{'name': 'file.jpe', 'data': 'data:image/jpeg;base64,'+b}],
    'visual_description': 'Test analysis upload from automated script.'
}

r2 = s.post(f"{BASE}/api/analysis/process", json=payload, headers=headers, timeout=30)
print('analysis status', r2.status_code)
try:
    print(r2.json())
except Exception:
    print(r2.text)
