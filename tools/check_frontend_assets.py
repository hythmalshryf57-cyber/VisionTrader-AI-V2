import requests
from bs4 import BeautifulSoup
import os

BASE = 'http://127.0.0.1:8000'
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

def check_page(path):
    url = f"{BASE}/{path}"
    try:
        r = requests.get(url, timeout=5)
    except Exception as e:
        return {'page': path, 'status': 'error', 'error': str(e)}
    if r.status_code != 200:
        return {'page': path, 'status': 'http_error', 'code': r.status_code}
    soup = BeautifulSoup(r.text, 'html.parser')
    assets = []
    for tag in soup.find_all(['script','link','img']):
        if tag.name == 'script' and tag.get('src'):
            assets.append(tag.get('src'))
        if tag.name == 'link' and tag.get('href'):
            assets.append(tag.get('href'))
        if tag.name == 'img' and tag.get('src'):
            assets.append(tag.get('src'))
    asset_results = []
    for a in assets:
        if a.startswith('http'):
            test_url = a
        else:
            test_url = BASE + ('/' + a.lstrip('/'))
        try:
            ra = requests.head(test_url, timeout=5)
            code = ra.status_code
        except Exception:
            try:
                ra = requests.get(test_url, timeout=5)
                code = ra.status_code
            except Exception as e:
                asset_results.append({'asset': a, 'status': 'error', 'error': str(e)})
                continue
        asset_results.append({'asset': a, 'status': 'ok' if 200 <= code < 300 else 'http_error', 'code': code})
    return {'page': path, 'status': 'ok', 'assets': asset_results}


def main():
    pages = [f for f in os.listdir(FRONTEND_DIR) if f.endswith('.html')]
    results = []
    for p in pages:
        print('Checking', p)
        res = check_page(p)
        results.append(res)
    import json
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
