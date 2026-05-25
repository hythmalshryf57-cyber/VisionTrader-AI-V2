import os
import urllib.request
import json

REQUIRED_PAGES = [
    'login.html', 'register.html', 'dashboard.html', 'upload.html', 'result.html', 
    'history.html', 'calendar.html', 'settings.html', 'backtest.html', 'journal.html', 
    'admin.html', 'strategy_factory.html', 'ask-ai.html', 'heatmap.html', 'academy.html', 
    'service-health.html', 'evolution.html', 'realtime.html', 'api-docs.html'
]

FRONTEND_DIR = r'C:\Users\user\Desktop\visiontrader_ai\frontend'

results = {}
all_passed = True

for page in REQUIRED_PAGES:
    file_path = os.path.join(FRONTEND_DIR, page)
    exists_locally = os.path.exists(file_path)
    
    server_status = None
    server_error = None
    if exists_locally:
        url = f'http://127.0.0.1:8000/{page}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=3)
            server_status = res.status
        except Exception as e:
            server_error = repr(e)
            all_passed = False
    else:
        all_passed = False
        
    results[page] = {
        'exists_locally': exists_locally,
        'size_bytes': os.path.getsize(file_path) if exists_locally else 0,
        'server_status': server_status,
        'server_error': server_error
    }

report = {
    'all_passed': all_passed,
    'results': results
}

print(json.dumps(report, indent=2))
with open(r'C:\Users\user\Desktop\visiontrader_ai\scratch\frontend_verification_results.json', 'w') as f:
    json.dump(report, f, indent=2)

if all_passed:
    print("ALL FRONTEND PAGES VERIFIED SUCCESSFULLY")
else:
    print("SOME FRONTEND PAGES FAILED VERIFICATION")
