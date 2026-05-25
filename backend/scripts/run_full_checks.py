import urllib.request, json, re, urllib.error, os, glob, time
BASE='http://127.0.0.1:8000'
results={'apis':[], 'pages':[]}
# fetch openapi
try:
    openapi=json.loads(urllib.request.urlopen(BASE+'/openapi.json', timeout=10).read().decode('utf-8'))
except Exception as e:
    print('FAILED_FETCH_OPENAPI', e)
    raise
ops=[]
for path, methods in openapi.get('paths', {}).items():
    for method, meta in methods.items():
        ops.append((method.upper(), path, meta))

for method, path, meta in ops:
    test_path = path
    for param in meta.get('parameters', []):
        name = param.get('name')
        if '{'+name+'}' in test_path:
            test_path = test_path.replace('{'+name+'}', '1')
    if '{' in test_path:
        test_path = re.sub(r'{[^/]+}', '1', test_path)
    url = BASE + test_path
    req = urllib.request.Request(url, method=method)
    if method == 'POST':
        req.add_header('Content-Type', 'application/json')
        req.data = b'{}'
    status=None
    msg=''
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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
    results['apis'].append({'method':method,'path':path,'tested_path':test_path,'url':url,'status':status,'msg':msg})
    time.sleep(0.02)

# frontend pages
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
html_files = sorted(glob.glob(os.path.join(frontend_dir, '*.html')))
for f in html_files:
    filename = os.path.basename(f)
    url = BASE + '/' + filename
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        status = f'ERR:{type(e).__name__}'
    results['pages'].append({'file':filename, 'url':url, 'status':status})

# also test root /
try:
    with urllib.request.urlopen(BASE+'/', timeout=10) as resp:
        root_status = resp.status
except urllib.error.HTTPError as e:
    root_status = e.code
except Exception as e:
    root_status = f'ERR:{type(e).__name__}'
results['root'] = root_status

# write results
outp='backend/test_results.json'
with open(outp, 'w', encoding='utf-8') as w:
    json.dump(results, w, ensure_ascii=False, indent=2)

# print summary
total_ops = len(results['apis'])
ok_2xx = sum(1 for a in results['apis'] if isinstance(a['status'], int) and 200 <= a['status'] < 300)
responded = sum(1 for a in results['apis'] if isinstance(a['status'], int))
errs = [a for a in results['apis'] if (isinstance(a['status'], str) and a['status'].startswith('ERR')) or (isinstance(a['status'], int) and a['status'] >= 500)]
print(json.dumps({'total_ops':total_ops,'ok_2xx':ok_2xx,'responded':responded,'errors_count':len(errs)}, ensure_ascii=False))
for e in errs[:50]:
    print('ERROR', e['method'], e['path'], e['status'], e['msg'])

# pages summary
total_pages = len(results['pages'])
pages_ok = sum(1 for p in results['pages'] if isinstance(p['status'], int) and p['status']==200)
print(json.dumps({'total_pages':total_pages,'pages_ok':pages_ok,'root_status':results['root']}, ensure_ascii=False))
for p in results['pages']:
    if not (isinstance(p['status'], int) and p['status']==200):
        print('PAGE_ISSUE', p['file'], p['status'])
print('WROTE', outp)
