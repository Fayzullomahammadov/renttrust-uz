import unittest
import time
import hmac
import hashlib
import json
import urllib.parse
from auth import verify_telegram_init_data, create_session_token, verify_session_token

class TestTelegramAuth(unittest.TestCase):
    def setUp(self):
        self.bot_token = "123456789:TEST_BOT_TOKEN_FOR_UNIT_TESTING"
        self.user = {
            "id": 987654321,
            "first_name": "Dilshod",
            "last_name": "Karimov",
            "username": "dilshod_k"
        }

    def generate_valid_init_data(self, auth_date_offset=0):
        auth_date = int(time.time()) + auth_date_offset
        params = {
            "auth_date": str(auth_date),
            "query_id": "AAHdF6IQAAAAAN0XohCq8hGz",
            "user": json.dumps(self.user, separators=(',', ':'))
        }
        sorted_keys = sorted(params.keys())
        data_check_string = "\n".join(f"{k}={params[k]}" for k in sorted_keys)
        
        secret_key = hmac.new(b"WebAppData", self.bot_token.encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params["hash"] = calculated_hash
        return urllib.parse.urlencode(params)

    def test_valid_init_data(self):
        init_data = self.generate_valid_init_data()
        verified_user = verify_telegram_init_data(init_data, bot_token=self.bot_token)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user["id"], self.user["id"])
        self.assertEqual(verified_user["first_name"], "Dilshod")

    def test_forged_hash_rejected(self):
        init_data = self.generate_valid_init_data()
        # Tamper with the hash
        forged_init_data = init_data.replace(init_data[-10:], "abcdef1234")
        verified_user = verify_telegram_init_data(forged_init_data, bot_token=self.bot_token)
        self.assertIsNone(verified_user, "Forged hash must be rejected!")

    def test_expired_auth_date_rejected(self):
        # auth_date from 2 hours ago (> 3600 seconds)
        expired_init_data = self.generate_valid_init_data(auth_date_offset=-7200)
        verified_user = verify_telegram_init_data(expired_init_data, bot_token=self.bot_token)
        self.assertIsNone(verified_user, "Expired auth_date (> 1h) must be rejected!")

    def test_session_token_flow(self):
        token = create_session_token(self.user, ttl_seconds=3600)
        self.assertIsNotNone(token)
        self.assertIn(".", token)

        user_from_token = verify_session_token(token)
        self.assertIsNotNone(user_from_token)
        self.assertEqual(user_from_token["id"], self.user["id"])

    def test_tampered_session_token_rejected(self):
        token = create_session_token(self.user, ttl_seconds=3600)
        tampered_token = token[:-5] + "XXXXX"
        self.assertIsNone(verify_session_token(tampered_token), "Tampered token must be rejected!")

    def test_expired_session_token_rejected(self):
        # 1-second TTL, then wait
        token = create_session_token(self.user, ttl_seconds=-10)
        self.assertIsNone(verify_session_token(token), "Expired session token must be rejected!")

if __name__ == "__main__":
    unittest.main()
