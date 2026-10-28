import unittest
import hashlib
import base64
import os
from payment_provider import (
    ClickProvider,
    PaymeProvider,
    UzumProvider,
    MockPaymentProvider,
    get_payment_provider
)

class TestPaymentProviders(unittest.TestCase):
    def setUp(self):
        self.click = ClickProvider(service_id="1111", merchant_id="2222", secret_key="test_click_secret")
        self.payme = PaymeProvider(merchant_id="test_payme_mid", secret_key="test_payme_sec")
        self.uzum = UzumProvider(service_id="test_uzum_sid", secret_key="test_uzum_sec")

        self.mock_order = {
            "id": "order_12345",
            "amount_uzs": 300000.0,
            "status": "initiated"
        }
        self.paid_orders = {}

    def get_order_func(self, order_id):
        if order_id == "order_12345":
            return self.mock_order
        return None

    def mark_paid_func(self, order_id, provider_tx_id, provider):
        self.paid_orders[order_id] = {
            "tx_id": provider_tx_id,
            "provider": provider,
            "status": "held"
        }
        self.mock_order["status"] = "held"

    # --- CLICK TESTS ---
    def test_click_create_payment_url(self):
        res = self.click.create_payment(amount=300000, order_id="order_12345", description="Escrow Hold")
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "click")
        self.assertIn("https://my.click.uz/services/pay?", res["payment_url"])
        self.assertIn("amount=300000", res["payment_url"])
        self.assertIn("transaction_param=order_12345", res["payment_url"])

    def test_click_signature_verification(self):
        # MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        click_trans_id = "998877"
        service_id = "1111"
        secret_key = "test_click_secret"
        merchant_trans_id = "order_12345"
        amount = "300000"
        action = "0"
        sign_time = "2026-10-28 12:00:00"

        raw = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
        valid_sign = hashlib.md5(raw.encode('utf-8')).hexdigest()

        self.assertTrue(self.click.verify_click_signature(
            click_trans_id, service_id, merchant_trans_id, amount, action, sign_time, valid_sign
        ))
        self.assertFalse(self.click.verify_click_signature(
            click_trans_id, service_id, merchant_trans_id, amount, action, sign_time, "wrong_hash"
        ))

    def test_click_handle_prepare_success(self):
        raw = f"101111test_click_secretorder_1234530000002026-10-28"
        valid_sign = hashlib.md5(raw.encode('utf-8')).hexdigest()

        req = {
            "click_trans_id": "10",
            "service_id": "1111",
            "merchant_trans_id": "order_12345",
            "amount": "300000",
            "action": "0",
            "sign_time": "2026-10-28",
            "sign_string": valid_sign
        }
        res = self.click.handle_prepare(req, self.get_order_func)
        self.assertEqual(res["error"], 0)
        self.assertIn("merchant_prepare_id", res)

    def test_click_handle_complete_success(self):
        raw = f"101111test_click_secretorder_1234530000012026-10-28"
        valid_sign = hashlib.md5(raw.encode('utf-8')).hexdigest()

        req = {
            "click_trans_id": "10",
            "service_id": "1111",
            "merchant_trans_id": "order_12345",
            "amount": "300000",
            "action": "1",
            "sign_time": "2026-10-28",
            "sign_string": valid_sign,
            "error": 0
        }
        res = self.click.handle_complete(req, self.get_order_func, self.mark_paid_func)
        self.assertEqual(res["error"], 0)
        self.assertIn("merchant_confirm_id", res)
        self.assertIn("order_12345", self.paid_orders)

    # --- PAYME TESTS ---
    def test_payme_create_payment_url(self):
        res = self.payme.create_payment(amount=300000, order_id="order_12345")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount_tiyin"], 30000000)
        self.assertTrue(res["payment_url"].startswith("https://checkout.paycom.uz/"))

        # Decode params
        b64_part = res["payment_url"].replace("https://checkout.paycom.uz/", "")
        decoded = base64.b64decode(b64_part).decode('utf-8')
        self.assertIn("m=test_payme_mid", decoded)
        self.assertIn("ac.order_id=order_12345", decoded)
        self.assertIn("a=30000000", decoded)

    def test_payme_auth_header(self):
        valid_cred = base64.b64encode(b"Paycom:test_payme_sec").decode('utf-8')
        auth_header = f"Basic {valid_cred}"
        self.assertTrue(self.payme.verify_auth_header(auth_header))
        self.assertFalse(self.payme.verify_auth_header("Basic invalid_base64"))

    def test_payme_json_rpc_lifecycle(self):
        tx_store = {}

        # 1. CheckPerformTransaction
        check_req = {
            "id": 1,
            "method": "CheckPerformTransaction",
            "params": {
                "amount": 30000000,
                "account": {"order_id": "order_12345"}
            }
        }
        check_res = self.payme.handle_json_rpc(check_req, self.get_order_func, self.mark_paid_func, tx_store)
        self.assertTrue(check_res["result"]["allow"])

        # 2. CreateTransaction
        create_req = {
            "id": 2,
            "method": "CreateTransaction",
            "params": {
                "id": "payme_tx_999",
                "amount": 30000000,
                "account": {"order_id": "order_12345"}
            }
        }
        create_res = self.payme.handle_json_rpc(create_req, self.get_order_func, self.mark_paid_func, tx_store)
        self.assertEqual(create_res["result"]["state"], 1)

        # 3. PerformTransaction
        perform_req = {
            "id": 3,
            "method": "PerformTransaction",
            "params": {"id": "payme_tx_999"}
        }
        perform_res = self.payme.handle_json_rpc(perform_req, self.get_order_func, self.mark_paid_func, tx_store)
        self.assertEqual(perform_res["result"]["state"], 2)
        self.assertIn("order_12345", self.paid_orders)

    # --- UZUM TESTS ---
    def test_uzum_create_payment_url(self):
        res = self.uzum.create_payment(amount=300000, order_id="order_12345")
        self.assertTrue(res["success"])
        self.assertIn("https://www.uzumbank.uz/open-service?", res["payment_url"])
        self.assertIn("amount=300000", res["payment_url"])

    # --- FACTORY TESTS ---
    def test_factory_instantiation(self):
        self.assertIsInstance(get_payment_provider("click"), ClickProvider)
        self.assertIsInstance(get_payment_provider("payme"), PaymeProvider)
        self.assertIsInstance(get_payment_provider("uzum"), UzumProvider)
        self.assertIsInstance(get_payment_provider("mock"), MockPaymentProvider)

if __name__ == "__main__":
    unittest.main()
