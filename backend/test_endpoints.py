import urllib.request

urls = [
    'http://localhost:8000/api/system/pulse',
    'http://localhost:8000/api/system/strategies',
    'http://localhost:8000/api/system/personality'
]
for u in urls:
    req = urllib.request.Request(u, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode('utf-8')
            print('URL:', u)
            print('Status:', r.status)
            print('Body:', body)
    except Exception as e:
        print('URL:', u)
        print('Error:', type(e).__name__, e)
