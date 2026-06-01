import sys
import requests
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

import time

BASE_URL = "http://127.0.0.1:8000"
test_user = {
    "email": f"testuser_{int(time.time())}@example.com",
    "password": "StrongPassword123!",
    "full_name": "Test User"
}

def print_result(name, res):
    print(f"=== {name} ===")
    print(f"Status: {res.status_code}")
    try:
        print(f"Response: {res.json()}")
    except:
        print(f"Response: {res.text}")
    print("\n")
    return res

print("1. Testing Registration...")
res_reg = requests.post(f"{BASE_URL}/api/auth/register", json=test_user)
print_result("Register", res_reg)

print("2. Testing Login...")
res_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
print_result("Login", res_login)

token = None
if res_login.status_code == 200:
    token = res_login.json().get("access_token")

headers = {"Authorization": f"Bearer {token}"} if token else {}

print("3. Testing System Pulse...")
print_result("System Pulse", requests.get(f"{BASE_URL}/api/system/pulse"))

print("4. Testing Analysis Latest...")
print_result("Analysis Latest", requests.get(f"{BASE_URL}/api/analysis/latest", headers=headers))

print("5. Testing Journal...")
print_result("Journal", requests.get(f"{BASE_URL}/api/journal", headers=headers))

print("6. Testing User Preferences...")
print_result("User Preferences", requests.get(f"{BASE_URL}/api/user/preferences", headers=headers))

print("7. Testing System Strategies...")
print_result("System Strategies", requests.get(f"{BASE_URL}/api/system/strategies", headers=headers))

print("8. Testing Calendar Events...")
print_result("Calendar Events", requests.get(f"{BASE_URL}/api/calendar/events", headers=headers))

print("9. Testing Market Session...")
print_result("Market Session", requests.get(f"{BASE_URL}/api/market/session", headers=headers))

print("10. Testing Trade Active...")
print_result("Trade Active", requests.get(f"{BASE_URL}/api/trade/active", headers=headers))

print("11. Testing Protection Status...")
print_result("Protection Status", requests.get(f"{BASE_URL}/api/protection/status", headers=headers))

print("12. Testing Daily Limits...")
print_result("Daily Limits", requests.get(f"{BASE_URL}/api/daily-limits/status", headers=headers))

# To test Admin, we might need an admin token. We will try with normal user first to see if it's protected properly.
print("13. Testing Admin System Health (should be forbidden if not admin)...")
print_result("Admin System Health", requests.get(f"{BASE_URL}/api/admin/system-health", headers=headers))
