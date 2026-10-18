import unittest
from fee_calculator import calculate_fees

class TestFeeCalculator(unittest.TestCase):
    def test_prompt_specified_example(self):
        """
        Example that must pass per prompt:
        Rent: 3,000,000 UZS -> Tenant pays 3,060,000 (plus deposit),
        Landlord receives 2,940,000, Platform keeps 120,000.
        """
        res = calculate_fees(monthly_rent=3000000, deposit=0)
        self.assertEqual(res["monthly_rent"], 3000000.0)
        self.assertEqual(res["deposit"], 0.0)
        self.assertEqual(res["tenant_fee"], 60000)
        self.assertEqual(res["landlord_fee"], 60000)
        self.assertEqual(res["platform_fee"], 120000)
        self.assertEqual(res["tenant_total"], 3060000)
        self.assertEqual(res["landlord_receives"], 2940000)

    def test_example_with_deposit(self):
        """With deposit: deposit has 0% commission."""
        res = calculate_fees(monthly_rent=3000000, deposit=1500000)
        # Tenant pays 3,000,000 + 60,000 fee + 1,500,000 deposit = 4,560,000
        self.assertEqual(res["tenant_total"], 4560000)
        self.assertEqual(res["platform_fee"], 120000)
        self.assertEqual(res["landlord_receives"], 2940000)

    def test_higher_rent(self):
        res = calculate_fees(monthly_rent=5000000, deposit=2000000)
        self.assertEqual(res["tenant_fee"], 100000)
        self.assertEqual(res["landlord_fee"], 100000)
        self.assertEqual(res["platform_fee"], 200000)
        self.assertEqual(res["tenant_total"], 7100000)
        self.assertEqual(res["landlord_receives"], 4900000)

    def test_negative_values_raise_error(self):
        with self.assertRaises(ValueError):
            calculate_fees(monthly_rent=-100)
        with self.assertRaises(ValueError):
            calculate_fees(monthly_rent=1000000, deposit=-50)

if __name__ == "__main__":
    unittest.main()
