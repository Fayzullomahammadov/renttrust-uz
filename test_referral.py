import unittest
import os
from referral_manager import (
    generate_referral_link,
    record_referral,
    mark_referral_eligible_on_release,
    get_user_referral_stats,
    REFERRALS_FILE
)

class TestReferralSystem(unittest.TestCase):
    def setUp(self):
        # Reset test referrals file
        if os.path.exists(REFERRALS_FILE):
            try:
                os.remove(REFERRALS_FILE)
            except Exception:
                pass

    def test_referral_link_format(self):
        link = generate_referral_link(123456789)
        self.assertTrue(link.startswith("https://t.me/"))
        self.assertIn("?startapp=ref_123456789", link)

    def test_self_referral_rejected(self):
        ok, msg = record_referral(referrer_id=555, referred_id=555)
        self.assertFalse(ok)
        self.assertIn("o'zingizni", msg.lower())

    def test_same_phone_rejected(self):
        ok, msg = record_referral(referrer_id=100, referred_id=200, referrer_phone="+998901112233", referred_phone="+998901112233")
        self.assertFalse(ok)
        self.assertIn("telefon", msg.lower())

    def test_valid_referral_and_eligibility(self):
        ok, rec = record_referral(referrer_id=1001, referred_id=2002, referred_name="Umid")
        self.assertTrue(ok)
        self.assertEqual(rec["status"], "pending")

        # Stats should show 1 invited, 0 deals
        stats = get_user_referral_stats(1001)
        self.assertEqual(stats["invited_count"], 1)
        self.assertEqual(stats["deals_count"], 0)

        # Mark eligible when deal released
        eligible_rec = mark_referral_eligible_on_release(referred_id=2002, booking_id="bk_999", monthly_rent_uzs=4000000)
        self.assertIsNotNone(eligible_rec)
        self.assertEqual(eligible_rec["status"], "eligible")
        # 4,000,000 * 0.02 = 80,000; 30% of 80,000 = 24,000
        self.assertEqual(eligible_rec["cashback_uzs"], 24000)

        # Stats should now reflect 1 deal and 24,000 UZS
        updated_stats = get_user_referral_stats(1001)
        self.assertEqual(updated_stats["deals_count"], 1)
        self.assertEqual(updated_stats["total_cashback_uzs"], 24000)

if __name__ == "__main__":
    unittest.main()
