import os
import json
import sqlite3
import datetime
import uuid
import urllib.request
import urllib.parse

# 1. Konfiguratsiya
DATABASE_URL = os.environ.get("DATABASE_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jicqycwmswpxagmnnyoj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_Hk3qScveZpR6IVhfaGU0LA_X6Mx2AvH")

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "renttrust.db")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def init_local_sqlite():
    """Lokal SQLite bazasini PostgreSQL sxemasiga muvofiq yaratish (agar kerak bo'lsa)."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        full_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        username TEXT,
        role TEXT DEFAULT 'tenant',
        is_verified INTEGER DEFAULT 0,
        trust_score REAL DEFAULT 5.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS properties (
        id TEXT PRIMARY KEY,
        landlord_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        district TEXT NOT NULL,
        address TEXT NOT NULL,
        rooms INTEGER NOT NULL,
        area_sqm REAL,
        floor INTEGER,
        total_floors INTEGER,
        monthly_rent_uzs REAL NOT NULL,
        deposit_uzs REAL DEFAULT 0,
        status TEXT DEFAULT 'available',
        is_verified INTEGER DEFAULT 0,
        photos TEXT DEFAULT '[]',
        amenities TEXT DEFAULT '{}',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        property_id TEXT,
        tenant_id TEXT,
        move_in_date TEXT,
        note TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS escrow_transactions (
        id TEXT PRIMARY KEY,
        application_id TEXT,
        property_id TEXT,
        tenant_id TEXT,
        landlord_id TEXT,
        type TEXT DEFAULT 'hold_fee',
        amount_uzs REAL NOT NULL,
        tenant_fee_uzs REAL DEFAULT 0,
        landlord_fee_uzs REAL DEFAULT 0,
        total_platform_fee_uzs REAL DEFAULT 0,
        payment_provider TEXT DEFAULT 'click',
        provider_transaction_id TEXT,
        status TEXT DEFAULT 'initiated',
        held_at TEXT,
        released_at TEXT,
        refunded_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payment_transactions (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        amount_uzs REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        provider_tx_id TEXT,
        raw_payload TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
    );
    """)
    conn.commit()
    conn.close()

# SQLite ni ishga tushirish
init_local_sqlite()


class DatabaseManager:
    """RentTrust UZ Ma'lumotlar bazasi boshqaruvchisi (PostgreSQL / Supabase / SQLite)."""
    
    @staticmethod
    def supabase_request(method, endpoint, data=None, params=None):
        try:
            url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
            if params:
                query_string = urllib.parse.urlencode(params)
                url = f"{url}?{query_string}"
            
            body = json.dumps(data).encode("utf-8") if data else None
            req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=6) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content) if content else {}
        except Exception as e:
            # print(f"Supabase request failed ({method} {endpoint}): {e}")
            return None

    @classmethod
    def get_escrow(cls, escrow_id: str) -> dict:
        """Escrow ma'lumotlarini olish."""
        # 1. Supabase orqali urinish
        res = cls.supabase_request("GET", f"escrow_transactions?id=eq.{escrow_id}")
        if res and len(res) > 0:
            return res[0]

        # 2. SQLite orqali olish
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM escrow_transactions WHERE id = ?", (escrow_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @classmethod
    def mark_escrow_paid(cls, escrow_id: str, provider_tx_id: str = None, provider: str = "click") -> bool:
        """To'lov amalga oshirilgach Escrow holatini 'held' (muzlatilgan) ga o'tkazish."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Supabase orqali yangilash
        patch_data = {
            "status": "held",
            "held_at": now_iso,
            "provider_transaction_id": provider_tx_id,
            "payment_provider": provider
        }
        sb_res = cls.supabase_request("PATCH", f"escrow_transactions?id=eq.{escrow_id}", patch_data)
        
        # 2. SQLite orqali yangilash
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE escrow_transactions 
            SET status = 'held', held_at = ?, provider_transaction_id = ?, payment_provider = ?
            WHERE id = ?
        """, (now_iso, provider_tx_id, provider, escrow_id))
        
        # Property statusini ham 'on_hold' qilish
        cur.execute("""
            UPDATE properties 
            SET status = 'on_hold'
            WHERE id = (SELECT property_id FROM escrow_transactions WHERE id = ?)
        """, (escrow_id,))
        
        conn.commit()
        conn.close()
        return True

    @classmethod
    def record_payment_log(cls, order_id: str, provider: str, amount_uzs: float, status: str = "pending", provider_tx_id: str = None, raw_payload: str = None):
        """Barcha to'lov loglarini xavfsiz saqlash."""
        tx_id = f"ptx_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payment_transactions (id, order_id, provider, amount_uzs, status, provider_tx_id, raw_payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx_id, order_id, provider, amount_uzs, status, provider_tx_id, str(raw_payload), now_iso))
        conn.commit()
        conn.close()
        return tx_id
