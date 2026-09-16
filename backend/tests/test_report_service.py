"""
Unit tests for Doctor Health Report Service & Endpoint
======================================================
Verifies deterministic statistics, chart generation, ReportLab PDF assembly,
dynamic recalculation upon adding records, and endpoint functionality.
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from services.report_service import (
    calculate_modality_stats,
    generate_bp_chart,
    generate_spo2_chart,
    generate_glucose_chart,
    generate_weight_chart,
    build_doctor_health_report_pdf
)


class TestReportService(unittest.TestCase):

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.bp_records = [
            {
                "id": "bp_1",
                "recorded_at": (self.now - timedelta(days=3)).isoformat(),
                "values": {"systolic": 128, "diastolic": 82, "pulse": 68}
            },
            {
                "id": "bp_2",
                "recorded_at": (self.now - timedelta(days=2)).isoformat(),
                "values": {"systolic": 134, "diastolic": 86, "pulse": 72}
            },
            {
                "id": "bp_3",
                "recorded_at": (self.now - timedelta(days=1)).isoformat(),
                "values": {"systolic": 138, "diastolic": 88, "pulse": 74}
            }
        ]

        self.spo2_records = [
            {
                "id": "spo2_1",
                "recorded_at": (self.now - timedelta(days=2)).isoformat(),
                "values": {"spo2": 98, "pulse": 70}
            },
            {
                "id": "spo2_2",
                "recorded_at": (self.now - timedelta(days=1)).isoformat(),
                "values": {"spo2": 97, "pulse": 72}
            }
        ]

        self.glucose_records = [
            {
                "id": "glu_1",
                "recorded_at": (self.now - timedelta(days=2)).isoformat(),
                "values": {"glucose_value": 95, "unit": "mg/dL", "meal_context": "fasting"}
            },
            {
                "id": "glu_2",
                "recorded_at": (self.now - timedelta(days=1)).isoformat(),
                "values": {"glucose_value": 142, "unit": "mg/dL", "meal_context": "after_meal"}
            }
        ]

        self.weight_records = [
            {
                "id": "w_1",
                "recorded_at": (self.now - timedelta(days=5)).isoformat(),
                "values": {"weight": 78.0, "unit": "kg"}
            },
            {
                "id": "w_2",
                "recorded_at": (self.now - timedelta(days=1)).isoformat(),
                "values": {"weight": 78.6, "unit": "kg"}
            }
        ]

        self.profile = {
            "name": "Alex Mercer",
            "dob": "1978-06-15",
            "gender": "Male",
            "height_cm": 178,
            "weight_kg": 78.6
        }

    def test_calculate_modality_stats_deterministic(self):
        stats = calculate_modality_stats(self.bp_records, "systolic")
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["latest"]["val"], 138.0)
        self.assertEqual(stats["previous"]["val"], 134.0)
        self.assertEqual(stats["change"], 4.0)
        self.assertEqual(stats["avg"], round((128 + 134 + 138) / 3, 1))
        self.assertEqual(stats["min"], 128.0)
        self.assertEqual(stats["max"], 138.0)
        self.assertEqual(stats["direction"], "increase")

    def test_calculate_modality_stats_empty(self):
        stats = calculate_modality_stats([], "systolic")
        self.assertEqual(stats["count"], 0)
        self.assertIsNone(stats["latest"])
        self.assertEqual(stats["avg"], 0.0)

    def test_chart_generation(self):
        bp_bytes = generate_bp_chart(self.bp_records)
        self.assertIsNotNone(bp_bytes)
        self.assertTrue(bp_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        spo2_bytes = generate_spo2_chart(self.spo2_records)
        self.assertIsNotNone(spo2_bytes)
        self.assertTrue(spo2_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        glu_bytes = generate_glucose_chart(self.glucose_records)
        self.assertIsNotNone(glu_bytes)
        self.assertTrue(glu_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        w_bytes = generate_weight_chart(self.weight_records)
        self.assertIsNotNone(w_bytes)
        self.assertTrue(w_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_build_doctor_health_report_pdf_valid(self):
        pdf_bytes = build_doctor_health_report_pdf(
            profile=self.profile,
            bp_records=self.bp_records,
            spo2_records=self.spo2_records,
            glucose_records=self.glucose_records,
            weight_records=self.weight_records,
            ai_analysis={"physician_summary": "Stable longitudinal trajectory across all modalities."}
        )
        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 5000)

    def test_dynamic_addition_recalculation(self):
        # Initial stats
        initial_stats = calculate_modality_stats(self.bp_records, "systolic")
        self.assertEqual(initial_stats["count"], 3)
        self.assertEqual(initial_stats["latest"]["val"], 138.0)

        # Add a new 4th reading
        new_record = {
            "id": "bp_4",
            "recorded_at": (self.now + timedelta(minutes=5)).isoformat(),
            "values": {"systolic": 122, "diastolic": 76, "pulse": 64}
        }
        updated_records = self.bp_records + [new_record]

        updated_stats = calculate_modality_stats(updated_records, "systolic")
        self.assertEqual(updated_stats["count"], 4)
        self.assertEqual(updated_stats["latest"]["val"], 122.0)
        self.assertEqual(updated_stats["min"], 122.0)
        self.assertNotEqual(initial_stats["avg"], updated_stats["avg"])

    @patch("routes.reports.get_firestore_db")
    @patch("services.report_service.get_or_compute_analysis")
    def test_doctor_report_endpoint(self, mock_ai, mock_db_getter):
        from security import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"uid": "test_user_123", "email": "doc@test.com"}

        # Mock firestore collections
        mock_db = MagicMock()
        mock_profile_doc = MagicMock()
        mock_profile_doc.exists = True
        mock_profile_doc.to_dict.return_value = self.profile
        mock_db.collection.return_value.document.return_value.get.return_value = mock_profile_doc

        # Mock measurements stream
        mock_meas_docs = []
        for r in self.bp_records:
            d = MagicMock()
            d.to_dict.return_value = {**r, "measurement_type": "blood_pressure"}
            mock_meas_docs.append(d)
        for r in self.spo2_records:
            d = MagicMock()
            d.to_dict.return_value = {**r, "measurement_type": "spo2"}
            mock_meas_docs.append(d)
        for r in self.glucose_records:
            d = MagicMock()
            d.to_dict.return_value = {**r, "measurement_type": "blood_glucose"}
            mock_meas_docs.append(d)

        mock_db.collection.return_value.document.return_value.collection.return_value.limit.return_value.stream.return_value = mock_meas_docs
        mock_db_getter.return_value = mock_db
        mock_ai.return_value = MagicMock(model_dump=lambda: {"physician_summary": "Test summary"})

        try:
            client = TestClient(app)
            response = client.post("/api/reports/doctor")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF"))
            self.assertIn("Doctor_Health_Report", response.headers.get("content-disposition", ""))
        finally:
            app.dependency_overrides.pop(get_current_user, None)


if __name__ == "__main__":
    unittest.main()
