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

load_dotenv()

from schemas import (
    ScanExtractionResponse,
    BloodPressureValues,
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
   - Identify whether this image displays a digital blood pressure monitor.
   - Supported types: "blood_pressure", "blood_glucose", "pulse_oximeter", "weight", "unknown".
   - If the image is NOT a digital blood pressure monitor (e.g., photo of a person, animal, document, prescription, or another medical device), set "detected_type" accordingly and set "is_readable": false.

2. DIGIT & VALUE EXTRACTION (for digital blood pressure monitors):
   - Typical blood pressure monitors show three main values on a seven-segment or LCD display:
     * SYS (Systolic blood pressure in mmHg, usually top or largest number, typical range 40 - 300)
     * DIA (Diastolic blood pressure in mmHg, usually middle number, typical range 30 - 200)
     * PUL / PULSE / Heart icon (Pulse rate in bpm, usually bottom or smallest number, typical range 30 - 250)
   - Read 7-segment display digits carefully: do not confuse '8' and '0', '1' and '7', '5' and '6', etc.
   - CRITICAL CLINICAL RULE: Systolic MUST be strictly greater than Diastolic (SYS > DIA).
   - If the display orientation or layout has DIA above SYS or if values appear inverted, correctly identify which is systolic and which is diastolic based on standard physiological reality (Systolic is the higher pressure, Diastolic is the lower pressure).
   - If pulse is not displayed or not present, set pulse to null.

3. IMAGE QUALITY & DIAGNOSTICS:
   - is_readable: true if SYS and DIA digits can be deciphered with high certainty; false if illegible, covered, or absent.
   - glare_detected: true if flash, sunlight, lamp reflection, or specular glare partially or wholly obscures digits.
   - display_cut_off: true if any portion of the digital display numbers is cropped out of the frame.
   - issues: list of specific actionable visual issues observed, e.g.:
     * "glare on diastolic display"
     * "partial digit cutoff on right edge"
     * "motion blur affecting pulse reading"
     * "low contrast seven-segment display"
     * "image is upside down or angled heavily"
     (empty list [] if perfectly clear).

4. CONFIDENCE SCORE CALIBRATION (0.00 to 1.00):
   - 0.90 to 1.00: Crystal clear, straight-on framing, high contrast, all digits unambiguous.
   - 0.70 to 0.89: Slight glare, tilt, or mild reflections, but digits are reliably decipherable.
   - 0.40 to 0.69: Significant glare, blur, or missing segment; values deduced with uncertainty.
   - 0.00 to 0.39: Unreadable, severely corrupted, heavily obstructed, or not a blood pressure monitor.

5. DEVICE METADATA:
   - device_name: Brand and model name if printed on the device bezel, casing, or display (e.g., "Omron HEM-7120", "Beurer BM 28", "Microlife BP A2", "A&D Medical", "Welch Allyn"). If not clearly visible or unbranded, return null.

6. RAW OCR TEXT:
   - raw_detected_text: Exact sequence of text and numbers read from the display screen (e.g., "SYS 128 DIA 82 PUL 74 / mmHg").

Return strictly a single valid JSON object with this exact schema:
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


def detect_and_extract_measurement(
    image_bytes: bytes, 
    mime_type: str = "image/jpeg"
) -> ScanExtractionResponse:
    """
    Main entrypoint called by POST /api/scan/extract.
    
    Args:
        image_bytes: Raw bytes of the uploaded image file.
        mime_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').
        
    Returns:
        ScanExtractionResponse: Typed object with extracted numbers, confidence, device name, and quality report.
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
    try:
        model = client.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        response = model.generate_content([VISION_DETECTION_PROMPT, image_part])
        cleaned_json = _clean_json_string(response.text)
        data = json.loads(cleaned_json)

        return parse_vision_response(data, scan_id)

    except Exception as e:
        print(f"[VisionService] Gemini Vision extraction error: {e}")
        raise ValueError(f"Failed to detect or extract reading from image: {e}")
