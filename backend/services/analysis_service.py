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
    RoteMemoryState,
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
        "total_weight_readings": len(weight_records) if weight_records else 0,
        "devices_detected": [],
        "avg_systolic": None,
        "avg_diastolic": None,
        "avg_pulse": None,
        "avg_glucose_mg_dl": None,
        "avg_spo2": None,
        "spo2_count": 0,
        "morning_avg_bp": None,
        "evening_avg_bp": None,
        "fasting_avg_glucose": None,
        "post_meal_avg_glucose": None,
        "glucose_tir_pct": None,
        "trajectory_7d_vs_14d": None,
        "confounder_effects": {},
        "paired_readings": [],
        "urgent_events": [],
        "weight_shifts": []
    }

    # -------------------------------------------------------------
    # Multi-Device Telemetry Setup & Blood Pressure Aggregations
    # -------------------------------------------------------------
    devices_detected: set = set()
    systolics = []
    diastolics = []
    pulses = []
    spo2_vals = []
    morning_sys, morning_dia = [], []
    evening_sys, evening_dia = [], []

    # Map tags to readings with and without tag
    tag_readings: Dict[str, List[Dict[str, Any]]] = {}

    for r in bp_records:
        vals = r.get("values", {})
        sys_val = vals.get("systolic")
        dia_val = vals.get("diastolic")
        pulse_val = vals.get("pulse")
        spo2_val = vals.get("spo2")

        d_type = r.get("device_type") or "Sphygmomanometer"
        devices_detected.add(d_type)
        if spo2_val is not None:
            spo2_vals.append(spo2_val)
            devices_detected.add("Pulse Oximeter")

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

        g_type = g.get("device_type") or "Glucometer"
        devices_detected.add(g_type)

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
        in_range_count = sum(1 for v in glucose_vals if 70 <= v <= 180)
        stats["glucose_tir_pct"] = round(in_range_count / len(glucose_vals) * 100, 1)
    if fasting_vals:
        stats["fasting_avg_glucose"] = round(sum(fasting_vals) / len(fasting_vals), 1)
    if post_meal_vals:
        stats["post_meal_avg_glucose"] = round(sum(post_meal_vals) / len(post_meal_vals), 1)

    if weight_records:
        for w in weight_records:
            devices_detected.add(w.get("device_type") or "Digital Scale")

    stats["devices_detected"] = sorted(list(devices_detected))
    stats["avg_spo2"] = round(sum(spo2_vals) / len(spo2_vals), 1) if spo2_vals else None
    stats["spo2_count"] = len(spo2_vals)

    # -------------------------------------------------------------
    # 7-Day vs 14-Day Longitudinal Trajectory Calculation
    # -------------------------------------------------------------
    bp_with_dt = [
        (_parse_iso_datetime(r.get("recorded_at")), r)
        for r in bp_records
        if _parse_iso_datetime(r.get("recorded_at")) and r.get("values", {}).get("systolic") is not None
    ]
    if bp_with_dt:
        bp_with_dt.sort(key=lambda x: x[0])
        max_dt = bp_with_dt[-1][0]
        min_dt = bp_with_dt[0][0]
        total_span_days = (max_dt - min_dt).total_seconds() / 86400.0

        if total_span_days >= 6.0:
            c_7d = max_dt - timedelta(days=7)
            c_14d = max_dt - timedelta(days=14)
            recent_recs = [r for dt, r in bp_with_dt if dt >= c_7d]
            prior_recs = [r for dt, r in bp_with_dt if c_14d <= dt < c_7d]
        elif len(bp_with_dt) >= 4:
            mid = len(bp_with_dt) // 2
            prior_recs = [r for _, r in bp_with_dt[:mid]]
            recent_recs = [r for _, r in bp_with_dt[mid:]]
        else:
            recent_recs = []
            prior_recs = []

        rec_sys = [r["values"]["systolic"] for r in recent_recs if r.get("values", {}).get("systolic") is not None]
        pri_sys = [r["values"]["systolic"] for r in prior_recs if r.get("values", {}).get("systolic") is not None]
        rec_dia = [r["values"]["diastolic"] for r in recent_recs if r.get("values", {}).get("diastolic") is not None]
        pri_dia = [r["values"]["diastolic"] for r in prior_recs if r.get("values", {}).get("diastolic") is not None]

        if rec_sys and pri_sys:
            avg_rec_s = round(sum(rec_sys) / len(rec_sys), 1)
            avg_pri_s = round(sum(pri_sys) / len(pri_sys), 1)
            delta_s = round(avg_rec_s - avg_pri_s, 1)
            avg_rec_d = round(sum(rec_dia) / len(rec_dia), 1) if rec_dia else None
            avg_pri_d = round(sum(pri_dia) / len(pri_dia), 1) if pri_dia else None
            delta_d = round(avg_rec_d - avg_pri_d, 1) if (avg_rec_d and avg_pri_d) else None

            stats["trajectory_7d_vs_14d"] = {
                "recent_7d_avg_systolic": avg_rec_s,
                "prior_7d_avg_systolic": avg_pri_s,
                "delta_systolic": delta_s,
                "recent_7d_avg_diastolic": avg_rec_d,
                "prior_7d_avg_diastolic": avg_pri_d,
                "delta_diastolic": delta_d,
                "recent_count": len(rec_sys),
                "prior_count": len(pri_sys),
                "direction": "improving" if delta_s <= -3.0 else "worsening" if delta_s >= 3.0 else "stable"
            }

    # -------------------------------------------------------------
    # Temporal Cross-Stream Pairing (+/- 2 Hours: Multi-Device BP & Glucose)
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

                bp_dev = bp.get("device_type") or "Sphygmomanometer"
                glu_dev = glu.get("device_type") or "Glucometer"

                stats["paired_readings"].append({
                    "bp_id": bp.get("id"),
                    "glucose_id": glu.get("id"),
                    "time_diff_minutes": round(diff_sec / 60, 1),
                    "systolic": bp.get("values", {}).get("systolic"),
                    "diastolic": bp.get("values", {}).get("diastolic"),
                    "pulse": bp.get("values", {}).get("pulse"),
                    "spo2": bp.get("values", {}).get("spo2"),
                    "glucose_mg_dl": round(glu_mg_dl, 1),
                    "meal_context": glu.get("meal_context"),
                    "bp_device": bp_dev,
                    "glucose_device": glu_dev,
                    "devices": [bp_dev, glu_dev]
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

    # Running accumulators for O(k) incremental updates
    stats["accumulators"] = {
        "bp_count": len(systolics),
        "sys_sum": round(sum(systolics), 1) if systolics else 0.0,
        "dia_sum": round(sum(diastolics), 1) if diastolics else 0.0,
        "pulse_count": len(pulses),
        "pulse_sum": round(sum(pulses), 1) if pulses else 0.0,
        "morning_count": len(morning_sys),
        "morning_sys_sum": round(sum(morning_sys), 1) if morning_sys else 0.0,
        "morning_dia_sum": round(sum(morning_dia), 1) if morning_dia else 0.0,
        "evening_count": len(evening_sys),
        "evening_sys_sum": round(sum(evening_sys), 1) if evening_sys else 0.0,
        "evening_dia_sum": round(sum(evening_dia), 1) if evening_dia else 0.0,
        "glucose_count": len(glucose_vals),
        "glucose_sum": round(sum(glucose_vals), 1) if glucose_vals else 0.0,
        "fasting_count": len(fasting_vals),
        "fasting_sum": round(sum(fasting_vals), 1) if fasting_vals else 0.0,
        "post_meal_count": len(post_meal_vals),
        "post_meal_sum": round(sum(post_meal_vals), 1) if post_meal_vals else 0.0,
        "baseline_sys_count": len(baseline_sys),
        "baseline_sys_sum": round(sum(baseline_sys), 1) if baseline_sys else 0.0,
        "confounder_counts": {
            tag: {
                "count": c["count"],
                "sys_sum": round(c["avg_systolic_with_tag"] * c["count"], 1)
            }
            for tag, c in stats.get("confounder_effects", {}).items()
        }
    }

    # Run full pattern detection on the raw records
    stats["patterns"] = detect_exact_patterns(bp_records, glucose_records)

    return stats


# =====================================================================
# 1b. Incremental Rote Accumulator Engine
# =====================================================================

def update_running_stats(
    prior_stats: Dict[str, Any],
    prior_accumulators: Dict[str, Any],
    delta_bp_records: List[Dict[str, Any]],
    delta_glucose_records: List[Dict[str, Any]],
    delta_weight_records: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Incrementally updates health statistics in O(k) time by combining prior accumulators
    with newly recorded delta measurements, avoiding re-scanning historical database records.
    """
    delta_stats = preaggregate_health_data(delta_bp_records, delta_glucose_records, delta_weight_records)
    delta_acc = delta_stats.get("accumulators", {})

    new_acc = {
        "bp_count": prior_accumulators.get("bp_count", 0) + delta_acc.get("bp_count", 0),
        "sys_sum": round(prior_accumulators.get("sys_sum", 0.0) + delta_acc.get("sys_sum", 0.0), 1),
        "dia_sum": round(prior_accumulators.get("dia_sum", 0.0) + delta_acc.get("dia_sum", 0.0), 1),
        "pulse_count": prior_accumulators.get("pulse_count", 0) + delta_acc.get("pulse_count", 0),
        "pulse_sum": round(prior_accumulators.get("pulse_sum", 0.0) + delta_acc.get("pulse_sum", 0.0), 1),
        "morning_count": prior_accumulators.get("morning_count", 0) + delta_acc.get("morning_count", 0),
        "morning_sys_sum": round(prior_accumulators.get("morning_sys_sum", 0.0) + delta_acc.get("morning_sys_sum", 0.0), 1),
        "morning_dia_sum": round(prior_accumulators.get("morning_dia_sum", 0.0) + delta_acc.get("morning_dia_sum", 0.0), 1),
        "evening_count": prior_accumulators.get("evening_count", 0) + delta_acc.get("evening_count", 0),
        "evening_sys_sum": round(prior_accumulators.get("evening_sys_sum", 0.0) + delta_acc.get("evening_sys_sum", 0.0), 1),
        "evening_dia_sum": round(prior_accumulators.get("evening_dia_sum", 0.0) + delta_acc.get("evening_dia_sum", 0.0), 1),
        "glucose_count": prior_accumulators.get("glucose_count", 0) + delta_acc.get("glucose_count", 0),
        "glucose_sum": round(prior_accumulators.get("glucose_sum", 0.0) + delta_acc.get("glucose_sum", 0.0), 1),
        "fasting_count": prior_accumulators.get("fasting_count", 0) + delta_acc.get("fasting_count", 0),
        "fasting_sum": round(prior_accumulators.get("fasting_sum", 0.0) + delta_acc.get("fasting_sum", 0.0), 1),
        "post_meal_count": prior_accumulators.get("post_meal_count", 0) + delta_acc.get("post_meal_count", 0),
        "post_meal_sum": round(prior_accumulators.get("post_meal_sum", 0.0) + delta_acc.get("post_meal_sum", 0.0), 1),
        "baseline_sys_count": prior_accumulators.get("baseline_sys_count", 0) + delta_acc.get("baseline_sys_count", 0),
        "baseline_sys_sum": round(prior_accumulators.get("baseline_sys_sum", 0.0) + delta_acc.get("baseline_sys_sum", 0.0), 1),
        "confounder_counts": dict(prior_accumulators.get("confounder_counts", {}))
    }

    # Merge confounder counts
    for tag, c_delta in delta_acc.get("confounder_counts", {}).items():
        if tag not in new_acc["confounder_counts"]:
            new_acc["confounder_counts"][tag] = {"count": 0, "sys_sum": 0.0}
        new_acc["confounder_counts"][tag]["count"] += c_delta["count"]
        new_acc["confounder_counts"][tag]["sys_sum"] = round(new_acc["confounder_counts"][tag]["sys_sum"] + c_delta["sys_sum"], 1)

    updated_stats: Dict[str, Any] = {
        "total_bp_readings": new_acc["bp_count"],
        "total_glucose_readings": new_acc["glucose_count"],
        "avg_systolic": round(new_acc["sys_sum"] / new_acc["bp_count"], 1) if new_acc["bp_count"] else None,
        "avg_diastolic": round(new_acc["dia_sum"] / new_acc["bp_count"], 1) if new_acc["bp_count"] else None,
        "avg_pulse": round(new_acc["pulse_sum"] / new_acc["pulse_count"], 1) if new_acc["pulse_count"] else None,
        "avg_glucose_mg_dl": round(new_acc["glucose_sum"] / new_acc["glucose_count"], 1) if new_acc["glucose_count"] else None,
        "morning_avg_bp": {
            "systolic": round(new_acc["morning_sys_sum"] / new_acc["morning_count"], 1),
            "diastolic": round(new_acc["morning_dia_sum"] / new_acc["morning_count"], 1),
            "count": new_acc["morning_count"]
        } if new_acc["morning_count"] else None,
        "evening_avg_bp": {
            "systolic": round(new_acc["evening_sys_sum"] / new_acc["evening_count"], 1),
            "diastolic": round(new_acc["evening_dia_sum"] / new_acc["evening_count"], 1),
            "count": new_acc["evening_count"]
        } if new_acc["evening_count"] else None,
        "fasting_avg_glucose": round(new_acc["fasting_sum"] / new_acc["fasting_count"], 1) if new_acc["fasting_count"] else None,
        "post_meal_avg_glucose": round(new_acc["post_meal_sum"] / new_acc["post_meal_count"], 1) if new_acc["post_meal_count"] else None,
        "confounder_effects": {},
        "paired_readings": list(prior_stats.get("paired_readings", [])) + delta_stats.get("paired_readings", []),
        "urgent_events": list(prior_stats.get("urgent_events", [])) + delta_stats.get("urgent_events", []),
        "weight_shifts": list(prior_stats.get("weight_shifts", [])) + delta_stats.get("weight_shifts", []),
        "accumulators": new_acc
    }

    base_sys = (new_acc["baseline_sys_sum"] / new_acc["baseline_sys_count"]) if new_acc["baseline_sys_count"] else updated_stats["avg_systolic"]
    for tag, c in new_acc["confounder_counts"].items():
        if c["count"] > 0 and base_sys is not None:
            tag_avg = round(c["sys_sum"] / c["count"], 1)
            updated_stats["confounder_effects"][tag] = {
                "count": c["count"],
                "avg_systolic_with_tag": tag_avg,
                "baseline_systolic": round(base_sys, 1),
                "delta_systolic": round(tag_avg - base_sys, 1)
            }

    # Merge patterns: update trend label, streak, and pulse pressure
    prior_patterns = prior_stats.get("patterns", {})
    delta_patterns = delta_stats.get("patterns", {})

    updated_patterns = dict(prior_patterns)
    if delta_patterns.get("bp_trend") and delta_patterns["bp_trend"].get("reading_count", 0) > 0:
        updated_patterns["bp_trend"] = delta_patterns["bp_trend"]
    if delta_patterns.get("consecutive_elevated_streak"):
        updated_patterns["consecutive_elevated_streak"] = delta_patterns["consecutive_elevated_streak"]
    if delta_patterns.get("pulse_pressure_stats"):
        updated_patterns["pulse_pressure_stats"] = delta_patterns["pulse_pressure_stats"]
    if delta_patterns.get("bp_variability_cv"):
        updated_patterns["bp_variability_cv"] = delta_patterns["bp_variability_cv"]
    if delta_patterns.get("bp_percentiles"):
        updated_patterns["bp_percentiles"] = delta_patterns["bp_percentiles"]
    if delta_patterns.get("glucose_variability_cv"):
        updated_patterns["glucose_variability_cv"] = delta_patterns["glucose_variability_cv"]
    if delta_patterns.get("time_of_day_heatmap"):
        updated_patterns["time_of_day_heatmap"] = delta_patterns["time_of_day_heatmap"]
    if delta_patterns.get("symptom_co_occurrence"):
        updated_patterns["symptom_co_occurrence"] = delta_patterns["symptom_co_occurrence"]

    updated_stats["patterns"] = updated_patterns
    return updated_stats


def reinforce_correlation_bank(
    prior_bank: Optional[Dict[str, Any]],
    current_correlations: List[CorrelationItem],
    session_resumed: bool = False
) -> Tuple[List[CorrelationItem], Dict[str, Any]]:
    """
    Maintains a persistent bank of clinical findings across sessions.
    Reinforces existing findings with incremental evidence rather than re-discovering from zero.
    """
    bank = dict(prior_bank) if prior_bank else {}
    reinforced_correlations: List[CorrelationItem] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in current_correlations:
        key = f"{item.category}_{item.headline[:30].lower().strip().replace(' ', '_')}"
        if key in bank and session_resumed:
            prior_entry = bank[key]
            new_evidence = max(prior_entry.get("evidence_count", 1) + 1, item.evidence_count)
            prior_entry["evidence_count"] = new_evidence
            prior_entry["last_reinforced_at"] = now_iso
            prior_entry["reinforcement_count"] = prior_entry.get("reinforcement_count", 1) + 1

            reinforced_correlations.append(CorrelationItem(
                category=item.category,
                confidence="high" if new_evidence >= 3 else item.confidence,
                headline=prior_entry.get("headline", item.headline),
                explanation=f"{item.explanation} [Reinforced across {new_evidence} cumulative logs]",
                evidence_count=new_evidence,
                clinical_suggestion=prior_entry.get("clinical_suggestion", item.clinical_suggestion)
            ))
        else:
            bank[key] = {
                "category": item.category,
                "confidence": item.confidence,
                "headline": item.headline,
                "explanation": item.explanation,
                "evidence_count": item.evidence_count,
                "clinical_suggestion": item.clinical_suggestion,
                "first_detected_at": now_iso,
                "last_reinforced_at": now_iso,
                "reinforcement_count": 1
            }
            reinforced_correlations.append(item)

    return reinforced_correlations, bank


def generate_progressive_doctor_summary(
    stats: Dict[str, Any],
    correlations: List[CorrelationItem],
    rote_memory: Optional[Dict[str, Any]] = None
) -> str:
    """
    Produces a progressive physician narrative that anchors on the historical baseline
    and highlights the incremental delta changes rather than writing a full summary from zero.
    """
    lines = []
    total_bp = stats.get("total_bp_readings", 0)
    total_glu = stats.get("total_glucose_readings", 0)
    avg_sys = stats.get("avg_systolic", "N/A")
    avg_dia = stats.get("avg_diastolic", "N/A")
    avg_glu = stats.get("avg_glucose_mg_dl", "N/A")

    if rote_memory is not None and not isinstance(rote_memory, dict):
        if hasattr(rote_memory, "model_dump"):
            rote_memory = rote_memory.model_dump()
        else:
            rote_memory = getattr(rote_memory, "__dict__", {})

    if rote_memory and rote_memory.get("session_resumed"):
        checkpoint_at = rote_memory.get("last_checkpoint_at", "previous session")
        delta_cnt = rote_memory.get("delta_readings_count", 0)
        shift_desc = rote_memory.get("trajectory_shift_summary", "")

        lines.append(
            f"Progressive Longitudinal Clinical Evaluation: Anchored across {total_bp} blood pressure and {total_glu} glucose measurements (cumulative baseline systolic/diastolic: {avg_sys}/{avg_dia} mmHg, glucose {avg_glu} mg/dL)."
        )
        lines.append(
            f"Since last evaluation ({checkpoint_at}), {delta_cnt} new reading(s) were recorded. {shift_desc}"
        )
    else:
        lines.append(
            f"Baseline Clinical Evaluation: Established across {total_bp} blood pressure measurements (mean systolic/diastolic: {avg_sys}/{avg_dia} mmHg) and {total_glu} glucose recordings (mean: {avg_glu} mg/dL)."
        )

    if correlations:
        top_items = [f"'{c.headline}' ({c.category.replace('_', ' ')})" for c in correlations[:3]]
        lines.append(f"Active clinical correlations under monitoring: {'; '.join(top_items)}.")
    else:
        lines.append("No acute cross-stream anomalies or adverse confounders were noted.")

    lines.append("Continue tracking routine diurnal vitals and share this cumulative longitudinal trajectory with your attending physician.")
    return " ".join(lines)


# =====================================================================
# 1c. Exact Pattern Detection Engine
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

    # 3. Multi-Device Telemetry & Metabolic-Cardiovascular Interactions
    paired = stats.get("paired_readings", [])
    if paired:
        post_meal_elevations = [
            p for p in paired
            if (p.get("glucose_mg_dl", 0) >= 140) and ((p.get("pulse") or 0) >= 85 or (p.get("systolic") or 0) >= 135)
        ]
        if post_meal_elevations:
            cnt = len(post_meal_elevations)
            avg_pulse_paired = round(sum(p["pulse"] for p in post_meal_elevations if p.get("pulse")) / cnt, 1) if any(p.get("pulse") for p in post_meal_elevations) else None
            avg_glu_paired = round(sum(p["glucose_mg_dl"] for p in post_meal_elevations) / cnt, 1)
            avg_sys_paired = round(sum(p["systolic"] for p in post_meal_elevations if p.get("systolic")) / cnt, 1) if any(p.get("systolic") for p in post_meal_elevations) else None
            pulse_desc = f"resting heart rate averaging {avg_pulse_paired} bpm and " if avg_pulse_paired else ""
            correlations.append(CorrelationItem(
                category="metabolic_cardiovascular",
                confidence="high" if cnt >= 3 else "moderate",
                headline="Post-Prandial Glycemic Excursions Coincide with Cardiovascular Load",
                explanation=f"In {cnt} paired measurement window{'s' if cnt > 1 else ''} within 2 hours, blood glucose elevation (>=140 mg/dL) coincided with {pulse_desc}elevated systolic pressure.",
                evidence_count=cnt,
                clinical_suggestion="Review meal carbohydrate density and consider light post-meal walking to moderate autonomic glycemic stress."
            ))
            correlations.append(CorrelationItem(
                category="multi_device_correlation",
                confidence="high" if cnt >= 3 else "moderate",
                headline="Multi-Device Synergy: Glucometer Spikes Correlate with Sphygmomanometer Pressure Surge",
                explanation=f"Across {cnt} cross-device paired window{'s' if cnt > 1 else ''} within 2 hours, blood glucose elevation on your Glucometer (averaging {avg_glu_paired} mg/dL) directly coincided with {pulse_desc}elevated systolic pressure (averaging {avg_sys_paired} mmHg) captured on your Sphygmomanometer.",
                evidence_count=cnt,
                clinical_suggestion="Review meal carbohydrate density and consider light post-meal walking to moderate autonomic glycemic-cardiovascular stress across both monitoring devices."
            ))

    # 3b. Multi-Device Pulse Oximeter & Sphygmomanometer Telemetry
    avg_spo2 = stats.get("avg_spo2")
    if avg_spo2 is not None:
        spo2_cnt = stats.get("spo2_count", 1)
        correlations.append(CorrelationItem(
            category="multi_device_correlation",
            confidence="high" if spo2_cnt >= 2 else "moderate",
            headline="Multi-Device Telemetry: Pulse Oximeter & Sphygmomanometer Perfusion Alignment",
            explanation=f"Peripheral blood oxygen saturation (SpO2) averaged {avg_spo2}% across {spo2_cnt} reading{'s' if spo2_cnt > 1 else ''} on your Pulse Oximeter, confirming adequate microvascular oxygenation during Sphygmomanometer blood pressure recordings.",
            evidence_count=spo2_cnt,
            clinical_suggestion="Continue synchronizing readings between your Sphygmomanometer and Pulse Oximeter."
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
                explanation=f"Morning blood pressure averages {m_sys}/{m_bp['diastolic']} mmHg, which is {diff} mmHg higher than your evening average of {e_sys}/{e_bp['diastolic']} mmHg on your Sphygmomanometer.",
                evidence_count=m_bp["count"] + e_bp["count"],
                clinical_suggestion="Discuss morning blood pressure surges with your physician to evaluate medication timing and morning autonomic activity."
            ))
        elif diff <= -8.0:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="moderate",
                headline="Evening Blood Pressure Elevation Noted",
                explanation=f"Evening blood pressure averages {e_sys}/{e_bp['diastolic']} mmHg, exceeding morning levels by {abs(diff)} mmHg on your Sphygmomanometer.",
                evidence_count=m_bp["count"] + e_bp["count"],
                clinical_suggestion="Log late afternoon stress and dietary sodium to investigate evening pressure increases."
            ))

    # 5. Multi-Device Fluid Shifts (Digital Scale + Sphygmomanometer)
    for ws in stats.get("weight_shifts", []):
        correlations.append(CorrelationItem(
            category="multi_device_correlation",
            confidence="high",
            headline="Multi-Device Correlation: Digital Scale Weight Surge Coincides with Hemodynamic Shift",
            explanation=f"A rapid weight change of +{ws['delta_kg']} kg was recorded over {ws['hours']} hours on your Digital Scale, which may indicate acute fluid accumulation impacting systemic vascular resistance.",
            evidence_count=1,
            clinical_suggestion="Consult your healthcare provider promptly if accompanied by lower extremity swelling, shortness of breath, or elevated blood pressure."
        ))

    # 5b. 7-Day vs 14-Day Trajectory Trend & Glycemic Target Range
    traj = stats.get("trajectory_7d_vs_14d")
    if traj and traj.get("recent_7d_avg_systolic") is not None and traj.get("prior_7d_avg_systolic") is not None:
        delta_s = traj["delta_systolic"]
        recent_s = traj["recent_7d_avg_systolic"]
        prior_s = traj["prior_7d_avg_systolic"]
        n_tot = traj.get("recent_count", 0) + traj.get("prior_count", 0)
        if delta_s <= -3.0:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="high",
                headline=f"7-Day vs 14-Day Trajectory: {abs(delta_s)} mmHg Systolic Improvement",
                explanation=f"Sphygmomanometer readings show progressive hemodynamic stabilization: 7-day average systolic dropped to {recent_s} mmHg compared to {prior_s} mmHg during the prior period (-{abs(delta_s)} mmHg improvement across {n_tot} readings).",
                evidence_count=n_tot,
                clinical_suggestion="Maintain consistent lifestyle and pharmacologic regimen to support continued blood pressure optimization."
            ))
        elif delta_s >= 3.0:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="high",
                headline=f"7-Day vs 14-Day Trajectory: +{delta_s} mmHg Systolic Drift",
                explanation=f"Recent 7-day systolic blood pressure on your Sphygmomanometer averaged {recent_s} mmHg compared to {prior_s} mmHg in the prior window (+{delta_s} mmHg drift across {n_tot} readings).",
                evidence_count=n_tot,
                clinical_suggestion="Review dietary sodium, stress logs, and medication compliance with your attending clinician."
            ))
        else:
            correlations.append(CorrelationItem(
                category="longitudinal_trend",
                confidence="moderate",
                headline="7-Day vs 14-Day Trajectory: Stable Longitudinal Hemodynamics",
                explanation=f"Systolic blood pressure on your Sphygmomanometer remains stable across consecutive monitoring windows ({recent_s} vs {prior_s} mmHg baseline across {n_tot} readings).",
                evidence_count=n_tot,
                clinical_suggestion="Continue regular morning and evening monitoring to track longitudinal stability."
            ))

    tir = stats.get("glucose_tir_pct")
    if tir is not None and stats.get("total_glucose_readings", 0) >= 3:
        correlations.append(CorrelationItem(
            category="longitudinal_trend",
            confidence="high" if stats.get("total_glucose_readings", 0) >= 6 else "moderate",
            headline=f"Glycemic Trend: {tir}% Time in ADA Target Range",
            explanation=f"Across {stats.get('total_glucose_readings')} Glucometer readings, {tir}% fell within the clinical target range (70-180 mg/dL), with fasting glucose averaging {stats.get('fasting_avg_glucose', 'N/A')} mg/dL.",
            evidence_count=stats.get("total_glucose_readings", 1),
            clinical_suggestion="Continue monitoring fasting and post-meal glucose to sustain glycemic stability."
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

    # 7. Rote Memory Incremental Continuation & Correlation Bank
    rote_mem = stats.get("rote_memory")
    session_resumed = bool(rote_mem.get("session_resumed")) if (rote_mem and isinstance(rote_mem, dict)) else False

    if rote_mem and session_resumed:
        shift_txt = rote_mem.get("trajectory_shift_summary") or f"{rote_mem.get('delta_readings_count')} new reading(s) integrated since previous session."
        correlations.insert(0, CorrelationItem(
            category="longitudinal_trend",
            confidence="high",
            headline="Session Resumed: Longitudinal Progression",
            explanation=f"Continuing from previous checkpoint ({rote_mem.get('last_checkpoint_at')}). {shift_txt}",
            evidence_count=int(rote_mem.get("delta_readings_count", 1)),
            clinical_suggestion="Continue regular logging to maintain longitudinal pattern tracking across sessions."
        ))

    prior_bank = rote_mem.get("correlation_bank") if (rote_mem and isinstance(rote_mem, dict)) else None
    reinforced_correlations, updated_bank = reinforce_correlation_bank(
        prior_bank=prior_bank,
        current_correlations=correlations,
        session_resumed=session_resumed
    )
    correlations = reinforced_correlations

    if rote_mem and isinstance(rote_mem, dict):
        rote_mem["correlation_bank"] = updated_bank
        if "accumulators" in stats and not rote_mem.get("accumulators"):
            rote_mem["accumulators"] = stats["accumulators"]

    doctor_summary = generate_progressive_doctor_summary(stats, correlations, rote_mem)

    now_iso = datetime.now(timezone.utc).isoformat()
    return HealthAnalysisResponse(
        user_id=user_id,
        generated_at=now_iso,
        is_cached=False,
        stats=AnalysisStats(
            total_bp_readings=stats.get("total_bp_readings", 0),
            total_glucose_readings=stats.get("total_glucose_readings", 0),
            total_weight_readings=stats.get("total_weight_readings", 0),
            devices_detected=stats.get("devices_detected", []),
            avg_systolic=stats.get("avg_systolic"),
            avg_diastolic=stats.get("avg_diastolic"),
            avg_pulse=stats.get("avg_pulse"),
            avg_glucose_mg_dl=stats.get("avg_glucose_mg_dl"),
            avg_spo2=stats.get("avg_spo2"),
            morning_avg_bp={"systolic": m_bp["systolic"], "diastolic": m_bp["diastolic"]} if m_bp else None,
            evening_avg_bp={"systolic": e_bp["systolic"], "diastolic": e_bp["diastolic"]} if e_bp else None,
            fasting_avg_glucose=stats.get("fasting_avg_glucose"),
            post_meal_avg_glucose=stats.get("post_meal_avg_glucose"),
            trajectory_7d_vs_14d=stats.get("trajectory_7d_vs_14d")
        ),
        patterns=stats.get("patterns"),
        rote_memory=RoteMemoryState(**rote_mem) if rote_mem else None,
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

STEP 3 — MULTI-DEVICE TELEMETRY & CROSS-STREAM PAIRING:
  For measurements taken across multiple clinical device modalities:
  - Sphygmomanometer (blood pressure and pulse)
  - Glucometer (capillary blood glucose)
  - Pulse Oximeter (SpO2 oxygen saturation and pulse)
  - Digital Scale (body weight and fluid shifts)
  Examine cross-device interactions: did post-meal Glucometer elevations precede Sphygmomanometer pressure/pulse surges? Does Pulse Oximeter SpO2 align with hemodynamic strain? Does Digital Scale weight surge match fluid-retention hypertension?
  Assign category "multi_device_correlation" for findings involving two or more device modalities.

STEP 4 — LONGITUDINAL TREND SYNTHESIS:
  After completing steps 1-3, synthesize:
  - Is the patient's overall 7-day vs 14-day trajectory IMPROVING, STABLE, or DETERIORATING?
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
      "category": "lifestyle_trigger" | "metabolic_cardiovascular" | "symptom_spike" | "longitudinal_trend" | "medication_response" | "fluid_weight_shift" | "multi_device_correlation" | "other",
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
    devs = stats.get("devices_detected", [])
    if devs:
        sections.append(f"Devices Active in Telemetry: {', '.join(devs)}")
    sections.append(f"Total Blood Pressure Recordings (Sphygmomanometer): {stats.get('total_bp_readings', 0)}")
    sections.append(f"Total Blood Glucose Recordings (Glucometer): {stats.get('total_glucose_readings', 0)}")
    if stats.get("total_weight_readings"):
        sections.append(f"Total Weight Recordings (Digital Scale): {stats.get('total_weight_readings')}")
    if stats.get("avg_spo2") is not None:
        sections.append(f"Pulse Oximeter Average SpO2: {stats['avg_spo2']}% (n={stats.get('spo2_count', 0)})")
    traj = stats.get("trajectory_7d_vs_14d")
    if traj:
        sections.append(
            f"7-Day vs 14-Day Trajectory Trend: Recent 7d Systolic {traj['recent_7d_avg_systolic']} mmHg vs Prior 7d {traj['prior_7d_avg_systolic']} mmHg (Δ {traj['delta_systolic']} mmHg, direction: {traj['direction']})"
        )
    if stats.get("glucose_tir_pct") is not None:
        sections.append(f"Glucometer Time in Range (70-180 mg/dL): {stats['glucose_tir_pct']}%")

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

    # Rote Memory (Pick up from where left off)
    rote_mem = stats.get("rote_memory")
    if rote_mem and rote_mem.get("session_resumed"):
        sections.append("\n=== RESUMED SESSION (CONTINUING FROM PRIOR EVALUATION) ===")
        sections.append(f"  Prior Checkpoint Timestamp: {rote_mem.get('last_checkpoint_at')}")
        sections.append(f"  Prior Baseline: Systolic={rote_mem.get('prior_baseline_systolic')} mmHg, Glucose={rote_mem.get('prior_baseline_glucose')} mg/dL")
        sections.append(f"  Prior Trajectory Trend: {rote_mem.get('prior_trajectory_trend')}")
        sections.append(f"  Delta Readings Integrated: {rote_mem.get('delta_readings_count')}")
        sections.append(f"  Longitudinal Shift: {rote_mem.get('trajectory_shift_summary')}")
        sections.append("  ROTE INSTRUCTION: Do NOT start from scratch. Build upon the prior findings and describe the trajectory progression.")

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
            valid_categories = {"lifestyle_trigger", "metabolic_cardiovascular", "symptom_spike", "longitudinal_trend", "medication_response", "fluid_weight_shift", "multi_device_correlation", "other"}
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

            rote_mem = stats.get("rote_memory")
            session_resumed = bool(rote_mem.get("session_resumed")) if (rote_mem and isinstance(rote_mem, dict)) else False
            if rote_mem and isinstance(rote_mem, dict):
                prior_bank = rote_mem.get("correlation_bank")
                correlations, updated_bank = reinforce_correlation_bank(
                    prior_bank=prior_bank,
                    current_correlations=correlations,
                    session_resumed=session_resumed
                )
                rote_mem["correlation_bank"] = updated_bank
                if "accumulators" in stats and not rote_mem.get("accumulators"):
                    rote_mem["accumulators"] = stats["accumulators"]

            return HealthAnalysisResponse(
                user_id=user_id,
                generated_at=now_iso,
                is_cached=False,
                stats=AnalysisStats(
                    total_bp_readings=stats.get("total_bp_readings", 0),
                    total_glucose_readings=stats.get("total_glucose_readings", 0),
                    total_weight_readings=stats.get("total_weight_readings", 0),
                    devices_detected=stats.get("devices_detected", []),
                    avg_systolic=stats.get("avg_systolic"),
                    avg_diastolic=stats.get("avg_diastolic"),
                    avg_pulse=stats.get("avg_pulse"),
                    avg_glucose_mg_dl=stats.get("avg_glucose_mg_dl"),
                    avg_spo2=stats.get("avg_spo2"),
                    morning_avg_bp={"systolic": m_bp["systolic"], "diastolic": m_bp["diastolic"]} if m_bp else None,
                    evening_avg_bp={"systolic": e_bp["systolic"], "diastolic": e_bp["diastolic"]} if e_bp else None,
                    fasting_avg_glucose=stats.get("fasting_avg_glucose"),
                    post_meal_avg_glucose=stats.get("post_meal_avg_glucose"),
                    trajectory_7d_vs_14d=stats.get("trajectory_7d_vs_14d")
                ),
                patterns=stats.get("patterns"),
                rote_memory=RoteMemoryState(**rote_mem) if rote_mem else None,
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

    # 1. Check cache validity & retrieve prior rote checkpoint
    prior_checkpoint_data = None
    if analysis_ref is not None:
        try:
            cached_doc = analysis_ref.get()
            if getattr(cached_doc, "exists", False) is True:
                doc_dict = cached_doc.to_dict()
                if isinstance(doc_dict, dict) and isinstance(doc_dict.get("generated_at"), str):
                    prior_checkpoint_data = doc_dict
                    gen_at = _parse_iso_datetime(prior_checkpoint_data.get("generated_at"))
                    if not force_refresh and gen_at and (now - gen_at).total_seconds() < 3600:
                        # Check if any measurement was created after generated_at
                        measurements_ref = db.collection("profiles").document(user_id).collection("measurements")
                        newer_docs = (
                            measurements_ref
                            .where("created_at", ">", prior_checkpoint_data.get("generated_at"))
                            .limit(1)
                            .stream()
                        )
                        has_newer = any(True for _ in newer_docs)
                        if not has_newer:
                            # Repetitive query with no new data: return cached directly without recomputation
                            resp = HealthAnalysisResponse(**prior_checkpoint_data)
                            resp.is_cached = True
                            return resp
        except Exception as cache_err:
            print(f"[AnalysisService] Cache read notice: {cache_err}. Computing fresh analysis.")

    # 2. Fetch measurements & evaluate: Incremental Rote vs Full Fetch
    prior_rote = prior_checkpoint_data.get("rote_memory", {}) if (prior_checkpoint_data and isinstance(prior_checkpoint_data.get("rote_memory"), dict)) else {}
    prior_accumulators = prior_rote.get("accumulators") or (prior_checkpoint_data.get("stats", {}).get("accumulators") if (prior_checkpoint_data and isinstance(prior_checkpoint_data.get("stats"), dict)) else None)
    prior_gen_at = str(prior_checkpoint_data.get("generated_at", "")) if (prior_checkpoint_data and prior_checkpoint_data.get("generated_at")) else None

    use_incremental = (
        not force_refresh
        and prior_checkpoint_data is not None
        and prior_accumulators is not None
        and bool(prior_gen_at)
        and db is not None
    )

    stats = None

    if use_incremental:
        delta_bp_records: List[Dict[str, Any]] = []
        delta_glucose_records: List[Dict[str, Any]] = []
        delta_weight_records: List[Dict[str, Any]] = []
        fetch_success = False

        try:
            m_ref = db.collection("profiles").document(user_id).collection("measurements")
            # Query only delta documents created strictly after prior checkpoint
            delta_docs = m_ref.where("created_at", ">", prior_gen_at).stream()
            for doc in delta_docs:
                item = doc.to_dict()
                m_type = item.get("measurement_type")
                if m_type == "blood_pressure":
                    delta_bp_records.append(item)
                elif m_type == "blood_glucose":
                    delta_glucose_records.append(item)

            w_ref = db.collection("profiles").document(user_id).collection("weight_history")
            w_docs = w_ref.where("recorded_at", ">", prior_gen_at).stream()
            delta_weight_records = [w.to_dict() for w in w_docs]
            fetch_success = True
        except Exception as delta_fetch_err:
            print(f"[AnalysisService] Notice: Delta fetch fallback to full fetch: {delta_fetch_err}")
            fetch_success = False

        if fetch_success:
            delta_count = len(delta_bp_records) + len(delta_glucose_records)
            # If 0 new measurements were logged, short-circuit and return cached analysis (0 reads / 0 ms)
            if delta_count == 0 and len(delta_weight_records) == 0:
                resp = HealthAnalysisResponse(**prior_checkpoint_data)
                resp.is_cached = True
                return resp

            # Update running statistics in O(k) time
            prior_stats = prior_checkpoint_data.get("stats", {}) if isinstance(prior_checkpoint_data.get("stats"), dict) else {}
            stats = update_running_stats(
                prior_stats=prior_stats,
                prior_accumulators=prior_accumulators,
                delta_bp_records=delta_bp_records,
                delta_glucose_records=delta_glucose_records,
                delta_weight_records=delta_weight_records
            )

            prior_sys = prior_stats.get("avg_systolic") if isinstance(prior_stats.get("avg_systolic"), (int, float)) else None
            prior_glu = prior_stats.get("avg_glucose_mg_dl") if isinstance(prior_stats.get("avg_glucose_mg_dl"), (int, float)) else None
            prior_patterns = prior_checkpoint_data.get("patterns", {}) if isinstance(prior_checkpoint_data.get("patterns"), dict) else {}
            bp_t = prior_patterns.get("bp_trend", {}) if isinstance(prior_patterns.get("bp_trend"), dict) else {}
            prior_trend = str(bp_t.get("trend_label", "")) if bp_t.get("trend_label") else None

            current_sys = stats.get("avg_systolic")
            if current_sys is not None and prior_sys is not None and delta_count > 0:
                diff_sys = round(current_sys - prior_sys, 1)
                dir_text = f"+{diff_sys} mmHg shift" if diff_sys > 0 else f"{diff_sys} mmHg shift" if diff_sys < 0 else "unchanged"
                shift_summary = f"Integrated {delta_count} new reading(s). Baseline systolic shifted from {prior_sys} to {current_sys} mmHg ({dir_text})."
            elif delta_count > 0:
                shift_summary = f"Integrated {delta_count} new reading(s) onto prior baseline."
            else:
                shift_summary = "Re-evaluating longitudinal baseline with existing data."

            prior_bank = prior_rote.get("correlation_bank") or (prior_checkpoint_data.get("correlation_bank") if isinstance(prior_checkpoint_data.get("correlation_bank"), dict) else {})
            prior_version = int(prior_rote.get("checkpoint_version", 1))

            stats["rote_memory"] = {
                "session_resumed": True,
                "last_checkpoint_at": prior_gen_at,
                "delta_readings_count": delta_count,
                "prior_baseline_systolic": prior_sys,
                "prior_baseline_glucose": prior_glu,
                "prior_trajectory_trend": prior_trend,
                "trajectory_shift_summary": shift_summary,
                "accumulators": stats.get("accumulators"),
                "correlation_bank": prior_bank,
                "checkpoint_version": prior_version + 1
            }
        else:
            use_incremental = False

    if not use_incremental:
        # Full historical fetch (initial baseline, forced refresh, or legacy checkpoint missing accumulators)
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

        stats = preaggregate_health_data(bp_records, glucose_records, weight_records)

        if prior_checkpoint_data and isinstance(prior_checkpoint_data, dict):
            prior_stats = prior_checkpoint_data.get("stats", {}) if isinstance(prior_checkpoint_data.get("stats"), dict) else {}
            prior_patterns = prior_checkpoint_data.get("patterns", {}) if isinstance(prior_checkpoint_data.get("patterns"), dict) else {}
            prior_sys = prior_stats.get("avg_systolic") if isinstance(prior_stats.get("avg_systolic"), (int, float)) else None
            prior_glu = prior_stats.get("avg_glucose_mg_dl") if isinstance(prior_stats.get("avg_glucose_mg_dl"), (int, float)) else None
            bp_t = prior_patterns.get("bp_trend", {}) if isinstance(prior_patterns.get("bp_trend"), dict) else {}
            prior_trend = str(bp_t.get("trend_label", "")) if bp_t.get("trend_label") else None

            delta_bp = sum(1 for r in bp_records if str(r.get("created_at") or r.get("recorded_at", "")) > (prior_gen_at or ""))
            delta_glu = sum(1 for g in glucose_records if str(g.get("created_at") or g.get("recorded_at", "")) > (prior_gen_at or ""))
            delta_count = delta_bp + delta_glu

            current_sys = stats.get("avg_systolic")
            if current_sys is not None and prior_sys is not None and delta_count > 0:
                diff_sys = round(current_sys - prior_sys, 1)
                dir_text = f"+{diff_sys} mmHg shift" if diff_sys > 0 else f"{diff_sys} mmHg shift" if diff_sys < 0 else "unchanged"
                shift_summary = f"Integrated {delta_count} new reading(s). Baseline systolic shifted from {prior_sys} to {current_sys} mmHg ({dir_text})."
            elif delta_count > 0:
                shift_summary = f"Integrated {delta_count} new reading(s) onto prior baseline."
            else:
                shift_summary = "Re-evaluating longitudinal baseline with existing data."

            prior_bank = prior_rote.get("correlation_bank") or (prior_checkpoint_data.get("correlation_bank") if isinstance(prior_checkpoint_data.get("correlation_bank"), dict) else {})
            prior_version = int(prior_rote.get("checkpoint_version", 1))

            stats["rote_memory"] = {
                "session_resumed": True,
                "last_checkpoint_at": prior_gen_at,
                "delta_readings_count": delta_count,
                "prior_baseline_systolic": prior_sys,
                "prior_baseline_glucose": prior_glu,
                "prior_trajectory_trend": prior_trend,
                "trajectory_shift_summary": shift_summary,
                "accumulators": stats.get("accumulators"),
                "correlation_bank": prior_bank,
                "checkpoint_version": prior_version + 1
            }
        else:
            stats["rote_memory"] = {
                "session_resumed": False,
                "last_checkpoint_at": None,
                "delta_readings_count": stats.get("total_bp_readings", 0) + stats.get("total_glucose_readings", 0),
                "prior_baseline_systolic": None,
                "prior_baseline_glucose": None,
                "prior_trajectory_trend": None,
                "trajectory_shift_summary": "Initial baseline established.",
                "accumulators": stats.get("accumulators"),
                "correlation_bank": {},
                "checkpoint_version": 1
            }

    analysis = generate_correlation_insights(user_id, stats)

    # 4. Save to cache as new rote checkpoint
    if db is not None and analysis_ref is not None:
        try:
            analysis_dict = analysis.model_dump()
            analysis_dict["is_cached"] = False
            analysis_ref.set(analysis_dict)
        except Exception as save_err:
            print(f"[AnalysisService] Error caching analysis: {save_err}")

    return analysis
