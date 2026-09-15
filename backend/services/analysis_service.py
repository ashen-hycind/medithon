"""
AI Clinical Correlation & Health Analysis Service
==================================================
This service:
1. Deterministically pre-aggregates longitudinal biometric streams (Blood Pressure,
   Blood Glucose, Weight) and context issues (symptoms, lifestyle, testing confounders).
2. Discovers temporal cross-stream pairings (BP & Glucose within +/- 2 hours).
3. Evaluates clinical correlation patterns via Gemini (gemini-flash-latest / gemini-1.5-flash)
   with strict non-diagnostic clinical boundaries, falling back to a deterministic rule engine
   if offline or when rate limits occur.
4. Implements a 1-hour Firestore caching layer at profiles/{uid}/analysis/latest.
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from schemas import (
    CorrelationItem,
    AnalysisStats,
    HealthAnalysisResponse
)


def get_gemini_client():
    """Initializes and returns the Gemini client using GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        print(f"[AnalysisService] Warning: Failed to configure Gemini client: {e}")
        return None


def _clean_json_string(raw_text: str) -> str:
    """Strips markdown code blocks, backticks, and extra whitespace to extract valid JSON."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_iso_datetime(dt_str: Any) -> Optional[datetime]:
    """Safely converts ISO-formatted string or datetime object to UTC datetime."""
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        if dt_str.tzinfo is None:
            return dt_str.replace(tzinfo=timezone.utc)
        return dt_str
    try:
        clean_str = str(dt_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# =====================================================================
# 1. Deterministic Pre-Aggregation (Math & Metrics in pure Python)
# =====================================================================

def preaggregate_health_data(
    bp_records: List[Dict[str, Any]],
    glucose_records: List[Dict[str, Any]],
    weight_records: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes factual, reproducible statistical baselines, confounder deltas,
    and temporal pairings without calling an LLM.
    """
    stats: Dict[str, Any] = {
        "total_bp_readings": len(bp_records),
        "total_glucose_readings": len(glucose_records),
        "avg_systolic": None,
        "avg_diastolic": None,
        "avg_pulse": None,
        "avg_glucose_mg_dl": None,
        "morning_avg_bp": None,
        "evening_avg_bp": None,
        "fasting_avg_glucose": None,
        "post_meal_avg_glucose": None,
        "confounder_effects": {},
        "paired_readings": [],
        "urgent_events": [],
        "weight_shifts": []
    }

    # -------------------------------------------------------------
    # Blood Pressure Aggregations
    # -------------------------------------------------------------
    systolics = []
    diastolics = []
    pulses = []
    morning_sys, morning_dia = [], []
    evening_sys, evening_dia = [], []

    # Map tags to readings with and without tag
    tag_readings: Dict[str, List[Dict[str, Any]]] = {}

    for r in bp_records:
        vals = r.get("values", {})
        sys_val = vals.get("systolic")
        dia_val = vals.get("diastolic")
        pulse_val = vals.get("pulse")

        if sys_val is not None and dia_val is not None:
            systolics.append(sys_val)
            diastolics.append(dia_val)
            if pulse_val is not None:
                pulses.append(pulse_val)

            # Check time of day
            dt = _parse_iso_datetime(r.get("recorded_at"))
            if dt:
                hour = dt.hour
                if 5 <= hour < 12:
                    morning_sys.append(sys_val)
                    morning_dia.append(dia_val)
                elif 17 <= hour <= 23:
                    evening_sys.append(sys_val)
                    evening_dia.append(dia_val)

            # Check attached issues
            issues = r.get("issues", [])
            for issue in issues:
                tag = issue.get("tag") if isinstance(issue, dict) else getattr(issue, "tag", None)
                if tag:
                    tag_readings.setdefault(tag, []).append(r)

            # Acute Hypertensive Crisis checks
            is_crisis = (sys_val >= 180 or dia_val >= 120 or r.get("clinical_stage") == "Hypertensive Crisis")
            has_red = r.get("has_red_flags", False)
            if is_crisis or has_red:
                stats["urgent_events"].append({
                    "type": "hypertensive_crisis_warning",
                    "recorded_at": r.get("recorded_at"),
                    "systolic": sys_val,
                    "diastolic": dia_val,
                    "issues": [i.get("label", i.get("tag", "")) if isinstance(i, dict) else getattr(i, "label", getattr(i, "tag", "")) for i in issues]
                })

    if systolics:
        stats["avg_systolic"] = round(sum(systolics) / len(systolics), 1)
        stats["avg_diastolic"] = round(sum(diastolics) / len(diastolics), 1)
    if pulses:
        stats["avg_pulse"] = round(sum(pulses) / len(pulses), 1)

    if morning_sys:
        stats["morning_avg_bp"] = {
            "systolic": round(sum(morning_sys) / len(morning_sys), 1),
            "diastolic": round(sum(morning_dia) / len(morning_dia), 1),
            "count": len(morning_sys)
        }
    if evening_sys:
        stats["evening_avg_bp"] = {
            "systolic": round(sum(evening_sys) / len(evening_sys), 1),
            "diastolic": round(sum(evening_dia) / len(evening_dia), 1),
            "count": len(evening_sys)
        }

    # Confounder Delta Calculations (e.g. caffeine, nsaid, sleep)
    baseline_sys = [
        r["values"]["systolic"] for r in bp_records
        if not r.get("issues") and r.get("values", {}).get("systolic") is not None
    ]
    baseline_avg_sys = (sum(baseline_sys) / len(baseline_sys)) if baseline_sys else stats["avg_systolic"]

    for tag, records_with_tag in tag_readings.items():
        tag_sys = [rec["values"]["systolic"] for rec in records_with_tag if rec.get("values", {}).get("systolic") is not None]
        if tag_sys and baseline_avg_sys is not None:
            avg_with_tag = sum(tag_sys) / len(tag_sys)
            delta = round(avg_with_tag - baseline_avg_sys, 1)
            stats["confounder_effects"][tag] = {
                "count": len(tag_sys),
                "avg_systolic_with_tag": round(avg_with_tag, 1),
                "baseline_systolic": round(baseline_avg_sys, 1),
                "delta_systolic": delta
            }

    # -------------------------------------------------------------
    # Blood Glucose Aggregations
    # -------------------------------------------------------------
    glucose_vals = []
    fasting_vals = []
    post_meal_vals = []

    for g in glucose_records:
        vals = g.get("values", {})
        val = vals.get("glucose_value")
        unit = vals.get("unit", "mg/dL")

        if val is not None:
            # Normalize to mg/dL
            val_mg_dl = val * 18.0182 if unit == "mmol/L" else float(val)
            glucose_vals.append(val_mg_dl)

            meal_ctx = g.get("meal_context")
            if meal_ctx == "fasting":
                fasting_vals.append(val_mg_dl)
            elif meal_ctx in {"after_meal", "post_meal"}:
                post_meal_vals.append(val_mg_dl)

            # Urgent glucose flags
            if val_mg_dl < 54:
                stats["urgent_events"].append({
                    "type": "severe_hypoglycemia",
                    "recorded_at": g.get("recorded_at"),
                    "glucose_mg_dl": round(val_mg_dl, 1)
                })
            elif val_mg_dl >= 300:
                stats["urgent_events"].append({
                    "type": "severe_hyperglycemia",
                    "recorded_at": g.get("recorded_at"),
                    "glucose_mg_dl": round(val_mg_dl, 1)
                })

    if glucose_vals:
        stats["avg_glucose_mg_dl"] = round(sum(glucose_vals) / len(glucose_vals), 1)
    if fasting_vals:
        stats["fasting_avg_glucose"] = round(sum(fasting_vals) / len(fasting_vals), 1)
    if post_meal_vals:
        stats["post_meal_avg_glucose"] = round(sum(post_meal_vals) / len(post_meal_vals), 1)

    # -------------------------------------------------------------
    # Temporal Cross-Stream Pairing (+/- 2 Hours: BP & Glucose)
    # -------------------------------------------------------------
    for bp in bp_records:
        bp_dt = _parse_iso_datetime(bp.get("recorded_at"))
        if not bp_dt:
            continue

        for glu in glucose_records:
            glu_dt = _parse_iso_datetime(glu.get("recorded_at"))
            if not glu_dt:
                continue

            diff_sec = abs((bp_dt - glu_dt).total_seconds())
            if diff_sec <= 7200:  # within 2 hours
                glu_val = glu.get("values", {}).get("glucose_value")
                unit = glu.get("values", {}).get("unit", "mg/dL")
                glu_mg_dl = glu_val * 18.0182 if unit == "mmol/L" else float(glu_val or 0)

                stats["paired_readings"].append({
                    "bp_id": bp.get("id"),
                    "glucose_id": glu.get("id"),
                    "time_diff_minutes": round(diff_sec / 60, 1),
                    "systolic": bp.get("values", {}).get("systolic"),
                    "diastolic": bp.get("values", {}).get("diastolic"),
                    "pulse": bp.get("values", {}).get("pulse"),
                    "glucose_mg_dl": round(glu_mg_dl, 1),
                    "meal_context": glu.get("meal_context")
                })

    # -------------------------------------------------------------
    # Fluid Shift / Weight Tracking
    # -------------------------------------------------------------
    if weight_records and len(weight_records) >= 2:
        sorted_weights = sorted(
            [w for w in weight_records if _parse_iso_datetime(w.get("recorded_at"))],
            key=lambda x: _parse_iso_datetime(x.get("recorded_at"))
        )
        for i in range(1, len(sorted_weights)):
            prev_w = sorted_weights[i - 1]
            curr_w = sorted_weights[i]
            dt_prev = _parse_iso_datetime(prev_w.get("recorded_at"))
            dt_curr = _parse_iso_datetime(curr_w.get("recorded_at"))
            if dt_prev and dt_curr:
                hours_apart = (dt_curr - dt_prev).total_seconds() / 3600
                if 0 < hours_apart <= 72:
                    delta_kg = curr_w.get("weight_kg", 0) - prev_w.get("weight_kg", 0)
                    if delta_kg >= 2.0:
                        stats["weight_shifts"].append({
                            "delta_kg": round(delta_kg, 1),
                            "hours": round(hours_apart, 1),
                            "recorded_at": curr_w.get("recorded_at")
                        })

    # Run full pattern detection on the raw records
    stats["patterns"] = detect_exact_patterns(bp_records, glucose_records)

    return stats


# =====================================================================
# 1b. Exact Pattern Detection Engine
# =====================================================================

def _classify_bp_stage(systolic: int, diastolic: int) -> str:
    """AHA/ACC 2017 blood pressure classification with exact thresholds."""
    if systolic >= 180 or diastolic >= 120:
        return "Hypertensive Crisis"
    if systolic >= 140 or diastolic >= 90:
        return "Stage 2 Hypertension"
    if systolic >= 130 or diastolic >= 80:
        return "Stage 1 Hypertension"
    if 120 <= systolic < 130 and diastolic < 80:
        return "Elevated"
    return "Normal"


def _cv_percent(values: List[float]) -> Optional[float]:
    """Coefficient of Variation (std/mean * 100). Returns None if fewer than 2 values."""
    if len(values) < 2:
        return None
    n = len(values)
    mean = sum(values) / n
    if mean == 0:
        return None
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = variance ** 0.5
    return round((std / mean) * 100, 1)


def _linear_slope(values: List[float]) -> Optional[float]:
    """
    Ordinary Least Squares slope of evenly-spaced observations.
    Positive = rising trend, Negative = falling trend.
    Returns None if fewer than 3 readings.
    """
    n = len(values)
    if n < 3:
        return None
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def detect_exact_patterns(
    bp_records: List[Dict[str, Any]],
    glucose_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes exact, reproducible pattern detection metrics from raw measurement records.
    All values are numerically precise — no estimation or rounding beyond stated precision.

    Returns:
        patterns: dict containing:
          - bp_trend:              Exact OLS slope of systolic over time + trend label
          - bp_stage_distribution: Exact count at each AHA/ACC stage
          - consecutive_elevated_streak: Longest and current run of Stage 1+ readings
          - pulse_pressure_stats:  Mean, min, max of (SYS - DIA) across all readings
          - bp_variability_cv:     Coefficient of Variation (%) for systolic and diastolic
          - glucose_variability_cv: CV% for glucose
          - time_of_day_heatmap:   Exact avg SYS/DIA/Glucose per 4-hour slot
          - post_prandial_response: Exact delta from fasting baseline per paired window
          - symptom_co_occurrence:  For each tag: exact count where SYS >= threshold
          - bp_percentiles:         25th, 50th, 75th, 90th, 95th percentile of systolic
    """
    patterns: Dict[str, Any] = {}

    # --- Sort BP records chronologically ---
    sorted_bp = sorted(
        [r for r in bp_records if r.get("values", {}).get("systolic") is not None
                                and r.get("values", {}).get("diastolic") is not None],
        key=lambda x: _parse_iso_datetime(x.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc)
    )
    sys_series = [r["values"]["systolic"] for r in sorted_bp]
    dia_series = [r["values"]["diastolic"] for r in sorted_bp]
    pulse_pressures = [s - d for s, d in zip(sys_series, dia_series)]

    # ---- 1. BP Trend (OLS Slope) ----
    slope = _linear_slope(sys_series)
    if slope is None:
        trend_label = "insufficient_data"
    elif slope > 1.0:
        trend_label = "rising"
    elif slope < -1.0:
        trend_label = "falling"
    elif abs(slope) <= 1.0 and len(sys_series) >= 3:
        # check oscillation: count direction changes
        direction_changes = sum(
            1 for i in range(1, len(sys_series) - 1)
            if (sys_series[i] - sys_series[i-1]) * (sys_series[i+1] - sys_series[i]) < 0
        )
        trend_label = "oscillating" if direction_changes >= len(sys_series) // 3 else "stable"
    else:
        trend_label = "stable"

    patterns["bp_trend"] = {
        "ols_slope_mmhg_per_reading": slope,
        "trend_label": trend_label,
        "reading_count": len(sys_series),
        "first_systolic": sys_series[0] if sys_series else None,
        "last_systolic": sys_series[-1] if sys_series else None,
        "absolute_change_mmhg": round(sys_series[-1] - sys_series[0], 1) if len(sys_series) >= 2 else None
    }

    # ---- 2. AHA Stage Distribution ----
    stage_counts: Dict[str, int] = {
        "Normal": 0,
        "Elevated": 0,
        "Stage 1 Hypertension": 0,
        "Stage 2 Hypertension": 0,
        "Hypertensive Crisis": 0
    }
    for r in sorted_bp:
        stage = _classify_bp_stage(r["values"]["systolic"], r["values"]["diastolic"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    total_bp = len(sorted_bp)
    patterns["bp_stage_distribution"] = {
        stage: {
            "count": count,
            "pct": round(count / total_bp * 100, 1) if total_bp else 0.0
        }
        for stage, count in stage_counts.items()
    }

    # ---- 3. Consecutive Elevated Streak ----
    # "Elevated" = Stage 1, Stage 2, or Crisis (SYS >= 130 or DIA >= 80)
    max_streak = 0
    current_streak = 0
    for r in sorted_bp:
        stage = _classify_bp_stage(r["values"]["systolic"], r["values"]["diastolic"])
        if stage not in {"Normal", "Elevated"}:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    patterns["consecutive_elevated_streak"] = {
        "max_streak": max_streak,
        "current_streak": current_streak,  # number of most recent readings that are Stage 1+
        "interpretation": (
            "Persistent hypertension pattern" if max_streak >= 3
            else "Intermittent elevation" if max_streak >= 1
            else "No persistent elevation detected"
        )
    }

    # ---- 4. Pulse Pressure Statistics ----
    # Normal: 40-60 mmHg. Wide PP > 60 = arterial stiffness risk.
    if pulse_pressures:
        pp_mean = round(sum(pulse_pressures) / len(pulse_pressures), 1)
        pp_min = min(pulse_pressures)
        pp_max = max(pulse_pressures)
        wide_pp_count = sum(1 for pp in pulse_pressures if pp > 60)
        narrow_pp_count = sum(1 for pp in pulse_pressures if pp < 30)
        patterns["pulse_pressure_stats"] = {
            "mean_mmhg": pp_mean,
            "min_mmhg": pp_min,
            "max_mmhg": pp_max,
            "wide_pp_count": wide_pp_count,        # PP > 60 mmHg (arterial stiffness risk)
            "narrow_pp_count": narrow_pp_count,    # PP < 30 mmHg (low cardiac output risk)
            "clinical_note": (
                f"Wide pulse pressure detected in {wide_pp_count} reading(s) (PP > 60 mmHg) — associated with arterial stiffness risk."
                if wide_pp_count > 0
                else "Pulse pressure within normal range across all readings (30-60 mmHg)."
            )
        }
    else:
        patterns["pulse_pressure_stats"] = None

    # ---- 5. BP Variability (Coefficient of Variation %) ----
    sys_cv = _cv_percent([float(v) for v in sys_series])
    dia_cv = _cv_percent([float(v) for v in dia_series])
    patterns["bp_variability_cv"] = {
        "systolic_cv_pct": sys_cv,
        "diastolic_cv_pct": dia_cv,
        "interpretation": (
            "High BP variability detected — visit-to-visit variability may independently predict cardiovascular risk."
            if (sys_cv or 0) > 10
            else "BP variability within acceptable range."
        )
    }

    # ---- 6. Systolic Percentiles ----
    if sys_series:
        sorted_sys = sorted(sys_series)
        n = len(sorted_sys)

        def _percentile(data: List[float], p: float) -> float:
            idx = (len(data) - 1) * p / 100
            lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
            return round(data[lo] + (data[hi] - data[lo]) * (idx - lo), 1)

        patterns["bp_percentiles"] = {
            "p25_systolic": _percentile(sorted_sys, 25),
            "p50_systolic": _percentile(sorted_sys, 50),
            "p75_systolic": _percentile(sorted_sys, 75),
            "p90_systolic": _percentile(sorted_sys, 90),
            "p95_systolic": _percentile(sorted_sys, 95),
            "total_readings": n
        }
    else:
        patterns["bp_percentiles"] = None

    # ---- 7. Time-of-Day Heat Map (4-hour buckets) ----
    # Buckets: Night (00-03), Early Morning (04-07), Morning (08-11),
    #          Afternoon (12-15), Evening (16-19), Late Night (20-23)
    HOUR_BUCKETS = [
        ("00-03 (Night)", 0, 4),
        ("04-07 (Early Morning)", 4, 8),
        ("08-11 (Morning)", 8, 12),
        ("12-15 (Afternoon)", 12, 16),
        ("16-19 (Evening)", 16, 20),
        ("20-23 (Late Night)", 20, 24)
    ]
    bucket_data: Dict[str, Dict[str, List[float]]] = {
        label: {"sys": [], "dia": []} for label, _, _ in HOUR_BUCKETS
    }

    for r in sorted_bp:
        dt = _parse_iso_datetime(r.get("recorded_at"))
        if not dt:
            continue
        hour = dt.hour
        for label, start, end in HOUR_BUCKETS:
            if start <= hour < end:
                bucket_data[label]["sys"].append(r["values"]["systolic"])
                bucket_data[label]["dia"].append(r["values"]["diastolic"])
                break

    heatmap = {}
    for label, data in bucket_data.items():
        if data["sys"]:
            heatmap[label] = {
                "avg_systolic": round(sum(data["sys"]) / len(data["sys"]), 1),
                "avg_diastolic": round(sum(data["dia"]) / len(data["dia"]), 1),
                "count": len(data["sys"])
            }

    # Also add glucose to heatmap
    sorted_glu = sorted(
        [g for g in glucose_records if g.get("values", {}).get("glucose_value") is not None],
        key=lambda x: _parse_iso_datetime(x.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc)
    )
    glu_bucket: Dict[str, List[float]] = {label: [] for label, _, _ in HOUR_BUCKETS}
    for g in sorted_glu:
        dt = _parse_iso_datetime(g.get("recorded_at"))
        if not dt:
            continue
        glu_val = g["values"]["glucose_value"]
        unit = g["values"].get("unit", "mg/dL")
        glu_mg_dl = glu_val * 18.0182 if unit == "mmol/L" else float(glu_val)
        hour = dt.hour
        for label, start, end in HOUR_BUCKETS:
            if start <= hour < end:
                glu_bucket[label].append(glu_mg_dl)
                break

    for label, vals in glu_bucket.items():
        if vals:
            if label not in heatmap:
                heatmap[label] = {}
            heatmap[label]["avg_glucose_mg_dl"] = round(sum(vals) / len(vals), 1)
            heatmap[label].setdefault("count", 0)

    patterns["time_of_day_heatmap"] = heatmap

    # ---- 8. Post-Prandial BP-Glucose Response ----
    # For each paired reading (BP + Glucose within ±2 hours):
    # compute exact delta from the overall fasting glucose baseline
    all_glu_mg_dl = []
    for g in glucose_records:
        val = g.get("values", {}).get("glucose_value")
        unit = g.get("values", {}).get("unit", "mg/dL")
        if val is not None:
            all_glu_mg_dl.append(val * 18.0182 if unit == "mmol/L" else float(val))

    fasting_glu_vals = [
        g["values"]["glucose_value"] * 18.0182
        if g["values"].get("unit") == "mmol/L"
        else float(g["values"]["glucose_value"])
        for g in glucose_records
        if g.get("meal_context") == "fasting"
        and g.get("values", {}).get("glucose_value") is not None
    ]
    fasting_baseline = round(sum(fasting_glu_vals) / len(fasting_glu_vals), 1) if fasting_glu_vals else None

    post_prandial_events = []
    for bp in sorted_bp:
        bp_dt = _parse_iso_datetime(bp.get("recorded_at"))
        if not bp_dt:
            continue
        for g in sorted_glu:
            glu_dt = _parse_iso_datetime(g.get("recorded_at"))
            if not glu_dt:
                continue
            diff_sec = abs((bp_dt - glu_dt).total_seconds())
            if diff_sec <= 7200:
                glu_val = g["values"]["glucose_value"]
                unit = g["values"].get("unit", "mg/dL")
                glu_mg_dl = round(glu_val * 18.0182 if unit == "mmol/L" else float(glu_val), 1)
                delta_from_fasting = round(glu_mg_dl - fasting_baseline, 1) if fasting_baseline else None
                post_prandial_events.append({
                    "recorded_at": bp.get("recorded_at"),
                    "systolic": bp["values"]["systolic"],
                    "diastolic": bp["values"]["diastolic"],
                    "pulse": bp["values"].get("pulse"),
                    "glucose_mg_dl": glu_mg_dl,
                    "delta_from_fasting_mg_dl": delta_from_fasting,
                    "meal_context": g.get("meal_context"),
                    "time_diff_minutes": round(diff_sec / 60, 1)
                })

    patterns["post_prandial_response"] = {
        "fasting_baseline_mg_dl": fasting_baseline,
        "events": post_prandial_events,
        "total_paired": len(post_prandial_events),
        "elevated_glucose_events": sum(1 for e in post_prandial_events if e["glucose_mg_dl"] >= 140),
        "max_delta_from_fasting": max(
            (e["delta_from_fasting_mg_dl"] for e in post_prandial_events if e["delta_from_fasting_mg_dl"] is not None),
            default=None
        )
    }

    # ---- 9. Glucose Variability CV ----
    if all_glu_mg_dl:
        patterns["glucose_variability_cv"] = {
            "cv_pct": _cv_percent(all_glu_mg_dl),
            "min_mg_dl": round(min(all_glu_mg_dl), 1),
            "max_mg_dl": round(max(all_glu_mg_dl), 1),
            "range_mg_dl": round(max(all_glu_mg_dl) - min(all_glu_mg_dl), 1),
            "interpretation": (
                "High glycemic variability — inconsistent glucose control detected."
                if (_cv_percent(all_glu_mg_dl) or 0) > 20
                else "Glucose variability within acceptable range."
            )
        }
    else:
        patterns["glucose_variability_cv"] = None

    # ---- 10. Symptom Co-occurrence Matrix ----
    # For each issue tag: count of readings where it co-occurs with Stage 1+ BP
    tag_cooccurrence: Dict[str, Dict[str, Any]] = {}
    for r in sorted_bp:
        stage = _classify_bp_stage(r["values"]["systolic"], r["values"]["diastolic"])
        is_elevated = stage not in {"Normal", "Elevated"}
        issues = r.get("issues", [])
        for issue in issues:
            tag = issue.get("tag") if isinstance(issue, dict) else getattr(issue, "tag", None)
            if not tag:
                continue
            if tag not in tag_cooccurrence:
                tag_cooccurrence[tag] = {
                    "total_occurrences": 0,
                    "co_occurring_with_stage1_plus": 0,
                    "avg_systolic_when_present": [],
                    "avg_diastolic_when_present": []
                }
            tag_cooccurrence[tag]["total_occurrences"] += 1
            tag_cooccurrence[tag]["avg_systolic_when_present"].append(r["values"]["systolic"])
            tag_cooccurrence[tag]["avg_diastolic_when_present"].append(r["values"]["diastolic"])
            if is_elevated:
                tag_cooccurrence[tag]["co_occurring_with_stage1_plus"] += 1

    # Finalize averages
    for tag, data in tag_cooccurrence.items():
        sys_vals = data.pop("avg_systolic_when_present")
        dia_vals = data.pop("avg_diastolic_when_present")
        data["avg_systolic_when_present"] = round(sum(sys_vals) / len(sys_vals), 1) if sys_vals else None
        data["avg_diastolic_when_present"] = round(sum(dia_vals) / len(dia_vals), 1) if dia_vals else None
        data["elevated_bp_rate_pct"] = round(
            data["co_occurring_with_stage1_plus"] / data["total_occurrences"] * 100, 1
        ) if data["total_occurrences"] else 0.0

    patterns["symptom_co_occurrence"] = tag_cooccurrence

    return patterns




# =====================================================================
# 2. Deterministic Heuristic Fallback Engine
# =====================================================================

def generate_heuristic_correlations(
    user_id: str,
    stats: Dict[str, Any]
) -> HealthAnalysisResponse:
    """
    Produces grounded, clinically sound correlation findings without calling LLMs.
    Guarantees offline functionality and protects against Gemini quota exhaustion.
    """
    correlations: List[CorrelationItem] = []
    urgent_alerts: List[str] = []

    # 1. Urgent Alerts
    for evt in stats.get("urgent_events", []):
        if evt.get("type") == "hypertensive_crisis_warning":
            sys_val = evt.get("systolic")
            dia_val = evt.get("diastolic")
            issues_str = ", ".join(evt.get("issues", []))
            alert_msg = f"Hypertensive Crisis reading ({sys_val}/{dia_val} mmHg)"
            if issues_str:
                alert_msg += f" co-occurring with reported symptoms: {issues_str}."
            else:
                alert_msg += " logged without context."
            urgent_alerts.append(alert_msg)
        elif evt.get("type") == "severe_hypoglycemia":
            urgent_alerts.append(f"Severe hypoglycemia reading ({evt.get('glucose_mg_dl')} mg/dL) requires immediate carbohydrate intake and monitoring.")
        elif evt.get("type") == "severe_hyperglycemia":
            urgent_alerts.append(f"Marked hyperglycemia reading ({evt.get('glucose_mg_dl')} mg/dL) detected.")

    # 2. Lifestyle / Confounder Triggers
    confounders = stats.get("confounder_effects", {})
    for tag, c_data in confounders.items():
        delta = c_data["delta_systolic"]
        cnt = c_data["count"]
        tag_display = tag.replace("_", " ").title()

        if delta >= 6.0 and cnt >= 1:
            confidence = "high" if cnt >= 3 else "moderate"
            correlations.append(CorrelationItem(
                category="lifestyle_trigger",
                confidence=confidence,
                headline=f"{tag_display} Associated with Systolic BP Elevation",
                explanation=f"On {cnt} occasion{'s' if cnt > 1 else ''} where {tag_display.lower()} was logged, systolic pressure averaged {c_data['avg_systolic_with_tag']} mmHg compared to your baseline average of {c_data['baseline_systolic']} mmHg (+{delta} mmHg).",
                evidence_count=cnt,
                clinical_suggestion=f"Allow adequate resting time or avoid {tag_display.lower()} prior to recording clinical blood pressure."
            ))
        elif delta <= -6.0 and cnt >= 1:
            correlations.append(CorrelationItem(
                category="lifestyle_trigger",
                confidence="moderate" if cnt >= 2 else "low",
                headline=f"{tag_display} Associated with Lower Systolic Readings",
                explanation=f"Systolic readings averaged {abs(delta)} mmHg lower during logs noting {tag_display.lower()} ({c_data['avg_systolic_with_tag']} vs {c_data['baseline_systolic']} mmHg baseline).",
                evidence_count=cnt,
                clinical_suggestion="Continue tracking to evaluate consistency of this response."
            ))

    # 3. Metabolic-Cardiovascular Interactions (Paired readings)
    paired = stats.get("paired_readings", [])
    if paired:
        post_meal_elevations = [
            p for p in paired
            if (p.get("glucose_mg_dl", 0) >= 140) and ((p.get("pulse") or 0) >= 85 or (p.get("systolic") or 0) >= 135)
        ]
        if post_meal_elevations:
            cnt = len(post_meal_elevations)
            avg_pulse_paired = round(sum(p["pulse"] for p in post_meal_elevations if p.get("pulse")) / cnt, 1) if any(p.get("pulse") for p in post_meal_elevations) else None
            pulse_desc = f"resting heart rate averaging {avg_pulse_paired} bpm and " if avg_pulse_paired else ""
            correlations.append(CorrelationItem(
                category="metabolic_cardiovascular",
                confidence="high" if cnt >= 3 else "moderate",
                headline="Post-Prandial Glycemic Excursions Coincide with Cardiovascular Load",
                explanation=f"In {cnt} paired measurement window{'s' if cnt > 1 else ''} within 2 hours, blood glucose elevation (>=140 mg/dL) coincided with {pulse_desc}elevated systolic pressure.",
                evidence_count=cnt,
                clinical_suggestion="Review meal carbohydrate density and consider light post-meal walking to moderate autonomic glycemic stress."
            ))

    # 4. Diurnal Variation (Morning vs Evening BP)
    m_bp = stats.get("morning_avg_bp")
    e_bp = stats.get("evening_avg_bp")
    if m_bp and e_bp and m_bp.get("count", 0) >= 2 and e_bp.get("count", 0) >= 2:
        m_sys = m_bp["systolic"]
        e_sys = e_bp["systolic"]
        diff = round(m_sys - e_sys, 1)
        if diff >= 8.0:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="moderate",
                headline="Morning Systolic Surge Observed",
                explanation=f"Morning blood pressure averages {m_sys}/{m_bp['diastolic']} mmHg, which is {diff} mmHg higher than your evening average of {e_sys}/{e_bp['diastolic']} mmHg.",
                evidence_count=m_bp["count"] + e_bp["count"],
                clinical_suggestion="Discuss morning blood pressure surges with your physician to evaluate medication timing and morning autonomic activity."
            ))
        elif diff <= -8.0:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="moderate",
                headline="Evening Blood Pressure Elevation Noted",
                explanation=f"Evening blood pressure averages {e_sys}/{e_bp['diastolic']} mmHg, exceeding morning levels by {abs(diff)} mmHg.",
                evidence_count=m_bp["count"] + e_bp["count"],
                clinical_suggestion="Log late afternoon stress and dietary sodium to investigate evening pressure increases."
            ))

    # 5. Rapid Fluid Shifts
    for ws in stats.get("weight_shifts", []):
        correlations.append(CorrelationItem(
            category="fluid_weight_shift",
            confidence="high",
            headline="Rapid Weight Gain Suggests Potential Fluid Retention",
            explanation=f"A weight increase of {ws['delta_kg']} kg was recorded over {ws['hours']} hours, which may indicate acute fluid accumulation.",
            evidence_count=1,
            clinical_suggestion="Consult your healthcare provider promptly if accompanied by lower extremity swelling, shortness of breath, or elevated blood pressure."
        ))

    # 6. Pattern Detection Exact Correlations
    patterns = stats.get("patterns", {})
    if patterns:
        # 6a. BP Trend Direction & OLS Slope
        bp_trend = patterns.get("bp_trend", {})
        slope = bp_trend.get("ols_slope_mmhg_per_reading")
        trend_label = bp_trend.get("trend_label")
        n_readings = bp_trend.get("reading_count", 0)
        abs_change = bp_trend.get("absolute_change_mmhg")

        if slope is not None and n_readings >= 3:
            if trend_label == "rising" and slope > 1.0:
                correlations.append(CorrelationItem(
                    category="longitudinal_trend",
                    confidence="high" if n_readings >= 5 else "moderate",
                    headline="Upward Blood Pressure Trajectory Detected",
                    explanation=f"Linear progression reveals a rising systolic trajectory (+{slope} mmHg/reading slope) across {n_readings} sequential readings, shifting from {bp_trend.get('first_systolic')} mmHg to {bp_trend.get('last_systolic')} mmHg (+{abs_change} mmHg net).",
                    evidence_count=n_readings,
                    clinical_suggestion="Schedule a follow-up review with your prescribing clinician to reassess anti-hypertensive therapy efficacy."
                ))
            elif trend_label == "falling" and slope < -1.0:
                correlations.append(CorrelationItem(
                    category="longitudinal_trend",
                    confidence="high" if n_readings >= 5 else "moderate",
                    headline="Improving Blood Pressure Trajectory Observed",
                    explanation=f"Sequential analysis shows a downward systolic trajectory ({slope} mmHg/reading slope) across {n_readings} readings, dropping {abs(abs_change)} mmHg from baseline ({bp_trend.get('first_systolic')} to {bp_trend.get('last_systolic')} mmHg).",
                    evidence_count=n_readings,
                    clinical_suggestion="Maintain current lifestyle modifications and treatment protocol."
                ))

        # 6b. Wide Pulse Pressure
        pp_stats = patterns.get("pulse_pressure_stats")
        if pp_stats and pp_stats.get("wide_pp_count", 0) > 0:
            wide_cnt = pp_stats["wide_pp_count"]
            correlations.append(CorrelationItem(
                category="metabolic_cardiovascular",
                confidence="high" if wide_cnt >= 2 else "moderate",
                headline="Elevated Pulse Pressure Detected (Arterial Stiffness Risk)",
                explanation=f"Pulse pressure (systolic minus diastolic) exceeded the 60 mmHg clinical benchmark in {wide_cnt} reading(s), averaging {pp_stats['mean_mmhg']} mmHg (range: {pp_stats['min_mmhg']}-{pp_stats['max_mmhg']} mmHg).",
                evidence_count=wide_cnt,
                clinical_suggestion="Discuss elevated pulse pressure with your physician as an indicator of large-artery stiffness and cardiovascular strain."
            ))

        # 6c. Consecutive Elevated Reading Streaks
        streak_stats = patterns.get("consecutive_elevated_streak", {})
        max_streak = streak_stats.get("max_streak", 0)
        if max_streak >= 3:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="high",
                headline="Persistent Hypertensive Elevation Streak",
                explanation=f"Identified {max_streak} consecutive readings meeting Stage 1 or Stage 2 Hypertension criteria without normal intervals, indicating sustained rather than isolated pressure elevation.",
                evidence_count=max_streak,
                clinical_suggestion="Persistent elevation requires clinical evaluation to rule out medication non-adherence or need for dosage titration."
            ))

        # 6d. High Glycemic Variability
        glu_cv = patterns.get("glucose_variability_cv")
        if glu_cv and (glu_cv.get("cv_pct") or 0) > 20.0:
            correlations.append(CorrelationItem(
                category="metabolic_cardiovascular",
                confidence="high",
                headline="Elevated Glycemic Variability Observed",
                explanation=f"Blood glucose coefficient of variation reached {glu_cv['cv_pct']}% (span: {glu_cv['min_mg_dl']} to {glu_cv['max_mg_dl']} mg/dL, range: {glu_cv['range_mg_dl']} mg/dL), indicating substantial glycemic fluctuations.",
                evidence_count=stats.get("total_glucose_readings", 1),
                clinical_suggestion="Consider reviewing meal composition, carbohydrate timing, and discussing glycemic variability with your endocrinologist."
            ))

        # 6e. Symptom Co-occurrence Matrix
        symptom_co = patterns.get("symptom_co_occurrence", {})
        for tag, sc in symptom_co.items():
            if sc.get("co_occurring_with_stage1_plus", 0) >= 2 and sc.get("elevated_bp_rate_pct", 0) >= 60.0:
                tag_label = tag.replace("_", " ").title()
                correlations.append(CorrelationItem(
                    category="symptom_spike",
                    confidence="high" if sc["total_occurrences"] >= 3 else "moderate",
                    headline=f"High Elevation Rate During Reported {tag_label}",
                    explanation=f"When {tag_label.lower()} was present, {sc['elevated_bp_rate_pct']}% of readings ({sc['co_occurring_with_stage1_plus']}/{sc['total_occurrences']}) reached Stage 1+ hypertension, with systolic averaging {sc['avg_systolic_when_present']} mmHg.",
                    evidence_count=sc["total_occurrences"],
                    clinical_suggestion=f"Monitor biometric responses carefully when experiencing {tag_label.lower()}."
                ))

    # Construct synthesized clinical summary
    doc_summary_lines = []
    if stats.get("total_bp_readings"):
        doc_summary_lines.append(
            f"Over {stats['total_bp_readings']} recorded blood pressure measurements, patient demonstrates an average reading of {stats.get('avg_systolic', 'N/A')}/{stats.get('avg_diastolic', 'N/A')} mmHg."
        )
    if stats.get("total_glucose_readings"):
        doc_summary_lines.append(
            f"Over {stats['total_glucose_readings']} glucose readings, mean concentration is {stats.get('avg_glucose_mg_dl', 'N/A')} mg/dL."
        )
    if correlations:
        top_headlines = "; ".join([f"'{c.headline}'" for c in correlations[:3]])
        doc_summary_lines.append(f"Key data-driven correlations identified include: {top_headlines}.")
    else:
        doc_summary_lines.append("No significant confounding or cross-stream anomalies were observed within the current logging period.")

    doctor_summary = " ".join(doc_summary_lines)

    now_iso = datetime.now(timezone.utc).isoformat()
    return HealthAnalysisResponse(
        user_id=user_id,
        generated_at=now_iso,
        is_cached=False,
        stats=AnalysisStats(
            total_bp_readings=stats.get("total_bp_readings", 0),
            total_glucose_readings=stats.get("total_glucose_readings", 0),
            avg_systolic=stats.get("avg_systolic"),
            avg_diastolic=stats.get("avg_diastolic"),
            avg_pulse=stats.get("avg_pulse"),
            avg_glucose_mg_dl=stats.get("avg_glucose_mg_dl"),
            morning_avg_bp={"systolic": m_bp["systolic"], "diastolic": m_bp["diastolic"]} if m_bp else None,
            evening_avg_bp={"systolic": e_bp["systolic"], "diastolic": e_bp["diastolic"]} if e_bp else None,
            fasting_avg_glucose=stats.get("fasting_avg_glucose"),
            post_meal_avg_glucose=stats.get("post_meal_avg_glucose")
        ),
        patterns=stats.get("patterns"),
        correlations=correlations,
        urgent_alerts=urgent_alerts,
        doctor_summary=doctor_summary
    )


# =====================================================================
# 3. Gemini Temporal Chain-of-Thought Reasoning
#    Based on: Kruse et al. (2025) "LLMs with Temporal Reasoning for
#    Longitudinal Clinical Summarization and Prediction"
#    EMNLP 2025 Findings — PMID: 41399802 / PMC12702291
# =====================================================================

# --- Step 1: Temporal Ordering Prompt ---
# The paper demonstrates that explicitly structuring data chronologically
# and requiring step-by-step temporal progression reasoning (CoT) yields
# significantly better clinical correlation quality over single-pass prompting.
ANALYSIS_SYSTEM_PROMPT = """
You are an expert clinical data analyst and chronic disease specialist.
You use evidence-based temporal reasoning techniques to analyze longitudinal patient health data.

=== METHODOLOGY (Temporal Chain-of-Thought Reasoning) ===
This approach is grounded in research showing that LLMs perform significantly better
at clinical reasoning when they explicitly reason step-by-step over chronological
health trajectories rather than processing raw data in a single pass.

You will receive pre-computed health statistics and timeline data. Reason in 4 explicit steps:

STEP 1 — TEMPORAL TRAJECTORY SCAN:
  Read the chronological ordering of events. Identify:
  - How values CHANGED over time (worsening, improving, oscillating, stable).
  - Time-clustered patterns (e.g., morning surge, post-meal spikes, nighttime dips).
  - Temporal co-occurrences (e.g., "on days when X was logged, Y was elevated the same or next day").

STEP 2 — CONFOUNDER & TRIGGER IDENTIFICATION:
  For each lifestyle/context tag (caffeine, NSAIDs, poor sleep, high stress, exercise):
  - Calculate: average biometric VALUE with tag vs. average WITHOUT tag.
  - The statistics are pre-computed and provided to you. Ground every claim in those numbers.
  - NEVER invent or estimate data not present in the provided statistics.

STEP 3 — CROSS-STREAM TEMPORAL PAIRING:
  For blood pressure and blood glucose readings taken within ±2 hours of each other:
  - Identify if glucose elevation preceded, co-occurred with, or followed cardiovascular load.
  - Note the directionality of the effect (e.g., "glucose rose BEFORE pulse elevation").
  - Characterize: was this a post-prandial spike? A fasting anomaly? A morning cortisol effect?

STEP 4 — LONGITUDINAL TREND SYNTHESIS:
  After completing steps 1-3, synthesize:
  - Is the patient's overall trajectory IMPROVING, STABLE, or DETERIORATING?
  - Are morning vs evening readings consistently different? (Diurnal pattern)
  - Are there acute crisis events? Do they cluster around specific lifestyle factors?
  - Construct a physician-grade, multi-paragraph synthesized summary.

=== CLINICAL SAFETY CONSTRAINTS ===
- NEVER state a definitive clinical diagnosis ("You have Type 2 Diabetes", "This is renal failure").
- Use objective, grounded language anchored to the provided statistics:
    "Data indicates...", "Readings show a correlation...", "Discuss with your clinician..."
- Do NOT hallucinate numbers. Every value cited must match the provided statistics.
- Flag acute danger events (Hypertensive Crisis ≥180/120, Severe Hypoglycemia <54 mg/dL) in urgent_alerts.

=== OUTPUT FORMAT ===
Return strictly valid JSON (no markdown fences, no explanation outside JSON):
{
  "temporal_reasoning_trace": "Brief description of key temporal patterns observed in Step 1-3 before final output (1-2 sentences)",
  "correlations": [
    {
      "category": "lifestyle_trigger" | "metabolic_cardiovascular" | "symptom_spike" | "longitudinal_trend" | "medication_response" | "fluid_weight_shift" | "other",
      "confidence": "high" | "moderate" | "low",
      "headline": "Concise clinical title",
      "explanation": "Specific data-anchored explanation citing exact numbers from the provided statistics",
      "evidence_count": <integer number of supporting measurement events>,
      "temporal_direction": "before" | "concurrent" | "after" | "bidirectional" | "not_applicable",
      "clinical_suggestion": "Actionable, non-diagnostic guidance for the patient"
    }
  ],
  "urgent_alerts": ["alert string"],
  "doctor_summary": "Physician-grade 2-3 paragraph summary covering: (1) temporal trajectory, (2) key correlations with specific values, (3) recommendations for clinical follow-up"
}
"""


def _build_temporal_content(stats: Dict[str, Any]) -> str:
    """
    Constructs a chronologically-ordered, grounded data payload for the Gemini prompt.
    Implements the paper's recommendation of structuring longitudinal data with
    explicit temporal markers before reasoning, mirroring RAG-style grounding.
    """
    sections = []

    sections.append("=== PATIENT HEALTH TIMELINE STATISTICS ===")
    sections.append(f"Total Blood Pressure Recordings: {stats.get('total_bp_readings', 0)}")
    sections.append(f"Total Blood Glucose Recordings: {stats.get('total_glucose_readings', 0)}")

    # Aggregate baselines
    if stats.get("avg_systolic") is not None:
        sections.append(
            f"\n--- BLOOD PRESSURE AVERAGES ---\n"
            f"Overall Average: {stats['avg_systolic']}/{stats.get('avg_diastolic')} mmHg "
            f"(Pulse: {stats.get('avg_pulse', 'N/A')} bpm)"
        )
    m_bp = stats.get("morning_avg_bp")
    e_bp = stats.get("evening_avg_bp")
    if m_bp:
        sections.append(f"Morning Average (05:00-11:59): {m_bp['systolic']}/{m_bp['diastolic']} mmHg (n={m_bp.get('count', '?')})")
    if e_bp:
        sections.append(f"Evening Average (17:00-23:59): {e_bp['systolic']}/{e_bp['diastolic']} mmHg (n={e_bp.get('count', '?')})")
    if m_bp and e_bp:
        delta = round(m_bp["systolic"] - e_bp["systolic"], 1)
        direction = "higher in morning" if delta > 0 else "higher in evening" if delta < 0 else "equal"
        sections.append(f"Diurnal Δ Systolic: {abs(delta)} mmHg {direction}")

    # Glucose baselines
    if stats.get("avg_glucose_mg_dl") is not None:
        sections.append(
            f"\n--- BLOOD GLUCOSE AVERAGES ---\n"
            f"Overall Average: {stats['avg_glucose_mg_dl']} mg/dL"
        )
    if stats.get("fasting_avg_glucose"):
        sections.append(f"Fasting Average: {stats['fasting_avg_glucose']} mg/dL")
    if stats.get("post_meal_avg_glucose"):
        sections.append(f"Post-Meal Average: {stats['post_meal_avg_glucose']} mg/dL")
    if stats.get("fasting_avg_glucose") and stats.get("post_meal_avg_glucose"):
        delta_glu = round(stats["post_meal_avg_glucose"] - stats["fasting_avg_glucose"], 1)
        sections.append(f"Post-Prandial Δ Glucose: +{delta_glu} mg/dL above fasting baseline")

    # Confounder effects — this is the primary grounding data
    confounders = stats.get("confounder_effects", {})
    if confounders:
        sections.append("\n--- CONFOUNDER / LIFESTYLE TRIGGER EFFECTS (Pre-computed) ---")
        for tag, c in confounders.items():
            tag_label = tag.replace("_", " ").title()
            sections.append(
                f"  [{tag_label}]: {c['count']} occurrences | "
                f"Avg SYS with tag: {c['avg_systolic_with_tag']} mmHg | "
                f"Baseline SYS: {c['baseline_systolic']} mmHg | "
                f"Δ SYS: {'+' if c['delta_systolic'] > 0 else ''}{c['delta_systolic']} mmHg"
            )

    # Cross-stream pairings
    paired = stats.get("paired_readings", [])
    if paired:
        sections.append(f"\n--- TEMPORAL CROSS-STREAM PAIRINGS (BP + Glucose within ±2 hours) ---")
        sections.append(f"  Total paired windows: {len(paired)}")
        post_meal_elevated = [p for p in paired if p.get("glucose_mg_dl", 0) >= 140]
        if post_meal_elevated:
            avg_sys_paired = round(sum(p["systolic"] or 0 for p in post_meal_elevated) / len(post_meal_elevated), 1)
            avg_glu_paired = round(sum(p["glucose_mg_dl"] for p in post_meal_elevated) / len(post_meal_elevated), 1)
            sections.append(
                f"  Elevated glucose windows (≥140 mg/dL): {len(post_meal_elevated)} events | "
                f"Average glucose in these windows: {avg_glu_paired} mg/dL | "
                f"Average systolic in same windows: {avg_sys_paired} mmHg"
            )

    # Acute / urgent events
    urgent_events = stats.get("urgent_events", [])
    if urgent_events:
        sections.append(f"\n--- ACUTE CLINICAL EVENTS ---")
        for evt in urgent_events:
            if evt["type"] == "hypertensive_crisis_warning":
                sections.append(
                    f"  [HYPERTENSIVE CRISIS] {evt.get('recorded_at', 'unknown time')}: "
                    f"SYS={evt.get('systolic')}, DIA={evt.get('diastolic')} mmHg "
                    f"| Associated symptoms: {', '.join(evt.get('issues', [])) or 'none reported'}"
                )
            elif evt["type"] == "severe_hypoglycemia":
                sections.append(f"  [SEVERE HYPOGLYCEMIA] {evt.get('recorded_at', 'unknown time')}: {evt.get('glucose_mg_dl')} mg/dL")
            elif evt["type"] == "severe_hyperglycemia":
                sections.append(f"  [SEVERE HYPERGLYCEMIA] {evt.get('recorded_at', 'unknown time')}: {evt.get('glucose_mg_dl')} mg/dL")

    # Weight shifts
    weight_shifts = stats.get("weight_shifts", [])
    if weight_shifts:
        sections.append(f"\n--- RAPID WEIGHT SHIFTS ---")
        for ws in weight_shifts:
            sections.append(f"  +{ws['delta_kg']} kg over {ws['hours']} hours at {ws.get('recorded_at', 'unknown time')}")

    # Exact Pattern Detection Metrics
    patterns = stats.get("patterns", {})
    if patterns:
        sections.append("\n--- EXACT PATTERN DETECTION METRICS ---")
        
        # BP Trend
        bp_t = patterns.get("bp_trend")
        if bp_t and bp_t.get("ols_slope_mmhg_per_reading") is not None:
            sections.append(
                f"  BP Trajectory Trend: {bp_t['trend_label'].upper()} | "
                f"OLS Slope: {bp_t['ols_slope_mmhg_per_reading']} mmHg/reading | "
                f"Span: {bp_t.get('first_systolic')} -> {bp_t.get('last_systolic')} mmHg "
                f"(Δ {bp_t.get('absolute_change_mmhg')} mmHg, n={bp_t.get('reading_count')})"
            )
            
        # AHA Staging
        stage_dist = patterns.get("bp_stage_distribution")
        if stage_dist:
            dist_str = ", ".join([f"{st}: {d['count']} ({d['pct']}%)" for st, d in stage_dist.items() if d['count'] > 0])
            sections.append(f"  AHA/ACC BP Stage Distribution: {dist_str}")

        # Consecutive Elevated Streak
        streak = patterns.get("consecutive_elevated_streak")
        if streak and streak.get("max_streak", 0) > 0:
            sections.append(f"  Consecutive Elevated Readings: max streak={streak['max_streak']}, current streak={streak['current_streak']} ({streak.get('interpretation', '')})")

        # Pulse Pressure
        pp = patterns.get("pulse_pressure_stats")
        if pp:
            sections.append(
                f"  Pulse Pressure (SYS-DIA): mean={pp['mean_mmhg']} mmHg, "
                f"range={pp['min_mmhg']}-{pp['max_mmhg']} mmHg, "
                f"wide PP (>60 mmHg) count={pp['wide_pp_count']} (arterial stiffness indicator)"
            )

        # BP Variability CV%
        bp_cv = patterns.get("bp_variability_cv")
        if bp_cv and bp_cv.get("systolic_cv_pct") is not None:
            sections.append(f"  BP Variability (CV%): Systolic CV={bp_cv['systolic_cv_pct']}%, Diastolic CV={bp_cv.get('diastolic_cv_pct')}%, {bp_cv.get('interpretation', '')}")

        # Systolic Percentiles
        pcts = patterns.get("bp_percentiles")
        if pcts:
            sections.append(f"  Systolic Percentiles: p25={pcts['p25_systolic']}, p50={pcts['p50_systolic']}, p75={pcts['p75_systolic']}, p90={pcts['p90_systolic']}, p95={pcts['p95_systolic']} mmHg")

        # Glycemic Variability CV%
        glu_cv = patterns.get("glucose_variability_cv")
        if glu_cv and glu_cv.get("cv_pct") is not None:
            sections.append(f"  Glycemic Variability (CV%): CV={glu_cv['cv_pct']}%, min={glu_cv['min_mg_dl']}, max={glu_cv['max_mg_dl']}, range={glu_cv['range_mg_dl']} mg/dL ({glu_cv.get('interpretation', '')})")

        # Symptom Co-occurrence Matrix
        sym_co = patterns.get("symptom_co_occurrence")
        if sym_co:
            sections.append("  Symptom Co-occurrence Matrix with Elevated BP:")
            for tag, sc in sym_co.items():
                tag_label = tag.replace("_", " ").title()
                sections.append(
                    f"    [{tag_label}]: {sc['total_occurrences']} logs | "
                    f"Co-occurring with Stage 1+ BP: {sc['co_occurring_with_stage1_plus']} ({sc['elevated_bp_rate_pct']}%) | "
                    f"Avg SYS when present: {sc['avg_systolic_when_present']} mmHg"
                )

    sections.append(
        "\n=== INSTRUCTIONS ===\n"
        "Apply your 4-step Temporal Chain-of-Thought methodology to the statistics above.\n"
        "Ground every number you cite in the provided data. Do not invent any values.\n"
        "Return valid JSON only."
    )

    return "\n".join(sections)


def generate_correlation_insights(
    user_id: str,
    stats: Dict[str, Any]
) -> HealthAnalysisResponse:
    """
    Calls Gemini using gemini-flash-latest (or fallback models) with deterministic
    statistics structured as a temporally-ordered clinical data payload.
    Implements Chain-of-Thought temporal reasoning from Kruse et al. (PMC12702291).
    Falls back gracefully to heuristic rule engine if offline or rate limited.
    """
    client = get_gemini_client()
    if not client:
        print("[AnalysisService] No GEMINI_API_KEY found. Utilizing deterministic heuristic analysis engine.")
        return generate_heuristic_correlations(user_id, stats)

    # Build grounded, temporally-structured input (RAG-style grounding as per paper)
    content = _build_temporal_content(stats)

    model_names = ["gemini-flash-latest", "gemini-1.5-flash", "gemini-2.5-flash"]
    last_error = None

    for model_name in model_names:
        try:
            model = client.GenerativeModel(
                model_name=model_name,
                system_instruction=ANALYSIS_SYSTEM_PROMPT,
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content(content)
            cleaned = _clean_json_string(response.text)
            data = json.loads(cleaned)

            # Log the temporal reasoning trace for observability
            trace = data.get("temporal_reasoning_trace", "")
            if trace:
                print(f"[AnalysisService] Temporal reasoning trace: {trace[:200]}")

            # Build correlations list
            correlations: List[CorrelationItem] = []
            valid_categories = {"lifestyle_trigger", "metabolic_cardiovascular", "symptom_spike", "longitudinal_trend", "medication_response", "fluid_weight_shift", "other"}
            valid_confidences = {"high", "moderate", "low"}

            for item in data.get("correlations", []):
                try:
                    category = item.get("category", "other")
                    if category not in valid_categories:
                        category = "other"
                    confidence = item.get("confidence", "moderate")
                    if confidence not in valid_confidences:
                        confidence = "moderate"

                    correlations.append(CorrelationItem(
                        category=category,
                        confidence=confidence,
                        headline=str(item.get("headline", "Clinical Observation")).strip(),
                        explanation=str(item.get("explanation", "")).strip(),
                        evidence_count=int(item.get("evidence_count", 1)),
                        clinical_suggestion=str(item.get("clinical_suggestion", "")).strip()
                    ))
                except Exception as parse_item_err:
                    print(f"[AnalysisService] Notice: Skipping malformed correlation item: {parse_item_err}")

            urgent_alerts = [str(a).strip() for a in data.get("urgent_alerts", []) if str(a).strip()]
            doctor_summary = str(data.get("doctor_summary", "")).strip() or "Clinical review generated from recorded longitudinal data streams."

            now_iso = datetime.now(timezone.utc).isoformat()
            m_bp = stats.get("morning_avg_bp")
            e_bp = stats.get("evening_avg_bp")

            return HealthAnalysisResponse(
                user_id=user_id,
                generated_at=now_iso,
                is_cached=False,
                stats=AnalysisStats(
                    total_bp_readings=stats.get("total_bp_readings", 0),
                    total_glucose_readings=stats.get("total_glucose_readings", 0),
                    avg_systolic=stats.get("avg_systolic"),
                    avg_diastolic=stats.get("avg_diastolic"),
                    avg_pulse=stats.get("avg_pulse"),
                    avg_glucose_mg_dl=stats.get("avg_glucose_mg_dl"),
                    morning_avg_bp={"systolic": m_bp["systolic"], "diastolic": m_bp["diastolic"]} if m_bp else None,
                    evening_avg_bp={"systolic": e_bp["systolic"], "diastolic": e_bp["diastolic"]} if e_bp else None,
                    fasting_avg_glucose=stats.get("fasting_avg_glucose"),
                    post_meal_avg_glucose=stats.get("post_meal_avg_glucose")
                ),
                patterns=stats.get("patterns"),
                correlations=correlations,
                urgent_alerts=urgent_alerts,
                doctor_summary=doctor_summary
            )

        except Exception as e:
            print(f"[AnalysisService] Warning: Gemini model '{model_name}' execution error: {e}")
            last_error = e
            continue


    print(f"[AnalysisService] All Gemini models failed ({last_error}). Falling back to deterministic heuristic engine.")
    return generate_heuristic_correlations(user_id, stats)


# =====================================================================
# 4. Caching Layer (Firestore 1-Hour Expiry & Invalidation)
# =====================================================================


def get_or_compute_analysis(
    user_id: str,
    db: Any,
    force_refresh: bool = False
) -> HealthAnalysisResponse:
    """
    Checks Firestore cache under profiles/{user_id}/analysis/latest.
    If cached within 1 hour AND no newer measurements exist, returns cached analysis.
    Otherwise fetches latest measurements, executes analysis, updates cache, and returns.
    """
    now = datetime.now(timezone.utc)
    analysis_ref = None

    if db is not None:
        try:
            analysis_ref = db.collection("profiles").document(user_id).collection("analysis").document("latest")
        except Exception as e:
            print(f"[AnalysisService] Firestore doc ref error: {e}")

    # 1. Check cache validity
    if not force_refresh and analysis_ref is not None:
        try:
            cached_doc = analysis_ref.get()
            if cached_doc.exists:
                data = cached_doc.to_dict()
                gen_at = _parse_iso_datetime(data.get("generated_at"))
                if gen_at and (now - gen_at).total_seconds() < 3600:
                    # Check if any measurement was created after generated_at
                    measurements_ref = db.collection("profiles").document(user_id).collection("measurements")
                    newer_docs = (
                        measurements_ref
                        .where("created_at", ">", data.get("generated_at"))
                        .limit(1)
                        .stream()
                    )
                    has_newer = any(True for _ in newer_docs)
                    if not has_newer:
                        # Return cached
                        resp = HealthAnalysisResponse(**data)
                        resp.is_cached = True
                        return resp
        except Exception as cache_err:
            print(f"[AnalysisService] Cache read notice: {cache_err}. Computing fresh analysis.")

    # 2. Fetch all user measurements for aggregation
    bp_records: List[Dict[str, Any]] = []
    glucose_records: List[Dict[str, Any]] = []
    weight_records: List[Dict[str, Any]] = []

    if db is not None:
        try:
            m_ref = db.collection("profiles").document(user_id).collection("measurements")
            docs = m_ref.limit(200).stream()
            for doc in docs:
                item = doc.to_dict()
                m_type = item.get("measurement_type")
                if m_type == "blood_pressure":
                    bp_records.append(item)
                elif m_type == "blood_glucose":
                    glucose_records.append(item)

            # Weight history
            w_ref = db.collection("profiles").document(user_id).collection("weight_history")
            w_docs = w_ref.limit(50).stream()
            weight_records = [w.to_dict() for w in w_docs]
        except Exception as fetch_err:
            print(f"[AnalysisService] Error reading user measurements: {fetch_err}")

    # 3. Pre-aggregate and generate
    stats = preaggregate_health_data(bp_records, glucose_records, weight_records)
    analysis = generate_correlation_insights(user_id, stats)

    # 4. Save to cache
    if db is not None and analysis_ref is not None:
        try:
            analysis_dict = analysis.model_dump()
            analysis_dict["is_cached"] = False
            analysis_ref.set(analysis_dict)
        except Exception as save_err:
            print(f"[AnalysisService] Error caching analysis: {save_err}")

    return analysis
