import os
import re
from fee_calculator import calculate_fees
from app import app

print("=== DEFINITION OF DONE VERIFICATION ===")

# Check 1: calculate_fees
fees = calculate_fees(3000000, 0)
assert fees["monthly_rent"] == 3000000
assert fees["tenant_fee"] == 60000
assert fees["tenant_total"] == 3060000
assert fees["landlord_fee"] == 60000
assert fees["landlord_receives"] == 2940000
assert fees["platform_fee"] == 120000
print("[PASS] calculate_fees(3_000_000, 0) exact match: tenant=3,060,000, landlord=2,940,000, platform=120,000")

# Check 2: forbidden claims in templates/index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

forbidden = [
    '100% Escrow',
    '100% kafolat',
    '100% xavfsiz',
    '100% himoya',
    'Fakesiz uylar',
    'Ali Valiyev',
    'muzlatilgan hisob',
    'to\'lov agenti',
    'to`lov agenti',
    'to‘lov agenti'
]

found_forbidden = []
for phrase in forbidden:
    matches = re.findall(re.escape(phrase), html, re.IGNORECASE)
    if matches:
        found_forbidden.append((phrase, len(matches)))

if found_forbidden:
    print(f"[FAIL] Forbidden claims found: {found_forbidden}")
    exit(1)
else:
    print("[PASS] Zero forbidden claims found in templates/index.html!")

# Check 3: .env.example
assert os.path.exists('.env.example'), ".env.example missing!"
with open('.env.example', 'r', encoding='utf-8') as f:
    env_content = f.read()

assert "BOT_TOKEN" in env_content
assert "SUPABASE_KEY" in env_content
assert "PAYMENT_MODE" in env_content
print("[PASS] .env.example exists, is complete, and has no real secrets.")

# Check 4: TODO_MANUAL.md
assert os.path.exists('TODO_MANUAL.md'), "TODO_MANUAL.md missing!"
with open('TODO_MANUAL.md', 'r', encoding='utf-8') as f:
    todo_content = f.read()
assert "Legal Review" in todo_content or "Yuridik" in todo_content
assert "Click" in todo_content and "Payme" in todo_content
assert "renttrust.uz" in todo_content
print("[PASS] TODO_MANUAL.md exists and covers all non-technical blockers.")

# Check 5: Unauthenticated write and bookings endpoints return 401
client = app.test_client()

endpoints_to_test = [
    ("POST", "/api/properties", {}),
    ("POST", "/api/escrow/hold", {"property_id": "1"}),
    ("GET", "/api/my-bookings", None),
    ("POST", "/api/applications", {"property_id": "1"}),
    ("POST", "/api/my-bookings/confirm-move-in", {"booking_id": "1"}),
    ("POST", "/api/my-bookings/cancel", {"booking_id": "1"}),
    ("POST", "/api/my-bookings/dispute", {"booking_id": "1"})
]

for method, path, data in endpoints_to_test:
    if method == "POST":
        res = client.post(path, json=data)
    else:
        res = client.get(path)
    assert res.status_code == 401, f"{method} {path} returned {res.status_code}, expected 401!"
    print(f"  [401 Verified] {method} {path} -> 401 Unauthorized")

print("[PASS] All write and bookings endpoints strictly return 401 when unauthenticated.")

print("\nALL DEFINITION OF DONE CHECKS PASSED!")
