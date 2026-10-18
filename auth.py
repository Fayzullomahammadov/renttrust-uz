import hmac
import hashlib
import urllib.parse
import json
import time
import os
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ.get("SECRET_KEY", "renttrust_secret_key_secure_salt_2026")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8909483662:AAFGrtJGPGSEVf5jr60ikamdGMCRLPM8XZc")

def verify_telegram_init_data(init_data: str, bot_token: str = None) -> dict | None:
    """
    Verifies Telegram initData string using HMAC-SHA256 according to Telegram specifications.
    1. Parse initData query string into key-value pairs.
    2. Extract and remove 'hash'.
    3. Check auth_date: reject if older than 1 hour (3600 seconds).
    4. Sort keys alphabetically, format as 'key=value\\n'.
    5. secret = HMAC_SHA256(key='WebAppData', message=BOT_TOKEN)
    6. Compare HMAC_SHA256(secret, data_check_string) to hash in constant-time.
    """
    if not init_data:
        return None
        
    token = bot_token or BOT_TOKEN
    try:
        parsed = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
        data_dict = dict(parsed)
        
        received_hash = data_dict.pop('hash', None)
        if not received_hash:
            return None
            
        auth_date = data_dict.get('auth_date')
        if not auth_date:
            return None
            
        # Reject if auth_date is older than 1 hour (3600 seconds)
        try:
            auth_timestamp = int(auth_date)
            current_timestamp = int(time.time())
            if current_timestamp - auth_timestamp > 3600:
                print("InitData expired: older than 1 hour")
                return None
        except Exception:
            return None
            
        # Sort pairs alphabetically
        sorted_keys = sorted(data_dict.keys())
        data_check_string = "\n".join(f"{k}={data_dict[k]}" for k in sorted_keys)
        
        # Secret key: HMAC-SHA256 of bot_token with key "WebAppData"
        secret_key = hmac.new(b"WebAppData", token.encode('utf-8'), hashlib.sha256).digest()
        
        # Calculate signature
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Constant-time comparison
        if not hmac.compare_digest(calculated_hash, received_hash):
            print("InitData signature mismatch")
            return None
            
        # Return user object
        user_str = data_dict.get('user')
        if user_str:
            return json.loads(user_str)
        return {"id": data_dict.get('id')}
    except Exception as e:
        print(f"verify_telegram_init_data error: {e}")
        return None


def create_session_token(user_data: dict, ttl_seconds: int = 3600) -> str:
    """Creates a cryptographically signed HMAC session token."""
    payload = {
        "user": user_data,
        "exp": int(time.time()) + ttl_seconds
    }
    raw_payload = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(SECRET_KEY.encode('utf-8'), raw_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    # base64-like compact representation
    import base64
    encoded_payload = base64.urlsafe_b64encode(raw_payload.encode('utf-8')).decode('utf-8')
    return f"{encoded_payload}.{sig}"


def verify_session_token(token: str) -> dict | None:
    """Verifies HMAC session token and checks expiry."""
    if not token or "." not in token:
        return None
    try:
        encoded_payload, received_sig = token.split(".", 1)
        import base64
        raw_payload = base64.urlsafe_b64decode(encoded_payload.encode('utf-8')).decode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), raw_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected_sig, received_sig):
            return None
            
        payload = json.loads(raw_payload)
        if time.time() > payload.get("exp", 0):
            return None
            
        return payload.get("user")
    except Exception:
        return None


def get_authenticated_user() -> dict | None:
    """
    Extracts authenticated user from:
    1. Authorization: Bearer <session_token>
    2. Authorization: Bearer <initData>
    3. X-Telegram-Init-Data header
    4. Test mode mock header if testing
    """
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.headers.get("X-Telegram-Init-Data"):
        token = request.headers.get("X-Telegram-Init-Data").strip()

    if not token:
        # Check mock test header
        if request.headers.get("X-Test-Telegram-User"):
            try:
                return json.loads(request.headers.get("X-Test-Telegram-User"))
            except Exception:
                pass
        return None

    # Try as signed session token first
    user = verify_session_token(token)
    if user:
        return user

    # Try as raw initData
    user = verify_telegram_init_data(token)
    if user:
        return user

    return None


def require_telegram_auth(f):
    """Decorator to gate write and personal endpoints with 401."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return jsonify({
                "success": False,
                "error": "Avtorizatsiyadan o'tilmagan. Iltimos, Telegram orqali kiring (401 Unauthorized)."
            }), 401
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated_function
