import requests
import time
import json
import uuid

BASE_URL = "http://localhost:8000/api"

report = {"success": 0, "failed": 0, "errors": []}

def test_endpoint(method, url, data=None, headers=None, expected_status=200):
    try:
        if method.upper() == "GET":
            res = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            res = requests.post(url, json=data, headers=headers)
        else:
            raise ValueError("Unsupported method")
            
        if res.status_code == expected_status or (expected_status == 200 and str(res.status_code).startswith('2')):
            report["success"] += 1
            return res.json()
        else:
            report["failed"] += 1
            report["errors"].append(f"Failed {method} {url}: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        report["failed"] += 1
        report["errors"].append(f"Exception {method} {url}: {str(e)}")
        return None

# 1. Health
print("Testing Health...")
test_endpoint("GET", f"{BASE_URL}/health")

# 2. User Scenario
print("Testing User Scenario...")
test_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
test_password = "Password123!"

# Register
reg_res = test_endpoint("POST", f"{BASE_URL}/auth/register", data={
    "email": test_email,
    "password": test_password,
    "full_name": "Test User"
})

# Login
login_res = test_endpoint("POST", f"{BASE_URL}/auth/login", data={
    "email": test_email,
    "password": test_password
})

user_token = None
if login_res and "access_token" in login_res:
    user_token = login_res["access_token"]

if user_token:
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # Upload/Analyze (mocking base64 image or using the existing process endpoint)
    # The endpoint might require multipart/form-data. We will use dummy data if it accepts JSON.
    # Let's check /analysis/latest first
    test_endpoint("GET", f"{BASE_URL}/analysis/latest", headers=headers)
    
    # Preferences
    test_endpoint("GET", f"{BASE_URL}/user/preferences", headers=headers)

# 3. Admin Scenario
print("Testing Admin Scenario...")
admin_email = "hythmalshryf57@gmail.com"
admin_login = test_endpoint("POST", f"{BASE_URL}/auth/login", data={
    "email": admin_email,
    "password": "admin" # assuming default or we might need to check DB
})

admin_token = None
if admin_login and "access_token" in admin_login:
    admin_token = admin_login["access_token"]
elif admin_login is None:
    print("Admin login failed. Need to seed or find password.")

if admin_token:
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Dashboard
    test_endpoint("GET", f"{BASE_URL}/admin/system-health", headers=admin_headers)
    
    # Strategies
    test_endpoint("GET", f"{BASE_URL}/system/strategies", headers=admin_headers)

# Save Report
with open(r"C:\Users\user\Desktop\visiontrader_ai\api_test_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)
    
print(f"API Test Complete. Success: {report['success']}, Failed: {report['failed']}")
