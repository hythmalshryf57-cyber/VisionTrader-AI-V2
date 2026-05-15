import urllib.request
import urllib.error
from urllib.parse import urlparse

urls = [
    'http://localhost:8000/api/system/pulse',
    'http://localhost:8000/api/system/strategies',
    'http://localhost:8000/api/system/personality'
]

for u in urls:
    print('---')
    print('URL:', u)
    req = urllib.request.Request(u, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # Increased timeout to 30 seconds
            body = r.read().decode('utf-8')
            print('Status:', r.status)
            print('Body:', body)
    except urllib.error.HTTPError as e:
        print('Status:', e.code)
        print('Body:', e.read().decode('utf-8'))
    except Exception as e:
        print('Error:', type(e).__name__, e)
