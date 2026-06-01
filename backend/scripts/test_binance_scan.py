import os
import sys
import requests

TOKEN = os.environ.get('TEST_TOKEN')
if not TOKEN:
    print('TEST_TOKEN env var not set')
    sys.exit(2)

url = 'http://127.0.0.1:8000/api/binance/scan?symbol=BTCUSDT'
try:
    r = requests.get(url, headers={'Authorization': f'Bearer {TOKEN}'}, timeout=15)
    print('STATUS', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
except Exception as e:
    print('ERROR', e)
