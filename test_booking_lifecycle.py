import unittest
import datetime
from booking_manager import (
    record_booking_event,
    get_booking_events,
    evaluate_cancellation,
    record_dispute,
    resolve_dispute
)

class TestBookingLifecycle(unittest.TestCase):
    def test_booking_event_recording(self):
        booking_id = "test_bk_001"
        evt = record_booking_event(booking_id, "HOLD", "FUNDED", "tenant", "Remainder paid")
        self.assertEqual(evt["booking_id"], booking_id)
        self.assertEqual(evt["from_state"], "HOLD")
        self.assertEqual(evt["to_state"], "FUNDED")

        history = get_booking_events(booking_id)
        self.assertTrue(any(e["event_id"] == evt["event_id"] for e in history))

    def test_cancellation_more_than_72_hours(self):
        """Cancelled 5 days before move in -> CANCELLED_REFUND."""
        now = datetime.datetime.now(datetime.timezone.utc)
        move_in = (now + datetime.timedelta(days=5)).strftime("%Y-%m-%d")

        eval_res = evaluate_cancellation(move_in_date_str=move_in, cancelled_at=now)
        self.assertEqual(eval_res["result_state"], "CANCELLED_REFUND")
        self.assertTrue(eval_res["refund_to_tenant"])
        self.assertFalse(eval_res["compensation_to_landlord"])

    def test_cancellation_less_than_72_hours(self):
        """Cancelled 24 hours before move in -> CANCELLED_COMPENSATION."""
        now = datetime.datetime.now(datetime.timezone.utc)
        move_in = (now + datetime.timedelta(hours=24)).strftime("%Y-%m-%d")

        eval_res = evaluate_cancellation(move_in_date_str=move_in, cancelled_at=now)
        self.assertEqual(eval_res["result_state"], "CANCELLED_COMPENSATION")
        self.assertFalse(eval_res["refund_to_tenant"])
        self.assertTrue(eval_res["compensation_to_landlord"])

    def test_cancellation_landlord_fault(self):
        """Landlord fault -> 100% immediate refund regardless of time."""
        now = datetime.datetime.now(datetime.timezone.utc)
        move_in = (now + datetime.timedelta(hours=5)).strftime("%Y-%m-%d")

        eval_res = evaluate_cancellation(move_in_date_str=move_in, cancelled_at=now, is_landlord_fault=True)
        self.assertEqual(eval_res["result_state"], "CANCELLED_REFUND")
        self.assertTrue(eval_res["refund_to_tenant"])

    def test_dispute_creation_and_resolution(self):
        disp = record_dispute("test_bk_002", "tenant", "Konditsioner ishlamayapti", ["photo1.jpg"])
        self.assertEqual(disp["status"], "under_review")

        resolved = resolve_dispute(disp["dispute_id"], "refund_tenant", "Ijarachi dalillari tasdiqlandi")
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["resolution"]["decision"], "refund_tenant")

if __name__ == "__main__":
    unittest.main()
