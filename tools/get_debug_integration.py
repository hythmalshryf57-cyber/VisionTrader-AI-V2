import requests
print(requests.get('http://127.0.0.1:8000/api/debug/integration').json())
