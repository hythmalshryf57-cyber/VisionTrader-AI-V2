import sys
import httpx
import json

BASE = "http://127.0.0.1:8501"
LOGIN = f"{BASE}/api/auth/login"
TV_FETCH = f"{BASE}/api/tradingview/fetch"
ANALYSIS_PROC = f"{BASE}/api/analysis/process"

EMAIL = "test@test.com"
PASSWORD = "Test1234!"
TV_URL = "https://www.tradingview.com/chart/?symbol=OANDA%3AXAUUSD"


def pretty(obj):
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def main():
    client = httpx.Client(timeout=60.0)

    print("1) تسجيل الدخول...")
    r = client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print("خطأ في تسجيل الدخول:", r.status_code, r.text)
        sys.exit(1)

    token = r.json().get("access_token")
    if not token:
        print("لم يُرجع توكن الوصول")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    print("تم تسجيل الدخول. أحصل على تحليل TradingView...")

    r2 = client.post(TV_FETCH, json={"url": TV_URL}, headers=headers)
    if r2.status_code != 200:
        print("خطأ عند جلب TradingView:", r2.status_code, r2.text)
    else:
        tv_json = None
        try:
            tv_json = r2.json()
        except Exception:
            print("رد غير JSON:", r2.text)
        print("--- /api/tradingview/fetch ---")
        print(pretty(tv_json))

        analysis_obj = None
        # Try to locate analysis in returned structure
        if isinstance(tv_json, dict):
            if 'analysis' in tv_json:
                analysis_obj = tv_json['analysis']
            elif 'result' in tv_json:
                analysis_obj = tv_json['result']
            else:
                analysis_obj = tv_json

        # Summarize common fields
        if isinstance(analysis_obj, dict):
            rec = analysis_obj.get('recommendation') or analysis_obj.get('recommend') or analysis_obj.get('label')
            conf = analysis_obj.get('confidence') or analysis_obj.get('score')
            note = analysis_obj.get('note') or analysis_obj.get('explanation') or analysis_obj.get('description')
            targets = analysis_obj.get('targets') or analysis_obj.get('take_profit') or analysis_obj.get('tps')
            stop = analysis_obj.get('stop') or analysis_obj.get('stop_loss')

            print('\nملخص التحليل:')
            print('توصية:', rec)
            print('ثقة:', conf)
            print('أهداف:', targets)
            print('وقف خسارة:', stop)
            print('شرح / ملاحظة:', note)

            # Attempt to call analysis process endpoint
            print('\n2) إرسال إلى /api/analysis/process ...')
            payload = {"market": "XAUUSD", "images": []}
            try:
                r3 = client.post(ANALYSIS_PROC, json=payload, headers=headers)
                if r3.status_code == 200:
                    print('رد /api/analysis/process:')
                    try:
                        print(pretty(r3.json()))
                    except Exception:
                        print(r3.text)
                else:
                    print('خطأ عند استدعاء /api/analysis/process:', r3.status_code, r3.text)
            except Exception as e:
                print('استثناء عند استدعاء /api/analysis/process:', e)
        else:
            print('لم يتم العثور على هيكل تحليل متوقع في رد TradingView.')


if __name__ == '__main__':
    main()
