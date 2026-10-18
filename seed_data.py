import urllib.request
import json
import uuid

SUPABASE_URL = "https://jicqycwmswpxagmnnyoj.supabase.co"
SUPABASE_KEY = "sb_publishable_Hk3qScveZpR6IVhfaGU0LA_X6Mx2AvH"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def post(endpoint, data):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error posting to {endpoint}: {e}")
        return None

def seed():
    print("1. Foydalanuvchilarni (Uy egalarini) kiritish...")
    landlord_1 = post("users", {
        "telegram_id": 987654321,
        "full_name": "Sardor Rahimov",
        "phone_number": "+998 90 123 45 67",
        "username": "sardor_r",
        "role": "landlord",
        "is_verified": True,
        "trust_score": 4.95,
        "total_reviews": 14
    })
    
    landlord_2 = post("users", {
        "telegram_id": 987654322,
        "full_name": "Nigora Karimova",
        "phone_number": "+998 93 987 65 43",
        "username": "nigora_k",
        "role": "landlord",
        "is_verified": True,
        "trust_score": 4.88,
        "total_reviews": 9
    })

    if not landlord_1 or not landlord_2:
        print("Foydalanuvchilarni kiritishda xatolik yuz berdi")
        return

    landlord_1_id = landlord_1[0]["id"]
    landlord_2_id = landlord_2[0]["id"]

    print("2. Uylarni (Properties) kiritish...")
    properties = [
        {
            "landlord_id": landlord_1_id,
            "title": "Novza metrosi yaqinida shinam 2 xonali kvartira",
            "description": "Talabalar yoki yosh oilalar uchun ajoyib variant. Hamma sharoitlar bor: konditsioner, muzlatgich, kir yuvish mashinasi, Wi-Fi. Metro 4 daqiqalik masofada. Shartnoma ijara.soliq.uz orqali rasmiylashtiriladi.",
            "district": "Chilonzor",
            "address": "Chilonzor 5-mavze, Novza metro ro'parasi",
            "rooms": 2,
            "area_sqm": 56.0,
            "floor": 3,
            "total_floors": 5,
            "monthly_rent_uzs": 4800000,
            "deposit_uzs": 1500000,
            "utilities_included": False,
            "status": "available",
            "is_verified": True,
            "photos": [
                "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80"
            ],
            "amenities": {"wifi": True, "ac": True, "washing_machine": True, "refrigerator": True, "tv": True}
        },
        {
            "landlord_id": landlord_2_id,
            "title": "Megaplanet yonida 3 xonali keng oilaviy xonadon",
            "description": "Yevro-ta'mirdan chiqqan. Keng oshxona va alohida xonalar. Maktab, bog'cha va Megaplanet savdo markaziga juda yaqin. Depozit RentTrust Escrow tizimida himoyalanadi.",
            "district": "Yunusobod",
            "address": "Yunusobod 11-mavze, Megaplanet yonida",
            "rooms": 3,
            "area_sqm": 82.0,
            "floor": 6,
            "total_floors": 9,
            "monthly_rent_uzs": 6500000,
            "deposit_uzs": 2000000,
            "utilities_included": True,
            "status": "available",
            "is_verified": True,
            "photos": [
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80"
            ],
            "amenities": {"wifi": True, "ac": True, "washing_machine": True, "refrigerator": True, "elevator": True}
        },
        {
            "landlord_id": landlord_1_id,
            "title": "Buyuk Ipak Yo'lida talabalar uchun 1 xonali studiya",
            "description": "Institut talabalari uchun eng maqbul joy. Yangi mebel va texnika. Metroga piyoda 3 daqiqa. Uy egasi talabalarga ijara berish imtiyozi tufayli daromad solig'idan ozod, ortiqcha to'lov yo'q.",
            "district": "Mirzo Ulug'bek",
            "address": "Mirzo Ulug'bek shoh ko'chasi, BIY metro 3 daqiqa",
            "rooms": 1,
            "area_sqm": 38.0,
            "floor": 2,
            "total_floors": 4,
            "monthly_rent_uzs": 3800000,
            "deposit_uzs": 1000000,
            "utilities_included": False,
            "status": "available",
            "is_verified": True,
            "photos": [
                "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=800&q=80"
            ],
            "amenities": {"wifi": True, "washing_machine": True, "refrigerator": True}
        },
        {
            "landlord_id": landlord_2_id,
            "title": "Shota Rustaveli ko'chasida zamonaviy 2 xonali kvartira",
            "description": "Shahar markazida, Grand Mir mehmonxonasi yaqinida. To'liq yevro-dizayn, yuqori sifatli mebellar. Xorijiy fuqarolar, IT mutaxassislari yoki oilalar uchun mo'ljallangan.",
            "district": "Yakkasaroy",
            "address": "Shota Rustaveli ko'chasi, Grand Mir yaqinida",
            "rooms": 2,
            "area_sqm": 68.0,
            "floor": 4,
            "total_floors": 8,
            "monthly_rent_uzs": 7200000,
            "deposit_uzs": 2500000,
            "utilities_included": False,
            "status": "available",
            "is_verified": True,
            "photos": [
                "https://images.unsplash.com/photo-1502005229762-ee1b2b8ab00f?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1540518614846-7ede433c4b18?auto=format&fit=crop&w=800&q=80"
            ],
            "amenities": {"wifi": True, "ac": True, "washing_machine": True, "refrigerator": True, "dishwasher": True, "tv": True}
        }
    ]

    for p in properties:
        res = post("properties", p)
        if res:
            print(f"Uy qo'shildi: {p['title']}")

    print("\nBarcha ma'lumotlar muvaffaqiyatli yuklandi!")

if __name__ == "__main__":
    seed()
