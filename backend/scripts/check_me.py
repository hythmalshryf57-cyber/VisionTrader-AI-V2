import sys, urllib.request, json

def main(token):
    req = urllib.request.Request('http://127.0.0.1:8000/api/auth/me', headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req) as r:
        print(r.read().decode())

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_me.py <token>')
    else:
        main(sys.argv[1])
