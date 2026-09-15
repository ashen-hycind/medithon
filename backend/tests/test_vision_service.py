import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import ScanExtractionResponse, BloodPressureValues, ImageQualityReport
from services.vision_service import (
    detect_and_extract_measurement,
    parse_vision_response,
    _clean_json_string,
    _parse_int
)


class TestVisionService(unittest.TestCase):
    def test_offline_mock_fallback(self):
        """When GEMINI_API_KEY is not set, returns valid mock ScanExtractionResponse."""
        with patch.dict(os.environ, {}, clear=True):
            result = detect_and_extract_measurement(b"dummy_image_bytes")
            self.assertIsInstance(result, ScanExtractionResponse)
            self.assertEqual(result.detected_type, "blood_pressure")
            self.assertGreater(result.values.systolic, result.values.diastolic)
            self.assertEqual(result.values.systolic, 128)
            self.assertEqual(result.values.diastolic, 82)
            self.assertEqual(result.values.pulse, 74)
            self.assertTrue(result.quality.is_readable)
            self.assertFalse(result.quality.glare_detected)
            self.assertFalse(result.quality.display_cut_off)
            self.assertGreaterEqual(result.confidence, 0.9)
            self.assertTrue(result.scan_id.startswith("scan_"))

    def test_parse_valid_response(self):
        data = {
            "detected_type": "blood_pressure",
            "device_name": "Omron HEM-7120",
            "confidence": 0.97,
            "values": {
                "systolic": "135",
                "diastolic": "85",
                "pulse": "70"
            },
            "quality": {
                "is_readable": True,
                "glare_detected": False,
                "display_cut_off": False,
                "issues": []
            },
            "raw_detected_text": "SYS 135 DIA 85 PUL 70"
        }
        res = parse_vision_response(data, "scan_test_123")
        self.assertEqual(res.scan_id, "scan_test_123")
        self.assertEqual(res.detected_type, "blood_pressure")
        self.assertEqual(res.device_name, "Omron HEM-7120")
        self.assertEqual(res.values.systolic, 135)
        self.assertEqual(res.values.diastolic, 85)
        self.assertEqual(res.values.pulse, 70)
        self.assertEqual(res.confidence, 0.97)
        self.assertTrue(res.quality.is_readable)
        self.assertEqual(res.raw_detected_text, "SYS 135 DIA 85 PUL 70")

    def test_clean_json_string_with_markdown_fences(self):
        raw = """```json
{
  "detected_type": "blood_pressure",
  "values": {"systolic": 120, "diastolic": 80}
}
```"""
        cleaned = _clean_json_string(raw)
        self.assertTrue(cleaned.startswith("{"))
        self.assertTrue(cleaned.endswith("}"))

    def test_inverted_systolic_diastolic_correction(self):
        """When display or model inverts SYS and DIA, auto-swap if clinically plausible."""
        data = {
            "detected_type": "blood_pressure",
            "confidence": 0.88,
            "values": {
                "systolic": 82,
                "diastolic": 130,
                "pulse": 68
            },
            "quality": {
                "is_readable": True,
                "glare_detected": False,
                "display_cut_off": False,
                "issues": []
            },
            "raw_detected_text": "130 / 82"
        }
        res = parse_vision_response(data, "scan_swap")
        self.assertEqual(res.values.systolic, 130)
        self.assertEqual(res.values.diastolic, 82)
        self.assertTrue(any("inverted" in issue.lower() for issue in res.quality.issues))

    def test_non_blood_pressure_image_rejection(self):
        data = {
            "detected_type": "blood_glucose",
            "values": {"systolic": 120, "diastolic": 80},
            "quality": {"is_readable": True}
        }
        with self.assertRaises(ValueError) as ctx:
            parse_vision_response(data, "scan_wrong_device")
        self.assertIn("classified as 'blood_glucose'", str(ctx.exception))

    def test_unreadable_image_rejection(self):
        data = {
            "detected_type": "blood_pressure",
            "values": {"systolic": 0, "diastolic": 0},
            "quality": {
                "is_readable": False,
                "glare_detected": True,
                "display_cut_off": True,
                "issues": ["Severe glare covers all digits", "Screen cut off"]
            }
        }
        with self.assertRaises(ValueError) as ctx:
            parse_vision_response(data, "scan_unreadable")
        self.assertIn("Image is not readable", str(ctx.exception))

    def test_out_of_bounds_validation(self):
        data = {
            "detected_type": "blood_pressure",
            "values": {
                "systolic": 380,
                "diastolic": 80,
                "pulse": 70
            },
            "quality": {"is_readable": True}
        }
        with self.assertRaises(ValueError) as ctx:
            parse_vision_response(data, "scan_oob")
        self.assertIn("outside valid physiological bounds", str(ctx.exception))

    def test_pulse_out_of_bounds_omitted_gracefully(self):
        data = {
            "detected_type": "blood_pressure",
            "values": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 350
            },
            "quality": {"is_readable": True, "issues": []}
        }
        res = parse_vision_response(data, "scan_pulse_oob")
        self.assertIsNone(res.values.pulse)
        self.assertTrue(any("Pulse reading" in issue for issue in res.quality.issues))

    def test_parse_int_helper(self):
        self.assertEqual(_parse_int("128 mmHg"), 128)
        self.assertEqual(_parse_int(128.0), 128)
        self.assertEqual(_parse_int(75), 75)
        self.assertIsNone(_parse_int(None))
        self.assertIsNone(_parse_int(True))
        self.assertIsNone(_parse_int("abc"))



class TestScanExtractEndpoint(unittest.TestCase):
    def setUp(self):
        # Mock firebase dependencies for isolated route testing
        sys.modules["firebase_admin"] = MagicMock()
        sys.modules["firebase_admin.auth"] = MagicMock()
        sys.modules["firebase_admin.firestore"] = MagicMock()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.measurements import router

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_endpoint_valid_image_upload(self):
        import io
        from schemas import BloodPressureValues, ImageQualityReport, ScanExtractionResponse
        mock_response = ScanExtractionResponse(
            scan_id="scan_test_mock",
            detected_type="blood_pressure",
            device_name="Omron HEM-7120",
            values=BloodPressureValues(systolic=128, diastolic=82, pulse=74),
            confidence=0.95,
            quality=ImageQualityReport(is_readable=True),
            raw_detected_text="SYS 128 DIA 82 PUL 74"
        )
        with patch("routes.measurements.detect_and_extract_measurement", return_value=mock_response):
            fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            response = self.client.post(
                "/api/scan/extract",
                files={"file": ("monitor.png", io.BytesIO(fake_png), "image/png")}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["detected_type"], "blood_pressure")
            self.assertGreater(data["values"]["systolic"], data["values"]["diastolic"])
            self.assertTrue(data["quality"]["is_readable"])

    def test_endpoint_invalid_file_type(self):
        import io
        response = self.client.post(
            "/api/scan/extract",
            files={"file": ("document.txt", io.BytesIO(b"not an image"), "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid image format", response.json()["detail"])

    def test_endpoint_empty_file(self):
        import io
        response = self.client.post(
            "/api/scan/extract",
            files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()

