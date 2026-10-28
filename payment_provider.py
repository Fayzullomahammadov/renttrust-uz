import os
import uuid
import datetime
import hashlib
import base64
import json
import hmac

class PaymentProvider:
    """RentTrust UZ to'lov provayderlari uchun asosiy sinf."""
    def create_payment(self, amount: float, order_id: str, description: str, return_url: str = None) -> dict:
        raise NotImplementedError

    def check_payment_status(self, provider_tx_id: str) -> dict:
        raise NotImplementedError

    def refund(self, provider_tx_id: str, amount: float, reason: str = "") -> dict:
        raise NotImplementedError


class ClickProvider(PaymentProvider):
    """
    O'zbekiston Click to'lov tizimi rasmiy integratsiyasi (Click Shop API).
    Hujjat: https://docs.click.uz/
    """
    def __init__(self, service_id: str = None, merchant_id: str = None, secret_key: str = None):
        self.service_id = service_id or os.environ.get("CLICK_SERVICE_ID", "12345")
        self.merchant_id = merchant_id or os.environ.get("CLICK_MERCHANT_ID", "67890")
        self.secret_key = secret_key or os.environ.get("CLICK_SECRET_KEY", "click_secret_key_mock")

    def create_payment(self, amount: float, order_id: str, description: str = "RentTrust Escrow Depozit", return_url: str = None) -> dict:
        """
        Click to'lov havolasini generatsiya qilish (Web va Telegram WebApp uchun).
        """
        amount_int = int(amount)
        base_url = "https://my.click.uz/services/pay"
        params = f"?service_id={self.service_id}&merchant_id={self.merchant_id}&amount={amount_int}&transaction_param={order_id}"
        if return_url:
            params += f"&return_url={return_url}"
        payment_url = f"{base_url}{params}"
        
        return {
            "success": True,
            "provider": "click",
            "order_id": order_id,
            "amount": amount_int,
            "payment_url": payment_url,
            "description": description
        }

    def verify_click_signature(self, click_trans_id: str, service_id: str, merchant_trans_id: str, 
                               amount: str, action: str, sign_time: str, sign_string: str) -> bool:
        """
        Click imzosini tekshirish:
        MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        """
        raw_sign = f"{click_trans_id}{service_id}{self.secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
        expected_sign = hashlib.md5(raw_sign.encode('utf-8')).hexdigest()
        return expected_sign.lower() == str(sign_string).lower()

    def handle_prepare(self, data: dict, get_order_func) -> dict:
        """
        Click Action 0 (Prepare) bosqichi:
        """
        click_trans_id = str(data.get("click_trans_id", ""))
        service_id = str(data.get("service_id", ""))
        merchant_trans_id = str(data.get("merchant_trans_id", ""))
        amount = str(data.get("amount", "0"))
        action = str(data.get("action", "0"))
        sign_time = str(data.get("sign_time", ""))
        sign_string = str(data.get("sign_string", ""))

        if not self.verify_click_signature(click_trans_id, service_id, merchant_trans_id, amount, action, sign_time, sign_string):
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -1,
                "error_note": "Imzo xato (SIGN_CHECK_FAILED)"
            }

        order = get_order_func(merchant_trans_id)
        if not order:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -5,
                "error_note": "Buyurtma topilmadi (ORDER_NOT_FOUND)"
            }

        expected_amount = float(order.get("amount_uzs", 0))
        if abs(expected_amount - float(amount)) > 1.0:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -2,
                "error_note": "Noto'g'ri to'lov summasi (INCORRECT_AMOUNT)"
            }

        if order.get("status") in ["held", "released_to_landlord", "completed"]:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -4,
                "error_note": "Buyurtma avval to'langan (ALREADY_PAID)"
            }

        merchant_prepare_id = f"prep_{uuid.uuid4().hex[:8]}"
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": merchant_prepare_id,
            "error": 0,
            "error_note": "Success"
        }

    def handle_complete(self, data: dict, get_order_func, mark_paid_func) -> dict:
        """
        Click Action 1 (Complete) bosqichi:
        """
        click_trans_id = str(data.get("click_trans_id", ""))
        service_id = str(data.get("service_id", ""))
        merchant_trans_id = str(data.get("merchant_trans_id", ""))
        amount = str(data.get("amount", "0"))
        action = str(data.get("action", "1"))
        sign_time = str(data.get("sign_time", ""))
        sign_string = str(data.get("sign_string", ""))
        error = int(data.get("error", 0))

        if not self.verify_click_signature(click_trans_id, service_id, merchant_trans_id, amount, action, sign_time, sign_string):
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -1,
                "error_note": "Imzo xato (SIGN_CHECK_FAILED)"
            }

        order = get_order_func(merchant_trans_id)
        if not order:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -5,
                "error_note": "Buyurtma topilmadi"
            }

        if error < 0:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": -9,
                "error_note": "Tranzaksiya bekor qilingan (TRANSACTION_CANCELLED)"
            }

        # To'lovni tasdiqlash
        mark_paid_func(merchant_trans_id, provider_tx_id=click_trans_id, provider="click")

        merchant_confirm_id = f"conf_{uuid.uuid4().hex[:8]}"
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": merchant_confirm_id,
            "error": 0,
            "error_note": "Success"
        }


class PaymeProvider(PaymentProvider):
    """
    O'zbekiston Payme (Paycom) rasmiy integratsiyasi (JSON-RPC 2.0).
    Hujjat: https://help.paycom.uz/ru/metody-merchant-api
    """
    def __init__(self, merchant_id: str = None, secret_key: str = None):
        self.merchant_id = merchant_id or os.environ.get("PAYME_MERCHANT_ID", "payme_merchant_mock")
        self.secret_key = secret_key or os.environ.get("PAYME_SECRET_KEY", "payme_secret_mock")

    def create_payment(self, amount: float, order_id: str, description: str = "RentTrust Escrow Depozit", return_url: str = None) -> dict:
        """
        Payme Checkout havolasini generatsiya qilish (summa tiyinda: 1 so'm = 100 tiyin).
        Format: https://checkout.paycom.uz/{base64(m=ID;ac.order_id=ORD;a=TIYIN)}
        """
        amount_tiyin = int(amount * 100)
        param_str = f"m={self.merchant_id};ac.order_id={order_id};a={amount_tiyin}"
        if return_url:
            param_str += f";c={return_url}"
        encoded_params = base64.b64encode(param_str.encode('utf-8')).decode('utf-8')
        payment_url = f"https://checkout.paycom.uz/{encoded_params}"

        return {
            "success": True,
            "provider": "payme",
            "order_id": order_id,
            "amount": amount,
            "amount_tiyin": amount_tiyin,
            "payment_url": payment_url,
            "description": description
        }

    def verify_auth_header(self, auth_header: str) -> bool:
        """
        Payme Basic Auth tekshirish:
        Authorization: Basic base64(Paycom:SECRET_KEY)
        """
        if not auth_header or not auth_header.startswith("Basic "):
            return False
        try:
            encoded = auth_header.split("Basic ")[1].strip()
            decoded = base64.b64decode(encoded).decode('utf-8')
            login, key = decoded.split(":", 1)
            return login.lower() == "paycom" and key == self.secret_key
        except Exception:
            return False

    def handle_json_rpc(self, request_body: dict, get_order_func, mark_paid_func, tx_store: dict) -> dict:
        """
        Payme JSON-RPC 2.0 so'rovlarini qayta ishlash:
        - CheckPerformTransaction
        - CreateTransaction
        - PerformTransaction
        - CancelTransaction
        - CheckTransaction
        """
        req_id = request_body.get("id")
        method = request_body.get("method")
        params = request_body.get("params", {})

        def error_response(code, msg_ru, msg_uz=None):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": code,
                    "message": {
                        "ru": msg_ru,
                        "uz": msg_uz or msg_ru,
                        "en": msg_ru
                    }
                }
            }

        now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)

        if method == "CheckPerformTransaction":
            account = params.get("account", {})
            order_id = account.get("order_id")
            amount_tiyin = params.get("amount", 0)

            order = get_order_func(order_id)
            if not order:
                return error_response(-31050, "Заказ не найден", "Buyurtma topilmadi")

            expected_tiyin = int(float(order.get("amount_uzs", 0)) * 100)
            if expected_tiyin != amount_tiyin:
                return error_response(-31001, "Неверная сумма", "Noto'g'ri to'lov summasi")

            if order.get("status") in ["held", "released_to_landlord", "completed"]:
                return error_response(-31051, "Заказ уже оплачен", "Buyurtma avval to'langan")

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "allow": True
                }
            }

        elif method == "CreateTransaction":
            tx_id = params.get("id")
            account = params.get("account", {})
            order_id = account.get("order_id")
            amount_tiyin = params.get("amount", 0)

            # Mavjud tranzaksiyani tekshirish
            if tx_id in tx_store:
                existing = tx_store[tx_id]
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "create_time": existing["create_time"],
                        "transaction": existing["transaction"],
                        "state": existing["state"]
                    }
                }

            order = get_order_func(order_id)
            if not order:
                return error_response(-31050, "Заказ не найден", "Buyurtma topilmadi")

            expected_tiyin = int(float(order.get("amount_uzs", 0)) * 100)
            if expected_tiyin != amount_tiyin:
                return error_response(-31001, "Неверная сумма", "Noto'g'ri to'lov summasi")

            tx_store[tx_id] = {
                "transaction": tx_id,
                "order_id": order_id,
                "amount": amount_tiyin,
                "create_time": now_ms,
                "perform_time": 0,
                "cancel_time": 0,
                "state": 1,  # In progress
                "reason": None
            }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "create_time": now_ms,
                    "transaction": tx_id,
                    "state": 1
                }
            }

        elif method == "PerformTransaction":
            tx_id = params.get("id")
            if tx_id not in tx_store:
                return error_response(-31003, "Транзакция не найдена", "Tranzaksiya topilmadi")

            tx = tx_store[tx_id]
            if tx["state"] == 1:
                tx["state"] = 2  # Completed
                tx["perform_time"] = now_ms
                mark_paid_func(tx["order_id"], provider_tx_id=tx_id, provider="payme")

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "transaction": tx["transaction"],
                    "perform_time": tx["perform_time"],
                    "state": tx["state"]
                }
            }

        elif method == "CheckTransaction":
            tx_id = params.get("id")
            if tx_id not in tx_store:
                return error_response(-31003, "Транзакция не найдена", "Tranzaksiya topilmadi")

            tx = tx_store[tx_id]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "create_time": tx["create_time"],
                    "perform_time": tx["perform_time"],
                    "cancel_time": tx["cancel_time"],
                    "transaction": tx["transaction"],
                    "state": tx["state"],
                    "reason": tx["reason"]
                }
            }

        elif method == "CancelTransaction":
            tx_id = params.get("id")
            reason = params.get("reason")
            if tx_id not in tx_store:
                return error_response(-31003, "Транзакция не найдена", "Tranzaksiya topilmadi")

            tx = tx_store[tx_id]
            if tx["state"] == 1:
                tx["state"] = -1
            elif tx["state"] == 2:
                tx["state"] = -2
            tx["cancel_time"] = now_ms
            tx["reason"] = reason

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "transaction": tx["transaction"],
                    "cancel_time": tx["cancel_time"],
                    "state": tx["state"]
                }
            }

        else:
            return error_response(-32601, "Метод не найден", "Metod topilmadi")


class UzumProvider(PaymentProvider):
    """
    O'zbekiston Uzum Bank to'lov tizimi integratsiyasi.
    """
    def __init__(self, service_id: str = None, secret_key: str = None):
        self.service_id = service_id or os.environ.get("UZUM_SERVICE_ID", "uzum_service_mock")
        self.secret_key = secret_key or os.environ.get("UZUM_SECRET_KEY", "uzum_secret_mock")

    def create_payment(self, amount: float, order_id: str, description: str = "RentTrust Escrow Depozit", return_url: str = None) -> dict:
        amount_int = int(amount)
        # Uzum Fast Pay URL
        payment_url = f"https://www.uzumbank.uz/open-service?service_id={self.service_id}&amount={amount_int}&order_id={order_id}"
        if return_url:
            payment_url += f"&redirect_url={return_url}"

        return {
            "success": True,
            "provider": "uzum",
            "order_id": order_id,
            "amount": amount_int,
            "payment_url": payment_url,
            "description": description
        }


class MockPaymentProvider(PaymentProvider):
    """
    Sandbox / Test rejimi to'lov provayderi (avtomatlashtirilgan testlar va demo uchun).
    """
    def create_payment(self, amount: float, order_id: str, description: str = "RentTrust Escrow Depozit", return_url: str = None) -> dict:
        tx_id = f"mock_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "provider": "mock",
            "transaction_id": tx_id,
            "amount": amount,
            "order_id": order_id,
            "status": "paid",
            "paid_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "payment_url": f"https://renttrust-uz.onrender.com/mock-pay-success?tx={tx_id}&order={order_id}"
        }

    def check_payment_status(self, provider_tx_id: str) -> dict:
        return {
            "success": True,
            "transaction_id": provider_tx_id,
            "status": "paid"
        }

    def refund(self, provider_tx_id: str, amount: float, reason: str = "") -> dict:
        return {
            "success": True,
            "transaction_id": provider_tx_id,
            "amount": amount,
            "status": "refunded",
            "reason": reason
        }


class ManualPaymentProvider(PaymentProvider):
    """
    Operator tomonidan admin panel orqali tasdiqlanadigan to'lov.
    """
    def create_payment(self, amount: float, order_id: str, description: str, return_url: str = None) -> dict:
        tx_id = f"manual_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "provider": "manual",
            "transaction_id": tx_id,
            "amount": amount,
            "order_id": order_id,
            "status": "pending_confirmation",
            "instructions": "To'lov operator tomonidan admin panelda tekshirilib tasdiqlanadi."
        }

    def check_payment_status(self, provider_tx_id: str) -> dict:
        return {
            "success": True,
            "transaction_id": provider_tx_id,
            "status": "pending_confirmation"
        }

    def refund(self, provider_tx_id: str, amount: float, reason: str = "") -> dict:
        return {
            "success": True,
            "transaction_id": provider_tx_id,
            "amount": amount,
            "status": "refunded",
            "note": "Operator tomonidan kartaga qaytariladi."
        }


def get_payment_provider(provider_name: str = None) -> PaymentProvider:
    """To'lov provayderi ob'ektini qaytaruvchi Factory funksiyasi."""
    mode = (provider_name or os.environ.get("PAYMENT_MODE", "mock")).lower().strip()
    if mode == "click":
        return ClickProvider()
    elif mode == "payme":
        return PaymeProvider()
    elif mode == "uzum":
        return UzumProvider()
    elif mode == "manual":
        return ManualPaymentProvider()
    else:
        return MockPaymentProvider()
