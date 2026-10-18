import os
import json
import datetime
import uuid

REFERRALS_FILE = os.path.join(os.path.dirname(__file__), "referrals_data.json")
MAX_REFERRALS_PER_USER = int(os.environ.get("MAX_REFERRALS_PER_USER", "20"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "RentTrust_Uz_Bot")
APP_SHORT_NAME = os.environ.get("APP_SHORT_NAME", "app")

def _load_data():
    if not os.path.exists(REFERRALS_FILE):
        return {"referrals": [], "balances": {}}
    try:
        with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("referrals_data.json o'qishda xatolik:", e)
        return {"referrals": [], "balances": {}}

def _save_data(data):
    try:
        with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("referrals_data.json yozishda xatolik:", e)

def generate_referral_link(telegram_id) -> str:
    """Format: https://t.me/<BOT_USERNAME>/<APP_SHORT_NAME>?startapp=ref_<telegram_id>"""
    return f"https://t.me/{BOT_USERNAME}/{APP_SHORT_NAME}?startapp=ref_{telegram_id}"

def record_referral(referrer_id, referred_id, referred_name="", referrer_phone=None, referred_phone=None, payout_card=None):
    """
    Registers a referral click/join.
    Validations:
    - Same telegram_id rejected.
    - Same phone rejected.
    - Per-referrer cap enforced.
    - Status starts as 'pending'.
    """
    if not referrer_id or not referred_id:
        return False, "ID kiritilmagan"

    s_ref = str(referrer_id).strip()
    s_user = str(referred_id).strip()

    # Self-referral check
    if s_ref == s_user:
        return False, "O'zingizni taklif qila olmaysiz"

    # Same phone check
    if referrer_phone and referred_phone and str(referrer_phone).strip() == str(referred_phone).strip():
        return False, "Bir xil telefon raqami orqali o'zini taklif qilish taqiqlangan"

    data = _load_data()

    # Per-referrer cap check
    existing_for_referrer = [r for r in data["referrals"] if str(r.get("referrer_id")) == s_ref]
    if len(existing_for_referrer) >= MAX_REFERRALS_PER_USER:
        return False, f"Takliflar soni chekloviga yetdingiz (maksimal {MAX_REFERRALS_PER_USER} ta)"

    # Check if referred user already registered
    for r in data["referrals"]:
        if str(r.get("referred_id")) == s_user:
            return False, "Bu foydalanuvchi allaqachon taklif qilingan"

    record = {
        "id": f"ref_{uuid.uuid4().hex[:10]}",
        "referrer_id": s_ref,
        "referred_id": s_user,
        "referred_name": referred_name or "Foydalanuvchi",
        "booking_id": None,
        "status": "pending",  # pending | eligible | paid | rejected
        "cashback_uzs": 0,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "eligible_at": None,
        "paid_at": None
    }
    data["referrals"].append(record)

    # Initialize balance if not present
    if s_ref not in data["balances"]:
        data["balances"][s_ref] = {
            "total_invited": 0,
            "completed_deals": 0,
            "total_cashback_uzs": 0
        }
    data["balances"][s_ref]["total_invited"] += 1

    _save_data(data)
    return True, record

def mark_referral_eligible_on_release(referred_id, booking_id, monthly_rent_uzs, is_disputed=False):
    """
    A referral becomes eligible ONLY when the referred friend's booking is RELEASED
    and its dispute window has closed.
    Cashback: 30% of platform commission (which is 2% of rent, or min 20,000 UZS).
    """
    if is_disputed:
        return None

    data = _load_data()
    target_ref = None
    s_user = str(referred_id).strip()

    for r in data["referrals"]:
        if str(r.get("referred_id")) == s_user and r.get("status") == "pending":
            target_ref = r
            break

    if not target_ref:
        return None

    platform_fee = float(monthly_rent_uzs) * 0.02
    cashback_uzs = int(platform_fee * 0.30)
    if cashback_uzs < 20000:
        cashback_uzs = 20000

    target_ref["status"] = "eligible"
    target_ref["booking_id"] = str(booking_id)
    target_ref["cashback_uzs"] = cashback_uzs
    target_ref["eligible_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    ref_id = str(target_ref["referrer_id"])
    if ref_id not in data["balances"]:
        data["balances"][ref_id] = {
            "total_invited": 1,
            "completed_deals": 0,
            "total_cashback_uzs": 0
        }
    data["balances"][ref_id]["completed_deals"] += 1
    data["balances"][ref_id]["total_cashback_uzs"] += cashback_uzs

    _save_data(data)
    return target_ref

def mark_referral_paid(referral_id: str, admin_notes: str = ""):
    """Manual payout confirmation by admin."""
    data = _load_data()
    target = None
    for r in data["referrals"]:
        if r.get("id") == referral_id:
            r["status"] = "paid"
            r["paid_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            r["admin_notes"] = admin_notes
            target = r
            break
    _save_data(data)
    return target

def get_user_referral_stats(telegram_id):
    """Returns real stats (invited, deals, cashback) for user."""
    data = _load_data()
    s_id = str(telegram_id).strip()
    user_refs = [r for r in data["referrals"] if str(r.get("referrer_id")) == s_id]
    
    invited_count = len(user_refs)
    deals_count = len([r for r in user_refs if r.get("status") in ["eligible", "paid"]])
    total_cashback = sum(r.get("cashback_uzs", 0) for r in user_refs if r.get("status") in ["eligible", "paid"])

    return {
        "invited_count": invited_count,
        "deals_count": deals_count,
        "total_cashback_uzs": total_cashback,
        "referrals": user_refs
    }

# Backward compatibility alias
reward_referral_on_deal = mark_referral_eligible_on_release
