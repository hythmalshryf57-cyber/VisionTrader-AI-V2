import json
import os
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"


def load_env_checks():
    from config import settings

    secret_ok = bool(settings.SECRET_KEY and settings.SECRET_KEY not in {"", "secret", "changeme", "default"})
    master_ok = bool(settings.MASTER_ENCRYPTION_KEY and settings.MASTER_ENCRYPTION_KEY not in {"", "secret", "changeme", "default"})
    telegram_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    telegram_configured = bool(telegram_token)
    admin_email = getattr(settings, "ADMIN_EMAIL", "")
    admin_password = getattr(settings, "ADMIN_PASSWORD", "")

    return {
        "SECRET_KEY_present": secret_ok,
        "MASTER_ENCRYPTION_KEY_present": master_ok,
        "TELEGRAM_BOT_TOKEN_present": telegram_configured,
        "ADMIN_EMAIL_present": bool(admin_email),
        "ADMIN_PASSWORD_present": bool(admin_password),
        "SECRET_KEY_value": settings.SECRET_KEY,
    }


def safe_get(path, headers=None, params=None, timeout=20):
    try:
        r = requests.get(BASE_URL + path, headers=headers or {}, params=params or {}, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body
    except Exception as exc:
        return "ERR", str(exc)


def safe_post(path, headers=None, json_payload=None, timeout=30):
    try:
        r = requests.post(BASE_URL + path, headers=headers or {}, json=json_payload or {}, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body
    except Exception as exc:
        return "ERR", str(exc)


def create_report_entry(name, status, payload=None, response=None, error=None):
    return {
        "name": name,
        "status": status,
        "payload": payload,
        "response": response,
        "error": error,
    }


def print_result(entry):
    print("===", entry["name"], "===")
    print("status:", entry["status"])
    if entry["payload"] is not None:
        print("payload:", entry["payload"])
    if entry["response"] is not None:
        print("response:", entry["response"])
    if entry["error"] is not None:
        print("error:", entry["error"])
    print()


def test_root_pages():
    pages = [
        "/",
        "/index.html",
        "/login.html",
        "/dashboard.html",
        "/journal.html",
        "/backtest.html",
        "/admin.html",
        "/strategy_factory.html",
    ]
    results = []
    for page in pages:
        status, body = safe_get(page, timeout=15)
        valid_html = status == 200 and "<html" in str(body).lower()
        results.append({"page": page, "status": status, "valid_html": valid_html, "body_snippet": str(body)[:180]})
    return results


def websocket_check():
    try:
        import asyncio
        import websockets
    except Exception as exc:
        return False, f"websockets unavailable: {exc}"

    async def run():
        uri = "ws://127.0.0.1:8000/ws/live"
        try:
            async with websockets.connect(uri) as ws:
                await ws.send("ping")
                msg = await ws.recv()
                return True, msg
        except Exception as exc:
            return False, str(exc)

    try:
        result = asyncio.run(run())
        return result
    except Exception as exc:
        return False, str(exc)


def check_services():
    services = {}

    # Telegram service config
    from services.telegram_service import telegram_service
    services["telegram_enabled"] = bool(telegram_service.bot_token and telegram_service._resolve_chat_id(None))
    services["telegram_token"] = telegram_service.bot_token
    services["telegram_chat_id"] = telegram_service._resolve_chat_id(None)

    # Self-healing availability
    try:
        import services.self_healing as sh
        services["self_healing_available"] = hasattr(sh, "SelfHealing") or hasattr(sh, "self_healing")
    except Exception as exc:
        services["self_healing_available"] = False
        services["self_healing_error"] = str(exc)

    # Degradation watcher availability
    try:
        import services.degradation_watcher as dw
        services["degradation_watcher_available"] = hasattr(dw, "DegradationWatcher")
        services["degradation_watcher_pipeline"] = getattr(dw, "_EVOLUTION_PIPELINE_AVAILABLE", False)
    except Exception as exc:
        services["degradation_watcher_available"] = False
        services["degradation_watcher_error"] = str(exc)

    return services


def run_validation():
    report = []
    report.append(create_report_entry("Server available", *safe_get("/api/health")))

    env_checks = load_env_checks()
    report.append(create_report_entry("Environment secret checks", "OK", None, env_checks))

    # Public system checks
    for path in ["/api/system/pulse", "/api/system/strategies"]:
        report.append(create_report_entry(path, *safe_get(path)))

    # User flow: register -> login
    test_email = f"visiontrader_test_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "TestPass123!"
    status, body = safe_post("/api/auth/register", json_payload={"email": test_email, "password": test_password})
    report.append(create_report_entry("Register new user", status, {"email": test_email}, body if status == 200 else None))
    if status != 200:
        report.append(create_report_entry("Register fallback login", *safe_post("/api/auth/login", json_payload={"email": test_email, "password": test_password})))

    status, body = safe_post("/api/auth/login", json_payload={"email": test_email, "password": test_password})
    report.append(create_report_entry("Login new user", status, {"email": test_email}, body))
    user_token = body.get("access_token") if isinstance(body, dict) else None
    user_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

    # User endpoints
    user_endpoints = [
        ("GET /api/calendar/events", "/api/calendar/events"),
        ("GET /api/calendar/high-impact", "/api/calendar/high-impact"),
        ("GET /api/user/preferences", "/api/user/preferences"),
        ("GET /api/market/session", "/api/market/session"),
        ("GET /api/trade/active", "/api/trade/active"),
        ("GET /api/protection/status", "/api/protection/status"),
        ("GET /api/daily-limits/status", "/api/daily-limits/status"),
    ]
    for name, path in user_endpoints:
        status, body = safe_get(path, headers=user_headers)
        report.append(create_report_entry(name, status, None, body))

    # Analysis flow
    analysis_payload = {"market": "XAUUSD", "timeframe": "1h", "notes": "Routine validation analysis"}
    status, body = safe_post("/api/analysis/process", headers=user_headers, json_payload=analysis_payload, timeout=60)
    report.append(create_report_entry("Process XAUUSD analysis", status, analysis_payload, body))
    analysis_id = None
    if isinstance(body, dict):
        analysis_id = body.get("analysis_id") or body.get("id")

    # Retrieve latest and by id if available
    status, body = safe_get("/api/analysis/latest", headers=user_headers)
    report.append(create_report_entry("Get latest analysis", status, None, body))
    if analysis_id:
        status, body = safe_get(f"/api/analysis/{analysis_id}", headers=user_headers)
        report.append(create_report_entry("Get analysis by id", status, {"analysis_id": analysis_id}, body))

    status, body = safe_get("/api/recommendation/quick/XAUUSD", headers=user_headers)
    report.append(create_report_entry("Quick recommendation XAUUSD", status, None, body))

    # Journal and preferences
    status, body = safe_get("/api/journal", headers=user_headers)
    report.append(create_report_entry("Journal list before", status, None, body))
    journal_payload = {"market": "XAUUSD", "result": "win", "notes": "Validation entry", "date": "2026-06-01"}
    status, body = safe_post("/api/journal", headers=user_headers, json_payload=journal_payload)
    report.append(create_report_entry("Journal add", status, journal_payload, body))
    status, body = safe_get("/api/journal", headers=user_headers)
    report.append(create_report_entry("Journal list after", status, None, body))

    prefs_payload = {"theme": "light", "language": "en", "favorite_strategies": ["momentum", "macro"]}
    status, body = safe_post("/api/user/preferences", headers=user_headers, json_payload=prefs_payload)
    report.append(create_report_entry("Update preferences", status, prefs_payload, body))
    status, body = safe_get("/api/user/preferences", headers=user_headers)
    report.append(create_report_entry("Get preferences", status, None, body))

    # Service checks - auto scanner, footprint, websocket
    status, body = safe_get("/api/scanner/status", headers=user_headers)
    report.append(create_report_entry("Scanner status", status, None, body))
    status, body = safe_get("/api/scanner/alerts", headers=user_headers)
    report.append(create_report_entry("Scanner alerts", status, None, body))
    status, body = safe_get("/api/debug/integration", headers=user_headers)
    report.append(create_report_entry("Debug integration", status, None, body))

    ws_ok, ws_body = websocket_check()
    report.append(create_report_entry("WebSocket /ws/live", "OK" if ws_ok else "FAIL", None, ws_body if ws_ok else None, None if ws_ok else ws_body))

    page_results = test_root_pages()
    report.append(create_report_entry("Static frontend pages", "OK", None, page_results))

    service_info = check_services()
    report.append(create_report_entry("Service availability", "OK", None, service_info))

    # Admin scenario
    admin_email = "hythmalshryf57@gmail.com"
    admin_password = "hytham774790416m"
    status, body = safe_post("/api/auth/login", json_payload={"email": admin_email, "password": admin_password})
    report.append(create_report_entry("Admin login", status, {"email": admin_email}, body))
    admin_token = body.get("access_token") if isinstance(body, dict) else None
    admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

    admin_paths = [
        ("Admin system health", "/api/admin/system-health"),
        ("Admin users", "/api/admin/users"),
        ("Admin stats", "/api/admin/stats"),
        ("Admin security logs", "/api/admin/security-logs"),
        ("SOC dashboard", "/api/admin/soc-dashboard"),
        ("System strategies", "/api/system/strategies"),
        ("Calendar events", "/api/calendar/events"),
        ("Calendar high-impact", "/api/calendar/high-impact"),
        ("Journal list (admin)", "/api/journal"),
        ("Backtest run", "/api/backtest/run"),
        ("Manual tune weights", "/api/system/tune-weights"),
        ("System health details", "/api/system/health-details"),
    ]
    # run backtest separately with payload
    for name, path in admin_paths:
        if path == "/api/backtest/run":
            payload = {"market": "EURUSD", "timeframe": "1h", "start_date": "2026-01-01", "end_date": "2026-01-05", "initial_capital": 1000, "simulations": 5, "n_windows": 1}
            status, body = safe_post(path, headers=admin_headers, json_payload=payload, timeout=60)
            report.append(create_report_entry(name, status, payload, body))
        elif path == "/api/system/tune-weights":
            status, body = safe_post(path, headers=admin_headers, timeout=60)
            report.append(create_report_entry(name, status, None, body))
        else:
            status, body = safe_get(path, headers=admin_headers)
            report.append(create_report_entry(name, status, None, body))

    admin_page_results = []
    for page in ["/admin.html", "/strategy_factory.html", "/dashboard.html"]:
        status, body = safe_get(page, timeout=15)
        admin_page_results.append({"page": page, "status": status, "valid_html": status == 200 and "<html" in str(body).lower()})
    report.append(create_report_entry("Admin pages", "OK", None, admin_page_results))

    # Security code search for publish/auto deploy
    code_matches = []
    for root, _, files in os.walk(Path(__file__).resolve().parent):
        for file_name in files:
            if file_name.endswith(".py"):
                file_path = Path(root) / file_name
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().lower()
                    if "publish" in text or "auto deploy" in text or "deploy" in text:
                        if "api/" in text or "publish" in text:
                            code_matches.append(str(file_path))
    report.append(create_report_entry("Code publish/deploy scan", "OK", None, {"matches": code_matches[:20]}))

    with open("full_validation_results.json", "w", encoding="utf-8") as outfile:
        json.dump(report, outfile, indent=2, ensure_ascii=False)

    for entry in report:
        print_result(entry)

    return report


if __name__ == "__main__":
    run_validation()
