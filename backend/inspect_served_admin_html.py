import urllib.request
text = urllib.request.urlopen('http://127.0.0.1:8000/admin.html', timeout=10).read().decode('utf-8')
print('displayStats in text:', 'displayStats' in text)
print('count function displayStats:', text.count('function displayStats'))
print('function displayStats present:', 'function displayStats' in text)
if 'function displayStats' in text:
    idx = text.index('function displayStats')
    print(text[idx-80:idx+200])
