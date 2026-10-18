import os
import json
import datetime
import urllib.request

ALERTS_FILE = os.path.join(os.path.dirname(__file__), "property_alerts.json")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8909483662:AAFGrtJGPGSEVf5jr60ikamdGMCRLPM8XZc")

def _load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("property_alerts.json o'qishda xatolik:", e)
        return []

def _save_alerts(alerts):
    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("property_alerts.json saqlashda xatolik:", e)

def subscribe_alert(telegram_id, full_name, phone_number, district="all", max_price_uzs=10000000, rooms="all"):
    """
    Foydalanuvchining yangi uylar haqida xabarnoma olish obunasini saqlash.
    """
    alerts = _load_alerts()
    user_str = str(telegram_id).strip()
    
    # Eskisini yangilash yoki yangi qo'shish
    filtered = [a for a in alerts if str(a.get("telegram_id")) != user_str]
    
    subscription = {
        "telegram_id": user_str,
        "full_name": full_name or "Foydalanuvchi",
        "phone_number": phone_number or "",
        "district": district.strip() if district else "all",
        "max_price_uzs": int(max_price_uzs) if max_price_uzs else 10000000,
        "rooms": str(rooms).strip() if rooms else "all",
        "created_at": datetime.datetime.now().isoformat(),
        "is_active": True
    }
    
    filtered.append(subscription)
    _save_alerts(filtered)
    
    # Foydalanuvchiga tasdiqlash xabarnomasi
    try:
        if user_str and user_str.isdigit():
            dist_text = "Barcha tumanlar" if district == "all" else district
            rooms_text = "Barchasi" if str(rooms) == "all" else f"{rooms} xonali"
            price_text = f"{int(max_price_uzs):,} so'm"
            msg = (
                f"🔔 <b>RentTrust UZ Xabarnoma obunasi faollashdi!</b>\n\n"
                f"Siz qidirayotgan mezonlar:\n"
                f"📍 Tuman: <b>{dist_text}</b>\n"
                f"📐 Xonalar: <b>{rooms_text}</b>\n"
                f"💵 Maksimal narx: <b>{price_text} gacha</b>\n\n"
                f"Ushbu mezonlarga mos yangi tekshirilgan xonadon platformaga chiqishi bilan sizga darhol xabar beramiz! 🚀"
            )
            send_telegram_msg(user_str, msg)
    except Exception as e:
        print("Obuna tasdiqlash xabarida xatolik:", e)
        
    return subscription

def check_and_notify_subscribers(property_data):
    """
    Yangi qo'shilgan xonadon mezonlariga mos barcha obunachilarga Telegram orqali xabar yuborish.
    """
    alerts = _load_alerts()
    if not alerts:
        return 0
        
    prop_id = property_data.get("id")
    prop_title = property_data.get("title", "Shinam xonadon")
    prop_district = property_data.get("district", "").strip().lower()
    prop_price = int(property_data.get("monthly_rent_uzs", 0))
    prop_rooms = str(property_data.get("rooms", 1)).strip()
    
    notified_count = 0
    bot_user = "RentTrust_Uz_Bot"
    
    for sub in alerts:
        if not sub.get("is_active"):
            continue
            
        sub_dist = str(sub.get("district", "all")).strip().lower()
        sub_max_price = int(sub.get("max_price_uzs", 10000000))
        sub_rooms = str(sub.get("rooms", "all")).strip().lower()
        
        # Narx tekshiruvi
        if prop_price > sub_max_price:
            continue
            
        # Tuman tekshiruvi
        if sub_dist != "all" and sub_dist not in prop_district:
            continue
            
        # Xonalar tekshiruvi
        if sub_rooms != "all" and sub_rooms != prop_rooms:
            continue
            
        # Mos keldi! Foydalanuvchiga xabar yuboramiz
        telegram_id = sub.get("telegram_id")
        if not telegram_id or not str(telegram_id).isdigit():
            continue
            
        msg = (
            f"🔔 <b>SIZ KUTGAN YANGI XONADON E'LON QILINDI!</b> 🏠\n\n"
            f"<b>{prop_title}</b>\n"
            f"📍 Toshkent sh., <b>{property_data.get('district', '')}</b> tumani\n"
            f"📐 <b>{prop_rooms} xonali</b> • {property_data.get('area_sqm', 45)} m²\n"
            f"💵 <b>Narxi:</b> {prop_price:,} so'm / oy\n\n"
            f"🛡 <b>RentTrust afzalligi:</b>\n"
            f"• Makler 50% yo'q — Ijarachidan 2%, uy egasidan 2% to'lov!\n"
            f"• 100% Escrow xavfsiz band qilish.\n\n"
            f"<i>Boshqalar band qilishidan oldin ko'rib oling!</i>"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🚀 Xonadonni ko'rish & Band qilish", "url": f"https://t.me/{bot_user}?start=prop_{prop_id}"}]
            ]
        }
        
        ok = send_telegram_msg(telegram_id, msg, reply_markup=keyboard)
        if ok:
            notified_count += 1
            
    return notified_count

def send_telegram_msg(chat_id, text, reply_markup=None):
    if not BOT_TOKEN or not chat_id:
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
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True
    except Exception as e:
        print(f"Alert xabari yuborishda xatolik ({chat_id}):", e)
        return False
