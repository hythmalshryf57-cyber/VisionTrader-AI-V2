import urllib.request, json, re, urllib.error, time, os
BASE='http://127.0.0.1:8000'
admin_payload={'email':'hythmalshryf57@gmail.com','password':'hytham774790416m'}
print('Logging in...')
try:
    data=json.dumps(admin_payload).encode()
    req=urllib.request.Request(BASE+'/api/auth/login', data=data, headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        body=json.loads(resp.read().decode('utf-8'))
        token=body.get('access_token')
        if not token:
            print('NO_TOKEN_IN_RESPONSE', body)
            raise SystemExit(1)
        print('Got token (len):', len(token))
except urllib.error.HTTPError as e:
    print('LOGIN_HTTP', e.code, e.read().decode())
    raise
except Exception as e:
    print('LOGIN_ERR', type(e).__name__, e)
    raise

# load openapi
try:
    openapi=json.loads(urllib.request.urlopen(BASE+'/openapi.json', timeout=10).read().decode('utf-8'))
except Exception as e:
    print('FAILED_FETCH_OPENAPI', e)
    raise

ops=[]
for path, methods in openapi.get('paths', {}).items():
    for method, meta in methods.items():
        ops.append((method.upper(), path, meta))

results={'apis':[]}
headers={'Authorization': f'Bearer {token}'}

for method, path, meta in ops:
    test_path = path
    for param in meta.get('parameters', []):
        name = param.get('name')
        if '{'+name+'}' in test_path:
            test_path = test_path.replace('{'+name+'}', '1')
    if '{' in test_path:
        test_path = re.sub(r'{[^/]+}', '1', test_path)
    url = BASE + test_path
    req_headers = {'Authorization': f'Bearer {token}'}
    req = urllib.request.Request(url, method=method, headers=req_headers)
    if method == 'POST':
        req.add_header('Content-Type', 'application/json')
        req.data = b'{}'
    status=None
    msg=''
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            body = resp.read(500).decode('utf-8', errors='replace')
            msg = body.replace('\n',' ')[:300]
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read(500).decode('utf-8', errors='replace')
            msg = body.replace('\n',' ')[:300]
        except:
            msg = str(e)
    except Exception as e:
        status = f'ERR:{type(e).__name__}'
        msg = str(e)
    rec={'method':method,'path':path,'tested_path':test_path,'url':url,'status':status,'msg':msg}
    results['apis'].append(rec)
    print(method, path, status)
    time.sleep(0.02)

outp='backend/test_results_with_token.json'
with open(outp,'w',encoding='utf-8') as w:
    json.dump(results,w,ensure_ascii=False,indent=2)

# compute unique paths and OK
paths={}
for a in results['apis']:
    paths.setdefault(a['path'],[]).append(a)
unique=len(paths)
ok_paths=sum(1 for p,ops in paths.items() if any(isinstance(o['status'],int) and 200<=o['status']<300 for o in ops))
print('\nSUMMARY:', 'unique_paths=', unique, 'ok_with_token=', ok_paths)
print('WROTE', outp)
