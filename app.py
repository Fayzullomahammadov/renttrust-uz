from flask import Flask, render_template, jsonify, request, send_file
import urllib.request
import urllib.parse
import json
import os
import sys
import datetime
import re
from contract_generator import generate_rental_contract_pdf
from ai_search_engine import parse_ai_query, filter_properties_ai
from referral_manager import record_referral, reward_referral_on_deal, get_user_referral_stats
from alerts_manager import subscribe_alert, check_and_notify_subscribers
from reviews_manager import get_property_reviews, add_property_review
from fee_calculator import calculate_fees
from payment_provider import get_payment_provider, ClickProvider, PaymeProvider, UzumProvider
from database import DatabaseManager
from booking_manager import (
    record_booking_event,
    get_booking_events,
    evaluate_cancellation,
    record_dispute,
    resolve_dispute
)
from auth import verify_telegram_init_data, create_session_token, verify_session_token, require_telegram_auth, get_authenticated_user
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
USER_PHONES_FILE = os.path.join(os.path.dirname(__file__), "user_phones.json")


# Windows konsolida UTF-8 xatoliklarini oldini olish
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = Flask(__name__)

REPORTS_FILE = os.path.join(os.path.dirname(__file__), "property_reports.json")
IMAGE_HASHES_FILE = os.path.join(os.path.dirname(__file__), "image_hashes.json")

def load_json_store(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json_store(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")


TASHKENT_DISTRICTS = [
    "Bektemir",
    "Chilonzor",
    "Mirobod",
    "Mirzo Ulug'bek",
    "Olmazor",
    "Sergeli",
    "Shayxontohur",
    "Uchtepa",
    "Yakkasaroy",
    "Yashnobod",
    "Yunusobod",
    "Yangihayot"
]


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

# Telegram rasm yuboruvchi yordamchi funksiya
def send_telegram_photo(chat_id, photo_url, caption="", reply_markup=None):
    if not chat_id or not BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True
    except Exception as e:
        print(f"send_telegram_photo xatoligi ({chat_id}): {e}")
        return False

# Telegram PDF hujjat yuboruvchi yordamchi funksiya
def send_telegram_document(chat_id, file_path, caption=""):
    if not chat_id or not BOT_TOKEN or not os.path.exists(file_path):
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n'
            f"{caption}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="parse_mode"\r\n\r\n'
            f"HTML\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=12) as resp:
            return True
    except Exception as e:
        print(f"send_telegram_document xatoligi ({chat_id}): {e}")
        return False

ADMIN_CHAT_FILE = os.path.join(os.path.dirname(__file__), "admin_chat_id.txt")
LATEST_CHAT_FILE = os.path.join(os.path.dirname(__file__), "latest_chat.txt")

ADMIN_TELEGRAM_IDS = [
    int(x.strip()) for x in os.environ.get("ADMIN_TELEGRAM_IDS", "111222333,999888777,1336499878,6025813342").split(",") if x.strip()
]
if os.path.exists(ADMIN_CHAT_FILE):
    try:
        with open(ADMIN_CHAT_FILE, "r") as f:
            c = f.read().strip()
            if c and c.isdigit() and int(c) not in ADMIN_TELEGRAM_IDS:
                ADMIN_TELEGRAM_IDS.append(int(c))
    except Exception:
        pass

def is_admin_tg(tg_id):
    if not tg_id:
        return False
    try:
        tg_id_int = int(tg_id)
        if tg_id_int in ADMIN_TELEGRAM_IDS:
            return True
        users = supabase_get(f"users?telegram_id=eq.{tg_id_int}&role=eq.admin")
        if users:
            if tg_id_int not in ADMIN_TELEGRAM_IDS:
                ADMIN_TELEGRAM_IDS.append(tg_id_int)
            return True
        return False
    except Exception:
        return False

CHANNEL_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "channel_config.txt")

def normalize_channel_username(ch):
    if not ch:
        return None
    ch = str(ch).strip()
    if "t.me/" in ch:
        ch = ch.split("t.me/")[-1].strip("/").strip("@")
    elif ch.startswith("@"):
        ch = ch[1:].strip()
    
    if not ch:
        return None
    if ch.startswith("-100") or ch.startswith("-"):
        return ch
    return f"@{ch}"

def get_telegram_channel_id():
    env_ch = os.environ.get("TELEGRAM_CHANNEL_ID")
    if env_ch:
        return normalize_channel_username(env_ch)
    if os.path.exists(CHANNEL_CONFIG_FILE):
        try:
            with open(CHANNEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                ch = f.read().strip()
                if ch:
                    return normalize_channel_username(ch)
        except Exception:
            pass
    return "@toshkent_kvartira_renttrust"

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "contracts")
os.makedirs(CONTRACTS_DIR, exist_ok=True)

def get_contract_data_for_escrow(escrow_id):
    """
    Escrow ID bo'yicha shartnoma va dalolatnoma uchun zarur barcha ma'lumotlarni to'plash.
    """
    try:
        escrows = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrows:
            return None, "Tranzaksiya topilmadi"
        escrow = escrows[0]
        
        props = supabase_get(f"properties?id=eq.{escrow['property_id']}")
        prop = props[0] if props else {}
        
        landlords = supabase_get(f"users?id=eq.{escrow['landlord_id']}")
        landlord = landlords[0] if landlords else {}
        
        tenants = supabase_get(f"users?id=eq.{escrow['tenant_id']}")
        tenant = tenants[0] if tenants else {}
        
        inspections = supabase_get(f"move_in_inspections?application_id=eq.{escrow['application_id']}")
        inspection = inspections[0] if inspections else None
        
        date_str = datetime.date.today().strftime("%d.%m.%Y")
        if escrow.get("held_at"):
            try:
                dt = datetime.datetime.fromisoformat(escrow["held_at"].replace("Z", "+00:00"))
                date_str = dt.strftime("%d.%m.%Y")
            except Exception:
                pass

        contract_data = {
            "contract_id": f"RT-{str(escrow_id)[:8].upper()}",
            "date": date_str,
            "landlord_name": landlord.get("full_name") or "Uy Egasi",
            "landlord_phone": landlord.get("phone_number") or "+998 90 000 00 00",
            "tenant_name": tenant.get("full_name") or "Ijarachi",
            "tenant_phone": tenant.get("phone_number") or "+998 90 000 00 00",
            "property_title": prop.get("title") or "Xonadon",
            "district": prop.get("district") or "Toshkent",
            "address": prop.get("address") or "",
            "rooms": prop.get("rooms") or 1,
            "area_sqm": prop.get("area_sqm") or 45,
            "monthly_rent_uzs": prop.get("monthly_rent_uzs") or 4000000,
            "deposit_uzs": prop.get("deposit_uzs") or 1000000,
            "hold_fee": escrow.get("amount_uzs") or 300000,
            "tenant_notes": inspection.get("tenant_notes") if inspection else "Xonadon ko'zdan kechirildi, barcha jihozlar va texnikalar soz holatda qabul qilindi.",
            "photos_count": len(inspection.get("inspection_photos", [])) if (inspection and inspection.get("inspection_photos")) else 0
        }
        return contract_data, None
    except Exception as e:
        print("get_contract_data_for_escrow xatoligi:", e)
        return None, str(e)

def publish_property_to_channel(prop, landlord_name=None):
    """
    Yangi tekshirilgan e'lonni Telegram ommaviy kanaliga avtomatik post qilish.
    """
    channel_id = get_telegram_channel_id()
    if not channel_id or not BOT_TOKEN:
        print("Channel auto-post skipped: kanal biriktirilmagan.")
        return False
        
    title = prop.get("title", "Shinam xonadon")
    district = prop.get("district", "Toshkent")
    address = prop.get("address", "")
    rooms = prop.get("rooms", 1)
    area = prop.get("area_sqm", 45)
    floor = prop.get("floor", 1)
    total_floors = prop.get("total_floors", 5)
    monthly_rent = prop.get("monthly_rent_uzs", 0)
    amenity_labels = {
        "ac": "❄️ Konditsioner",
        "wifi": "📶 Wi-Fi",
        "elevator": "🛗 Lift",
        "refrigerator": "🧊 Muzlatgich",
        "washing_machine": "🧺 Kir yuvish mashinasi",
        "tv": "📺 Televizor",
        "parking": "🚗 Avtoturargoh",
        "balcony": "🌿 Balkon",
        "furniture": "🛋 Mebel"
    }
    raw_amenities = prop.get("amenities", [])
    if raw_amenities:
        amenities = ", ".join([amenity_labels.get(a, a) for a in raw_amenities])
    else:
        amenities = "Barcha qulayliklar mavjud"
    prop_id = prop.get("id")
    
    caption = (
        f"🌟 <b>YANGI TEKSHIRILGAN XONADON | RENTTRUST UZ</b> 🌟\n\n"
        f"🏠 <b>{title}</b>\n"
        f"📍 Toshkent sh., <b>{district}</b> tumani, {address}\n"
        f"📐 <b>{rooms} xonali</b> • {area} m² • {floor}/{total_floors}-qavat\n\n"
        f"💵 <b>Oylik ijara:</b> {int(monthly_rent):,} so'm / oy\n"
        f"🔒 <b>Xavfsiz depozit:</b> {int(deposit):,} so'm (Escrow kafolatida)\n\n"
        f"✨ <b>Qulayliklar:</b> {amenities}\n\n"
        f"🛡 <b>Nega RentTrust UZ?</b>\n"
        f"• Rieltorlarga 50% yo'q — atigi <b>2% Split komissiya</b>!\n"
        f"• Himoyalangan to'lov kafolati: Pul uyni ko'rib, kalit olmaguncha platformada xavfsiz saqlanadi.\n"
        f"• Qonuniy shartnoma va 12% talabalar soliq imtiyozi.\n\n"
        f"📲 <i>Xonadonni ko'rish va 24 soatga kafolatli band qilish:</i>"
    )
    
    bot_user = "RentTrust_Uz_Bot"
    bot_deep_link = f"https://t.me/{bot_user}?start=prop_{prop_id}"
    web_url = f"https://renttrust-uz.onrender.com/?prop={prop_id}"
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚀 Xonadonni ko'rish & Band qilish", "url": bot_deep_link}
            ],
            [
                {"text": "🌐 Sayt orqali ko'rish", "url": web_url}
            ]
        ]
    }
    
    photos = prop.get("photos", [])
    if photos and len(photos) > 0 and str(photos[0]).startswith("http"):
        ok = send_telegram_photo(channel_id, photos[0], caption=caption, reply_markup=keyboard)
        if ok:
            return True
            
    return send_telegram_notification(channel_id, caption, reply_markup=keyboard)

def get_admin_chat_id():
    # 0. Doimiy admin ro'yxatidan
    if ADMIN_TELEGRAM_IDS:
        return ADMIN_TELEGRAM_IDS[0]
    # 1. Supabase admin foydalanuvchisi
    try:
        admins = supabase_get("users?role=eq.admin&limit=1")
        if admins and admins[0].get("telegram_id"):
            return admins[0]["telegram_id"]
    except Exception:
        pass
    # 2. Admin faylidan
    if os.path.exists(ADMIN_CHAT_FILE):
        try:
            with open(ADMIN_CHAT_FILE, "r") as f:
                cid = f.read().strip()
                if cid:
                    return int(cid)
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


@app.route("/api/districts", methods=["GET"])
def get_districts():
    return jsonify({
        "success": True,
        "districts": TASHKENT_DISTRICTS
    })

@app.route("/")
def index():
    return render_template("index.html", districts=TASHKENT_DISTRICTS)

@app.after_request
def add_cache_headers(response):
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

@app.route("/api/admin/verify-access", methods=["POST"])
def verify_admin_access():
    try:
        payload = request.json or {}
        tg_id = payload.get("telegram_id")
        init_data = payload.get("initData", "")
        
        if init_data:
            verified_user = verify_telegram_init_data(init_data)
            if verified_user:
                tg_id = verified_user.get("id")
                
        if tg_id and is_admin_tg(tg_id):
            return jsonify({"success": True, "is_admin": True})
            
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ")[1]
            token_user = verify_session_token(token)
            if token_user and is_admin_tg(token_user.get("id")):
                return jsonify({"success": True, "is_admin": True})
                
        return jsonify({"success": False, "is_admin": False, "error": "Ruxsat etilmagan (Admin emassiz)"}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nSitemap: https://renttrust-uz.onrender.com/sitemap.xml\n"
    return content, 200, {"Content-Type": "text/plain"}

@app.route("/sitemap.xml")
def sitemap_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://renttrust-uz.onrender.com/</loc>
    <priority>1.0</priority>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://renttrust-uz.onrender.com/admin</loc>
    <priority>0.5</priority>
    <changefreq>weekly</changefreq>
  </url>
</urlset>"""
    return xml, 200, {"Content-Type": "application/xml"}

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


# -------------------------------------------------------------
# PHASE 4: Telegram Authentication & Session Management
# -------------------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    try:
        payload = request.json or {}
        init_data = payload.get("initData", "")
        user = verify_telegram_init_data(init_data)
        if not user:
            # Check if testing with mock user
            if request.headers.get("X-Test-Telegram-User"):
                try:
                    user = json.loads(request.headers.get("X-Test-Telegram-User"))
                except Exception:
                    pass
            if not user:
                return jsonify({"success": False, "error": "Noto'g'ri yoki eskirgan Telegram initData (401)"}), 401
                
        token = create_session_token(user)
        return jsonify({
            "success": True,
            "token": token,
            "user": user
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/user/phone", methods=["GET"])
@require_telegram_auth
def get_user_phone():
    tg_user = request.tg_user
    tg_id = str(tg_user.get("id"))
    phones = load_json_store(USER_PHONES_FILE)
    phone = phones.get(tg_id, "")
    return jsonify({"success": True, "phone": phone})

@app.route("/api/properties", methods=["POST"])
@require_telegram_auth
def add_property():
    try:
        tg_user = request.tg_user
        payload = request.json or {}
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
        # C) Telegram ommaviy kanaliga avtomatik post chiqarish
        try:
            publish_property_to_channel(created[0], landlord_name=landlord_name)
        except Exception as ch_err:
            print("Kanalga post chiqarishda xatolik:", ch_err)

        # D) Yangi uylar bo'yicha obunachilarga shaxsiy xabar yuborish (Smart Alerts)
        try:
            check_and_notify_subscribers(created[0])
        except Exception as alert_err:
            print("Obunachilarga xabar yuborishda xatolik:", alert_err)

        return jsonify({"success": True, "data": created[0]})
    except Exception as e:
        print("E'lon qo'shish xatoligi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/applications", methods=["POST"])
@require_telegram_auth
def create_application():
    try:
        payload = request.json
        property_id = payload.get("property_id")
        tenant_name = (payload.get("tenant_name") or "Ijarachi").strip()
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

PAYME_TX_FILE = os.path.join(os.path.dirname(__file__), "payme_transactions.json")

def finalize_paid_escrow(escrow_id, provider_tx_id="", provider="click"):
    """
    To'lov muvaffaqiyatli o'tgach (Click, Payme, Uzum yoki Mock):
    1. Escrow statusini 'held' ga o'tkazish
    2. Mulk statusini 'on_hold' qilish
    3. Uy egasi va Ijarachiga Telegram bildirishnoma yuborish
    """
    try:
        escrow = DatabaseManager.get_escrow(escrow_id)
        if not escrow:
            # Supabase fallback
            es = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
            if es:
                escrow = es[0]
        
        if not escrow:
            print(f"finalize_paid_escrow: Escrow {escrow_id} topilmadi")
            return False

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Holatni yangilash
        DatabaseManager.mark_escrow_paid(escrow_id, provider_tx_id=provider_tx_id, provider=provider)
        try:
            supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
                "status": "held",
                "held_at": now_iso,
                "provider_transaction_id": provider_tx_id,
                "payment_provider": provider
            })
        except Exception:
            pass

        property_id = escrow.get("property_id")
        amount = float(escrow.get("amount_uzs", 300000))
        
        # Mulkni on_hold qilish
        try:
            supabase_patch(f"properties?id=eq.{property_id}", {"status": "on_hold"})
        except Exception:
            pass

        # Ma'lumotlarni olish
        prop_list = supabase_get(f"properties?id=eq.{property_id}")
        prop = prop_list[0] if prop_list else {"title": "Xonadon", "district": "Toshkent", "address": ""}

        landlord_id = escrow.get("landlord_id") or prop.get("landlord_id")
        landlord_list = supabase_get(f"users?id=eq.{landlord_id}") if landlord_id else []
        landlord = landlord_list[0] if landlord_list else {}

        tenant_id = escrow.get("tenant_id")
        tenant_list = supabase_get(f"users?id=eq.{tenant_id}") if tenant_id else []
        tenant = tenant_list[0] if tenant_list else {}

        tenant_name = tenant.get("full_name", "Ijarachi")
        tenant_phone = tenant.get("phone_number", "+998 90 000 00 00")
        tenant_username = tenant.get("username", "")

        # Telegram bildirishnomalar
        landlord_tg = landlord.get("telegram_id")
        if landlord_tg:
            tg_mention = f"@{tenant_username}" if tenant_username else tenant_name
            msg_landlord = (
                f"🔔 <b>DIQQAT: YANGI ESCROW TO'LOVI QABUL QILINDI!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('district')}, {prop.get('address')}\n"
                f"👤 <b>Ijarachi:</b> {tenant_name} ({tg_mention}, {tenant_phone})\n"
                f"💰 <b>Hold summasi:</b> {int(amount):,} so'm\n"
                f"💳 <b>To'lov tizimi:</b> {provider.upper()}\n"
                f"🛡 <b>Xavfsizlik:</b> Mablag' RentTrust Escrow hisobida muzlatildi va xonadon 24 soatga ushbu ijarachi uchun band qilindi.\n\n"
                f"📞 <i>Ijarachi bilan zudlik bilan bog'lanib, xonadonni ko'rish va kalit topshirish vaqtini kelishib oling.</i>"
            )
            send_telegram_notification(landlord_tg, msg_landlord)

        tenant_recipient = tenant.get("telegram_id") or get_admin_chat_id()
        if tenant_recipient:
            msg_tenant = (
                f"🎉 <b>TABRIKLAYMIZ! TO'LOV MUVAFFAQIYATLI AMALGA OSHIRILDI</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('district')}, {prop.get('address')}\n"
                f"💰 <b>Muzlatilgan depozit:</b> {int(amount):,} so'm (Escrow kafolati)\n"
                f"💳 <b>To'lov tizimi:</b> {provider.upper()}\n"
                f"🔑 <b>Uy egasi:</b> {landlord.get('full_name', 'Uy egasi')} ({landlord.get('phone_number', '')})\n\n"
                f"🛡 <b>Himoyalangan to'lov Himoyasi:</b>\n"
                f"Pulingiz to'g'ridan-to'g'ri uy egasiga o'tkazilmadi. Siz xonadonga ko'chib kirib, dalolatnomani tasdiqlamaguningizcha mablag' platforma kafolatida xavfsiz saqlanadi."
            )
            send_telegram_notification(tenant_recipient, msg_tenant)

        admin_id = get_admin_chat_id()
        if admin_id and admin_id != landlord_tg and admin_id != tenant_recipient:
            msg_admin = (
                f"⚡️ <b>Yangi Escrow To'lovi:</b>\n"
                f"🏠 {prop.get('title')}\n"
                f"👤 Ijarachi: {tenant_name}\n"
                f"💳 To'lov: {provider.upper()} ({int(amount):,} UZS)"
            )
            send_telegram_notification(admin_id, msg_admin)

        return True
    except Exception as e:
        print(f"finalize_paid_escrow xatosi: {e}")
        return False


@app.route("/api/payments/click", methods=["POST"])
def click_webhook():
    """Click Shop API Webhook (Action 0 Prepare, Action 1 Complete)."""
    data = request.form.to_dict() if request.form else (request.json or {})
    provider = ClickProvider()

    def get_order(order_id):
        escrow = DatabaseManager.get_escrow(order_id)
        if not escrow:
            es = supabase_get(f"escrow_transactions?id=eq.{order_id}")
            if es:
                escrow = es[0]
        return escrow

    def mark_paid(order_id, provider_tx_id, provider_name):
        finalize_paid_escrow(order_id, provider_tx_id=provider_tx_id, provider=provider_name)

    action = str(data.get("action", "0"))
    if action == "0":
        res = provider.handle_prepare(data, get_order)
    else:
        res = provider.handle_complete(data, get_order, mark_paid)

    return jsonify(res)


@app.route("/api/payments/payme", methods=["POST"])
def payme_webhook():
    """Payme (Paycom) JSON-RPC 2.0 Webhook."""
    auth_header = request.headers.get("Authorization", "")
    provider = PaymeProvider()

    if os.environ.get("FLASK_ENV") == "production" and not provider.verify_auth_header(auth_header):
        return jsonify({
            "jsonrpc": "2.0",
            "id": request.json.get("id") if request.json else None,
            "error": {"code": -32504, "message": {"ru": "Недостаточно привилегий", "uz": "Ruxsat etilmagan"}}
        })

    tx_store = load_json_store(PAYME_TX_FILE)
    if not isinstance(tx_store, dict):
        tx_store = {}

    def get_order(order_id):
        escrow = DatabaseManager.get_escrow(order_id)
        if not escrow:
            es = supabase_get(f"escrow_transactions?id=eq.{order_id}")
            if es:
                escrow = es[0]
        return escrow

    def mark_paid(order_id, provider_tx_id, provider_name):
        finalize_paid_escrow(order_id, provider_tx_id=provider_tx_id, provider=provider_name)

    req_data = request.json or {}
    res = provider.handle_json_rpc(req_data, get_order, mark_paid, tx_store)
    save_json_store(PAYME_TX_FILE, tx_store)
    return jsonify(res)


@app.route("/api/payments/uzum", methods=["POST"])
def uzum_webhook():
    """Uzum Bank Webhook."""
    data = request.json or {}
    order_id = data.get("order_id")
    tx_id = data.get("transaction_id", f"uzum_{uuid.uuid4().hex[:8]}")
    if order_id:
        finalize_paid_escrow(order_id, provider_tx_id=tx_id, provider="uzum")
        return jsonify({"success": True, "status": "CONFIRMED"})
    return jsonify({"success": False, "error": "Order ID required"}), 400


@app.route("/api/escrow/hold", methods=["POST"])
@require_telegram_auth
def create_hold():
    try:
        payload = request.json
        property_id = payload.get("property_id")
        amount = float(payload.get("amount", 300000))
        tenant_name = (payload.get("tenant_name") or "Ijarachi").strip().strip()
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
            "status": "accepted"
        })
        application_id = app_res[0]["id"]

        # 4. To'lov provayderi va Escrow tranzaksiyasini yaratish (2% + 2% komissiya)
        provider_name = (payload.get("provider") or os.environ.get("PAYMENT_MODE", "mock")).lower().strip()
        provider_obj = get_payment_provider(provider_name)

        tenant_fee = amount * 0.02
        landlord_fee = amount * 0.02
        total_fee = tenant_fee + landlord_fee
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        initial_status = "held" if provider_name in ["mock", "demo"] else "initiated"

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
            "payment_provider": provider_name,
            "status": initial_status,
            "held_at": now_iso if initial_status == "held" else None
        })
        escrow_id = escrow_res[0]["id"]

        # To'lov havolasini generatsiya qilish
        return_url = f"https://renttrust-uz.onrender.com/?payment_success=1&escrow_id={escrow_id}"
        payment_info = provider_obj.create_payment(
            amount=amount,
            order_id=escrow_id,
            description=f"RentTrust Escrow: {prop.get('title', 'Xonadon')[:30]}",
            return_url=return_url
        )

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
                f"🛡 <b>Himoyalangan to'lov Himoyasi:</b>\n"
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

        return jsonify({"success": True, "data": escrow_res[0], "payment_url": payment_info.get("payment_url"), "provider": provider_name})
    except Exception as e:
        print("Escrow hold xatoligi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/my-bookings", methods=["GET"])
@require_telegram_auth
def get_my_bookings():
    try:
        telegram_id = request.args.get("telegram_id")
        user_id = None
        if telegram_id:
            users = supabase_get(f"users?telegram_id=eq.{telegram_id}")
            if users:
                user_id = users[0]["id"]
        
        if user_id:
            escrows = supabase_get(f"escrow_transactions?tenant_id=eq.{user_id}&order=created_at.desc")
        else:
            escrows = supabase_get("escrow_transactions?order=created_at.desc&limit=5")
        
        results = []
        for e in escrows:
            prop_list = supabase_get(f"properties?id=eq.{e['property_id']}")
            prop = prop_list[0] if prop_list else {}
            landlord_list = supabase_get(f"users?id=eq.{e['landlord_id']}")
            landlord = landlord_list[0] if landlord_list else {}
            
            results.append({
                "escrow_id": e["id"],
                "status": e.get("status", "held"),
                "amount_uzs": e.get("amount_uzs", 300000),
                "held_at": e.get("held_at") or e.get("created_at"),
                "property": {
                    "id": prop.get("id"),
                    "title": prop.get("title", "Shinam xonadon"),
                    "district": prop.get("district", "Toshkent"),
                    "address": prop.get("address", ""),
                    "monthly_rent_uzs": prop.get("monthly_rent_uzs", 0),
                    "photos": prop.get("photos", [])
                },
                "landlord": {
                    "full_name": landlord.get("full_name", "Uy Egasi"),
                    "phone_number": landlord.get("phone_number", "+998 90 000 00 00"),
                    "username": landlord.get("username", "")
                }
            })
            
        return jsonify({"success": True, "data": results})
    except Exception as e:
        print("get_my_bookings xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

def dispatch_contract_pdf_and_referral(escrow_id, tenant_tg, landlord_tg, monthly_rent, tenant_id=None):
    """
    Shartnoma tasdiqlanganda PDF yaratib Telegram orqali yuborish va agar referral bo'lsa keshbek to'lash.
    """
    try:
        contract_data, err = get_contract_data_for_escrow(escrow_id)
        if contract_data:
            pdf_path = os.path.join(CONTRACTS_DIR, f"RentTrust_Shartnoma_{str(escrow_id)[:8]}.pdf")
            generate_rental_contract_pdf(pdf_path, contract_data)
            
            caption = (
                f"📄 <b>Rasmiy Ijara Shartnomasi va Dalolatnoma (PDF)</b>\n\n"
                f"Shartnoma raqami: <b>{contract_data['contract_id']}</b>\n"
                f"Sana: <b>{contract_data['date']}</b>\n"
                f"🛡 RentTrust UZ Himoyalangan to'lov kafolati bilan tasdiqlangan."
            )
            if tenant_tg:
                send_telegram_document(tenant_tg, pdf_path, caption=caption)
            if landlord_tg and landlord_tg != tenant_tg:
                send_telegram_document(landlord_tg, pdf_path, caption=caption)
    except Exception as pdf_err:
        print("PDF shartnoma generatsiya yoki yuborishda xatolik:", pdf_err)
        
    # Keshbek / Referral hisoblash
    try:
        ref_target = tenant_tg or tenant_id
        if ref_target:
            reward = reward_referral_on_deal(ref_target, escrow_id, monthly_rent)
            if reward:
                ref_id = reward["referrer_id"]
                ref_msg = (
                    f"💰 <b>TABRIKLAYMIZ! SIZGA 30% KESHBEK TUSHDI!</b>\n\n"
                    f"Siz taklif qilgan do'stingiz <b>{reward['referee_name']}</b> xonadonga ko'chib kirdi va shartnoma kuchga kirdi.\n\n"
                    f"🎁 Sizning hisobingizga: <b>{reward['cashback_uzs']:,} so'm</b> keshbek o'tkazildi!\n"
                    f"💵 Jami to'plangan keshbekingiz: <b>{reward['total_cashback_uzs']:,} so'm</b>.\n\n"
                    f"RentTrust UZ bilan daromad qiling!"
                )
                try:
                    send_telegram_notification(int(ref_id), ref_msg)
                except Exception:
                    pass
    except Exception as ref_err:
        print("Referral keshbek hisoblashda xatolik:", ref_err)

@app.route("/api/contract/<escrow_id>/download", methods=["GET"])
def download_contract(escrow_id):
    try:
        contract_data, err = get_contract_data_for_escrow(escrow_id)
        if err or not contract_data:
            return jsonify({"success": False, "error": err or "Shartnoma topilmadi"}), 404
            
        pdf_path = os.path.join(CONTRACTS_DIR, f"RentTrust_Shartnoma_{str(escrow_id)[:8]}.pdf")
        generate_rental_contract_pdf(pdf_path, contract_data)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"RentTrust_Ijara_Shartnomasi_{str(escrow_id)[:8]}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        print("PDF download xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/my-bookings/confirm-move-in", methods=["POST"])
@require_telegram_auth
def confirm_move_in():
    try:
        payload = request.json
        escrow_id = payload.get("escrow_id")
        
        escrows = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrows:
            return jsonify({"success": False, "error": "Bandlik topilmadi"}), 404
        escrow = escrows[0]
        
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
            "status": "released_to_landlord",
            "released_at": now_iso
        })
        supabase_patch(f"properties?id=eq.{escrow['property_id']}", {"status": "rented"})
        
        props = supabase_get(f"properties?id=eq.{escrow['property_id']}")
        prop = props[0] if props else {}
        landlords = supabase_get(f"users?id=eq.{escrow['landlord_id']}")
        landlord = landlords[0] if landlords else {}
        tenants = supabase_get(f"users?id=eq.{escrow['tenant_id']}")
        tenant = tenants[0] if tenants else {}
        amount = escrow.get("amount_uzs", 300000)
        
        # 1. Uy egasiga xabarnoma
        if landlord.get("telegram_id"):
            msg_landlord = (
                f"🎉 <b>IJARACHI KO'CHIB KIRDI VA KALITNI OLDI!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"👤 <b>Ijarachi:</b> {tenant.get('full_name')}\n"
                f"💰 <b>Muzlatilgan hold summasi:</b> {int(amount):,} so'm hisobingizga o'tkazildi!\n\n"
                f"🤝 RentTrust UZ bilan hamkorlik uchun tashakkur!"
            )
            send_telegram_notification(landlord["telegram_id"], msg_landlord)
            
        # 2. Ijarachiga xabarnoma
        tenant_tg = tenant.get("telegram_id") or get_admin_chat_id()
        if tenant_tg:
            msg_tenant = (
                f"🎉 <b>TABRIKLAYMIZ! YANGI UYINGIZ MUBORAK BO'LSIN!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('address')}\n\n"
                f"✅ Xonadon holati va kalit qabul qilingani tasdiqlandi. RentTrust UZ bilan ijara — xavfsiz va shaffof!"
            )
            send_telegram_notification(tenant_tg, msg_tenant)

        # 3. PDF shartnomani yaratish, yuborish va referral keshbek hisoblash
        dispatch_contract_pdf_and_referral(
            escrow_id,
            tenant_tg,
            landlord.get("telegram_id"),
            prop.get("monthly_rent_uzs", 4000000),
            tenant.get("telegram_id")
        )
            
        return jsonify({"success": True})
    except Exception as e:
        print("confirm_move_in xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/my-bookings/inspection", methods=["POST"])
def submit_move_in_inspection():
    try:
        payload = request.json
        escrow_id = payload.get("escrow_id")
        photos = payload.get("photos", [])
        tenant_notes = payload.get("tenant_notes", "Xonadon ko'zdan kechirildi va kalit qabul qilindi.").strip()
        
        escrows = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrows:
            return jsonify({"success": False, "error": "Bandlik topilmadi"}), 404
        escrow = escrows[0]
        
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Dalolatnoma (move_in_inspections) jadvaliga saqlash
        inspection_data = {
            "application_id": escrow["application_id"],
            "tenant_confirmed": True,
            "landlord_confirmed": True,
            "inspection_photos": photos,
            "tenant_notes": tenant_notes,
            "confirmed_at": now_iso
        }
        try:
            supabase_post("move_in_inspections", inspection_data)
        except Exception as ie:
            print("Inspection saqlashda eslatma:", ie)
            
        # 2. Escrow statusini 'released_to_landlord' ga o'tkazish
        supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
            "status": "released_to_landlord",
            "released_at": now_iso
        })
        supabase_patch(f"properties?id=eq.{escrow['property_id']}", {"status": "rented"})
        
        props = supabase_get(f"properties?id=eq.{escrow['property_id']}")
        prop = props[0] if props else {}
        landlords = supabase_get(f"users?id=eq.{escrow['landlord_id']}")
        landlord = landlords[0] if landlords else {}
        tenants = supabase_get(f"users?id=eq.{escrow['tenant_id']}")
        tenant = tenants[0] if tenants else {}
        amount = escrow.get("amount_uzs", 300000)
        
        # 3. Telegram bildirishnomalar:
        # A) Uy egasiga
        if landlord.get("telegram_id"):
            msg_landlord = (
                f"📋 <b>KO'CHIB KIRISH DALOLATNOMASI TASDIQLANDI!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"👤 <b>Ijarachi:</b> {tenant.get('full_name')}\n"
                f"📸 <b>Qayd etilgan kamchilik suratlari:</b> {len(photos)} ta\n"
                f"📝 <b>Ijarachi izohi:</b> {tenant_notes}\n\n"
                f"💰 <b>Escrow to'lovi:</b> {int(amount):,} so'm hisobingizga o'tkazildi!\n"
                f"🤝 RentTrust UZ kafolati ostida xavfsiz ijara rasmiylashtirildi."
            )
            send_telegram_notification(landlord["telegram_id"], msg_landlord)
            
        # B) Ijarachiga
        tenant_tg = tenant.get("telegram_id") or get_admin_chat_id()
        if tenant_tg:
            msg_tenant = (
                f"🎉 <b>KO'CHIB KIRISH VA DALOLATNOMA RASMIYLASHTIRILDI!</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"📍 <b>Manzil:</b> {prop.get('address')}\n"
                f"📸 <b>Qayd etilgan fotosuratlar:</b> {len(photos)} ta rasmiy dalolatnomaga biriktirildi.\n"
                f"🛡 <b>Depozit xavfsizligi:</b> Ko'chib chiqayotganingizda ushbu fotodalillar depozitni to'liq qaytarib olishingiz uchun xizmat qiladi.\n\n"
                f"🔑 Yangi uyingiz qutlug' bo'lsin!"
            )
            send_telegram_notification(tenant_tg, msg_tenant)
            
        # C) Platforma adminiga
        admin_id = get_admin_chat_id()
        if admin_id and admin_id != landlord.get("telegram_id") and admin_id != tenant_tg:
            msg_admin = (
                f"⚡️ <b>Yangi Move-in Dalolatnoma:</b>\n"
                f"🏠 {prop.get('title')}\n"
                f"👤 {tenant.get('full_name')}\n"
                f"📸 Fotosuratlar: {len(photos)} ta"
            )
            send_telegram_notification(admin_id, msg_admin)

        # 4. PDF shartnomani yaratish, yuborish va referral keshbek hisoblash
        dispatch_contract_pdf_and_referral(
            escrow_id,
            tenant_tg,
            landlord.get("telegram_id"),
            prop.get("monthly_rent_uzs", 4000000),
            tenant.get("telegram_id")
        )
            
        return jsonify({"success": True})
    except Exception as e:
        print("submit_move_in_inspection xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/my-bookings/cancel", methods=["POST"])
@require_telegram_auth
def cancel_booking():
    try:
        payload = request.json
        escrow_id = payload.get("escrow_id")
        reason = payload.get("reason", "Ijarachi tomonidan bekor qilindi")
        
        escrows = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrows:
            return jsonify({"success": False, "error": "Bandlik topilmadi"}), 404
        escrow = escrows[0]
        
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
            "status": "refunded_to_tenant",
            "refunded_at": now_iso,
            "dispute_reason": reason
        })
        supabase_patch(f"properties?id=eq.{escrow['property_id']}", {"status": "available"})
        
        props = supabase_get(f"properties?id=eq.{escrow['property_id']}")
        prop = props[0] if props else {}
        landlords = supabase_get(f"users?id=eq.{escrow['landlord_id']}")
        landlord = landlords[0] if landlords else {}
        tenants = supabase_get(f"users?id=eq.{escrow['tenant_id']}")
        tenant = tenants[0] if tenants else {}
        amount = escrow.get("amount_uzs", 300000)
        
        # 1. Ijarachiga refund xabari
        tenant_tg = tenant.get("telegram_id") or get_admin_chat_id()
        if tenant_tg:
            msg_tenant = (
                f"↩️ <b>BANDLIK BEKOR QILINDI (REFUND)</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"💰 <b>Qaytarilgan mablag':</b> {int(amount):,} so'm\n\n"
                f"Mablag' RentTrust Escrow tomonidan kartangizga qaytarildi."
            )
            send_telegram_notification(tenant_tg, msg_tenant)
            
        # 2. Uy egasiga xabarnoma
        if landlord.get("telegram_id"):
            msg_landlord = (
                f"ℹ️ <b>Xonadon bandligi bekor qilindi</b>\n\n"
                f"🏠 <b>Xonadon:</b> {prop.get('title')}\n"
                f"E'loningiz qaytadan platforma katalogi va xaritasida mavjud holatga o'tkazildi."
            )
            send_telegram_notification(landlord["telegram_id"], msg_landlord)
            
        return jsonify({"success": True})
    except Exception as e:
        print("cancel_booking xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/my-bookings/dispute", methods=["POST"])
@require_telegram_auth
def open_booking_dispute():
    try:
        payload = request.json or {}
        escrow_id = payload.get("escrow_id")
        reason = payload.get("reason", "Nizo").strip()
        photos = payload.get("photos", [])
        
        escrow_list = supabase_get(f"escrow_transactions?id=eq.{escrow_id}")
        if not escrow_list:
            return jsonify({"success": False, "error": "Escrow tranzaksiyasi topilmadi"}), 404
            
        escrow = escrow_list[0]
        supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
            "status": "disputed",
            "dispute_reason": reason
        })
        
        disp = record_dispute(escrow_id, "tenant", reason, photos)
        record_booking_event(escrow_id, escrow.get("status", "HELD"), "DISPUTE", "tenant", reason)
        
        # Notify admins
        for admin_id in ADMIN_TELEGRAM_IDS:
            send_telegram_notification(
                admin_id,
                f"⚖️ <b>Yangi Nizo (DISPUTE) ochildi!</b>\n"
                f"Escrow ID: <code>{escrow_id}</code>\n"
                f"Sababi: <i>{reason}</i>\n"
                f"48 soat ichida dalillar ko'rib chiqilishi kerak."
            )
            
        return jsonify({"success": True, "data": disp})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/escrow/resolve", methods=["POST"])
def resolve_escrow_admin():
    try:
        payload = request.json or {}
        
        # Admin authorization check
        admin_ok = False
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ")[1]
            token_user = verify_session_token(token)
            if token_user and is_admin_tg(token_user.get("id")):
                admin_ok = True
                
        if not admin_ok:
            init_data = payload.get("initData") or request.headers.get("X-Telegram-Init-Data")
            if init_data:
                v_user = verify_telegram_init_data(init_data)
                if v_user and is_admin_tg(v_user.get("id")):
                    admin_ok = True
                    
        if not admin_ok:
            tg_id = payload.get("telegram_id")
            if tg_id and is_admin_tg(tg_id):
                admin_ok = True
                
        if not admin_ok:
            return jsonify({"success": False, "error": "Ruxsat etilmagan: Faqat tizim administratori uchun"}), 403
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

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if action == "release":
            supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
                "status": "released_to_landlord",
                "released_at": now_iso
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
                "refunded_at": now_iso
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

# -------------------------------------------------------------
# AI Smart Search API (Pillar 3)
# -------------------------------------------------------------
@app.route("/api/ai-search", methods=["GET", "POST"])
def api_ai_search():
    try:
        q = request.args.get("q")
        if not q and request.is_json and request.json:
            q = request.json.get("q")
        if not q:
            return jsonify({"success": False, "error": "Qidiruv so'rovi kiritilmadi"}), 400
            
        props = supabase_get("properties?select=*,users:landlord_id(*)&order=created_at.desc")
        res = filter_properties_ai(props, q)
        return jsonify({
            "success": True,
            "query": q,
            "filters": res["filters"],
            "ai_summary": res["ai_summary"],
            "is_exact_match": res["is_exact_match"],
            "count": res["count"],
            "data": res["results"]
        })
    except Exception as e:
        print("api_ai_search xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------------------------------------------
# Referral & Cashback API (Pillar 4)
# -------------------------------------------------------------
@app.route("/api/referral/join", methods=["POST"])
def api_referral_join():
    try:
        data = request.json or {}
        referrer_id = data.get("referrer_id")
        referee_id = data.get("referee_id")
        referee_name = data.get("referee_name", "")
        ok, msg = record_referral(referrer_id, referee_id, referee_name)
        return jsonify({"success": ok, "message": str(msg)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/referral/stats", methods=["GET"])
def api_referral_stats():
    try:
        user_id = request.args.get("user_id") or request.args.get("telegram_id")
        stats = get_user_referral_stats(user_id or "111222333")
        return jsonify({
            "success": True,
            "data": {
                "total_invited": stats["invited_count"],
                "completed_deals": stats["deals_count"],
                "total_cashback_uzs": stats["total_cashback_uzs"],
                "referrals": stats.get("referrals", [])
            }
        })
    except Exception as e:
        print("api_referral_stats xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------------------------------------------
# Smart Alerts API
# -------------------------------------------------------------
@app.route("/api/alerts/subscribe", methods=["POST"])
def api_subscribe_alert():
    try:
        data = request.json or {}
        telegram_id = data.get("telegram_id")
        full_name = data.get("full_name", "Foydalanuvchi")
        phone_number = data.get("phone_number", "")
        district = data.get("district", "all")
        max_price_uzs = data.get("max_price_uzs", 10000000)
        rooms = data.get("rooms", "all")
        
        if not telegram_id:
            admin_ch = get_admin_chat_id()
            if admin_ch:
                telegram_id = str(admin_ch)
            else:
                return jsonify({"success": False, "error": "Telegram ID kiritilmadi"}), 400
                
        sub = subscribe_alert(telegram_id, full_name, phone_number, district, max_price_uzs, rooms)
        return jsonify({"success": True, "data": sub})
    except Exception as e:
        print("api_subscribe_alert xatoligi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------------------------------------------
# Property Reviews & Trust Score API
# -------------------------------------------------------------
@app.route("/api/properties/<property_id>/reviews", methods=["GET"])
def api_get_reviews(property_id):
    try:
        res = get_property_reviews(property_id)
        return jsonify({"success": True, "data": res})
    except Exception as e:
        print("api_get_reviews xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/properties/<property_id>/reviews", methods=["POST"])
def api_add_review(property_id):
    try:
        data = request.json or {}
        author = data.get("author", "Mehmon")
        rating = data.get("rating", 5)
        comment = data.get("comment", "")
        role = data.get("role", "Ijarachi")
        if not comment:
            return jsonify({"success": False, "error": "Sharh matni kiritilmadi"}), 400
            
        res = add_property_review(property_id, author, rating, comment, role)
        return jsonify({"success": True, "data": res})
    except Exception as e:
        print("api_add_review xatosi:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------------------------------------------
# Telegram Webhook Endpoint (24/7 Cloud Bot & WebApp Controller)
# -------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        # Verify secret token if configured
        if WEBHOOK_SECRET:
            secret_hdr = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if secret_hdr != WEBHOOK_SECRET:
                return jsonify({"error": "Unauthorized"}), 403

        update = request.json
        if not update or "message" not in update:
            return "OK", 200
        
        message = update["message"]
        
        # Handle phone contact shared via Telegram
        if "contact" in message:
            contact = message["contact"]
            phone_num = contact.get("phone_number")
            sender_id = message["from"]["id"]
            if phone_num:
                phones = load_json_store(USER_PHONES_FILE)
                if not isinstance(phones, dict):
                    phones = {}
                phones[str(sender_id)] = phone_num
                save_json_store(USER_PHONES_FILE, phones)
                
                try:
                    u = supabase_get(f"users?telegram_id=eq.{sender_id}")
                    if u:
                        supabase_patch(f"users?id=eq.{u[0]['id']}", {"phone_number": phone_num})
                except Exception as ex:
                    print("Error updating phone in DB:", ex)
                    
                send_telegram_notification(sender_id, f"✅ Telefon raqamingiz ({phone_num}) muvaffaqiyatli tasdiqlandi!")
            return "OK", 200
        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        first_name = message["chat"].get("first_name", "Foydalanuvchi")
        text = message.get("text", "").strip()

        # Faol foydalanuvchini ro'yxatga olish
        save_active_chat(chat_id, from_user)

        # Tashqi WebApp URL
        app_host = request.host_url.rstrip("/")
        bot_user = "RentTrust_Uz_Bot"

        # 1. Admin buyruqlari
        if text in ["/admin", "/setadmin"]:
            if not is_admin_tg(chat_id):
                send_telegram_notification(chat_id, "⛔️ <b>Ruxsat etilmagan!</b>\n\nSiz RentTrust UZ tizimi administratori emassiz.")
                return "OK", 200
            
            admin_msg = (
                f"👑 <b>RentTrust UZ Admin Boshqaruv Markazi</b>\n\n"
                f"Barcha yangi e'lonlar, Escrow band qilishlar va arbitraj xabarlari nazorat markazi.\n\n"
                f"📊 Veb-boshqaruv paneli: <a href='{app_host}/admin'>{app_host}/admin</a>"
            )
            admin_kb = {
                "inline_keyboard": [
                    [{"text": "👑 Admin panelni ochish", "web_app": {"url": app_host + "/admin"}}]
                ]
            }
            send_telegram_notification(chat_id, admin_msg, admin_kb)
            return "OK", 200

        # 2. Kanalni ulash buyrug'i (Pillar 2)
        if text.startswith("/setchannel"):
            parts = text.split()
            if len(parts) > 1:
                raw_target = parts[1].strip()
                target_ch = normalize_channel_username(raw_target)
                if not target_ch:
                    send_telegram_notification(chat_id, "⚠️ Noto'g'ri kanal formati. Iltimos <code>@kanal_nomi</code> yoki havola ko'rinishida yuboring.")
                    return "OK", 200
                with open(CHANNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
                    f.write(target_ch)
                send_telegram_notification(
                    chat_id, 
                    f"✅ <b>Telegram kanal muvaffaqiyatli biriktirildi:</b> {target_ch}\n\n"
                    f"Endi barcha yangi e'lonlar avtomatik tarzda ushbu kanalga chiroyli surat va WebApp tugmasi bilan joylab boriladi!\n"
                    f"<i>(Iltimos, @RentTrust_Uz_Bot botini ushbu kanalda administrator qilib tayinlaganingizga ishonch hosil qiling)</i>"
                )
                try:
                    send_telegram_notification(target_ch, "🚀 <b>RentTrust UZ boti ushbu kanalga muvaffaqiyatli ulandi!</b>\nEndi barcha tekshirilgan xavfsiz xonadonlar shu yerda e'lon qilinadi.")
                except Exception as ch_test_err:
                    print("Kanalga test xabar yuborishda:", ch_test_err)
            else:
                send_telegram_notification(chat_id, "ℹ️ Kanalni ulash formati: <code>/setchannel @kanal_nomi</code>")
            return "OK", 200

        if text in ["/channel", "/kanal"]:
            ch = get_telegram_channel_id()
            if ch:
                send_telegram_notification(chat_id, f"📢 Hozirgi ulangan kanal: <b>{ch}</b>\nO'zgartirish uchun: <code>/setchannel @yangi_kanal</code>\nTest e'lon yuborish uchun: <code>/testpost</code>")
            else:
                send_telegram_notification(chat_id, "ℹ️ Hozircha ommaviy kanal ulanmagan. Ulash uchun: <code>/setchannel @kanal_nomi</code> deb yuboring.")
            return "OK", 200

        if text in ["/testpost", "/post"]:
            ch = get_telegram_channel_id()
            if not ch:
                send_telegram_notification(chat_id, "⚠️ Hali kanal biriktirilmagan. Avval <code>/setchannel @kanal_nomi</code> deb yuboring.")
                return "OK", 200
            try:
                props = supabase_get("properties?order=created_at.desc&limit=1")
                if props:
                    ok = publish_property_to_channel(props[0])
                    if ok:
                        send_telegram_notification(chat_id, f"✅ Test e'lon kanalingizga (<b>{ch}</b>) muvaffaqiyatli joylandi! Kanalga kirib ko'rishingiz mumkin.")
                    else:
                        send_telegram_notification(chat_id, f"⚠️ E'lonni kanalga yuborishda xatolik yuz berdi. Bot kanalda admin ekanligiga va xabar yozish huquqi borligiga ishonch hosil qiling.")
                else:
                    send_telegram_notification(chat_id, "ℹ️ E'lonlar bazasi bo'sh.")
            except Exception as e:
                send_telegram_notification(chat_id, f"❌ Xatolik: {e}")
            return "OK", 200

        # 3. Referral va Keshbek buyrug'i (Pillar 4)
        if text in ["/referral", "/keshbek", "/bonus"]:
            ref_link = f"https://t.me/{bot_user}?start=ref_{chat_id}"
            stats = get_user_referral_stats(chat_id)
            share_text = f"RentTrust UZ orqali rieltorlarning 50% komissiyasisiz, Himoyalangan to'lov kafolati bilan xonadon toping! Havola orqali o'ting va 30% chegirma oling: {ref_link}"
            share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"
            
            msg_ref = (
                f"🎁 <b>DO'STLARNI TAKLIF QILISH VA 30% KESHBEK DASTURI</b>\n\n"
                f"Do'stlaringizga RentTrust UZ ni tavsiya qiling. Ular platforma orqali muvaffaqiyatli xonadon ijaraga olganda, "
                f"platformamiz o'z komissiyasining <b>30% ini</b> sizga naqd keshbek qilib beradi!\n\n"
                f"📊 <b>Sizning statistikangiz:</b>\n"
                f"👥 Taklif qilingan do'stlar: <b>{stats['total_invited']} ta</b>\n"
                f"🏠 Muvaffaqiyatli ijara bitimlari: <b>{stats['completed_deals']} ta</b>\n"
                f"💰 To'plangan keshbek balansi: <b>{stats['total_cashback_uzs']:,} so'm</b>\n\n"
                f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n"
                f"<code>{ref_link}</code>"
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📲 Telegram orqali do'stlarga yuborish", "url": share_url}],
                    [{"text": "🚀 Web App ni ochish", "web_app": {"url": app_host}}]
                ]
            }
            send_telegram_notification(chat_id, msg_ref, keyboard)
            return "OK", 200

        # 4. Yangi uylar xabarnomasi obunasi (/obuna, /alert)
        if text.startswith("/obuna") or text.startswith("/alert"):
            sub = subscribe_alert(chat_id, first_name, "", "all", 10000000, "all")
            msg_sub = (
                f"🔔 <b>Siz RentTrust UZ yangi uylar xabarnomasiga obuna bo'ldingiz!</b>\n\n"
                f"Toshkentda yangi tekshirilgan xonadon e'lon qilinishi bilan sizga darhol Telegramda xabar yuboramiz.\n"
                f"Mezonlarni (tuman, xona, narx) Web App ichidagi 🔔 tugmasi orqali aniqroq sozlab olishingiz mumkin."
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "⚙️ Web App'da aniq sozlash", "web_app": {"url": app_host}}]
                ]
            }
            send_telegram_notification(chat_id, msg_sub, keyboard)
            return "OK", 200

        # 5. Tizim holati
        if text == "/status":
            try:
                props = supabase_get("properties?select=id")
                escrows = supabase_get("escrow_transactions?select=id,status")
                held_count = len([e for e in escrows if e.get("status") == "held"])
                ch = get_telegram_channel_id() or "Ulanmagan"
                status_text = (
                    f"📊 <b>RentTrust UZ Jonli Statistikasi:</b>\n\n"
                    f"🏠 Jami e'lonlar: <b>{len(props)} ta</b>\n"
                    f"🔒 Faol Escrow tranzaksiyalari: <b>{held_count} ta</b>\n"
                    f"📢 Telegram kanal: <b>{ch}</b>\n"
                    f"⚡️ Server holati: <b>Ishchi (24/7 Live)</b>\n\n"
                    f"Web App: {app_host}"
                )
            except Exception as se:
                status_text = f"Server holati: Faol. (Statistika yuklashda: {se})"
            send_telegram_notification(chat_id, status_text)
            return "OK", 200

        # 5. /start buyrug'i (Oddiy yoki Referral / Property deep link bilan)
        if text.startswith("/start"):
            parts = text.split()
            is_referral_welcome = False
            
            # Agar do'st taklif havolasi orqali kirgan bo'lsa
            if len(parts) > 1 and parts[1].startswith("ref_"):
                referrer_code = parts[1].replace("ref_", "").strip()
                if str(referrer_code) == str(chat_id):
                    # O'zining havolasini bosgan holat
                    self_ref_msg = (
                        f"Assalomu alaykum, {first_name}! 👋\n\n"
                        f"ℹ️ <b>Bu sizning shaxsiy taklif havolangiz!</b>\n\n"
                        f"Do'stlaringiz yoki guruhlarga ushbu havolani yuboring:\n"
                        f"<code>https://t.me/{bot_user}?start=ref_{chat_id}</code>\n\n"
                        f"Do'stingiz platforma orqali xonadonga ko'chib kirganda, RentTrust komissiyasining <b>30% qismi (keshbek)</b> sizning hisobingizga tushadi! 💰"
                    )
                    share_link = f"https://t.me/{bot_user}?start=ref_{chat_id}"
                    share_txt = "RentTrust UZ orqali rieltorlarning 50% to'lovisiz, Himoyalangan to'lov kafolati bilan Toshkentdan xonadon toping! Havola orqali o'ting va 30% chegirma oling:"
                    self_kb = {
                        "inline_keyboard": [
                            [{"text": "📲 Telegram orqali do'stlarga ulashish", "url": f"https://t.me/share/url?url={urllib.parse.quote(share_link)}&text={urllib.parse.quote(share_txt)}"}],
                            [{"text": "🚀 Web App ni ochish", "web_app": {"url": app_host}}]
                        ]
                    }
                    send_telegram_notification(chat_id, self_ref_msg, self_kb)
                    return "OK", 200

                ok, rec = record_referral(referrer_code, chat_id, first_name)
                if ok:
                    is_referral_welcome = True
                    try:
                        ref_int = int(referrer_code)
                        send_telegram_notification(
                            ref_int,
                            f"🎉 <b>YANGI TAKLIF QILINGAN DO'ST!</b>\n\n"
                            f"Do'stingiz <b>{first_name}</b> sizning havolangiz orqali RentTrust UZ ga qo'shildi!\n"
                            f"U xonadonga ko'chib kirib ijara bitimini tasdiqlaganida, platforma komissiyasining <b>30% qismi (keshbek)</b> to'g'ridan-to'g'ri balansingizga o'tkaziladi! 💰"
                        )
                    except Exception as err:
                        print("Referrerga bildirishnoma yuborishda:", err)

            if is_referral_welcome:
                welcome_text = (
                    f"Assalomu alaykum, {first_name}! 👋\n\n"
                    f"🎁 <b>Siz do'stingiz taklif havolasi orqali kirdingiz!</b>\n"
                    f"Siz uchun birinchi ijarangizda platforma komissiyasiga <b>30% maxsus chegirma</b> taqdim etiladi.\n\n"
                    "🏢 <b>RentTrust UZ</b> — Toshkentdagi Himoyalangan to'lov kafolatlangan uy ijarasi platformasi!\n"
                    "• Rieltorlarga 50% komissiya yo'q — atigi <b>2% Split xizmat haqi</b>\n"
                    "• Pul uyni ko'rib, kalit olmaguncha xavfsiz muzlatiladi\n"
                    "• Rasmiy shartnoma va 12% talabalar soliq imtiyozi.\n\n"
                    "Quyidagi tugma orqali eng yaxshi xonadonlarni tanlang 👇"
                )
            else:
                welcome_text = (
                    f"Assalomu alaykum, {first_name}! 👋\n\n"
                    "🏢 <b>RentTrust UZ</b> — Toshkentdagi ishonchli va xavfsiz uy ijarasi platformasiga xush kelibsiz!\n\n"
                    "🛡 <b>Bizning afzalliklarimiz:</b>\n"
                    "• <b>Himoyalangan to'lov kafolati:</b> Pulingiz uy egasiga emas, RentTrust nazoratidagi hisobga tushadi.\n"
                    "• <b>Split komissiya:</b> Rieltorga 50% berish o‘rniga, atigi <b>2% xizmat haqi</b>!\n"
                    "• <b>Depozit dalolatnomasi:</b> Ko‘chib chiqayotganda depozit asossiz ushlab qolinmaydi.\n\n"
                    "💡 <i>Menga istalgan talabingizni yozib yuboring (masalan: «Chilonzorda 2 xonali 400$ gacha»), AI maslahatchimiz sizga eng mos uylarni topib beradi!</i>\n\n"
                    "Yoki quyidagi tugmani bosib Web App ni oching 👇"
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
                    (
                        [
                            {"text": "🎁 30% Keshbek & Do'stlar", "callback_data": "ref_info"},
                            {"text": "👑 Admin panel", "web_app": {"url": app_host + "/admin"}}
                        ] if is_admin_tg(chat_id) else [
                            {"text": "🎁 30% Keshbek & Do'stlar", "callback_data": "ref_info"}
                        ]
                    )
                ]
            }
            send_telegram_notification(chat_id, welcome_text, keyboard)
            return "OK", 200

        # 6. AI Smart Natural Language Search Chatbot (Pillar 3)
        # Foydalanuvchi oddiy matn yuborganida (masalan: "Chilonzorda 2 xonali arzon uy bormi")
        if text and not text.startswith("/"):
            try:
                props = supabase_get("properties?select=*,users:landlord_id(*)&order=created_at.desc")
                ai_res = filter_properties_ai(props, text)
                
                ai_summary = ai_res["ai_summary"]
                matches = ai_res["results"][:3]
                
                reply_text = f"🤖 <b>RentTrust AI Maslahatchi:</b>\n\n{ai_summary}\n\n"
                
                inline_keyboard = []
                for idx, p in enumerate(matches, 1):
                    rent_str = f"{int(p.get('monthly_rent_uzs', 0)):,} UZS"
                    reply_text += (
                        f"<b>{idx}. {p.get('title')}</b>\n"
                        f"📍 {p.get('district')} tumani, {p.get('address')}\n"
                        f"💵 <b>{rent_str}/oy</b> • {p.get('rooms')} xonali ({p.get('area_sqm')} m²)\n"
                        f"🛡 2% Split komissiya | Himoyalangan to'lov kafolati\n\n"
                    )
                    prop_web_url = f"{app_host}/?prop={p.get('id')}"
                    inline_keyboard.append([{
                        "text": f"👀 {idx}-xonadonni ko'rish & Band qilish",
                        "web_app": {"url": prop_web_url}
                    }])
                    
                inline_keyboard.append([{
                    "text": "🔍 Barcha variantlarni ko'rish (Web App)",
                    "web_app": {"url": app_host}
                }])
                
                keyboard = {"inline_keyboard": inline_keyboard}
                send_telegram_notification(chat_id, reply_text, keyboard)
                return "OK", 200
            except Exception as ai_err:
                print("Bot AI search xatosi:", ai_err)
                send_telegram_notification(
                    chat_id, 
                    f"Savolingiz yoki so'rovingiz bo'yicha uylarni ko'rish uchun quyidagi tugmani bosing 👇",
                    {"inline_keyboard": [[{"text": "🚀 Web App da ko'rish", "web_app": {"url": app_host}}]]}
                )
                return "OK", 200

        return "OK", 200
    except Exception as e:
        print("Webhook xatoligi:", e)
        return "ERROR", 500

if __name__ == "__main__":
    print("RentTrust UZ serveri ishga tushmoqda: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)


# ------------------------------------------------------------------------------
# PHASE 3: Listing Moderation, Reports & Admin Endpoints
# ------------------------------------------------------------------------------
@app.route("/api/properties/<property_id>/report", methods=["POST"])
def report_property(property_id):
    try:
        payload = request.json or {}
        reason = payload.get("reason", "Shubhali e'lon").strip()
        reporter_tg_id = payload.get("reporter_tg_id")
        reporter_name = payload.get("reporter_name", "Foydalanuvchi")
        
        reports = load_json_store(REPORTS_FILE)
        new_report = {
            "id": f"rep_{int(datetime.datetime.now().timestamp())}",
            "property_id": property_id,
            "reporter_tg_id": reporter_tg_id,
            "reporter_name": reporter_name,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        reports.append(new_report)
        save_json_store(REPORTS_FILE, reports)
        
        # Notify admins
        for admin_id in ADMIN_TELEGRAM_IDS:
            send_telegram_notification(
                admin_id,
                f"🚩 <b>Yangi Shikoyat!</b>\n"
                f"E'lon ID: <code>{property_id}</code>\n"
                f"Kimdan: {reporter_name} (ID: {reporter_tg_id})\n"
                f"Sababi: <i>{reason}</i>"
            )
            
        return jsonify({"success": True, "message": "Shikoyat qabul qilindi va ko'rib chiqiladi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/properties/<property_id>/status", methods=["POST"])
def admin_set_property_status(property_id):
    try:
        payload = request.json or {}
        admin_tg = payload.get("admin_tg_id")
        if not is_admin_tg(admin_tg):
            return jsonify({"success": False, "error": "Ruxsat berilmagan (Admin emas)"}), 403
            
        new_status = payload.get("status") # 'approved' | 'rejected' | 'pending_review'
        if new_status not in ["approved", "rejected", "pending_review", "available", "rented"]:
            return jsonify({"success": False, "error": "Noto'g'ri status"}), 400
            
        updated = supabase_patch(f"properties?id=eq.{property_id}", {"status": new_status})
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/properties/<property_id>/verify", methods=["POST"])
def admin_toggle_property_verify(property_id):
    try:
        payload = request.json or {}
        admin_tg = payload.get("admin_tg_id")
        if not is_admin_tg(admin_tg):
            return jsonify({"success": False, "error": "Ruxsat berilmagan (Admin emas)"}), 403
            
        is_verified = bool(payload.get("verified", True))
        updated = supabase_patch(f"properties?id=eq.{property_id}", {"is_verified": is_verified})
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/reports", methods=["GET"])
def admin_get_reports():
    try:
        admin_tg = request.args.get("admin_tg_id")
        if not is_admin_tg(admin_tg):
            return jsonify({"success": False, "error": "Ruxsat berilmagan"}), 403
        reports = load_json_store(REPORTS_FILE)
        return jsonify({"success": True, "data": reports})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/payments/confirm", methods=["POST"])
def admin_confirm_payment():
    try:
        payload = request.json or {}
        admin_tg = payload.get("admin_tg_id")
        if not is_admin_tg(admin_tg):
            return jsonify({"success": False, "error": "Ruxsat berilmagan"}), 403
            
        escrow_id = payload.get("escrow_id")
        # Update escrow status to funded/held
        updated = supabase_patch(f"escrow_transactions?id=eq.{escrow_id}", {
            "status": "held",
            "held_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
