-- ==============================================================================
-- RentTrust UZ — PostgreSQL / Supabase Ma'lumotlar Bazasi Sxemasi (Schema)
-- ==============================================================================

-- 1. EXTENSIONS (UUID va boshqa yordamchilar)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUM TIPLARI (Statuslar va rollar)
CREATE TYPE user_role AS ENUM ('tenant', 'landlord', 'admin');
CREATE TYPE property_status AS ENUM ('available', 'on_hold', 'rented', 'inactive');
CREATE TYPE application_status AS ENUM ('pending', 'accepted', 'on_hold', 'completed', 'rejected', 'cancelled');
CREATE TYPE escrow_type AS ENUM ('hold_fee', 'first_month_rent', 'security_deposit');
CREATE TYPE escrow_status AS ENUM ('initiated', 'held', 'released_to_landlord', 'refunded_to_tenant', 'disputed');
CREATE TYPE payment_provider AS ENUM ('click', 'payme', 'bank_transfer');

-- 3. USERS (Foydalanuvchilar: Ijarachilar va Uy egalari)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    username VARCHAR(100),
    role user_role DEFAULT 'tenant',
    is_verified BOOLEAN DEFAULT FALSE,
    trust_score NUMERIC(3, 2) DEFAULT 5.00, -- O'rtacha reyting (1.00 dan 5.00 gacha)
    total_reviews INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. PROPERTIES (Uylar / Kvartiralar)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    landlord_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    district VARCHAR(100) NOT NULL, -- Masalan: Chilonzor, Yunusobod, Mirzo Ulug'bek
    address TEXT NOT NULL,
    rooms INT NOT NULL,
    area_sqm NUMERIC(6, 2), -- Maydoni (m2)
    floor INT,
    total_floors INT,
    monthly_rent_uzs NUMERIC(15, 2) NOT NULL, -- Oylik ijara narxi (so'mda)
    deposit_uzs NUMERIC(15, 2) NOT NULL DEFAULT 0, -- Talab qilinadigan depozit
    utilities_included BOOLEAN DEFAULT FALSE, -- Kommunal xarajatlar ichidami?
    status property_status DEFAULT 'available',
    is_verified BOOLEAN DEFAULT FALSE, -- RentTrust eksperti tekshirganmi?
    photos TEXT[] DEFAULT '{}', -- Rasmlar URL manzillari
    amenities JSONB DEFAULT '{}', -- Jihozlar (muzlatgich, konditsioner, wi-fi va h.k.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. APPLICATIONS (Ijarachilar arizalari)
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    move_in_date DATE NOT NULL,
    note TEXT, -- Masalan: "Men 2 nafar talabaman, 1-noyabrdan ko'chmoqchimiz"
    status application_status DEFAULT 'pending',
    hold_expires_at TIMESTAMP WITH TIME ZONE, -- Hold to'langach, 24 soatlik bloklash muddati
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. ESCROW_TRANSACTIONS (Escrow / Himoyalangan to'lovlar hisobi)
CREATE TABLE escrow_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id),
    tenant_id UUID NOT NULL REFERENCES users(id),
    landlord_id UUID NOT NULL REFERENCES users(id),
    type escrow_type NOT NULL, -- Bron puli, 1-oy to'lovi yoki Depozit
    amount_uzs NUMERIC(15, 2) NOT NULL, -- Asosiy to'lov summasi
    
    -- 2% + 2% SPLIT KOMISSIYA HISOBI:
    tenant_fee_uzs NUMERIC(15, 2) NOT NULL DEFAULT 0, -- Ijarachidan 2%
    landlord_fee_uzs NUMERIC(15, 2) NOT NULL DEFAULT 0, -- Uy egasidan 2%
    total_platform_fee_uzs NUMERIC(15, 2) NOT NULL DEFAULT 0, -- Jami 4%
    
    payment_provider payment_provider DEFAULT 'click',
    provider_transaction_id VARCHAR(100),
    status escrow_status DEFAULT 'initiated',
    
    held_at TIMESTAMP WITH TIME ZONE, -- Pul platformada muzlatilgan vaqt
    released_at TIMESTAMP WITH TIME ZONE, -- Pul uy egasiga o'tkazilgan vaqt
    refunded_at TIMESTAMP WITH TIME ZONE, -- Pul ijarachiga qaytarilgan vaqt
    dispute_reason TEXT, -- Agar nizo chiqsa, sababi
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. MOVE_IN_INSPECTIONS (Ko'chish kuni qabul qilish akti va dalolatnomasi)
CREATE TABLE move_in_inspections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    tenant_confirmed BOOLEAN DEFAULT FALSE,
    landlord_confirmed BOOLEAN DEFAULT FALSE,
    inspection_photos TEXT[] DEFAULT '{}', -- Ijarachi yuklagan uy holati suratlari
    tenant_notes TEXT,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. REVIEWS (Ikki tomonlama baholash va sharhlar)
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id),
    reviewer_id UUID NOT NULL REFERENCES users(id), -- Baholovchi
    reviewee_id UUID NOT NULL REFERENCES users(id), -- Baholangan (kim haqida)
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==============================================================================
-- INDEKSLAR (Tezkor qidiruv va filtrlar uchun)
-- ==============================================================================
CREATE INDEX idx_properties_district ON properties(district);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_price ON properties(monthly_rent_uzs);
CREATE INDEX idx_applications_property ON applications(property_id);
CREATE INDEX idx_applications_tenant ON applications(tenant_id);
CREATE INDEX idx_escrow_status ON escrow_transactions(status);
