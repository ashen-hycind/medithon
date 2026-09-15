"""
Vision & Measurement Detection Service
======================================
This service is responsible for:
1. Detecting and classifying digital health measurement devices (specifically blood pressure monitors).
2. Extracting numerical values (systolic, diastolic, pulse) with clinical validation.
3. Diagnosing image quality (glare detection, display cut-off, readability assessment).
4. Extracting visible device brand/model metadata and raw display text.

Strict adherence to data contract:
- Returns: schemas.ScanExtractionResponse
- Clinical rule: systolic must be strictly greater than diastolic
- Preserves offline mock fallback when GEMINI_API_KEY is not configured
"""

import os
import json
import uuid
import re
from typing import Optional, Any, Dict

from dotenv import load_dotenv
from pathlib import Path
_backend_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_backend_env, override=True)
load_dotenv(override=True)

from schemas import (
    ScanExtractionResponse,
    BloodPressureValues,
    BloodGlucoseValues,
    ImageQualityReport
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
        print(f"[VisionService] Warning: Failed to configure Gemini client: {e}")
        return None


# =====================================================================
# Teammate Workspace: Prompts & Extraction Logic
# =====================================================================

VISION_DETECTION_PROMPT = """
You are an expert clinical computer vision diagnostic system specializing in digital medical devices.
Analyze this photo of a medical device display or health measurement reading.

Your objectives:
1. CLASSIFY DEVICE & MEASUREMENT:
   - Identify device type:
     * "blood_pressure" (digital monitor with SYS, DIA, and PULSE readings)
     * "blood_glucose" (digital glucometer display with blood sugar reading and mg/dL or mmol/L unit)
     * "pulse_oximeter" (finger pulse oximeter with SpO2% and PR bpm)
     * "weight" (scale with kg/lbs)
     * "unknown" (photo of a person, animal, document, prescription, or non-medical device)
   - If the image is "unknown", set "is_readable": false.

2. DIGIT & VALUE EXTRACTION:
   A. For Blood Pressure monitors:
      - SYS: systolic blood pressure in mmHg (typical range 40 - 300)
      - DIA: diastolic blood pressure in mmHg (typical range 30 - 200)
      - pulse: pulse rate in bpm (or null if not shown)
      - CRITICAL: Systolic MUST be strictly greater than Diastolic (SYS > DIA).
   B. For Blood Glucose meters (Glucometers):
      - glucose_value: numerical reading (float or int, e.g. 104, 126, 5.8).
      - unit: "mg/dL" or "mmol/L". Look for text label on screen. If not visible: values >= 35 are "mg/dL", values < 35 with or without decimals are "mmol/L".
      - meal_context: "fasting", "before_meal", "after_meal", "bedtime", or null if not indicated by screen icons (e.g. apple icon).

3. IMAGE QUALITY & DIAGNOSTICS:
   - is_readable: true if primary measurement digits can be deciphered with high certainty.
   - glare_detected: true if flash, specular glare, or reflection obscures display digits.
   - display_cut_off: true if any portion of digits is cropped out of the camera frame.
   - issues: list of specific actionable issues observed (e.g. ["glare on bottom digits", "test strip error"]), or [] if clear.

4. CONFIDENCE SCORE CALIBRATION (0.00 to 1.00):
   - 0.90 to 1.00: Clear, sharp contrast, unambiguous reading.
   - 0.70 to 0.89: Slight tilt, glare, or reflection, but digits deduced reliably.
   - 0.40 to 0.69: Heavy blur or missing segment; values uncertain.
   - 0.00 to 0.39: Unreadable or not a medical device.

5. DEVICE METADATA & OCR TEXT:
   - device_name: Brand/model (e.g. "Omron HEM-7120", "Accu-Chek Guide", "OneTouch Verio", "Contour Next"). If not visible, return null.
   - raw_detected_text: Exact sequence of text/numbers read from the screen.

Return strictly a single valid JSON object matching either schema:

For Blood Pressure:
{
  "detected_type": "blood_pressure",
  "device_name": "Omron HEM-7120",
  "confidence": 0.95,
  "values": {
    "systolic": 128,
    "diastolic": 82,
    "pulse": 74
  },
  "quality": {
    "is_readable": true,
    "glare_detected": false,
    "display_cut_off": false,
    "issues": []
  },
  "raw_detected_text": "SYS 128 DIA 82 PUL 74"
}

For Blood Glucose:
{
  "detected_type": "blood_glucose",
  "device_name": "Accu-Chek Instant",
  "confidence": 0.98,
  "values": {
    "glucose_value": 104.0,
    "unit": "mg/dL",
    "meal_context": "fasting"
  },
  "quality": {
    "is_readable": true,
    "glare_detected": false,
    "display_cut_off": false,
    "issues": []
  },
  "raw_detected_text": "104 mg/dL"
}
"""


def _clean_json_string(raw_text: str) -> str:
    """Strips markdown code blocks, backticks, and extra whitespace to extract valid JSON."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening fence (e.g. ```json or ```)
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_int(val: Any) -> Optional[int]:
    """Safely parses integer values from strings, floats, or mixed text."""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        # Extract digits
        digits = re.findall(r"\d+", val)
        if digits:
            return int("".join(digits))
    return None


def parse_vision_response(data: Dict[str, Any], scan_id: str) -> ScanExtractionResponse:
    """
    Parses, validates, and normalizes the parsed JSON dictionary from Gemini into ScanExtractionResponse.
    Enforces clinical validations and physiological range checks.
    """
    detected_type = str(data.get("detected_type", "unknown")).lower()
    if detected_type != "blood_pressure":
        raise ValueError(
            f"Image was classified as '{detected_type}', not a digital blood pressure monitor."
        )

    # Parse Image Quality
    quality_info = data.get("quality", {})
    is_readable = bool(quality_info.get("is_readable", True))
    glare_detected = bool(quality_info.get("glare_detected", False))
    display_cut_off = bool(quality_info.get("display_cut_off", False))
    issues = list(quality_info.get("issues", []))

    quality = ImageQualityReport(
        is_readable=is_readable,
        glare_detected=glare_detected,
        display_cut_off=display_cut_off,
        issues=issues
    )

    if not is_readable:
        issues_desc = "; ".join(issues) if issues else "Display digits are illegible or missing."
        raise ValueError(f"Image is not readable: {issues_desc}")

    # Parse Numerical Values
    values_dict = data.get("values", {})
    if not isinstance(values_dict, dict):
        raise ValueError("Missing 'values' object in model response.")

    systolic = _parse_int(values_dict.get("systolic"))
    diastolic = _parse_int(values_dict.get("diastolic"))
    pulse = _parse_int(values_dict.get("pulse"))

    if systolic is None or diastolic is None:
        raise ValueError("Could not extract both systolic and diastolic numbers from the image.")

    # Clinical validation: systolic must be strictly greater than diastolic
    if systolic <= diastolic:
        # Check if values were inadvertently inverted by display orientation
        if diastolic > systolic and (40 <= diastolic <= 300) and (30 <= systolic <= 200):
            print(f"[VisionService] Swapping inverted values: SYS was {systolic}, DIA was {diastolic} -> SYS={diastolic}, DIA={systolic}")
            quality.issues.append("Detected inverted SYS/DIA readings; values were corrected.")
            systolic, diastolic = diastolic, systolic
        else:
            raise ValueError(
                f"Clinically invalid reading: Systolic ({systolic} mmHg) must be strictly greater than Diastolic ({diastolic} mmHg)."
            )

    # Physiological range checks
    if not (40 <= systolic <= 300):
        raise ValueError(f"Systolic value {systolic} mmHg is outside valid physiological bounds (40 - 300 mmHg).")
    if not (30 <= diastolic <= 200):
        raise ValueError(f"Diastolic value {diastolic} mmHg is outside valid physiological bounds (30 - 200 mmHg).")
    if pulse is not None and not (30 <= pulse <= 250):
        quality.issues.append(f"Pulse reading {pulse} bpm fell outside standard physiological range (30 - 250 bpm) and was omitted.")
        pulse = None

    values = BloodPressureValues(
        systolic=systolic,
        diastolic=diastolic,
        pulse=pulse
    )

    # Confidence score calibration
    raw_confidence = data.get("confidence", 0.9)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.85
    confidence = max(0.0, min(1.0, confidence))

    # Device name & OCR text
    device_name = data.get("device_name")
    if device_name and not isinstance(device_name, str):
        device_name = str(device_name)
    if device_name and device_name.strip().lower() in {"null", "none", ""}:
        device_name = None

    raw_detected_text = data.get("raw_detected_text")
    if raw_detected_text and not isinstance(raw_detected_text, str):
        raw_detected_text = str(raw_detected_text)

    return ScanExtractionResponse(
        scan_id=scan_id,
        detected_type="blood_pressure",
        device_name=device_name.strip() if device_name else None,
        values=values,
        confidence=confidence,
        quality=quality,
        raw_detected_text=raw_detected_text.strip() if raw_detected_text else None
    )


def parse_glucose_response(data: Dict[str, Any], scan_id: str) -> ScanExtractionResponse:
    """
    Parses, validates, and normalizes the parsed JSON dictionary from Gemini for a digital glucometer.
    Enforces physiological bounds and unit integrity.
    """
    quality_info = data.get("quality", {})
    is_readable = bool(quality_info.get("is_readable", True))
    glare_detected = bool(quality_info.get("glare_detected", False))
    display_cut_off = bool(quality_info.get("display_cut_off", False))
    issues = list(quality_info.get("issues", []))

    quality = ImageQualityReport(
        is_readable=is_readable,
        glare_detected=glare_detected,
        display_cut_off=display_cut_off,
        issues=issues
    )

    if not is_readable:
        issues_desc = "; ".join(issues) if issues else "Glucometer display digits are illegible or missing."
        raise ValueError(f"Image is not readable: {issues_desc}")

    values_dict = data.get("values", {})
    if not isinstance(values_dict, dict):
        raise ValueError("Missing 'values' object in model response.")

    raw_glucose = values_dict.get("glucose_value")
    if raw_glucose is None:
        raise ValueError("Could not extract blood glucose reading from the image.")

    try:
        glucose_val = float(raw_glucose)
    except (TypeError, ValueError):
        digits = re.findall(r"\d+\.?\d*", str(raw_glucose))
        if digits:
            glucose_val = float(digits[0])
        else:
            raise ValueError(f"Invalid glucose reading: {raw_glucose}")

    raw_unit = str(values_dict.get("unit", "")).strip().lower()
    if "mmol" in raw_unit:
        unit = "mmol/L"
    else:
        # If unit wasn't specified, deduce by magnitude
        if glucose_val < 35.0 and ("." in str(raw_glucose) or raw_unit == "mmol/l"):
            unit = "mmol/L"
        else:
            unit = "mg/dL"

    # Physiological range checks
    if unit == "mg/dL":
        if not (10.0 <= glucose_val <= 700.0):
            raise ValueError(f"Blood glucose reading {glucose_val} mg/dL is outside valid bounds (10 - 700 mg/dL).")
    else:
        if not (0.5 <= glucose_val <= 40.0):
            raise ValueError(f"Blood glucose reading {glucose_val} mmol/L is outside valid bounds (0.5 - 40.0 mmol/L).")

    raw_meal = values_dict.get("meal_context")
    meal_context = None
    if raw_meal and str(raw_meal).lower() in {"fasting", "before_meal", "after_meal", "bedtime", "random"}:
        meal_context = str(raw_meal).lower()

    glucose_values = BloodGlucoseValues(
        glucose_value=glucose_val,
        unit=unit,
        meal_context=meal_context
    )

    # Confidence score calibration
    raw_confidence = data.get("confidence", 0.95)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.90
    confidence = max(0.0, min(1.0, confidence))

    device_name = data.get("device_name")
    if device_name and not isinstance(device_name, str):
        device_name = str(device_name)
    if device_name and device_name.strip().lower() in {"null", "none", ""}:
        device_name = None

    raw_detected_text = data.get("raw_detected_text")
    if raw_detected_text and not isinstance(raw_detected_text, str):
        raw_detected_text = str(raw_detected_text)

    return ScanExtractionResponse(
        scan_id=scan_id,
        detected_type="blood_glucose",
        device_name=device_name.strip() if device_name else None,
        values=glucose_values,
        confidence=confidence,
        quality=quality,
        raw_detected_text=raw_detected_text.strip() if raw_detected_text else None
    )


def detect_and_extract_measurement(
    image_bytes: bytes, 
    mime_type: str = "image/jpeg"
) -> ScanExtractionResponse:
    """
    Main entrypoint called by POST /api/scan/extract.
    Supports both digital blood pressure monitors and digital glucometers.
    """
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    client = get_gemini_client()

    # -----------------------------------------------------------------
    # Fallback / Mock Mode: Allows frontend & API testing without API key
    # -----------------------------------------------------------------
    if not client:
        print("[VisionService] No GEMINI_API_KEY found. Returning mock blood pressure reading for development.")
        return ScanExtractionResponse(
            scan_id=scan_id,
            detected_type="blood_pressure",
            device_name="Omron HEM-7120 (Mock)",
            values=BloodPressureValues(systolic=128, diastolic=82, pulse=74),
            confidence=0.95,
            quality=ImageQualityReport(
                is_readable=True,
                glare_detected=False,
                display_cut_off=False,
                issues=[]
            ),
            raw_detected_text="SYS 128 / DIA 82 / PUL 74"
        )

    # -----------------------------------------------------------------
    # Live AI Vision Execution via Gemini Multimodal
    # -----------------------------------------------------------------
    preferred_model = os.getenv("GEMINI_MODEL")
    candidate_models = [preferred_model] if preferred_model else [
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash"
    ]

    last_err = None
    for model_name in candidate_models:
        if not model_name:
            continue
        try:
            model = client.GenerativeModel(
                model_name=model_name,
                generation_config={"response_mime_type": "application/json"}
            )

            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }

            response = model.generate_content([VISION_DETECTION_PROMPT, image_part])
            cleaned_json = _clean_json_string(response.text)
            data = json.loads(cleaned_json)

            detected_type = str(data.get("detected_type", "")).lower()
            if detected_type == "blood_glucose":
                return parse_glucose_response(data, scan_id)
            else:
                return parse_vision_response(data, scan_id)

        except Exception as e:
            print(f"[VisionService] Model '{model_name}' failed: {e}")
            last_err = e
            continue

    print(f"[VisionService] All Gemini Vision candidates failed: {last_err}")
    raise ValueError(f"Failed to detect or extract reading from image: {last_err}")

