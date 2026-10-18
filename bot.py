import urllib.request
import urllib.parse
import json
import time
import sys

# Windows konsolida UTF-8 emoji xatoligini oldini olish
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Sizning joriy HTTPS Web App manzilingiz:
WEB_APP_URL = "https://e11e72a18c5436.lhr.life"

def send_telegram_request(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    if data:
        encoded_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded_data, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Telegram API xatoligi ({method}): {e}")
        return None

def start_bot(token):
    print("🤖 RentTrust UZ Telegram boti ishga tushmoqda...")
    me = send_telegram_request(token, "getMe")
    if not me or not me.get("ok"):
        print("❌ Xato: Bot tokeni noto'g'ri yoki Telegramga ulanib bo'lmadi.")
        return

    bot_name = me["result"]["first_name"]
    bot_username = me["result"]["username"]
    print(f"✅ Bot muvaffaqiyatli ulandi: @{bot_username} ({bot_name})")
    print(f"🔗 Web App URL: {WEB_APP_URL}")

    # Menu tugmasini sozlash (Pastki doimiy WebApp menyusi)
    send_telegram_request(token, "setChatMenuButton", {
        "menu_button": {
            "type": "web_app",
            "text": "🏠 Uylarni ko'rish",
            "web_app": {"url": WEB_APP_URL}
        }
    })

    last_update_id = 0
    print("\n📩 Yangi xabarlar kutilmoqda (To'xtatish uchun Ctrl+C)...")

    while True:
        try:
            updates = send_telegram_request(token, "getUpdates", {
                "offset": last_update_id + 1,
                "timeout": 20
            })
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update["update_id"]
                    message = update.get("message")
                    if not message:
                        continue

                    chat_id = message["chat"]["id"]
                    first_name = message["chat"].get("first_name", "Foydalanuvchi")
                    text = message.get("text", "")

                    if text.startswith("/start"):
                        welcome_text = (
                            f"Assalomu alaykum, {first_name}! 👋\n\n"
                            "🏢 *RentTrust UZ* — Toshkentdagi ishonchli va xavfsiz uy ijarasi platformasiga xush kelibsiz!\n\n"
                            "🛡 *Bizning afzalliklarimiz:*\n"
                            "• *to'liq Escrow kafolati:* Pulingiz uy egasiga emas, platformaning RentTrust nazoratidagi hisobiga tushadi.\n"
                            "• *Split komissiya:* Rieltorga 50% berish o‘rniga, atigi *2% xizmat haqi*!\n"
                            "• *Depozit dalolatnomasi:* Ko‘chib chiqayotganda depozit asossiz ushlab qolinmaydi.\n\n"
                            "Quyidagi tugmani bosing va Toshkentdagi tekshirilgan xonadonlarni ko‘ring 👇"
                        )

                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "🚀 Uylarni ko'rish (Web App)",
                                        "web_app": {"url": WEB_APP_URL}
                                    }
                                ],
                                [
                                    {
                                        "text": "💬 Qo'llab-quvvatlash",
                                        "url": "https://t.me/renttrust_admin"
                                    }
                                ]
                            ]
                        }

                        send_telegram_request(token, "sendMessage", {
                            "chat_id": chat_id,
                            "text": welcome_text,
                            "parse_mode": "Markdown",
                            "reply_markup": keyboard
                        })
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nBot to'xtatildi.")
            break
        except Exception as e:
            print(f"Xatolik: {e}")
            time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("Telegram Bot Tokenini kiriting: ").strip()
    if token:
        start_bot(token)
    else:
        print("Token kiritilmadi.")
