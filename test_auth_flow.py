import requests
import json

BASE = "http://localhost:5173"

session = requests.Session()

# Step 1: Get CSRF token
r = session.get(f"{BASE}/api/security/csrf-token")
csrf = r.json().get("csrf_token")
print(f"1. CSRF token: {csrf[:20]}...")

# Step 2: Login
r = session.post(f"{BASE}/api/auth/login", json={"email": "admin@test.com", "password": "Admin123!"}, headers={"X-CSRF-Token": csrf})
print(f"2. Login: {r.status_code}")
data = r.json()
token = data.get("access_token")
user = data.get("user")
print(f"   Token: {token[:30]}...")
print(f"   User: {user}")

# Step 3: Get new CSRF for authenticated requests
r = session.get(f"{BASE}/api/security/csrf-token")
csrf = r.json().get("csrf_token")

# Step 4: Test /api/auth/me
H = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
r = session.get(f"{BASE}/api/auth/me", headers=H)
print(f"3. /api/auth/me: {r.status_code}")
if r.status_code == 200:
    print(f"   User: {r.json()}")
else:
    print(f"   Error: {r.text[:200]}")

# Step 5: Test dashboard-relevant endpoints
tests = [
    ("Career Insights", "GET", "/api/career/insights"),
    ("Applications", "GET", "/api/applications/"),
    ("Application Stats", "GET", "/api/applications/stats"),
    ("Profile", "GET", "/api/profile/me"),
    ("Resumes", "GET", "/api/resume/"),
    ("Jobs", "GET", "/api/jobs/"),
    ("Research", "GET", "/api/research"),
    ("Career Goals", "GET", "/api/career/goals"),
    ("Interview Saved", "GET", "/api/interview/saved"),
]

print(f"\n{'TEST':<25} {'STATUS':<8} {'RESULT'}")
print("=" * 60)
for label, method, path in tests:
    r = session.get(f"{BASE}{path}", headers=H, timeout=10)
    mark = "PASS" if r.status_code < 400 else "FAIL"
    detail = ""
    if r.status_code >= 400:
        try: detail = f" - {r.json().get('detail', r.text[:80])}"
        except: detail = f" - {r.text[:80]}"
    print(f"{label:<25} {r.status_code:<8} {mark}{detail}")
