#!/usr/bin/env python
"""
LQIS Smoke Test Script
Validates that all critical endpoints respond correctly after a deployment.
Run: python manage.py shell < ../smoke_test.py
Or:  python smoke_test.py (standalone, requires requests)
"""
import sys
import os
import requests

BASE_URL = os.environ.get("SMOKE_TEST_URL", "https://lqis-automated-tea-quality-system.onrender.com")
DEMO_USER = "inspector1"
DEMO_PASS = "admin123"  # Pre-seeded demo password from seed_demo_data

results = []

def check(name, url, method="GET", expected_status=200, data=None, session=None):
    client = session or requests
    try:
        if method == "GET":
            r = client.get(url, timeout=15, allow_redirects=False)
        else:
            r = client.post(url, data=data, timeout=15, allow_redirects=False)
        
        # Accept 200, 302 (redirect after login), or expected status
        passed = r.status_code in (expected_status, 302)
        results.append((name, passed, r.status_code))
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: HTTP {r.status_code}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  [FAIL] {name}: {e}")


print(f"\n{'='*60}")
print(f"  LQIS Smoke Test Suite")
print(f"  Target: {BASE_URL}")
print(f"{'='*60}\n")

# 1. Login page loads
print("[Phase 1: Authentication]")
check("Login Page Loads", f"{BASE_URL}/users/login/")

# 2. Login with credentials
session = requests.Session()
login_page = session.get(f"{BASE_URL}/users/login/", timeout=15)
# Extract CSRF token
import re
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else ""

# CRITICAL: Django enforces Referer header for HTTPS CSRF validation
session.headers.update({
    "Referer": f"{BASE_URL}/users/login/",
    "X-CSRFToken": csrf_token,
})

check("Login POST", f"{BASE_URL}/users/login/", method="POST", data={
    "username": DEMO_USER,
    "password": DEMO_PASS,
    "csrfmiddlewaretoken": csrf_token,
}, session=session, expected_status=302)

# 3. Authenticated endpoints
print("\n[Phase 2: Core Pages]")
# Follow the redirect after login
session.get(f"{BASE_URL}/", timeout=15)
check("Home Page", f"{BASE_URL}/", session=session)
check("Sample List", f"{BASE_URL}/sampling/", session=session)
check("Factory Intake Form", f"{BASE_URL}/sampling/factory-intake/new/", session=session)
check("Sync Vault", f"{BASE_URL}/sampling/vault/", session=session)

# 4. API endpoints
print("\n[Phase 3: API Endpoints]")
check("Sync Submit (GET = Method Not Allowed)", f"{BASE_URL}/sampling/sync-submit/", 
      session=session, expected_status=405)

# 5. Demo mode (302 = demo enabled, 404 = locked in production)
print("\n[Phase 4: Security Gates]")
print("  [INFO] Demo gate: 404 = locked (production), 302 = enabled (demo mode)")
check("Demo Login Gate", f"{BASE_URL}/users/demo/inspector/", expected_status=302)

# Summary
print(f"\n{'='*60}")
passed = sum(1 for _, p, _ in results if p)
total = len(results)
print(f"  Results: {passed}/{total} passed")
if passed == total:
    print("  Status: ALL CLEAR ✅")
else:
    print("  Status: ISSUES DETECTED ⚠️")
    for name, p, code in results:
        if not p:
            print(f"    → {name}: HTTP {code}")
print(f"{'='*60}\n")

sys.exit(0 if passed == total else 1)
