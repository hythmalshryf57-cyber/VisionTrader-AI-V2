import urllib.request

url = 'http://127.0.0.1:8000/admin.html'
with urllib.request.urlopen(url, timeout=10) as r:
    text = r.read().decode('utf-8')
    print(text[:1200])
    print('----')
    print('displayStats' in text)
