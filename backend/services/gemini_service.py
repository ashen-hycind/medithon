import os
import json
import uuid
import re
from typing import List, Optional
import google.generativeai as genai
from pydantic import ValidationError

from schemas import (
    ExtractedIssue,
    ScanExtractionResponse,
    BloodPressureValues,
    ImageQualityReport
)

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        print(f"Warning: Failed to configure Gemini client: {e}")
        return None

ISSUES_EXTRACTION_PROMPT = """
You are an expert clinical context extractor for home blood pressure readings.
The user was asked: "Did you experience any issues, symptoms, or unusual conditions while taking this test?"
The 4 clinical pillars (based on CDC / American Heart Association guidelines) are:
1. Current Symptoms: dizziness, headache, chest pain, vision changes, shortness of breath.
   - CRITICAL: If chest pain, vision changes, or shortness of breath is mentioned, set is_red_flag = true.
2. Lifestyle Factors: daily stress, high salt intake, physical activity, sleep duration/quality.
3. Medications: DO NOT assume the user is on prescription blood pressure pills unless they explicitly say so!
   Extract:
   - Over-the-counter painkillers/NSAIDs (e.g. ibuprofen, Advil, Aleve, naproxen) which raise blood pressure.
   - Decongestants / cold medicines (pseudoephedrine) which raise blood pressure.
   - Herbal supplements that raise pressure.
   - Prescription BP drugs (e.g. amlodipine, lisinopril, losartan) ONLY if specifically mentioned as taken or missed.
   - If user explicitly notes they take no meds, do not output an issue for it.
4. Testing Conditions: caffeine/coffee/tea within 30 minutes, nicotine/smoking within 30 minutes, exercise right before test, anxiety / feeling rushed ("white coat syndrome"), resting time, posture, arm used.
5. Device Problems: cuff too loose, battery low, error codes.

Return a JSON array of objects with the following structure:
[
  {
    "category": "symptom" | "lifestyle" | "medication" | "testing_condition" | "device_problem" | "other",
    "tag": "standardized_snake_case_tag",
    "label": "Short User Friendly Label",
    "user_detail": "exact phrase from user",
    "is_red_flag": boolean,
    "severity": "mild" | "moderate" | "severe" | null
  }
]

Common tags: 'headache', 'dizziness', 'chest_pain', 'vision_changes', 'shortness_of_breath', 'caffeine_intake', 'nicotine_intake', 'recent_exercise', 'anxious_rushed', 'poor_sleep', 'high_stress', 'high_salt', 'otc_nsaid', 'decongestant', 'bp_med_taken', 'bp_med_missed'.

If the text indicates everything went well, no issues, normal reading, or no symptoms, return an empty array [].
Return strictly the JSON array.
"""

def extract_issues_heuristic(text: str) -> List[ExtractedIssue]:
    """
    Fallback deterministic heuristic extractor when Gemini API key is not configured.
    """
    lower = text.lower()
    issues: List[ExtractedIssue] = []

    # Symptoms
    if "chest pain" in lower or "chest tightness" in lower:
        issues.append(ExtractedIssue(
            category="symptom",
            tag="chest_pain",
            label="Chest Pain",
            user_detail="chest pain or tightness reported",
            is_red_flag=True,
            severity="severe"
        ))
    if "vision" in lower or "blurred" in lower:
        issues.append(ExtractedIssue(
            category="symptom",
            tag="vision_changes",
            label="Vision Changes",
            user_detail="vision changes reported",
            is_red_flag=True,
            severity="moderate"
        ))
    if "short of breath" in lower or "shortness of breath" in lower or "trouble breathing" in lower:
        issues.append(ExtractedIssue(
            category="symptom",
            tag="shortness_of_breath",
            label="Shortness of Breath",
            user_detail="shortness of breath reported",
            is_red_flag=True,
            severity="severe"
        ))
    if "headache" in lower or "head ache" in lower:
        issues.append(ExtractedIssue(
            category="symptom",
            tag="headache",
            label="Headache",
            user_detail="headache reported",
            is_red_flag=False,
            severity="mild"
        ))
    if "dizzy" in lower or "dizziness" in lower:
        issues.append(ExtractedIssue(
            category="symptom",
            tag="dizziness",
            label="Dizziness",
            user_detail="dizziness reported",
            is_red_flag=False,
            severity="mild"
        ))

    # Testing conditions
    if any(w in lower for w in ["coffee", "espresso", "latte", "caffeine", "tea"]):
        issues.append(ExtractedIssue(
            category="testing_condition",
            tag="caffeine_intake",
            label="Caffeine within 30 min",
            user_detail="caffeine intake reported",
            is_red_flag=False
        ))
    if any(w in lower for w in ["smoke", "smoked", "cigarette", "vape", "nicotine"]):
        issues.append(ExtractedIssue(
            category="testing_condition",
            tag="nicotine_intake",
            label="Nicotine within 30 min",
            user_detail="nicotine/smoking reported",
            is_red_flag=False
        ))
    if any(w in lower for w in ["exercis", "workout", "ran", "running", "jog"]):
        issues.append(ExtractedIssue(
            category="testing_condition",
            tag="recent_exercise",
            label="Recent Exercise",
            user_detail="exercise before test reported",
            is_red_flag=False
        ))
    if any(w in lower for w in ["anxious", "nervous", "rushed", "white coat", "panic"]):
        issues.append(ExtractedIssue(
            category="testing_condition",
            tag="anxious_rushed",
            label="Anxious / Rushed",
            user_detail="anxiety or feeling rushed reported",
            is_red_flag=False
        ))

    # Lifestyle
    if any(w in lower for w in ["poor sleep", "bad sleep", "little sleep", "4 hour", "5 hour", "insomnia"]):
        issues.append(ExtractedIssue(
            category="lifestyle",
            tag="poor_sleep",
            label="Poor Sleep",
            user_detail="sleep deficit reported",
            is_red_flag=False
        ))
    if "stress" in lower:
        issues.append(ExtractedIssue(
            category="lifestyle",
            tag="high_stress",
            label="High Stress",
            user_detail="stress reported",
            is_red_flag=False
        ))
    if "salt" in lower or "salty" in lower:
        issues.append(ExtractedIssue(
            category="lifestyle",
            tag="high_salt",
            label="High Salt Intake",
            user_detail="high salt reported",
            is_red_flag=False
        ))

    # Medications (without assuming prescription BP meds)
    if any(w in lower for w in ["advil", "ibuprofen", "motrin", "aleve", "naproxen", "nsaid"]):
        issues.append(ExtractedIssue(
            category="medication",
            tag="otc_nsaid",
            label="Painkiller / NSAID Taken",
            user_detail="NSAID painkiller reported",
            is_red_flag=False
        ))
    if any(w in lower for w in ["sudafed", "decongestant", "cold medicine"]):
        issues.append(ExtractedIssue(
            category="medication",
            tag="decongestant",
            label="Decongestant / Cold Medicine Taken",
            user_detail="decongestant reported",
            is_red_flag=False
        ))
    if any(w in lower for w in ["forgot pill", "missed pill", "missed dose", "forgot meds", "forgot to take"]):
        issues.append(ExtractedIssue(
            category="medication",
            tag="bp_med_missed",
            label="Missed Blood Pressure Medication",
            user_detail="missed medication dose reported",
            is_red_flag=False
        ))
    elif any(w in lower for w in ["took pill", "took my pill", "took meds", "took my medication", "took amlodipine", "took lisinopril", "took losartan"]):
        issues.append(ExtractedIssue(
            category="medication",
            tag="bp_med_taken",
            label="Blood Pressure Medication Taken",
            user_detail="blood pressure medication taken",
            is_red_flag=False
        ))

    return issues

def extract_issues_from_text(user_text: str) -> List[ExtractedIssue]:
    """
    Extracts clinical issues from free-form user sentences using Gemini Flash.
    Falls back to heuristic rules if Gemini API key is not configured or unavailable.
    """
    if not user_text or not user_text.strip():
        return []

    client = get_gemini_client()
    if not client:
        # Graceful fallback for local development/testing without key
        return extract_issues_heuristic(user_text)

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        prompt = f"{ISSUES_EXTRACTION_PROMPT}\n\nUser Input: \"{user_text}\""
        response = model.generate_content(prompt)
        
        raw_json = response.text.strip()
        data = json.loads(raw_json)
        
        if not isinstance(data, list):
            if isinstance(data, dict) and "issues" in data:
                data = data["issues"]
            else:
                return extract_issues_heuristic(user_text)

        extracted: List[ExtractedIssue] = []
        for item in data:
            try:
                extracted.append(ExtractedIssue(**item))
            except ValidationError:
                continue
        return extracted
    except Exception as e:
        print(f"Gemini API call failed ({e}), falling back to heuristic extractor.")
        return extract_issues_heuristic(user_text)

def extract_blood_pressure_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> ScanExtractionResponse:
    """
    Extracts blood pressure measurements from an uploaded monitor photo using Gemini Multimodal Vision.
    """
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    client = get_gemini_client()

    if not client:
        # Mock/development response when Gemini is not configured
        return ScanExtractionResponse(
            scan_id=scan_id,
            detected_type="blood_pressure",
            device_name="Demo Blood Pressure Monitor",
            values=BloodPressureValues(systolic=128, diastolic=82, pulse=74),
            confidence=0.95,
            quality=ImageQualityReport(is_readable=True, glare_detected=False, display_cut_off=False, issues=[]),
            raw_detected_text="SYS 128 / DIA 82 / PUL 74"
        )

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        vision_prompt = """
        You are a medical device reader. Extract blood pressure measurements from this image of a digital blood pressure monitor.
        Identify:
        1. systolic: number (mmHg)
        2. diastolic: number (mmHg)
        3. pulse: number (bpm, or null if missing)
        4. device_name: brand or model visible (e.g. Omron, Beurer, Microlife) or null
        5. confidence: float 0.0 to 1.0 reflecting how clearly the digits are visible
        6. quality: object with:
           - is_readable: boolean
           - glare_detected: boolean
           - display_cut_off: boolean
           - issues: array of strings (e.g. "glare on diastolic digit")
        7. raw_detected_text: string of visible text tokens on the monitor

        Ensure systolic > diastolic. Return strictly JSON matching this structure:
        {
          "systolic": 128,
          "diastolic": 82,
          "pulse": 74,
          "device_name": "Omron HEM-7120",
          "confidence": 0.98,
          "quality": {
            "is_readable": true,
            "glare_detected": false,
            "display_cut_off": false,
            "issues": []
          },
          "raw_detected_text": "SYS 128 DIA 82 PULSE 74"
        }
        """

        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        response = model.generate_content([vision_prompt, image_part])
        data = json.loads(response.text.strip())

        quality_data = data.get("quality", {})
        quality = ImageQualityReport(
            is_readable=quality_data.get("is_readable", True),
            glare_detected=quality_data.get("glare_detected", False),
            display_cut_off=quality_data.get("display_cut_off", False),
            issues=quality_data.get("issues", [])
        )

        values = BloodPressureValues(
            systolic=int(data["systolic"]),
            diastolic=int(data["diastolic"]),
            pulse=int(data["pulse"]) if data.get("pulse") is not None else None
        )

        return ScanExtractionResponse(
            scan_id=scan_id,
            detected_type="blood_pressure",
            device_name=data.get("device_name"),
            values=values,
            confidence=float(data.get("confidence", 0.9)),
            quality=quality,
            raw_detected_text=data.get("raw_detected_text")
        )
    except Exception as e:
        print(f"Gemini Vision failed: {e}")
        raise ValueError(f"Could not reliably extract blood pressure from image: {e}")
