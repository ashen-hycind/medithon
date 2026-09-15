import sys
import os
import unittest
from pydantic import ValidationError

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import (
    BloodGlucoseValues,
    ScanExtractionResponse,
    BloodGlucoseMeasurementCreate,
    BloodGlucoseMeasurementResponse,
    ExtractedIssue
)
from services.clinical_service import classify_blood_glucose, evaluate_glucose_alerts
from services.vision_service import parse_glucose_response


class TestBloodGlucoseClinicalService(unittest.TestCase):
    def test_severe_hypoglycemia_mgdl(self):
        vals = BloodGlucoseValues(glucose_value=48.0, unit="mg/dL")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Severe Hypoglycemia")

        stage, has_red_flags, alerts = evaluate_glucose_alerts(vals, [])
        self.assertTrue(has_red_flags)
        self.assertEqual(stage, "Severe Hypoglycemia")
        self.assertTrue(any("Rule of 15" in a or "CRITICAL EMERGENCY" in a for a in alerts))

    def test_severe_hypoglycemia_mmol(self):
        # 2.5 mmol/L * 18.018 = ~45 mg/dL
        vals = BloodGlucoseValues(glucose_value=2.5, unit="mmol/L")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Severe Hypoglycemia")

    def test_hypoglycemia_alert(self):
        vals = BloodGlucoseValues(glucose_value=65.0, unit="mg/dL")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Hypoglycemia Alert")

        stage, has_red_flags, alerts = evaluate_glucose_alerts(vals, [])
        self.assertEqual(stage, "Hypoglycemia Alert")
        self.assertTrue(any("Rule of 15" in a for a in alerts))

    def test_normal_fasting(self):
        vals = BloodGlucoseValues(glucose_value=85.0, unit="mg/dL", meal_context="fasting")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Normal")

    def test_elevated_fasting_prediabetes(self):
        vals = BloodGlucoseValues(glucose_value=112.0, unit="mg/dL", meal_context="fasting")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Elevated")

    def test_normal_post_meal(self):
        vals = BloodGlucoseValues(glucose_value=128.0, unit="mg/dL", meal_context="post_meal")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Normal")

    def test_elevated_post_meal(self):
        vals = BloodGlucoseValues(glucose_value=165.0, unit="mg/dL", meal_context="post_meal")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Elevated")

    def test_hyperglycemia(self):
        vals = BloodGlucoseValues(glucose_value=240.0, unit="mg/dL")
        stage = classify_blood_glucose(vals)
        self.assertEqual(stage, "Hyperglycemia")

    def test_hyperglycemic_crisis(self):
        vals = BloodGlucoseValues(glucose_value=340.0, unit="mg/dL")
        stage, has_red_flags, alerts = evaluate_glucose_alerts(vals, [])
        self.assertEqual(stage, "Hyperglycemic Crisis")
        self.assertTrue(has_red_flags)
        self.assertTrue(any("CRITICAL ALERT" in a for a in alerts))

    def test_bounds_validation(self):
        # mg/dL outside 10 - 700
        with self.assertRaises(ValidationError):
            BloodGlucoseValues(glucose_value=5.0, unit="mg/dL")
        with self.assertRaises(ValidationError):
            BloodGlucoseValues(glucose_value=800.0, unit="mg/dL")

        # mmol/L outside 0.5 - 40.0
        with self.assertRaises(ValidationError):
            BloodGlucoseValues(glucose_value=0.2, unit="mmol/L")
        with self.assertRaises(ValidationError):
            BloodGlucoseValues(glucose_value=55.0, unit="mmol/L")


class TestGlucometerVisionParsing(unittest.TestCase):
    def test_parse_valid_glucometer_mgdl(self):
        data = {
            "detected_type": "blood_glucose",
            "device_name": "Accu-Chek Instant",
            "confidence": 0.97,
            "values": {
                "glucose_value": "104",
                "unit": "mg/dL",
                "meal_context": "fasting"
            },
            "quality": {
                "is_readable": True,
                "glare_detected": False,
                "display_cut_off": False,
                "issues": []
            },
            "raw_detected_text": "104 mg/dL 8:30 AM"
        }
        res = parse_glucose_response(data, "scan_glu_123")
        self.assertIsInstance(res, ScanExtractionResponse)
        self.assertEqual(res.detected_type, "blood_glucose")
        self.assertEqual(res.device_name, "Accu-Chek Instant")
        self.assertEqual(res.values.glucose_value, 104.0)
        self.assertEqual(res.values.unit, "mg/dL")
        self.assertEqual(res.values.meal_context, "fasting")
        self.assertEqual(res.confidence, 0.97)

    def test_parse_valid_glucometer_mmol(self):
        data = {
            "detected_type": "blood_glucose",
            "device_name": "OneTouch Verio",
            "confidence": 0.95,
            "values": {
                "glucose_value": 5.8,
                "unit": "mmol/L",
                "meal_context": "after_meal"
            },
            "quality": {
                "is_readable": True,
                "glare_detected": False,
                "display_cut_off": False,
                "issues": []
            },
            "raw_detected_text": "5.8 mmol/L"
        }
        res = parse_glucose_response(data, "scan_glu_456")
        self.assertEqual(res.values.glucose_value, 5.8)
        self.assertEqual(res.values.unit, "mmol/L")
        self.assertEqual(res.values.meal_context, "after_meal")

    def test_unreadable_glucometer_raises_error(self):
        data = {
            "detected_type": "blood_glucose",
            "quality": {
                "is_readable": False,
                "issues": ["heavy glare on LCD"]
            },
            "values": {}
        }
        with self.assertRaises(ValueError):
            parse_glucose_response(data, "scan_glu_err")


if __name__ == "__main__":
    unittest.main()
