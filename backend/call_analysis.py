import urllib.request, urllib.error, json
origin = 'http://127.0.0.1:8000'
try:
    data = json.dumps({'email':'test@test.com','password':'Test1234!'}).encode('utf-8')
    req = urllib.request.Request(origin + '/api/auth/login', data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        token = json.loads(r.read().decode())['access_token']
        print('TOKEN_OK')
except Exception as e:
    print('LOGIN_ERR', e)
    raise
try:
    payload = {'market':'TEST_MARKET','images':[{'name':'test.png','data':'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='}], 'visual_description':'test'}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(origin + '/api/analysis/process', data=data, headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(req, timeout=20) as r:
        print('ANALYSIS_STATUS', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception as inner:
        print('BODY_ERR', inner)
except Exception as e:
    print('ERR', e)
