import unittest

import pandas as pd

from apply_queue import compute_market_queue_adjustment, location_matches_focus, market_apply_now_allowed
from config import get_market_profile


class ApplyQueueMarketAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.ma_profile = get_market_profile("ma", "all")

    def test_non_target_language_role_is_forced_to_review(self):
        row = pd.Series(
            {
                "title": "Service Desk Analyst (Turkish) - Rabat",
                "description": "Technical support for end users.",
                "company": "HCLTech",
            }
        )
        penalty, reasons, force_review = compute_market_queue_adjustment(row, self.ma_profile)
        self.assertTrue(force_review)
        self.assertLessEqual(penalty, -12)
        self.assertIn("language:tr", reasons)

    def test_core_junior_infra_role_keeps_no_penalty(self):
        row = pd.Series(
            {
                "title": "Junior infra - Casablanca",
                "description": "Configuration of servers, user support, and network monitoring.",
                "company": "Confidential",
            }
        )
        penalty, reasons, force_review = compute_market_queue_adjustment(row, self.ma_profile)
        self.assertEqual(penalty, 0)
        self.assertEqual(reasons, "")
        self.assertFalse(force_review)

    def test_product_owner_is_forced_to_review(self):
        row = pd.Series(
            {
                "title": "Proxy Product Owner (F/H) - Casablanca",
                "description": "Service desk governance and roadmap.",
                "company": "Sofrecom Maroc",
            }
        )
        penalty, reasons, force_review = compute_market_queue_adjustment(row, self.ma_profile)
        self.assertTrue(force_review)
        self.assertLessEqual(penalty, -10)
        self.assertIn("product_owner", reasons)

    def test_italophone_service_desk_is_demoted_for_non_target_language(self):
        row = pd.Series(
            {
                "title": "Technicien Service Desk / Support IT (Franco-Italophone) - Casablanca",
                "description": "Agent helpdesk italophone pour assistance utilisateurs.",
                "company": "AFRICAWORK",
            }
        )
        penalty, reasons, force_review = compute_market_queue_adjustment(row, self.ma_profile)
        self.assertTrue(force_review)
        self.assertLessEqual(penalty, -12)
        self.assertIn("language:it", reasons)

    def test_generic_engineer_language_title_cannot_be_apply_now(self):
        row = pd.Series(
            {
                "title": "Ingenieur Anglophone - Casablanca",
                "description": "Missions IT et telecom.",
                "company": "Consulting",
            }
        )
        allowed, reason = market_apply_now_allowed(row, self.ma_profile)
        self.assertFalse(allowed)
        self.assertEqual(reason, "generic_language_title")

    def test_clear_junior_it_title_can_be_apply_now(self):
        row = pd.Series(
            {
                "title": "Technicien IT Junior CDI - Tanger",
                "description": "Support N1/N2, maintenance postes et reseau.",
                "company": "Manpower",
            }
        )
        allowed, reason = market_apply_now_allowed(row, self.ma_profile)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_technicien_en_informatique_can_be_apply_now(self):
        row = pd.Series(
            {
                "title": "Technicien en Informatique - Rabat",
                "description": "Administration serveurs, support utilisateurs, maintenance parc.",
                "company": "Confidentiel",
            }
        )
        allowed, reason = market_apply_now_allowed(row, self.ma_profile)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")


    def test_rabat_or_remote_focus_accepts_remote_jobs(self):
        self.assertTrue(location_matches_focus("Casablanca", "rabat_or_remote", "ma", is_remote=True))
        self.assertFalse(location_matches_focus("Casablanca", "rabat_or_remote", "ma", is_remote=False))

    def test_rabat_focus_matches_sale_cluster(self):
        self.assertTrue(location_matches_focus("Salé, Technopolis", "rabat", "ma"))
        self.assertTrue(location_matches_focus("Rabat et région - Maroc", "rabat", "ma"))
        self.assertFalse(location_matches_focus("Casablanca", "rabat", "ma"))


if __name__ == "__main__":
    unittest.main()

