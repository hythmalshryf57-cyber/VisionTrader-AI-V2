import requests
BASE='http://127.0.0.1:8000'
email='testuser@example.com'
password='TestPass123!'

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={'email': email, 'password': password})
if r.status_code!=200:
    print('login failed', r.text); raise SystemExit(1)
headers={'Authorization': f"Bearer {r.json().get('access_token')}"}

# get latest analysis
la = s.get(f"{BASE}/api/analysis/latest", headers=headers)
print('latest analysis', la.status_code, la.text)
if la.status_code==200:
    anal = la.json()
    # add journal entry as user clicks OK
    je = {'market': anal.get('market'), 'recommendation': anal.get('recommendation') or 'تعليق', 'result': 'pending', 'pnl': 0}
    jresp = s.post(f"{BASE}/api/journal", json=je, headers=headers)
    print('journal add', jresp.status_code, jresp.text)

# fetch history
hist = s.get(f"{BASE}/api/journal", headers=headers)
print('history', hist.status_code, hist.text)

# update settings: change language to en and theme to light
prefs = {'language':'en','theme':'light'}
up = s.post(f"{BASE}/api/user/preferences", json=prefs, headers=headers)
print('update prefs', up.status_code, up.text)

# check preferences
gp = s.get(f"{BASE}/api/user/preferences", headers=headers)
print('get prefs', gp.status_code, gp.text)

# logout: there's no endpoint, so just finish
print('user flow done')
