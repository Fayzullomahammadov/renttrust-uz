-- ==============================================================================
-- RentTrust UZ — RLS Ruxsatlari va Dastlabki Uylar (Seed Data)
-- ==============================================================================

-- 1. Jadvallarni ommaviy o'qish va yozish uchun ochish (MVP testi uchun)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE properties DISABLE ROW LEVEL SECURITY;
ALTER TABLE applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE escrow_transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE move_in_inspections DISABLE ROW LEVEL SECURITY;
ALTER TABLE reviews DISABLE ROW LEVEL SECURITY;

-- 2. Dastlabki uy egalari (Users)
INSERT INTO users (id, telegram_id, full_name, phone_number, username, role, is_verified, trust_score, total_reviews)
VALUES 
    ('a0000000-0000-0000-0000-000000000001', 987654321, 'Sardor Rahimov', '+998 90 123 45 67', 'sardor_r', 'landlord', true, 4.95, 14),
    ('a0000000-0000-0000-0000-000000000002', 987654322, 'Nigora Karimova', '+998 93 987 65 43', 'nigora_k', 'landlord', true, 4.88, 9)
ON CONFLICT (telegram_id) DO NOTHING;

-- 3. Toshkent bo'yicha realistik e'lonlar (Properties)
INSERT INTO properties (
    landlord_id, title, description, district, address, rooms, area_sqm, floor, total_floors,
    monthly_rent_uzs, deposit_uzs, utilities_included, status, is_verified, photos, amenities
)
VALUES 
    (
        'a0000000-0000-0000-0000-000000000001',
        'Novza metrosi yaqinida shinam 2 xonali kvartira',
        'Talabalar yoki yosh oilalar uchun ajoyib variant. Hamma sharoitlar bor: konditsioner, muzlatgich, kir yuvish mashinasi, Wi-Fi. Metro 4 daqiqalik masofada. Shartnoma ijara.soliq.uz orqali rasmiylashtiriladi.',
        'Chilonzor',
        'Chilonzor 5-mavze, Novza metro ro''parasi',
        2, 56.0, 3, 5,
        4800000, 1500000, false, 'available', true,
        ARRAY[
            'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80'
        ],
        '{"wifi": true, "ac": true, "washing_machine": true, "refrigerator": true, "tv": true}'::jsonb
    ),
    (
        'a0000000-0000-0000-0000-000000000002',
        'Megaplanet yonida 3 xonali keng oilaviy xonadon',
        'Yevro-ta''mirdan chiqqan. Keng oshxona va alohida xonalar. Maktab, bog''cha va Megaplanet savdo markaziga juda yaqin. Depozit RentTrust Escrow tizimida himoyalanadi.',
        'Yunusobod',
        'Yunusobod 11-mavze, Megaplanet yonida',
        3, 82.0, 6, 9,
        6500000, 2000000, true, 'available', true,
        ARRAY[
            'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80'
        ],
        '{"wifi": true, "ac": true, "washing_machine": true, "refrigerator": true, "elevator": true}'::jsonb
    ),
    (
        'a0000000-0000-0000-0000-000000000001',
        'Buyuk Ipak Yo''lida talabalar uchun 1 xonali studiya',
        'Institut talabalari uchun eng maqbul joy. Yangi mebel va texnika. Metroga piyoda 3 daqiqa. Uy egasi talabalarga ijara berish imtiyozi tufayli daromad solig''idan ozod, ortiqcha to''lov yo''q.',
        'Mirzo Ulug''bek',
        'Mirzo Ulug''bek shoh ko''chasi, BIY metro 3 daqiqa',
        1, 38.0, 2, 4,
        3800000, 1000000, false, 'available', true,
        ARRAY[
            'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=800&q=80'
        ],
        '{"wifi": true, "washing_machine": true, "refrigerator": true}'::jsonb
    ),
    (
        'a0000000-0000-0000-0000-000000000002',
        'Shota Rustaveli ko''chasida zamonaviy 2 xonali kvartira',
        'Shahar markazida, Grand Mir mehmonxonasi yaqinida. To''liq yevro-dizayn, yuqori sifatli mebellar. Xorijiy fuqarolar, IT mutaxassislari yoki oilalar uchun mo''ljallangan.',
        'Yakkasaroy',
        'Shota Rustaveli ko''chasi, Grand Mir yaqinida',
        2, 68.0, 4, 8,
        7200000, 2500000, false, 'available', true,
        ARRAY[
            'https://images.unsplash.com/photo-1502005229762-ee1b2b8ab00f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1540518614846-7ede433c4b18?auto=format&fit=crop&w=800&q=80'
        ],
        '{"wifi": true, "ac": true, "washing_machine": true, "refrigerator": true, "dishwasher": true, "tv": true}'::jsonb
    );
