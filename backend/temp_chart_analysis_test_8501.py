import urllib.request
import urllib.error
import json

origin = 'http://127.0.0.1:8501'

try:
    login_data = json.dumps({'email': 'test@test.com', 'password': 'Test1234!'}).encode('utf-8')
    req = urllib.request.Request(origin + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        token = json.loads(r.read().decode())['access_token']
        print('LOGIN_OK')
except urllib.error.HTTPError as e:
    print('LOGIN_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
    raise
except Exception as e:
    print('LOGIN_ERR', e)
    raise

try:
    payload = {
        'market': 'XAUUSD',
        'visual_description': 'ذهب فريم ساعة، اتجاه صاعد، سعر 2685',
        'images': [],
        'chart_data': {
            'opens': [2678,2679,2681,2683,2682,2684,2685,2687,2686,2688,2689,2691,2690,2692,2691,2693,2694,2692,2695,2685],
            'highs': [2680,2682,2684,2685,2684,2686,2688,2689,2688,2690,2692,2693,2692,2694,2693,2695,2696,2694,2696,2696],
            'lows': [2675,2678,2679,2681,2680,2682,2683,2685,2684,2686,2687,2689,2688,2690,2689,2691,2692,2690,2691,2682],
            'closes': [2679,2681,2683,2682,2684,2685,2687,2686,2688,2689,2691,2690,2692,2691,2693,2694,2692,2695,2685,2685],
            'volumes': [1200,1350,1100,1400,1250,1500,1600,1450,1700,1800,1900,1750,2000,1850,2100,1950,1800,1700,1600,1500],
            'timestamps': ["2024-01-15T08:00:00","2024-01-15T09:00:00","2024-01-15T10:00:00","2024-01-15T11:00:00","2024-01-15T12:00:00","2024-01-15T13:00:00","2024-01-15T14:00:00","2024-01-15T15:00:00","2024-01-15T16:00:00","2024-01-15T17:00:00","2024-01-15T18:00:00","2024-01-15T19:00:00","2024-01-15T20:00:00","2024-01-15T21:00:00","2024-01-15T22:00:00","2024-01-15T23:00:00","2024-01-16T00:00:00","2024-01-16T01:00:00","2024-01-16T02:00:00","2024-01-16T03:00:00"],
            'support_levels': [2678, 2682],
            'resistance_levels': [2692, 2700],
            'candle_patterns': ['Bullish Engulfing', 'Morning Star'],
            'trend': 'صاعد',
            'raw_text': ['ذهب', 'فريم ساعة', 'اتجاه صاعد', 'Bullish Engulfing', 'دعم 2678', 'مقاومة 2692', 'RSI 62', 'Bollinger يتوسع', 'MACD تقاطع إيجابي']
        }
    }
    analysis_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(origin + '/api/analysis/process', data=analysis_data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        print('ANALYSIS_STATUS', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('ANALYSIS_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
    raise
except Exception as e:
    print('ANALYSIS_ERR', e)
    raise
