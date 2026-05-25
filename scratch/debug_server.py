import urllib.request
import sys

urls = [
    'http://127.0.0.1:8000/',
    'http://127.0.0.1:8000/api/health',
    'http://127.0.0.1:8000/login.html',
]

for url in urls:
    print("Testing URL:", url)
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        res = urllib.request.urlopen(req, timeout=5)
        print("  Status:", res.status)
        print("  Headers:", dict(res.headers))
        print("  Body snippet:", res.read()[:200])
    except Exception as e:
        print("  Error:", repr(e))
