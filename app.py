from flask import Flask, render_template, jsonify, request
import urllib.request
import urllib.parse
import json
import os

app = Flask(__name__)

SUPABASE_URL = "https://jicqycwmswpxagmnnyoj.supabase.co"
SUPABASE_KEY = "sb_publishable_Hk3qScveZpR6IVhfaGU0LA_X6Mx2AvH"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8909483662:AAFGrtJGPGSEVf5jr60ikamdGMCRLPM8XZc")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def supabase_get(endpoint, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def supabase_post(endpoint, data):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

@app.route("/api/properties", methods=["GET"])
def get_properties():
    try:
        district = request.args.get("district")
        if district and district != "Barchasi":
            data = supabase_get(f"properties?district=eq.{urllib.parse.quote(district)}&order=created_at.desc")
        else:
            data = supabase_get("properties?order=created_at.desc")
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/properties", methods=["POST"])
def add_property():
    try:
        payload = request.json
        title = payload.get("title", "").strip()
        description = payload.get("description", "").strip()
        district = payload.get("district", "Chilonzor")
        address = payload.get("address", "").strip()
        rooms = int(payload.get("rooms", 1))
        area_sqm = float(payload.get("area_sqm", 45.0))
        floor = int(payload.get("floor", 1))
        total_floors = int(payload.get("total_floors", 5))
        monthly_rent_uzs = float(payload.get("monthly_rent_uzs", 4000000))
        deposit_uzs = float(payload.get("deposit_uzs", 1000000))
        utilities_included = bool(payload.get("utilities_included", False))
        photos = payload.get("photos", [])
        amenities = payload.get("amenities", {})
        landlord_name = payload.get("landlord_name", "Uy Egasi").strip()
        landlord_phone = payload.get("landlord_phone", "+998 90 000 00 00").strip()

        if not photos:
            photos = ["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80"]

        # 1. Uy egasi foydalanuvchisini olish yoki yaratish
        landlord_id = "a0000000-0000-0000-0000-000000000001" # standart fallback
        try:
            clean_phone = landlord_phone.replace(" ", "").replace("-", "")
            users = supabase_get(f"users?phone_number=eq.{urllib.parse.quote(clean_phone)}")
            if users:
                landlord_id = users[0]["id"]
            else:
                import random
                dummy_tg_id = random.randint(100000000, 999999999)
                new_user = supabase_post("users", {
                    "telegram_id": dummy_tg_id,
                    "full_name": landlord_name,
                    "phone_number": clean_phone,
                    "role": "landlord",
                    "is_verified": True,
                    "trust_score": 5.0,
                    "total_reviews": 1
                })
                if new_user:
                    landlord_id = new_user[0]["id"]
        except Exception as ue:
            print("Uy egasi yaratishda eslatma:", ue)

        # 2. Yangi e'lonni joylash
        prop_data = {
            "landlord_id": landlord_id,
            "title": title,
            "description": description,
            "district": district,
            "address": address,
            "rooms": rooms,
            "area_sqm": area_sqm,
            "floor": floor,
            "total_floors": total_floors,
            "monthly_rent_uzs": monthly_rent_uzs,
            "deposit_uzs": deposit_uzs,
            "utilities_included": utilities_included,
            "status": "available",
            "is_verified": True,
            "photos": photos,
            "amenities": amenities
        }

        created = supabase_post("properties", prop_data)
        return jsonify({"success": True, "data": created[0]})
    except Exception as e:
        print("E'lon qo'shish xatoligi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/applications", methods=["POST"])
def create_application():
    try:
        payload = request.json
        property_id = payload.get("property_id")
        tenant_name = payload.get("tenant_name", "Ali Valiyev")
        move_in_date = payload.get("move_in_date", "2026-11-01")
        note = payload.get("note", "Talabaman, uyni ko'chishga tayyorman.")
        
        tenant_users = supabase_get("users?telegram_id=eq.111222333")
        if not tenant_users:
            tenant_users = supabase_post("users", {
                "telegram_id": 111222333,
                "full_name": tenant_name,
                "phone_number": "+998 90 999 88 77",
                "role": "tenant",
                "trust_score": 5.0
            })
        tenant_id = tenant_users[0]["id"]

        app_res = supabase_post("applications", {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "move_in_date": move_in_date,
            "note": note,
            "status": "pending"
        })
        
        return jsonify({"success": True, "data": app_res[0]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/escrow/hold", methods=["POST"])
def create_hold():
    try:
        payload = request.json
        application_id = payload.get("application_id")
        property_id = payload.get("property_id")
        amount = payload.get("amount", 300000)
        
        tenant_fee = amount * 0.02
        landlord_fee = amount * 0.02
        total_fee = tenant_fee + landlord_fee

        prop = supabase_get(f"properties?id=eq.{property_id}")[0]

        escrow_res = supabase_post("escrow_transactions", {
            "application_id": application_id,
            "property_id": property_id,
            "tenant_id": payload.get("tenant_id"),
            "landlord_id": prop["landlord_id"],
            "type": "hold_fee",
            "amount_uzs": amount,
            "tenant_fee_uzs": tenant_fee,
            "landlord_fee_uzs": landlord_fee,
            "total_platform_fee_uzs": total_fee,
            "payment_provider": "click",
            "status": "held",
            "held_at": "NOW()"
        })

        patch_url = f"{SUPABASE_URL}/rest/v1/properties?id=eq.{property_id}"
        patch_req = urllib.request.Request(
            patch_url, 
            data=json.dumps({"status": "on_hold"}).encode("utf-8"), 
            headers=HEADERS, 
            method="PATCH"
        )
        with urllib.request.urlopen(patch_req) as resp:
            pass

        return jsonify({"success": True, "data": escrow_res[0]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Telegram Webhook Endpoint (Bulutli serverda 24/7 ishlashi uchun)
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.json
        if not update or "message" not in update:
            return "OK", 200
        
        message = update["message"]
        chat_id = message["chat"]["id"]
        first_name = message["chat"].get("first_name", "Foydalanuvchi")
        text = message.get("text", "")

        # Tashqi WebApp URL
        app_host = request.host_url.rstrip("/")
        
        if text.startswith("/start"):
            welcome_text = (
                f"Assalomu alaykum, {first_name}! 👋\n\n"
                "🏢 *RentTrust UZ* — Toshkentdagi ishonchli va xavfsiz uy ijarasi platformasiga xush kelibsiz!\n\n"
                "🛡 *Bizning afzalliklarimiz:*\n"
                "• *100% Escrow kafolati:* Pulingiz uy egasiga emas, platformaning muzlatilgan hisobiga tushadi.\n"
                "• *Split komissiya:* Rieltorga 50% berish o‘rniga, atigi *2% xizmat haqi*!\n"
                "• *Depozit himoyasi:* Ko‘chib chiqayotganda depozit asossiz ushlab qolinmaydi.\n\n"
                "Quyidagi tugmani bosing va Toshkentdagi tekshirilgan xonadonlarni ko‘ring 👇"
            )

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚀 Uylarni ko'rish (Web App)",
                            "web_app": {"url": app_host}
                        }
                    ],
                    [
                        {
                            "text": "➕ Uy egasi: E'lon berish",
                            "web_app": {"url": app_host + "?action=add"}
                        }
                    ]
                ]
            }

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            req_data = json.dumps({
                "chat_id": chat_id,
                "text": welcome_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }).encode("utf-8")

            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                pass

        return "OK", 200
    except Exception as e:
        print("Webhook xatoligi:", e)
        return "ERROR", 500

if __name__ == "__main__":
    print("RentTrust UZ serveri ishga tushmoqda: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
