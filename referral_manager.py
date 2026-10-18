import os
import json
import datetime

REFERRALS_FILE = os.path.join(os.path.dirname(__file__), "referrals_data.json")

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

def record_referral(referrer_id, referee_id, referee_name=""):
    """
    Yangi foydalanuvchi do'stining taklif havolasi orqali kirganda saqlash.
    """
    if str(referrer_id) == str(referee_id):
        return False, "O'zingizni taklif qila olmaysiz"
        
    data = _load_data()
    # Foydalanuvchi allaqachon kimdir orqali qo'shilganmi tekshirish
    for r in data["referrals"]:
        if str(r.get("referee_id")) == str(referee_id):
            return False, "Bu foydalanuvchi allaqachon biriktirilgan"
            
    record = {
        "referrer_id": str(referrer_id),
        "referee_id": str(referee_id),
        "referee_name": referee_name or "Foydalanuvchi",
        "created_at": datetime.datetime.now().isoformat(),
        "status": "joined",
        "deal_escrow_id": None,
        "cashback_uzs": 0
    }
    data["referrals"].append(record)
    
    ref_key = str(referrer_id)
    if ref_key not in data["balances"]:
        data["balances"][ref_key] = {
            "total_invited": 0,
            "completed_deals": 0,
            "total_cashback_uzs": 0
        }
    data["balances"][ref_key]["total_invited"] += 1
    
    _save_data(data)
    return True, record

def reward_referral_on_deal(referee_id, escrow_id, rent_amount_uzs):
    """
    Ijarachi muvaffaqiyatli ko'chib kirganda, taklif qilgan odamga 30% keshbek hisoblash.
    RentTrust komissiyasi = 2% (rent_amount_uzs * 0.02)
    Keshbek = komissiyaning 30% (platform_fee * 0.30)
    """
    data = _load_data()
    target_ref = None
    for r in data["referrals"]:
        if str(r.get("referee_id")) == str(referee_id) and r.get("status") == "joined":
            target_ref = r
            break
            
    if not target_ref:
        return None
        
    platform_fee = float(rent_amount_uzs) * 0.02
    cashback_uzs = int(platform_fee * 0.30)
    if cashback_uzs < 20000:
        cashback_uzs = 20000 # minimal kafolatlangan bonus 20 000 so'm
        
    target_ref["status"] = "escrow_completed"
    target_ref["deal_escrow_id"] = str(escrow_id)
    target_ref["cashback_uzs"] = cashback_uzs
    target_ref["completed_at"] = datetime.datetime.now().isoformat()
    
    referrer_id = str(target_ref["referrer_id"])
    if referrer_id not in data["balances"]:
        data["balances"][referrer_id] = {
            "total_invited": 1,
            "completed_deals": 0,
            "total_cashback_uzs": 0
        }
    data["balances"][referrer_id]["completed_deals"] += 1
    data["balances"][referrer_id]["total_cashback_uzs"] += cashback_uzs
    
    _save_data(data)
    return {
        "referrer_id": referrer_id,
        "referee_name": target_ref.get("referee_name", "Do'stingiz"),
        "cashback_uzs": cashback_uzs,
        "total_cashback_uzs": data["balances"][referrer_id]["total_cashback_uzs"]
    }

def get_user_referral_stats(user_id):
    """
    Foydalanuvchining shaxsiy takliflari va to'plagan keshbek balansi.
    """
    data = _load_data()
    uid = str(user_id)
    stats = data["balances"].get(uid, {
        "total_invited": 0,
        "completed_deals": 0,
        "total_cashback_uzs": 0
    })
    
    # Do'stlar ro'yxati
    friends = []
    for r in data["referrals"]:
        if str(r.get("referrer_id")) == uid:
            friends.append({
                "name": r.get("referee_name", "Do'st"),
                "status": "Ijarada (Keshbek berildi)" if r.get("status") == "escrow_completed" else "Ro'yxatdan o'tdi",
                "cashback": r.get("cashback_uzs", 0)
            })
            
    return {
        "total_invited": stats["total_invited"],
        "completed_deals": stats["completed_deals"],
        "total_cashback_uzs": stats["total_cashback_uzs"],
        "friends": friends
    }
