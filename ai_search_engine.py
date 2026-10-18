import re

TASHKENT_DISTRICTS = [
    ("chilonzor", "Chilonzor"),
    ("yunusobod", "Yunusobod"),
    ("mirzo ulug'bek", "Mirzo Ulug‘bek"),
    ("mirzo ulugbek", "Mirzo Ulug‘bek"),
    ("ulug'bek", "Mirzo Ulug‘bek"),
    ("mirobod", "Mirobod"),
    ("yakkasaroy", "Yakkasaroy"),
    ("shayxontohur", "Shayxontohur"),
    ("olmazor", "Olmazor"),
    ("uchtepa", "Uchtepa"),
    ("sergeli", "Sergeli"),
    ("yashnobod", "Yashnobod"),
    ("bektemir", "Bektemir"),
    ("yangihayot", "Yangihayot")
]

def parse_ai_query(query_text):
    """
    Foydalanuvchining erkin matnli so'rovidan tuman, xonalar soni, maksimal narx va kalit so'zlarni ajratib olish.
    """
    q = (query_text or "").lower()
    
    # 1. Tumanni aniqlash
    detected_district = None
    for pattern, name in TASHKENT_DISTRICTS:
        if pattern in q:
            detected_district = name
            break
            
    # 2. Xonalar sonini aniqlash
    detected_rooms = None
    room_match = re.search(r'(\d+)\s*(?:xona|xonali|xonalik|komn|x\b)', q)
    if room_match:
        try:
            detected_rooms = int(room_match.group(1))
        except Exception:
            pass
    elif "bir xona" in q:
        detected_rooms = 1
    elif "ikki xona" in q:
        detected_rooms = 2
    elif "uch xona" in q:
        detected_rooms = 3
    elif "to'rt xona" in q or "tort xona" in q:
        detected_rooms = 4
        
    # 3. Maksimal narxni aniqlash
    max_price = None
    # A) Dollar ($ / usd / dollar)
    usd_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\$|usd|dollar|y\.e)', q)
    if usd_match:
        usd_val = float(usd_match.group(1))
        max_price = usd_val * 12800  # 1$ = 12 800 UZS
    else:
        # B) Million so'm (mln, million)
        mln_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mln|million|milyon)', q)
        if mln_match:
            mln_val = float(mln_match.group(1).replace(",", "."))
            max_price = mln_val * 1000000
        else:
            # C) To'liq summa (masalan 4000000 yoki 5000000)
            full_match = re.search(r'(\d{7,8})', q)
            if full_match:
                max_price = float(full_match.group(1))
                
    # 4. Qo'shimcha qulaylik va xususiyatlar
    keywords = []
    if "metro" in q or "metrogacha" in q:
        keywords.append("metro")
    if "talaba" in q or "student" in q:
        keywords.append("talaba")
    if "oila" in q or "oilaviy" in q:
        keywords.append("oila")
    if "mebel" in q or "jihoz" in q or "shkaf" in q:
        keywords.append("mebel")
    if "remont" in q or "evro" in q or "toza" in q:
        keywords.append("evroremont")
    if "konditsioner" in q or "kondits" in q:
        keywords.append("konditsioner")
    if "arzon" in q:
        keywords.append("arzon")

    return {
        "district": detected_district,
        "rooms": detected_rooms,
        "max_price": max_price,
        "keywords": keywords,
        "original_query": query_text
    }

def filter_properties_ai(properties, query_text):
    """
    Katalogdagi e'lonlarni aqlli filtrlash va foydalanuvchiga xulosa tuzish.
    """
    filters = parse_ai_query(query_text)
    
    scored_items = []
    for p in properties:
        score = 0
        p_dist = (p.get("district") or "").lower()
        p_title = (p.get("title") or "").lower()
        p_desc = (p.get("description") or "").lower()
        p_addr = (p.get("address") or "").lower()
        p_amen = " ".join(p.get("amenities") or []).lower()
        full_text = f"{p_title} {p_desc} {p_addr} {p_amen} {p_dist}"
        
        # Tuman mosligi
        if filters["district"]:
            if filters["district"].lower() in p_dist:
                score += 60
            else:
                continue # Tuman ko'rsatilgan bo'lsa, qat'iy tekshiramiz
                
        # Xonalar soni
        if filters["rooms"]:
            if p.get("rooms") == filters["rooms"]:
                score += 50
            else:
                continue # Xonalar ko'rsatilgan bo'lsa, qat'iy
                
        # Narx mosligi (10% zaxira marjasi bilan)
        if filters["max_price"]:
            rent = float(p.get("monthly_rent_uzs", 0))
            if rent <= filters["max_price"] * 1.15:
                score += 40
            else:
                continue
                
        # Kalit so'zlar
        for kw in filters["keywords"]:
            if kw in full_text:
                score += 15
                
        scored_items.append((score, p))
        
    scored_items.sort(key=lambda x: x[0], reverse=True)
    results = [item[1] for item in scored_items]
    
    # Agar hech narsa topilmasa, eng yaqin variantlarni tavsiya sifatida olamiz
    is_exact_match = len(results) > 0
    if not results:
        for p in properties:
            p_dist = (p.get("district") or "").lower()
            if filters["district"] and filters["district"].lower() in p_dist:
                results.append(p)
            elif filters["rooms"] and p.get("rooms") == filters["rooms"]:
                results.append(p)
        if not results:
            results = properties[:4]
            
    # AI Tabiiy Xulosa matni
    parts = []
    if filters["district"]:
        parts.append(f"{filters['district']} tumanida")
    if filters["rooms"]:
        parts.append(f"{filters['rooms']} xonali")
    if filters["max_price"]:
        parts.append(f"{int(filters['max_price']):,} so'mgacha")
    if filters["keywords"]:
        parts.append(f"({', '.join(filters['keywords'])})")
        
    criteria_str = " ".join(parts) if parts else f"«{query_text}» bo'yicha"
    
    if is_exact_match:
        ai_summary = (
            f"✨ <b>RentTrust AI Natijasi:</b> {criteria_str} so'rovingizga to'liq mos keluvchi "
            f"<b>{len(results)} ta tekshirilgan</b> xonadon topildi! Barcha uylarda 100% Escrow kafolati va 2% tejamkor komissiya amal qiladi."
        )
    else:
        ai_summary = (
            f"✨ <b>RentTrust AI Tavsiyasi:</b> Hozircha {criteria_str} bo'yicha aniq mos variant mavjud emas. "
            f"Biroq sizga yaqin tumanlardagi eng ommabop va ishonchli quyidagi xonadonlarni tavsiya qilamiz:"
        )

    return {
        "filters": filters,
        "ai_summary": ai_summary,
        "is_exact_match": is_exact_match,
        "count": len(results),
        "results": results
    }
