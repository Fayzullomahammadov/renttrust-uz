import os
import uuid
import datetime

class PaymentProvider:
    """Abstract Base Class for RentTrust Payment Providers."""
    def create_payment(self, amount: float, order_id: str, description: str, return_url: str = None) -> dict:
        raise NotImplementedError

    def check_payment_status(self, provider_tx_id: str) -> dict:
        raise NotImplementedError

    def refund(self, provider_tx_id: str, amount: float, reason: str = "") -> dict:
        raise NotImplementedError


class ManualPaymentProvider(PaymentProvider):
    """
    Manual Payment Provider:
    Operator confirms payment via admin dashboard or bank transfer.
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
            "instructions": "To'lov operator tomonidan admin panelda tekshirilib tasdiqlanadi (yoki Click/Payme o'tkazma cheki orqali)."
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
            "status": "refund_queued",
            "note": "Operator tomonidan kartaga qaytariladi."
        }


class MockPaymentProvider(PaymentProvider):
    """
    Mock Payment Provider:
    Used for automated tests and sandbox verification.
    """
    def create_payment(self, amount: float, order_id: str, description: str, return_url: str = None) -> dict:
        tx_id = f"mock_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "provider": "mock",
            "transaction_id": tx_id,
            "amount": amount,
            "order_id": order_id,
            "status": "paid",
            "paid_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
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


class ClickPaymePaymentProvider(PaymentProvider):
    """
    Click / Payme Payment Provider Stub:
    Per Ground Rules: Do NOT make real Click/Payme calls.
    Throws 'not configured' until commercial credentials and merchant certificates are deployed.
    """
    def create_payment(self, amount: float, order_id: str, description: str, return_url: str = None) -> dict:
        raise RuntimeError("Click/Payme to'lov tizimi integratsiyasi sozlanmagan (not configured). Iltimos, PAYMENT_MODE=manual yoki mock dan foydalaning.")

    def check_payment_status(self, provider_tx_id: str) -> dict:
        raise RuntimeError("Click/Payme to'lov tizimi integratsiyasi sozlanmagan (not configured).")

    def refund(self, provider_tx_id: str, amount: float, reason: str = "") -> dict:
        raise RuntimeError("Click/Payme to'lov tizimi integratsiyasi sozlanmagan (not configured).")


def get_payment_provider(mode: str = None) -> PaymentProvider:
    """Factory function to instantiate payment provider based on env."""
    selected_mode = (mode or os.environ.get("PAYMENT_MODE", "manual")).lower().strip()
    if selected_mode == "mock":
        return MockPaymentProvider()
    elif selected_mode in ["click", "payme", "click_payme"]:
        return ClickPaymePaymentProvider()
    else:
        return ManualPaymentProvider()
