from flask import Flask, render_template, jsonify, request
import urllib.request
import urllib.parse
import json
import os
import sys

# Windows konsolida UTF-8 xatoliklarini oldini olish
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

def supabase_patch(endpoint, data):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=HEADERS, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode("utf-8")
        return json.loads(content) if content else {}

# Telegram bildirishnoma yuboruvchi yordamchi funksiya
def send_telegram_notification(chat_id, text, reply_markup=None):
    if not chat_id or not BOT_TOKEN:
        print(f"Skipping notification: chat_id={chat_id}")
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            return True
    except Exception as e:
        print(f"Telegram notification xatoligi ({chat_id}): {e}")
        return False

ADMIN_CHAT_FILE = os.path.join(os.path.dirname(__file__), "admin_chat_id.txt")
LATEST_CHAT_FILE = os.path.join(os.path.dirname(__file__), "latest_chat.txt")

def get_admin_chat_id():
    # 1. Admin faylidan
    if os.path.exists(ADMIN_CHAT_FILE):
        try:
            with open(ADMIN_CHAT_FILE, "r") as f:
                cid = f.read().strip()
                if cid:
                    return int(cid)
        except Exception:
            pass
    # 2. Eng oxirgi faol chatdan
    if os.path.exists(LATEST_CHAT_FILE):
        try:
            with open(LATEST_CHAT_FILE, "r") as f:
                cid = f.read().strip()
                if cid:
                    return int(cid)
        except Exception:
            pass
    # 3. Supabase admin foydalanuvchisi
    try:
        admins = supabase_get("users?role=eq.admin&limit=1")
        if admins and admins[0].get("telegram_id"):
            return admins[0]["telegram_id"]
    except Exception:
        pass
    return None

def save_active_chat(chat_id, user_info=None):
    try:
        with open(LATEST_CHAT_FILE, "w") as f:
            f.write(str(chat_id))
    except Exception:
        pass

    if user_info:
        try:
            users = supabase_get(f"users?telegram_id=eq.{chat_id}")
            full_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or "Telegram Foydalanuvchisi"
            username = user_info.get("username", "")
            if not users:
                supabase_post("users", {
                    "telegram_id": chat_id,
                    "full_name": full_name,
                    "username": username,
                    "phone_number": "+998 90 000 00 00",
                    "role": "tenant",
                    "trust_score": 5.0
                })
        except Exception as e:
            print("Foydalanuvchini saqlashda xatolik:", e)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Fayl yuborilmadi'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Fayl tanlanmadi'}), 400
        if file and allowed_file(file.filename):
            import time
            import re
            clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '', file.filename)
            filename = f"prop_{int(time.time())}_{clean_name}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            file_url = f"/static/uploads/{filename}"
            return jsonify({'success': True, 'url': file_url})
        return jsonify({'success': False, 'error': 'Faqat rasm fayllari (jpg, png, webp) qabul qilinadi'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        landlord_tg_id = payload.get("landlord_tg_id")

        if not photos:
            photos = ["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80"]

        # 1. Uy egasi foydalanuvchisini olish yoki yaratish
        landlord_id = "a0000000-0000-0000-0000-000000000001" # standart fallback
        try:
            clean_phone = landlord_phone.replace(" ", "").replace("-", "")
            users = None
            if landlord_tg_id:
                users = supabase_get(f"users?telegram_id=eq.{landlord_tg_id}")
            if not users:
                users = supabase_get(f"users?phone_number=eq.{urllib.parse.quote(clean_phone)}")
            
            if users:
                landlord_id = users[0]["id"]
            else:
                import random
                tg_id_val = landlord_tg_id if landlord_tg_id else random.randint(100000000, 999999999)
                new_user = supabase_post("users", {
                    "telegram_id": tg_id_val,
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
        
        # 3. Real-vaqtda Telegram xabarnoma yuborish
        # A) Uy egasiga (agar tg_id bo'lsa)
        if landlord_tg_id:
            msg_landlord = (
                f"🎉 <b>E'LONINGIZ QABUL QILINDI!</b>\n\n"
                f"🏠 <b>{title}</b>\n"
                f"📍 <b>Manzil:</b> {district}, {address}\n"
                f"💵 <b>Oylik ijara:</b> {int(monthly_rent_uzs):,} so'm\n"
                f"🛡 <b>2% Split model:</b> Maklerga 50% yo'q, xavfsiz Escrow kafolati yoqilgan!\n\n"
                f"<i>E'loningiz Toshkent xaritasida va platformada faollashtirildi.</i>"
            )
            send_telegram_notification(landlord_tg_id, msg_landlord)

        # B) Admin / Monitoring kanaliga
        admin_id = get_admin_chat_id()
        if admin_id and admin_id != landlord_tg_id:
            msg_admin = (
                f"📢 <b>YANGI E'LON JOYLANDI!</b>\n\n"
                f"🏠 <b>{title}</b> ({district})\n"
                f"📍 {address} | {rooms} xona, {area_sqm} m²\n"
                f"💵 <b>Narx:</b> {int(monthly_rent_uzs):,} UZS/oy\n"
                f"👤 <b>Uy egasi:</b> {landlord_name} ({landlord_phone})"
            )
            send_telegram_notification(admin_id, msg_admin)

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
        tenant_tg_id = payload.get("tenant_tg_id", 111222333)
        
        tenant_users = supabase_get(f"users?telegram_id=eq.{tenant_tg_id}")
        if not tenant_users:
            tenant_users = supabase_post("users", {
                "telegram_id": tenant_tg_id,
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
        property_id = payload.get("property_id")
        amount = float(payload.get("amount", 300000))
        tenant_name = payload.get("tenant_name", "Ali Valiyev").strip()
        tenant_phone = payload.get("tenant_phone", "+998 90 999 88 77").strip()
        tenant_tg_id = payload.get("tenant_tg_id")
        tenant_username = payload.get("tenant_username", "")
        move_in_date = payload.get("move_in_date", "2026-11-01")
        note = payload.get("note", "RentTrust Escrow hold orqali band qilindi")
        
        # 1. Mulk va uy egasi ma'lumotlarini olish
        prop_list = supabase_get(f"properties?id=eq.{property_id}")
        if not prop_list:
            return jsonify({"success": False, "error": "Mulk topilmadi"}), 404
        prop = prop_list[0]

        landlord_list = supabase_get(f"users?id=eq.{prop['landlord_id']}")
        landlord = landlord_list[0] if landlord_list else {"full_name": "Uy Egasi", "phone_number": "+998 90 123 45 67", "telegram_id": None}

        # 2. Ijarachi foydalanuvchisini olish yoki yaratish
        tenant_id = None
        if tenant_tg_id:
            t_users = supabase_get(f"users?telegram_id=eq.{tenant_tg_id}")
            if t_users:
                tenant_id = t_users[0]["id"]
        
        if not tenant_id:
            import random
            dummy_tg = tenant_tg_id if tenant_tg_id else random.randint(100000000, 999999999)
            new_t = supabase_post("users", {
                "telegram_id": dummy_tg,
                "full_name": tenant_name,
                "username": tenant_username,
                "phone_number": tenant_phone,
                "role": "tenant",
                "trust_score": 5.0
            })
            if new_t:
                tenant_id = new_t[0]["id"]

        # 3. Application (Ariza) yaratish
        app_res = supabase_post("applications", {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "move_in_date": move_in_date,
            "note": note,
            "status": "approved"
        })
        application_id = app_res[0]["id"]

        # 4. Escrow tranzaksiyasini yaratish (2% + 2% komissiya)
        tenant_fee = amount * 0.02
        landlord_fee = amount * 0.02
        total_fee = tenant_fee + landlord_fee

        escrow_res = supabase_post("escrow_transactions", {
            "application_id": application_id,
            "property_id": property_id,
            "tenant_id": tenant_id,
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

        # 5. Mulk statusini "on_hold" ga o'zgartirish
        supabase_patch(f"properties?id=eq.{property_id}", {"status": "on_hold"})

        # 6. Telegram Push Bildirishnomalar
        # A) Uy egasiga ogohlantirish:
        landlord_tg = landlord.get("telegram_id")
        if landlord_tg:
            tg_mention = f"@{tenant_username}" if tenant_username else tenant_name
            msg_landlord = (
                f"🔔 <b>DIQQAT: YANGI ESCROW BAND QILISH!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('district')}, {prop.get('address')}\n"
                f"👤 <b>Ijarachi:</b> {tenant_name} ({tg_mention}, {tenant_phone})\n"
                f"💰 <b>Hold summasi:</b> {int(amount):,} so'm\n"
                f"🛡 <b>Xavfsizlik:</b> Mablag' RentTrust Escrow hisobida muzlatildi va xonadon 24 soatga ushbu ijarachi uchun band qilindi.\n\n"
                f"📞 <i>Ijarachi bilan zudlik bilan bog'lanib, xonadonni ko'rish va kalit topshirish vaqtini kelishib oling.</i>"
            )
            send_telegram_notification(landlord_tg, msg_landlord)

        # B) Ijarachiga rasmiy tasdiqnoma:
        tenant_recipient = tenant_tg_id or get_admin_chat_id()
        if tenant_recipient:
            msg_tenant = (
                f"🎉 <b>TABRIKLAYMIZ! XONADON BAND QILINDI</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('district')}, {prop.get('address')}\n"
                f"💰 <b>Muzlatilgan depozit:</b> {int(amount):,} so'm (Escrow kafolati)\n"
                f"🔑 <b>Uy egasi:</b> {landlord.get('full_name')} ({landlord.get('phone_number')})\n\n"
                f"🛡 <b>100% Escrow Himoyasi:</b>\n"
                f"Pulingiz to'g'ridan-to'g'ri uy egasiga o'tkazilmadi. Siz xonadonga ko'chib kirib, dalolatnomani tasdiqlamaguningizcha mablag' platforma kafolatida xavfsiz saqlanadi."
            )
            send_telegram_notification(tenant_recipient, msg_tenant)

        # C) Platforma adminiga xabarnoma:
        admin_id = get_admin_chat_id()
        if admin_id and admin_id != landlord_tg and admin_id != tenant_recipient:
            msg_admin = (
                f"⚡️ <b>Yangi Escrow Band Qilish:</b>\n"
                f"🏠 {prop.get('title')}\n"
                f"👤 Ijarachi: {tenant_name}\n"
                f"💵 Summa: {int(amount):,} UZS"
            )
            send_telegram_notification(admin_id, msg_admin)

        return jsonify({"success": True, "data": escrow_res[0]})
    except Exception as e:
        print("Escrow hold xatoligi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/escrow/resolve", methods=["POST"])
def resolve_escrow_admin():
    try:
        payload = request.json
        escrow_id = payload.get("id")
        action = payload.get("action") # 'release' yoki 'refund'

        escrows = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrows:
            return jsonify({"success": False, "error": "Tranzaksiya topilmadi"}), 404
        escrow = escrows[0]

        props = supabase_get(f"properties?id=eq.{escrow['property_id']}")
        prop = props[0] if props else {"title": "Xonadon"}

        landlords = supabase_get(f"users?id=eq.{escrow['landlord_id']}")
        landlord = landlords[0] if landlords else {}

        tenants = supabase_get(f"users?id=eq.{escrow['tenant_id']}")
        tenant = tenants[0] if tenants else {}

        amount = escrow.get("amount_uzs", 0)

        if action == "release":
            supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
                "status": "released_to_landlord",
                "released_at": "NOW()"
            })
            supabase_patch(f"properties?id=eq.{escrow['property_id']}", {"status": "rented"})

            # Uy egasiga xabarnoma
            if landlord.get("telegram_id"):
                msg_landlord = (
                    f"💵 <b>ESCROW MABLAG'I HISOBINGIZGA O'TKAZILDI!</b>\n\n"
                    f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                    f"💰 <b>O'tkazilgan summa:</b> {int(amount):,} so'm\n\n"
                    f"🤝 RentTrust UZ bilan hamkorlik qilganingiz uchun tashakkur!"
                )
                send_telegram_notification(landlord["telegram_id"], msg_landlord)

            # Ijarachiga xabarnoma
            tenant_tg = tenant.get("telegram_id") or get_admin_chat_id()
            if tenant_tg:
                msg_tenant = (
                    f"🤝 <b>IJARA KELISHUVI TO'LIQ TASDIQLANDI!</b>\n\n"
                    f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                    f"Xonadonga muvaffaqiyatli ko'chib kirganingiz tasdiqlandi. Yangi uyingiz qutlug' bo'lsin!"
                )
                send_telegram_notification(tenant_tg, msg_tenant)

        elif action == "refund":
            supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
                "status": "refunded_to_tenant",
                "refunded_at": "NOW()"
            })
            supabase_patch(f"properties?id=eq.{escrow['property_id']}", {"status": "available"})

            # Ijarachiga qaytarish xabarnomasi
            tenant_tg = tenant.get("telegram_id") or get_admin_chat_id()
            if tenant_tg:
                msg_tenant = (
                    f"↩️ <b>DEPOZIT TO'LIQ QAYTARILDI (REFUND)</b>\n\n"
                    f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                    f"💰 <b>Qaytarilgan summa:</b> {int(amount):,} so'm\n\n"
                    f"Mablag' RentTrust Escrow tomonidan kartangizga qaytarildi."
                )
                send_telegram_notification(tenant_tg, msg_tenant)

            # Uy egasiga xabar
            if landlord.get("telegram_id"):
                msg_landlord = (
                    f"ℹ️ <b>Band qilish bekor qilindi</b>\n\n"
                    f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                    f"Ijarachi bilan kelishuv bekor qilindi va e'loningiz qaytadan qidiruvda faollashtirildi."
                )
                send_telegram_notification(landlord["telegram_id"], msg_landlord)

        return jsonify({"success": True})
    except Exception as e:
        print("Escrow resolve xatoligi:", e)
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
        from_user = message.get("from", {})
        first_name = message["chat"].get("first_name", "Foydalanuvchi")
        text = message.get("text", "").strip()

        # Faol foydalanuvchini ro'yxatga olish
        save_active_chat(chat_id, from_user)

        # Tashqi WebApp URL
        app_host = request.host_url.rstrip("/")

        # Buyruqlar:
        if text in ["/admin", "/setadmin"]:
            with open(ADMIN_CHAT_FILE, "w") as f:
                f.write(str(chat_id))
            try:
                users = supabase_get(f"users?telegram_id=eq.{chat_id}")
                if users:
                    supabase_patch(f"users?id=eq.{users[0]['id']}", {"role": "admin"})
            except Exception:
                pass
            
            admin_msg = (
                f"👑 <b>Siz RentTrust UZ tizimi admini etib belgilandingiz!</b>\n\n"
                f"Barcha yangi e'lonlar, Escrow band qilishlar va arbitraj xabarlari endi zudlik bilan shu Telegram chatga keladi.\n\n"
                f"📊 Veb-boshqaruv paneli: <a href='{app_host}/admin'>{app_host}/admin</a>"
            )
            send_telegram_notification(chat_id, admin_msg)
            return "OK", 200

        if text == "/status":
            try:
                props = supabase_get("properties?select=id")
                escrows = supabase_get("escrow_transactions?select=id,status")
                held_count = len([e for e in escrows if e.get("status") == "held"])
                status_text = (
                    f"📊 <b>RentTrust UZ Jonli Statistikasi:</b>\n\n"
                    f"🏠 Jami e'lonlar: <b>{len(props)} ta</b>\n"
                    f"🔒 Faol Escrow tranzaksiyalari: <b>{held_count} ta</b>\n"
                    f"⚡️ Server holati: <b>Ishchi (24/7 Live)</b>\n\n"
                    f"Web App: {app_host}"
                )
            except Exception as se:
                status_text = f"Server holati: Faol. (Statistika yuklashda: {se})"
            send_telegram_notification(chat_id, status_text)
            return "OK", 200

        if text.startswith("/start"):
            welcome_text = (
                f"Assalomu alaykum, {first_name}! 👋\n\n"
                "🏢 <b>RentTrust UZ</b> — Toshkentdagi ishonchli va xavfsiz uy ijarasi platformasiga xush kelibsiz!\n\n"
                "🛡 <b>Bizning afzalliklarimiz:</b>\n"
                "• <b>100% Escrow kafolati:</b> Pulingiz uy egasiga emas, platformaning muzlatilgan hisobiga tushadi.\n"
                "• <b>Split komissiya:</b> Rieltorga 50% berish o‘rniga, atigi <b>2% xizmat haqi</b>!\n"
                "• <b>Depozit himoyasi:</b> Ko‘chib chiqayotganda depozit asossiz ushlab qolinmaydi.\n\n"
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
                    ],
                    [
                        {
                            "text": "👑 Admin panel",
                            "web_app": {"url": app_host + "/admin"}
                        }
                    ]
                ]
            }

            send_telegram_notification(chat_id, welcome_text, keyboard)

        return "OK", 200
    except Exception as e:
        print("Webhook xatoligi:", e)
        return "ERROR", 500

if __name__ == "__main__":
    print("RentTrust UZ serveri ishga tushmoqda: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
