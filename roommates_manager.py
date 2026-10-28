import os
import json
import uuid
import datetime

ROOMMATES_FILE = os.path.join(os.path.dirname(__file__), "roommates_data.json")

def load_roommates():
    if not os.path.exists(ROOMMATES_FILE):
        # Boshlang'ich test ma'lumotlari (Toshkent talabalari va yoshlar uchun)
        initial_data = [
            {
                "id": "rm_001",
                "name": "Jamshidbek",
                "age": 21,
                "gender": "male",
                "is_student": True,
                "university": "TATU (Axborot xavfsizligi, 3-kurs)",
                "district": "Yunusobod",
                "budget_uzs": 1500000,
                "preferred_rooms": 2,
                "about": "Tartibli, chekmayman. O'zim bilan birga yashashga 1 yoki 2 nafar sherik qidiryapman. Metro yaqinida bo'lsa yaxshi.",
                "telegram_username": "jamshid_dev",
                "phone_number": "+998 90 123 45 67",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": "active"
            },
            {
                "id": "rm_002",
                "name": "Madinabonu",
                "age": 20,
                "gender": "female",
                "is_student": True,
                "university": "O'zMU (Iqtisodiyot, 2-kurs)",
                "district": "Olmazor",
                "budget_uzs": 1200000,
                "preferred_rooms": 3,
                "about": "Universitet talabalar shaharchasiga yaqin joydan 2 nafar qiz bilan xonadon sheriklikka olamiz. Tozalik va tartib muhim.",
                "telegram_username": "madina_stat",
                "phone_number": "+998 93 987 65 43",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": "active"
            },
            {
                "id": "rm_003",
                "name": "Sardor",
                "age": 24,
                "gender": "male",
                "is_student": False,
                "university": "IT Kompaniyada dizayner",
                "district": "Chilonzor",
                "budget_uzs": 2000000,
                "preferred_rooms": 2,
                "about": "Ishlaydigan yigitman. Chilonzorda 2 xonali kvartiraga ikkinchi xonaga bitta tinch, ishlaydigan sherik olaman.",
                "telegram_username": "sardor_ui",
                "phone_number": "+998 99 555 44 33",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": "active"
            }
        ]
        save_roommates(initial_data)
        return initial_data

    try:
        with open(ROOMMATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("roommates_data.json o'qishda xatolik:", e)
        return []

def save_roommates(data):
    try:
        with open(ROOMMATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("roommates_data.json saqlashda xatolik:", e)

def get_roommate_posts(district="all", gender="all", is_student=None):
    """Xonadosh qidiruv e'lonlarini filtrlash."""
    posts = load_roommates()
    results = []

    district_clean = str(district).strip().lower() if district else "all"
    gender_clean = str(gender).strip().lower() if gender else "all"

    for p in posts:
        if p.get("status") != "active":
            continue

        # Tuman filtri
        if district_clean != "all":
            post_dist = str(p.get("district", "")).strip().lower()
            if district_clean not in post_dist:
                continue

        # Jins filtri
        if gender_clean != "all":
            post_gender = str(p.get("gender", "")).strip().lower()
            if post_gender != gender_clean:
                continue

        # Talabalik filtri
        if is_student is not None and is_student != "all":
            student_bool = str(is_student).lower() in ["true", "1", "yes"]
            if bool(p.get("is_student")) != student_bool:
                continue

        results.append(p)

    return results

def create_roommate_post(data: dict) -> dict:
    """Yangi xonadosh qidirish e'lonini yaratish."""
    posts = load_roommates()
    post_id = f"rm_{uuid.uuid4().hex[:8]}"

    new_post = {
        "id": post_id,
        "name": str(data.get("name", "Foydalanuvchi")).strip(),
        "age": int(data.get("age", 20)),
        "gender": str(data.get("gender", "male")).strip().lower(),
        "is_student": bool(data.get("is_student", True)),
        "university": str(data.get("university", "")).strip(),
        "district": str(data.get("district", "Chilonzor")).strip(),
        "budget_uzs": int(data.get("budget_uzs", 1500000)),
        "preferred_rooms": int(data.get("preferred_rooms", 2)),
        "about": str(data.get("about", "")).strip(),
        "telegram_username": str(data.get("telegram_username", "")).strip().lstrip("@"),
        "phone_number": str(data.get("phone_number", "")).strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "active"
    }

    posts.insert(0, new_post)
    save_roommates(posts)
    return new_post
