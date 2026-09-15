"""
Vision & Measurement Detection Service
======================================
This service is responsible for:
1. Detecting / classifying the health measurement type from an uploaded image
   (e.g., blood pressure monitor, glucometer, pulse oximeter, scale, urinalysis).
2. Extracting numerical values, units, device model name, and confidence score.
3. Performing an image quality assessment (checking for glare, blur, or cut-off displays).

Instructions for Teammate:
- Implement or refine the Gemini Multimodal Vision prompt and parsing below.
- Ensure the function `detect_and_extract_measurement` returns a valid `ScanExtractionResponse`.
- The FastAPI route at `backend/routes/measurements.py` calls this function directly.
"""

import os
import json
import uuid
from typing import Optional
import google.generativeai as genai

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
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        print(f"[VisionService] Warning: Failed to configure Gemini client: {e}")
        return None

# =====================================================================
# Teammate Workspace: Prompts & Extraction Logic
# =====================================================================

VISION_DETECTION_PROMPT = """
You are an expert medical computer vision system.
Analyze this photo of a medical device display or health measurement.

Tasks:
1. Classify the measurement / device type:
   - "blood_pressure" (digital monitor with SYS, DIA, PULSE)
   - "blood_glucose" (glucometer reading with mg/dL or mmol/L)
   - "pulse_oximeter" (finger oximeter with SpO2% and PR bpm)
   - "weight" (scale with kg/lbs)
   - "unknown"

2. For Blood Pressure monitors, extract:
   - systolic: number (mmHg)
   - diastolic: number (mmHg)
   - pulse: number (bpm, or null if not shown)
   - Ensure systolic is strictly greater than diastolic.

3. Confidence score: float from 0.0 to 1.0 based on display clarity.

4. Image Quality Assessment:
   - is_readable: boolean (true if digits can be read with high certainty)
   - glare_detected: boolean (true if reflection obscures digits)
   - display_cut_off: boolean (true if the screen is partially outside the frame)
   - issues: array of strings describing any visual problems (e.g., ["glare on diastolic display", "blurry numbers"])

Return strictly JSON matching this format:
{
  "detected_type": "blood_pressure",
  "confidence": 0.96,
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
        ScanExtractionResponse: Typed object with extracted numbers, confidence, and quality report.
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
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        response = model.generate_content([VISION_DETECTION_PROMPT, image_part])
        data = json.loads(response.text.strip())

        # Parse image quality
        quality_info = data.get("quality", {})
        quality = ImageQualityReport(
            is_readable=quality_info.get("is_readable", True),
            glare_detected=quality_info.get("glare_detected", False),
            display_cut_off=quality_info.get("display_cut_off", False),
            issues=quality_info.get("issues", [])
        )

        # Parse numerical values
        values_dict = data.get("values", {})
        values = BloodPressureValues(
            systolic=int(values_dict["systolic"]),
            diastolic=int(values_dict["diastolic"]),
            pulse=int(values_dict["pulse"]) if values_dict.get("pulse") is not None else None
        )

        return ScanExtractionResponse(
            scan_id=scan_id,
            detected_type=data.get("detected_type", "blood_pressure"),
            values=values,
            confidence=float(data.get("confidence", 0.9)),
            quality=quality,
            raw_detected_text=data.get("raw_detected_text")
        )


    except Exception as e:
        print(f"[VisionService] Gemini Vision extraction error: {e}")
        raise ValueError(f"Failed to detect or extract reading from image: {e}")
