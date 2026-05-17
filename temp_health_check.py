import urllib.request, sys
try:
    res = urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)
    print('STATUS', res.status)
    print(res.read().decode())
except Exception as e:
    print('ERROR', repr(e))
    sys.exit(1)
