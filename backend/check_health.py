import urllib.request

url = 'http://127.0.0.1:8000/api/health'
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        print(r.status)
        print(r.read().decode('utf-8'))
except Exception as e:
    print('ERROR', e)
