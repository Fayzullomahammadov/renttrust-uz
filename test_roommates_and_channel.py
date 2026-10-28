import unittest
from roommates_manager import get_roommate_posts, create_roommate_post

class TestRoommatesAndChannel(unittest.TestCase):
    def test_get_roommate_posts_default(self):
        posts = get_roommate_posts()
        self.assertIsInstance(posts, list)
        self.assertGreaterEqual(len(posts), 1)

    def test_filter_roommates_by_gender(self):
        male_posts = get_roommate_posts(gender="male")
        for p in male_posts:
            self.assertEqual(p["gender"], "male")

        female_posts = get_roommate_posts(gender="female")
        for p in female_posts:
            self.assertEqual(p["gender"], "female")

    def test_filter_roommates_by_district(self):
        chilonzor_posts = get_roommate_posts(district="Chilonzor")
        for p in chilonzor_posts:
            self.assertIn("chilonzor", p["district"].lower())

    def test_create_roommate_post(self):
        new_data = {
            "name": "Azizbek",
            "age": 22,
            "gender": "male",
            "is_student": True,
            "university": "Inha universiteti",
            "district": "Mirzo Ulug'bek",
            "budget_uzs": 1800000,
            "about": "Inha 4-kurs talabasiman. Xonadosh qidiryapman.",
            "telegram_username": "aziz_inha",
            "phone_number": "+998 97 111 22 33"
        }
        res = create_roommate_post(new_data)
        self.assertEqual(res["name"], "Azizbek")
        self.assertEqual(res["gender"], "male")
        self.assertTrue(res["id"].startswith("rm_"))

        # Verify retrieved in get_roommate_posts
        all_posts = get_roommate_posts()
        self.assertTrue(any(p["id"] == res["id"] for p in all_posts))

if __name__ == "__main__":
    unittest.main()
