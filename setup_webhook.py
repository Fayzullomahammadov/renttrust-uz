import os
import urllib.request
import urllib.parse
import json
import sys

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

def set_webhook(base_url, token=None):
    global BOT_TOKEN
    if token:
        BOT_TOKEN = token
    if not BOT_TOKEN:
        BOT_TOKEN = input("Telegram Bot Tokenini kiriting: ").strip()
    base_url = base_url.rstrip("/")
    webhook_url = f"{base_url}/webhook"
    
    print(f"🔗 1. Telegram Webhook ulanmoqda: {webhook_url}")
    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={urllib.parse.quote(webhook_url)}"
    with urllib.request.urlopen(set_url) as r:
        res = json.loads(r.read().decode())
        print("Webhook natijasi:", res.get("description", "Muvaffaqiyatli"))

    print(f"📱 2. Telegram Menu tugmasi sozlanmoqda: {base_url}")
    menu_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"
    data = json.dumps({
        "menu_button": {
            "type": "web_app",
            "text": "🏠 Uylarni ko'rish",
            "web_app": {"url": base_url}
        }
    }).encode("utf-8")
    req = urllib.request.Request(menu_url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        res = json.loads(r.read().decode())
        print("Menu tugmasi natijasi:", res.get("description", "Muvaffaqiyatli"))

    print("\n✅ Bot endi 24/7 serverda to'liq avtomatik ishlaydi!")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("Server HTTPS havolasi (masalan: https://renttrust-uz.onrender.com): ").strip()
    token = sys.argv[2] if len(sys.argv) > 2 else None
    if url:
        set_webhook(url, token)
