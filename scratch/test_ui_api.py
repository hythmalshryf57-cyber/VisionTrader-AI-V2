import os
import re
import requests
import json
import time

FRONTEND_DIR = r"C:\Users\user\Desktop\visiontrader_ai\frontend"
BASE_URL = "http://127.0.0.1:8000"

report = []

def check(condition, msg_success, msg_fail):
    if condition:
        report.append(f"✅ {msg_success}")
        return True
    else:
        report.append(f"❌ {msg_fail}")
        return False

def read_html(filename):
    path = os.path.join(FRONTEND_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_login():
    html = read_html("login.html")
    report.append("--- login.html ---")
    check("dark-theme" in html or "bg" in html, "Design seems to have dark/space theme", "No dark/space theme found")
    check('id="email"' in html and 'id="password"' in html, "Email and Password fields exist", "Email/Password fields missing")
    check('id="loginBtn"' in html or 'تسجيل الدخول' in html, "Login button exists", "Login button missing")
    check('googleSignIn' in html or 'تسجيل الدخول بـ Google' in html, "Google Sign-In button exists", "Google Sign-In button missing")
    check('href="register.html"' in html, "Register link exists", "Register link missing")

def test_upload():
    html = read_html("upload.html")
    report.append("--- upload.html ---")
    # count links in sidebar
    # Side menu usually has nav-link class or something
    sidebar_links = re.findall(r'<a[^>]*class="[^"]*nav-link[^"]*"[^>]*>', html)
    if not sidebar_links:
        sidebar_links = re.findall(r'<a[^>]*href="[^"]*"[^>]*>\s*<i', html)
    check(len(sidebar_links) == 4, f"Sidebar has 4 links (found {len(sidebar_links)})", f"Sidebar does not have 4 links (found {len(sidebar_links)})")
    
    check('id="dropZone"' in html or 'drag' in html.lower() or 'drop' in html.lower(), "Drag and Drop area exists", "Drag and Drop missing")
    check('id="market"' in html or 'marketSelect' in html, "Market dropdown exists", "Market dropdown missing")
    check('id="timeframe"' in html or 'timeframeSelect' in html, "Timeframe dropdown exists", "Timeframe dropdown missing")
    check('id="analyzeBtn"' in html or 'ابدأ التحليل' in html, "Start Analysis button exists", "Start Analysis button missing")
    check('scanner' in html.lower() or 'laser' in html.lower() or 'scan-line' in html.lower() or 'scan-effect' in html.lower() or 'scanning' in html.lower(), "Laser scanner effect exists", "Laser scanner effect missing")
    check("result.html" in html, "Redirects to result.html", "No redirection to result.html found")

def test_result():
    html = read_html("result.html")
    report.append("--- result.html ---")
    check('recommendation' in html.lower() or 'التوصية' in html, "Recommendation exists", "Recommendation missing")
    check('confidence' in html.lower() or 'الثقة' in html, "Confidence exists", "Confidence missing")
    check('entry' in html.lower() or 'الدخول' in html, "Entry area exists", "Entry area missing")
    check('target' in html.lower() or 'الهدف' in html or 'أهداف' in html, "Targets exist", "Targets missing")
    check('stop' in html.lower() or 'وقف' in html, "Stop loss exists", "Stop loss missing")
    check('thesis' in html.lower() or 'أطروحة' in html, "Market thesis exists", "Market thesis missing")
    check('accept' in html.lower() or 'موافق' in html or 'acceptBtn' in html, "Accept button exists", "Accept button missing")
    check('reject' in html.lower() or 'رافض' in html or 'rejectBtn' in html, "Reject button exists", "Reject button missing")
    check('pdf' in html.lower() or 'pdfBtn' in html, "PDF button exists", "PDF button missing")
    check('share' in html.lower() or 'مشاركة' in html or 'shareBtn' in html, "Share button exists", "Share button missing")

def test_history():
    html = read_html("history.html")
    report.append("--- history.html ---")
    check('history' in html.lower() or 'السابقة' in html or 'تحليلات' in html, "Previous analyses visible", "Previous analyses missing")
    check('filter' in html.lower() or 'فلتر' in html or 'بحث' in html, "Filtering exists", "Filtering missing")
    check('expand' in html.lower() or 'توسيع' in html or 'تفاصيل' in html or 'details' in html.lower(), "Expand exists", "Expand missing")

def test_settings():
    html = read_html("settings.html")
    report.append("--- settings.html ---")
    check('setting' in html.lower() or 'إعدادات' in html, "User settings exist", "User settings missing")
    check('language' in html.lower() or 'لغة' in html or 'lang' in html.lower(), "Change language exists", "Change language missing")
    check('mode' in html.lower() or 'وضع التداول' in html or 'tradingMode' in html, "Trading mode exists", "Trading mode missing")
    check('theme' in html.lower() or 'dark' in html.lower() or 'مظهر' in html, "Dark/Light mode exists", "Dark/Light mode missing")

def test_dashboard():
    html = read_html("dashboard.html")
    report.append("--- dashboard.html ---")
    check('api' in html.lower() or 'fetch(' in html or 'axios' in html, "Stats fetch from API", "No API call for stats found")
    check('ticker' in html.lower() or 'شريط' in html or 'marquee' in html, "News Ticker exists", "News Ticker missing")
    check('watchlist' in html.lower() or 'قائمة' in html, "Watchlist exists", "Watchlist missing")
    check('session' in html.lower() or 'جلسة' in html or 'timer' in html.lower() or 'عداد' in html, "Session timer exists", "Session timer missing")

def test_strategy():
    html = read_html("strategy_factory.html")
    report.append("--- strategy_factory.html ---")
    check('api' in html.lower() or 'fetch(' in html, "Strategies fetch from API", "No API call for strategies found")
    check('slider' in html.lower() or 'range' in html.lower() or 'وزن' in html, "Weight slider exists", "Weight slider missing")
    check('save' in html.lower() or 'حفظ' in html, "Save button exists", "Save button missing")

def test_backtest():
    html = read_html("backtest.html")
    report.append("--- backtest.html ---")
    check('market' in html.lower() or 'سوق' in html, "Market select exists", "Market select missing")
    check('timeframe' in html.lower() or 'فريم' in html, "Timeframe select exists", "Timeframe select missing")
    check('date' in html.lower() or 'تاريخ' in html, "Dates select exists", "Dates select missing")
    check('start' in html.lower() or 'بدء الاختبار' in html or 'startBtn' in html, "Start test button exists", "Start test button missing")
    check('result' in html.lower() or 'نتائج' in html, "Results area exists", "Results area missing")
    check('monte carlo' in html.lower() or 'مونت كارلو' in html, "Monte Carlo exists", "Monte Carlo missing")

def test_others():
    pages = ["journal.html", "calendar.html", "admin.html", "ask-ai.html", "heatmap.html", "academy.html", "service-health.html", "evolution.html", "realtime.html", "api-docs.html", "strategy-battle.html", "admin-engine.html"]
    report.append("--- Other pages ---")
    for p in pages:
        path = os.path.join(FRONTEND_DIR, p)
        check(os.path.exists(path), f"{p} exists", f"{p} does NOT exist")

test_login()
test_upload()
test_result()
test_history()
test_settings()
test_dashboard()
test_strategy()
test_backtest()
test_others()

print("\n".join(report))
