import unittest
from scripts.package_turnip import sanitize_suffix


class TestPackageTurnip(unittest.TestCase):
    def test_sanitize_suffix(self):
        self.assertEqual(sanitize_suffix("Turnip_Gen8_V39"), ".turnipgen8v39")
        self.assertEqual(sanitize_suffix("Turnip_v27.0.0-R2-Oneui"), ".turnipv2700r2oneui")
        self.assertEqual(sanitize_suffix("Turnip_Gen8_V39_Patched"), ".turnipgen8v39patched")
        self.assertEqual(sanitize_suffix("custom-driver"), ".turnipcustomdriver")


if __name__ == "__main__":
    unittest.main()
