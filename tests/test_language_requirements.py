import unittest

import adzuna_fetch as af


class LanguageRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        af.configure_market("be")

    def test_english_and_dutch_mandatory_is_blocked(self):
        text = "Azure Platform Support Engineer - English and Dutch (Mandatory Speaking)."
        req = af.language_requirements(text)
        self.assertIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "blocked_language_req:dutch_required")

    def test_dutch_plus_is_optional_only(self):
        text = "Dutch is a plus, English required."
        req = af.language_requirements(text)
        self.assertIn("nl", req["optional_langs"])
        self.assertNotIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "")

    def test_french_and_dutch_mastery_is_blocked(self):
        text = "Nous demandons une bonne maitrise du francais et du neerlandais."
        req = af.language_requirements(text)
        self.assertIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "blocked_language_req:dutch_required")

    def test_nederlands_plus_is_not_blocked(self):
        text = "Kennis van Engels is vereist. Nederlands is een plus."
        req = af.language_requirements(text)
        self.assertIn("nl", req["optional_langs"])
        self.assertNotIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "")

    def test_trilingual_fr_nl_en_is_blocked(self):
        text = "Trilingual profile required: French / Dutch / English."
        req = af.language_requirements(text)
        self.assertIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "blocked_language_req:dutch_required")

    def test_french_or_dutch_is_manual_review_not_blocked(self):
        text = "You can work in French or Dutch depending on customer portfolio."
        self.assertEqual(af.blocked_language_requirement_reason(text), "")
        self.assertEqual(af.language_manual_review_reason(text), "")

    def test_german_required_is_blocked_for_be_policy(self):
        text = "German required, English required."
        self.assertEqual(af.blocked_language_requirement_reason(text), "blocked_language_req:german_required")

    def test_html_noise_still_detects_required_dutch(self):
        text = "<html><body><div>Must speak Dutch and English required</div></body></html>"
        req = af.language_requirements(text)
        self.assertIn("nl", req["required_langs"])
        self.assertEqual(af.blocked_language_requirement_reason(text), "blocked_language_req:dutch_required")

    def test_dutch_or_french_is_acceptable(self):
        text = "Languages: English required. Dutch or French."
        self.assertTrue(af.has_acceptable_language_alternative(text))
        self.assertFalse(af.has_blocked_language_requirement(text))
        self.assertEqual(af.language_manual_review_reason(text), "")

    def test_dutch_required_still_blocks_even_with_alt_phrase(self):
        text = "Fluency in Dutch is required. Dutch or French is a plus."
        self.assertFalse(af.has_acceptable_language_alternative(text))
        self.assertTrue(af.has_blocked_language_requirement(text))

    def test_business_development_stakeholder_context_not_blocking(self):
        title = "DevOps Engineer"
        desc = "Our team includes analytics, AI, IT/OT and business development stakeholders."
        self.assertEqual(af.role_forbidden_reason(title, desc), "")
        self.assertTrue(af.role_relevant(title, desc))

    def test_business_development_in_title_blocks(self):
        title = "Business Development Analyst"
        desc = "Build pipelines and dashboards."
        self.assertEqual(af.role_forbidden_reason(title, desc), "business development")


if __name__ == "__main__":
    unittest.main()
