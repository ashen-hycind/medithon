import sys
import os
import unittest
from unittest.mock import patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError
from schemas import BloodPressureValues, ExtractedIssue
from services.clinical_service import classify_blood_pressure, evaluate_clinical_alerts
from services.gemini_service import extract_issues_from_text

class TestTextExtractionAndClinicalRules(unittest.TestCase):
    def test_blood_pressure_validation(self):
        # Valid reading
        bp = BloodPressureValues(systolic=120, diastolic=80, pulse=72)
        self.assertEqual(bp.systolic, 120)
        self.assertEqual(bp.diastolic, 80)
        self.assertEqual(bp.pulse, 72)

        # Inverted reading (systolic <= diastolic) must fail
        with self.assertRaises(ValidationError):
            BloodPressureValues(systolic=80, diastolic=120)

        # Equal reading must fail
        with self.assertRaises(ValidationError):
            BloodPressureValues(systolic=90, diastolic=90)

        # Out of bounds
        with self.assertRaises(ValidationError):
            BloodPressureValues(systolic=350, diastolic=80)

    def test_clinical_staging(self):
        # Normal: <120 and <80
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=115, diastolic=75)), "Normal")

        # Elevated: 120-129 and <80
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=125, diastolic=78)), "Elevated")

        # Stage 1: 130-139 or 80-89
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=135, diastolic=75)), "Hypertension Stage 1")
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=118, diastolic=85)), "Hypertension Stage 1")

        # Stage 2: >=140 or >=90
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=145, diastolic=85)), "Hypertension Stage 2")
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=125, diastolic=95)), "Hypertension Stage 2")

        # Hypertensive Crisis: >180 and/or >120
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=185, diastolic=95)), "Hypertensive Crisis")
        self.assertEqual(classify_blood_pressure(BloodPressureValues(systolic=150, diastolic=125)), "Hypertensive Crisis")

    def test_clinical_alerts_and_red_flags(self):
        # Test crisis with acute red flags
        red_flag_issue = ExtractedIssue(
            category="symptom",
            tag="chest_pain",
            label="Chest Pain",
            is_red_flag=True
        )
        bp_crisis = BloodPressureValues(systolic=190, diastolic=115)
        stage, has_red_flags, alerts = evaluate_clinical_alerts(bp_crisis, [red_flag_issue])

        self.assertEqual(stage, "Hypertensive Crisis")
        self.assertTrue(has_red_flags)
        self.assertTrue(any("EMERGENCY WARNING" in a for a in alerts))

        # Test temporary factor alerts (caffeine / NSAID)
        caffeine_issue = ExtractedIssue(
            category="testing_condition",
            tag="caffeine_intake",
            label="Caffeine within 30 min",
            is_red_flag=False
        )
        bp_normal = BloodPressureValues(systolic=125, diastolic=78)
        stage, has_red_flags, alerts = evaluate_clinical_alerts(bp_normal, [caffeine_issue])
        self.assertFalse(has_red_flags)
        self.assertTrue(any("temporarily raise blood pressure" in a for a in alerts))

    @patch("services.gemini_service.get_gemini_client", return_value=None)
    def test_text_extraction_caffeine_and_sleep_no_med_assumption(self, _mock_client):
        text = "Drank a double espresso and had poor sleep, not on any medications."
        issues = extract_issues_from_text(text)
        tags = [i.tag for i in issues]

        self.assertIn("caffeine_intake", tags)
        self.assertIn("poor_sleep", tags)
        # Ensure no false missed dose assumption
        self.assertNotIn("bp_med_missed", tags)
        self.assertNotIn("bp_med_taken", tags)

    @patch("services.gemini_service.get_gemini_client", return_value=None)
    def test_text_extraction_dizziness_headache_and_otc_painkiller(self, _mock_client):
        text = "Felt dizzy and took an Advil for my headache"
        issues = extract_issues_from_text(text)
        tags = [i.tag for i in issues]

        self.assertIn("dizziness", tags)
        self.assertIn("headache", tags)
        self.assertIn("otc_nsaid", tags)

    @patch("services.gemini_service.get_gemini_client", return_value=None)
    def test_text_extraction_acute_red_flags(self, _mock_client):
        text = "I'm having tightness in my chest and shortness of breath"
        issues = extract_issues_from_text(text)
        
        red_flags = [i for i in issues if i.is_red_flag]
        self.assertGreater(len(red_flags), 0)
        tags = [i.tag for i in issues]
        self.assertTrue("chest_pain" in tags or "shortness_of_breath" in tags)

    @patch("services.gemini_service.get_gemini_client", return_value=None)
    def test_text_extraction_normal_no_issues(self, _mock_client):
        text = "Everything was normal, felt fine"
        issues = extract_issues_from_text(text)
        self.assertEqual(len(issues), 0)

if __name__ == "__main__":
    unittest.main()
