import requests

resp = requests.post('http://127.0.0.1:8000/api/auth/register', json={
    'email': 'admin@visiontrader.ai',
    'password': 'AdminPass123'
})
print(resp.status_code)
print(resp.text)
