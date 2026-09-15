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

    return stats


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
