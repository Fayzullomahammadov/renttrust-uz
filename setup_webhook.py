import urllib.request
import urllib.parse
import json
import sys

BOT_TOKEN = "8909483662:AAFGrtJGPGSEVf5jr60ikamdGMCRLPM8XZc"

def set_webhook(base_url):
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
    if len(sys.argv) > 1:
        url = sys.argv[1]
        set_webhook(url)
    else:
        url = input("Serveringizning HTTPS havolasini kiriting (masalan: https://renttrust-uz.onrender.com): ").strip()
        if url:
            set_webhook(url)
