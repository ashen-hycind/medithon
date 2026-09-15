import sys
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import HealthAnalysisResponse, CorrelationItem, AnalysisStats
from services.analysis_service import (
    preaggregate_health_data,
    detect_exact_patterns,
    generate_heuristic_correlations,
    generate_correlation_insights,
    get_or_compute_analysis,
    _clean_json_string
)


class TestAnalysisPreaggregation(unittest.TestCase):
    def test_preaggregation_averages_and_confounders(self):
        # 3 BP readings: 2 with caffeine, 1 baseline
        bp_records = [
            {
                "id": "bp_1",
                "recorded_at": "2026-09-16T08:30:00+00:00",
                "values": {"systolic": 140, "diastolic": 88, "pulse": 76},
                "issues": [{"tag": "caffeine_intake", "label": "Caffeine within 30m"}],
                "has_red_flags": False
            },
            {
                "id": "bp_2",
                "recorded_at": "2026-09-16T09:00:00+00:00",
                "values": {"systolic": 144, "diastolic": 90, "pulse": 78},
                "issues": [{"tag": "caffeine_intake", "label": "Caffeine within 30m"}],
                "has_red_flags": False
            },
            {
                "id": "bp_3",
                "recorded_at": "2026-09-16T19:00:00+00:00",
                "values": {"systolic": 124, "diastolic": 80, "pulse": 70},
                "issues": [],
                "has_red_flags": False
            }
        ]

        # 2 Glucose readings: 1 fasting, 1 post_meal
        glucose_records = [
            {
                "id": "glu_1",
                "recorded_at": "2026-09-16T07:00:00+00:00",
                "values": {"glucose_value": 95, "unit": "mg/dL"},
                "meal_context": "fasting"
            },
            {
                "id": "glu_2",
                "recorded_at": "2026-09-16T09:30:00+00:00",
                "values": {"glucose_value": 165, "unit": "mg/dL"},
                "meal_context": "after_meal"
            }
        ]

        stats = preaggregate_health_data(bp_records, glucose_records)

        self.assertEqual(stats["total_bp_readings"], 3)
        self.assertEqual(stats["total_glucose_readings"], 2)
        # Average sys: (140 + 144 + 124) / 3 = 136.0
        self.assertEqual(stats["avg_systolic"], 136.0)
        self.assertEqual(stats["avg_diastolic"], 86.0)
        self.assertEqual(stats["avg_pulse"], 74.7)

        # Morning avg vs Evening avg
        self.assertIsNotNone(stats["morning_avg_bp"])
        self.assertEqual(stats["morning_avg_bp"]["count"], 2)
        self.assertEqual(stats["morning_avg_bp"]["systolic"], 142.0)
        self.assertIsNotNone(stats["evening_avg_bp"])
        self.assertEqual(stats["evening_avg_bp"]["systolic"], 124.0)

        # Confounder effects
        caffeine_effect = stats["confounder_effects"].get("caffeine_intake")
        self.assertIsNotNone(caffeine_effect)
        self.assertEqual(caffeine_effect["count"], 2)
        self.assertEqual(caffeine_effect["avg_systolic_with_tag"], 142.0)
        self.assertEqual(caffeine_effect["baseline_systolic"], 124.0)
        self.assertEqual(caffeine_effect["delta_systolic"], 18.0)

        # Temporal pairing: bp_2 (09:00) and glu_2 (09:30) are 30 mins apart (<= 2 hours)
        self.assertGreaterEqual(len(stats["paired_readings"]), 1)
        paired = stats["paired_readings"][0]
        self.assertLessEqual(paired["time_diff_minutes"], 120)

    def test_glucose_unit_normalization(self):
        # 5.5 mmol/L should normalize to ~99.1 mg/dL
        glucose_records = [
            {
                "id": "glu_mmol",
                "recorded_at": "2026-09-16T08:00:00Z",
                "values": {"glucose_value": 5.5, "unit": "mmol/L"},
                "meal_context": "fasting"
            }
        ]
        stats = preaggregate_health_data([], glucose_records)
        self.assertAlmostEqual(stats["avg_glucose_mg_dl"], 99.1, places=1)

    def test_acute_events_and_rapid_weight_shift(self):
        bp_records = [
            {
                "id": "bp_crisis",
                "recorded_at": "2026-09-16T12:00:00Z",
                "values": {"systolic": 188, "diastolic": 115, "pulse": 90},
                "issues": [{"tag": "chest_pain", "label": "Chest tightness"}],
                "clinical_stage": "Hypertensive Crisis",
                "has_red_flags": True
            }
        ]
        weight_records = [
            {"weight_kg": 72.0, "recorded_at": "2026-09-14T08:00:00Z"},
            {"weight_kg": 74.5, "recorded_at": "2026-09-16T08:00:00Z"}  # +2.5 kg in 48h
        ]
        stats = preaggregate_health_data(bp_records, [], weight_records)
        self.assertEqual(len(stats["urgent_events"]), 1)
        self.assertEqual(stats["urgent_events"][0]["type"], "hypertensive_crisis_warning")
        self.assertEqual(len(stats["weight_shifts"]), 1)
        self.assertEqual(stats["weight_shifts"][0]["delta_kg"], 2.5)


class TestHeuristicEngine(unittest.TestCase):
    def test_heuristic_fallback_generation(self):
        stats = {
            "total_bp_readings": 4,
            "total_glucose_readings": 3,
            "avg_systolic": 138.0,
            "avg_diastolic": 86.0,
            "avg_pulse": 75.0,
            "avg_glucose_mg_dl": 125.0,
            "morning_avg_bp": {"systolic": 142.0, "diastolic": 88.0, "count": 2},
            "evening_avg_bp": {"systolic": 128.0, "diastolic": 82.0, "count": 2},
            "confounder_effects": {
                "caffeine_intake": {
                    "count": 3,
                    "avg_systolic_with_tag": 144.0,
                    "baseline_systolic": 128.0,
                    "delta_systolic": 16.0
                }
            },
            "paired_readings": [
                {"systolic": 138, "pulse": 88, "glucose_mg_dl": 165.0}
            ],
            "urgent_events": [
                {"type": "hypertensive_crisis_warning", "systolic": 185, "diastolic": 112, "issues": ["Headache"]}
            ],
            "weight_shifts": []
        }

        resp = generate_heuristic_correlations("user_test", stats)
        self.assertIsInstance(resp, HealthAnalysisResponse)
        self.assertEqual(resp.user_id, "user_test")
        self.assertFalse(resp.is_cached)

        # Check urgent alert
        self.assertEqual(len(resp.urgent_alerts), 1)
        self.assertIn("Hypertensive Crisis", resp.urgent_alerts[0])

        # Check correlations
        categories = [c.category for c in resp.correlations]
        self.assertIn("lifestyle_trigger", categories)
        self.assertIn("metabolic_cardiovascular", categories)
        self.assertIn("longitudinal_trend", categories)

        # Check doctor summary
        self.assertIn("systolic", resp.doctor_summary.lower())
        self.assertIn("caffeine", resp.doctor_summary.lower())


class TestGeminiCorrelationReasoning(unittest.TestCase):
    def test_gemini_reasoning_with_mock(self):
        """Mock Gemini API output to test JSON cleaning, parsing, and non-diagnostic formatting."""
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_client.GenerativeModel.return_value = mock_model

        mock_llm_json = """```json
{
  "correlations": [
    {
      "category": "lifestyle_trigger",
      "confidence": "high",
      "headline": "Caffeine Elevation Observed",
      "explanation": "Systolic readings increase by 15 mmHg following caffeine consumption.",
      "evidence_count": 3,
      "clinical_suggestion": "Wait 30 minutes after coffee before measuring."
    }
  ],
  "urgent_alerts": [],
  "doctor_summary": "Patient exhibits stage 1 systolic hypertension modulated by caffeine intake."
}
```"""
        mock_response = MagicMock()
        mock_response.text = mock_llm_json
        mock_model.generate_content.return_value = mock_response

        with patch("services.analysis_service.get_gemini_client", return_value=mock_client):
            stats = {"total_bp_readings": 5, "avg_systolic": 135.0, "avg_diastolic": 85.0}
            res = generate_correlation_insights("user_mock", stats)

            self.assertIsInstance(res, HealthAnalysisResponse)
            self.assertEqual(len(res.correlations), 1)
            self.assertEqual(res.correlations[0].category, "lifestyle_trigger")
            self.assertEqual(res.correlations[0].headline, "Caffeine Elevation Observed")
            self.assertEqual(res.correlations[0].evidence_count, 3)
            self.assertIn("stage 1", res.doctor_summary)

    def test_clean_json_string(self):
        raw = "```json\n{\"test\": 123}\n```"
        self.assertEqual(_clean_json_string(raw), "{\"test\": 123}")


class TestCachingLayer(unittest.TestCase):
    def test_cache_hit_within_1_hour(self):
        user_id = "user_cache"
        mock_db = MagicMock()
        mock_profile_doc = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_profile_doc

        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
        cached_data = {
            "user_id": user_id,
            "generated_at": recent_time,
            "is_cached": False,
            "stats": {"total_bp_readings": 2, "total_glucose_readings": 0},
            "correlations": [],
            "urgent_alerts": [],
            "doctor_summary": "Cached clinical summary"
        }
        cached_doc_mock = MagicMock()
        cached_doc_mock.exists = True
        cached_doc_mock.to_dict.return_value = cached_data

        analysis_coll = MagicMock()
        analysis_coll.document.return_value.get.return_value = cached_doc_mock

        measurements_coll = MagicMock()
        measurements_coll.where.return_value.limit.return_value.stream.return_value = []

        def get_subcollection(name):
            if name == "analysis":
                return analysis_coll
            elif name == "measurements":
                return measurements_coll
            return MagicMock()

        mock_profile_doc.collection.side_effect = get_subcollection

        res = get_or_compute_analysis(user_id=user_id, db=mock_db, force_refresh=False)
        self.assertTrue(res.is_cached)
        self.assertEqual(res.doctor_summary, "Cached clinical summary")

    def test_cache_invalidation_on_force_refresh(self):
        user_id = "user_cache_refresh"
        mock_db = MagicMock()
        mock_profile_doc = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_profile_doc

        m_coll = MagicMock()
        m_coll.limit.return_value.stream.return_value = []
        mock_profile_doc.collection.return_value = m_coll

        with patch("services.analysis_service.get_gemini_client", return_value=None):
            res = get_or_compute_analysis(user_id=user_id, db=mock_db, force_refresh=True)
            self.assertFalse(res.is_cached)


class TestAnalysisApiEndpoint(unittest.TestCase):
    def setUp(self):
        sys.modules["firebase_admin"] = MagicMock()
        sys.modules["firebase_admin.auth"] = MagicMock()
        sys.modules["firebase_admin.firestore"] = MagicMock()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.analysis import router
        from security import get_current_user

        app = FastAPI()
        # Override get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"uid": "test_uid_123", "email": "test@example.com"}
        app.include_router(router)
        self.client = TestClient(app)

    @patch("routes.analysis.get_firestore_db", return_value=None)
    def test_get_correlations_endpoint(self, mock_db):
        with patch("services.analysis_service.get_gemini_client", return_value=None):
            resp = self.client.get("/api/analysis/correlations")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["user_id"], "test_uid_123")
            self.assertIn("stats", data)
            self.assertIn("correlations", data)
            self.assertIn("doctor_summary", data)

    @patch("routes.analysis.get_firestore_db", return_value=None)
    def test_post_generate_endpoint(self, mock_db):
        with patch("services.analysis_service.get_gemini_client", return_value=None):
            resp = self.client.post("/api/analysis/generate")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["user_id"], "test_uid_123")


class TestExactPatternDetection(unittest.TestCase):
    def test_linear_trend_rising_falling_stable(self):
        # 5 readings rising by 6 mmHg each
        rising_bp = [
            {"id": f"bp_{i}", "recorded_at": f"2026-09-1{i}T10:00:00Z", "values": {"systolic": 120 + i * 6, "diastolic": 80}}
            for i in range(5)
        ]
        res = detect_exact_patterns(rising_bp, [])
        trend = res["bp_trend"]
        self.assertEqual(trend["trend_label"], "rising")
        self.assertEqual(trend["ols_slope_mmhg_per_reading"], 6.0)
        self.assertEqual(trend["first_systolic"], 120)
        self.assertEqual(trend["last_systolic"], 144)
        self.assertEqual(trend["absolute_change_mmhg"], 24.0)

        # 4 readings falling by 5 mmHg each
        falling_bp = [
            {"id": f"bp_{i}", "recorded_at": f"2026-09-1{i}T10:00:00Z", "values": {"systolic": 150 - i * 5, "diastolic": 85}}
            for i in range(4)
        ]
        res_falling = detect_exact_patterns(falling_bp, [])
        self.assertEqual(res_falling["bp_trend"]["trend_label"], "falling")
        self.assertEqual(res_falling["bp_trend"]["ols_slope_mmhg_per_reading"], -5.0)

        # Stable readings (slope 0)
        stable_bp = [
            {"id": f"bp_{i}", "recorded_at": f"2026-09-1{i}T10:00:00Z", "values": {"systolic": 122, "diastolic": 80}}
            for i in range(4)
        ]
        res_stable = detect_exact_patterns(stable_bp, [])
        self.assertEqual(res_stable["bp_trend"]["trend_label"], "stable")
        self.assertEqual(res_stable["bp_trend"]["ols_slope_mmhg_per_reading"], 0.0)

    def test_aha_staging_distribution(self):
        records = [
            {"id": "1", "recorded_at": "2026-09-10T10:00:00Z", "values": {"systolic": 115, "diastolic": 75}},  # Normal
            {"id": "2", "recorded_at": "2026-09-11T10:00:00Z", "values": {"systolic": 125, "diastolic": 78}},  # Elevated
            {"id": "3", "recorded_at": "2026-09-12T10:00:00Z", "values": {"systolic": 134, "diastolic": 82}},  # Stage 1
            {"id": "4", "recorded_at": "2026-09-13T10:00:00Z", "values": {"systolic": 145, "diastolic": 92}},  # Stage 2
            {"id": "5", "recorded_at": "2026-09-14T10:00:00Z", "values": {"systolic": 185, "diastolic": 125}}, # Crisis
        ]
        patterns = detect_exact_patterns(records, [])
        dist = patterns["bp_stage_distribution"]

        self.assertEqual(dist["Normal"]["count"], 1)
        self.assertEqual(dist["Normal"]["pct"], 20.0)
        self.assertEqual(dist["Elevated"]["count"], 1)
        self.assertEqual(dist["Stage 1 Hypertension"]["count"], 1)
        self.assertEqual(dist["Stage 2 Hypertension"]["count"], 1)
        self.assertEqual(dist["Hypertensive Crisis"]["count"], 1)

    def test_consecutive_elevated_streaks(self):
        records = [
            {"id": "1", "recorded_at": "2026-09-10T10:00:00Z", "values": {"systolic": 118, "diastolic": 76}},  # Normal
            {"id": "2", "recorded_at": "2026-09-11T10:00:00Z", "values": {"systolic": 135, "diastolic": 85}},  # Stage 1
            {"id": "3", "recorded_at": "2026-09-12T10:00:00Z", "values": {"systolic": 142, "diastolic": 92}},  # Stage 2
            {"id": "4", "recorded_at": "2026-09-13T10:00:00Z", "values": {"systolic": 138, "diastolic": 88}},  # Stage 1
            {"id": "5", "recorded_at": "2026-09-14T10:00:00Z", "values": {"systolic": 116, "diastolic": 74}},  # Normal
            {"id": "6", "recorded_at": "2026-09-15T10:00:00Z", "values": {"systolic": 132, "diastolic": 82}},  # Stage 1
        ]
        patterns = detect_exact_patterns(records, [])
        streak = patterns["consecutive_elevated_streak"]
        self.assertEqual(streak["max_streak"], 3)
        self.assertEqual(streak["current_streak"], 1)

    def test_pulse_pressure_statistics(self):
        records = [
            {"id": "1", "recorded_at": "2026-09-10T10:00:00Z", "values": {"systolic": 150, "diastolic": 80}},  # PP = 70 (wide)
            {"id": "2", "recorded_at": "2026-09-11T10:00:00Z", "values": {"systolic": 120, "diastolic": 80}},  # PP = 40 (normal)
            {"id": "3", "recorded_at": "2026-09-12T10:00:00Z", "values": {"systolic": 145, "diastolic": 75}},  # PP = 70 (wide)
        ]
        patterns = detect_exact_patterns(records, [])
        pp = patterns["pulse_pressure_stats"]
        self.assertIsNotNone(pp)
        self.assertEqual(pp["mean_mmhg"], 60.0)
        self.assertEqual(pp["min_mmhg"], 40)
        self.assertEqual(pp["max_mmhg"], 70)
        self.assertEqual(pp["wide_pp_count"], 2)
        self.assertEqual(pp["narrow_pp_count"], 0)

    def test_glycemic_variability_cv(self):
        glucose_records = [
            {"id": "g1", "recorded_at": "2026-09-10T08:00:00Z", "values": {"glucose_value": 80, "unit": "mg/dL"}},
            {"id": "g2", "recorded_at": "2026-09-10T12:00:00Z", "values": {"glucose_value": 180, "unit": "mg/dL"}},
            {"id": "g3", "recorded_at": "2026-09-10T18:00:00Z", "values": {"glucose_value": 100, "unit": "mg/dL"}},
        ]
        patterns = detect_exact_patterns([], glucose_records)
        glu_cv = patterns["glucose_variability_cv"]
        self.assertIsNotNone(glu_cv)
        self.assertEqual(glu_cv["min_mg_dl"], 80.0)
        self.assertEqual(glu_cv["max_mg_dl"], 180.0)
        self.assertEqual(glu_cv["range_mg_dl"], 100.0)
        self.assertGreater(glu_cv["cv_pct"], 20.0)

    def test_symptom_cooccurrence_matrix(self):
        bp_records = [
            {
                "id": "bp_1",
                "recorded_at": "2026-09-10T10:00:00Z",
                "values": {"systolic": 145, "diastolic": 92}, # Stage 2
                "issues": [{"tag": "poor_sleep", "label": "Poor Sleep"}]
            },
            {
                "id": "bp_2",
                "recorded_at": "2026-09-11T10:00:00Z",
                "values": {"systolic": 142, "diastolic": 90}, # Stage 2
                "issues": [{"tag": "poor_sleep", "label": "Poor Sleep"}]
            },
            {
                "id": "bp_3",
                "recorded_at": "2026-09-12T10:00:00Z",
                "values": {"systolic": 118, "diastolic": 76}, # Normal
                "issues": []
            }
        ]
        patterns = detect_exact_patterns(bp_records, [])
        co = patterns["symptom_co_occurrence"]
        self.assertIn("poor_sleep", co)
        ps = co["poor_sleep"]
        self.assertEqual(ps["total_occurrences"], 2)
        self.assertEqual(ps["co_occurring_with_stage1_plus"], 2)
        self.assertEqual(ps["elevated_bp_rate_pct"], 100.0)
        self.assertEqual(ps["avg_systolic_when_present"], 143.5)

    def test_heuristic_correlations_with_patterns(self):
        # 5 rising BP readings with poor sleep
        bp_records = [
            {
                "id": f"bp_{i}",
                "recorded_at": f"2026-09-1{i}T10:00:00Z",
                "values": {"systolic": 130 + i * 4, "diastolic": 70}, # PP = 60, 64, 68, 72, 76 (all wide PP!)
                "issues": [{"tag": "poor_sleep"}] if i < 3 else []
            }
            for i in range(5)
        ]
        stats = preaggregate_health_data(bp_records, [])
        res = generate_heuristic_correlations(user_id="pattern_user", stats=stats)

        # Check that patterns are populated in response
        self.assertIsNotNone(res.patterns)
        self.assertIn("bp_trend", res.patterns)

        # Check correlations generated
        categories = [c.category for c in res.correlations]
        self.assertIn("longitudinal_trend", categories)
        self.assertIn("metabolic_cardiovascular", categories)


class TestRoteMemoryIntegration(unittest.TestCase):
    def test_heuristic_correlations_resumes_from_rote_memory(self):
        stats = {
            "total_bp_readings": 4,
            "total_glucose_readings": 0,
            "avg_systolic": 142.0,
            "avg_diastolic": 88.0,
            "avg_pulse": 76.0,
            "avg_glucose_mg_dl": None,
            "confounder_effects": {},
            "paired_readings": [],
            "urgent_events": [],
            "weight_shifts": [],
            "patterns": {},
            "rote_memory": {
                "session_resumed": True,
                "last_checkpoint_at": "2026-09-15T12:00:00+00:00",
                "delta_readings_count": 2,
                "prior_baseline_systolic": 134.0,
                "prior_baseline_glucose": None,
                "prior_trajectory_trend": "rising",
                "trajectory_shift_summary": "Integrated 2 new reading(s). Baseline systolic shifted from 134.0 to 142.0 mmHg (+8.0 mmHg shift)."
            }
        }
        res = generate_heuristic_correlations(user_id="rote_test_user", stats=stats)
        
        # Verify rote memory is propagated
        self.assertIsNotNone(res.rote_memory)
        self.assertTrue(res.rote_memory.session_resumed)
        self.assertEqual(res.rote_memory.delta_readings_count, 2)
        self.assertEqual(res.rote_memory.prior_baseline_systolic, 134.0)

        # Verify a specific longitudinal progression correlation item was generated
        headlines = [c.headline for c in res.correlations]
        self.assertIn("Session Resumed: Longitudinal Progression", headlines)
        resumed_item = next(c for c in res.correlations if c.headline == "Session Resumed: Longitudinal Progression")
        self.assertIn("Continuing from previous checkpoint", resumed_item.explanation)
        self.assertIn("+8.0 mmHg shift", resumed_item.explanation)

    def test_get_or_compute_analysis_with_prior_checkpoint_delta(self):
        user_id = "user_rote_checkpoint"
        mock_db = MagicMock()
        mock_profile_doc = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_profile_doc

        # Prior checkpoint doc
        mock_analysis_doc = MagicMock()
        mock_analysis_doc.exists = True
        mock_analysis_doc.to_dict.return_value = {
            "user_id": user_id,
            "generated_at": "2026-09-15T10:00:00+00:00",
            "is_cached": False,
            "stats": {
                "total_bp_readings": 2,
                "total_glucose_readings": 0,
                "avg_systolic": 130.0,
                "avg_diastolic": 82.0
            },
            "patterns": {
                "bp_trend": {"trend_label": "stable"}
            },
            "correlations": [],
            "urgent_alerts": [],
            "doctor_summary": "Prior evaluation summary."
        }

        # Measurement stream has 1 new measurement after generated_at
        mock_new_bp = MagicMock()
        mock_new_bp.to_dict.return_value = {
            "id": "bp_new",
            "created_at": "2026-09-16T08:00:00+00:00",
            "recorded_at": "2026-09-16T08:00:00+00:00",
            "measurement_type": "blood_pressure",
            "values": {"systolic": 144, "diastolic": 90, "pulse": 80}
        }

        def get_subcollection(name):
            coll = MagicMock()
            if name == "analysis":
                coll.document.return_value.get.return_value = mock_analysis_doc
                return coll
            elif name == "measurements":
                coll.limit.return_value.stream.return_value = [mock_new_bp]
                # when querying newer_docs:
                coll.where.return_value.limit.return_value.stream.return_value = [mock_new_bp]
                return coll
            elif name == "weight_history":
                coll.limit.return_value.stream.return_value = []
                return coll
            return coll

        mock_profile_doc.collection.side_effect = get_subcollection

        with patch("services.analysis_service.get_gemini_client", return_value=None):
            res = get_or_compute_analysis(user_id=user_id, db=mock_db, force_refresh=False)
            self.assertFalse(res.is_cached)
            self.assertIsNotNone(res.rote_memory)
            self.assertTrue(res.rote_memory.session_resumed)
            self.assertEqual(res.rote_memory.delta_readings_count, 1)
            self.assertEqual(res.rote_memory.prior_baseline_systolic, 130.0)


if __name__ == "__main__":
    unittest.main()


