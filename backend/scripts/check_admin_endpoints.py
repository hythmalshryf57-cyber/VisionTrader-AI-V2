import sys, urllib.request, json

def get(path, token):
    req = urllib.request.Request('http://127.0.0.1:8000' + path, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read().decode()
            print('===', path, 'STATUS', r.status)
            try:
                print(json.dumps(json.loads(content), indent=2, ensure_ascii=False))
            except Exception:
                print(content[:1000])
    except Exception as e:
        print('===', path, 'ERROR', e)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_admin_endpoints.py <token>')
        sys.exit(1)
    token = sys.argv[1]
    for p in ['/api/admin/stats', '/api/admin/users', '/api/admin/soc-dashboard', '/api/admin/invite-codes', '/api/admin/security-logs']:
        get(p, token)
