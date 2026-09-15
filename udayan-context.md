# Udayan's Vision & Measurement Detection Guide (`udayan-context.md`)

Welcome, Udayan! 👋 

This document defines your workspace, the exact data contract the backend expects, and how your Gemini Multimodal Vision service connects to the rest of the platform.

---

## 1. Your File & Responsibility

- **Your Primary File**: [`backend/services/vision_service.py`](file:///c:/Users/ashen/Work/personal-health-monitor/backend/services/vision_service.py)
- **Calling API Route**: [`POST /api/scan/extract`](file:///c:/Users/ashen/Work/personal-health-monitor/backend/routes/measurements.py)
- **Your Mission**:
  1. Receive uploaded device images (photos of digital monitors or screenshots).
  2. Classify the measurement device type (currently focusing on **`blood_pressure`**).
  3. Extract numerical values (`systolic`, `diastolic`, `pulse`), device brand, and image quality metrics using Gemini Multimodal Vision.
  4. Return a strictly typed **`ScanExtractionResponse`**.

---

## 2. The Expected Function Signature

In `backend/services/vision_service.py`, the backend calls:

```python
def detect_and_extract_measurement(
    image_bytes: bytes, 
    mime_type: str = "image/jpeg"
) -> ScanExtractionResponse:
    ...
```

---

## 3. The Expected Data Return Contract (`ScanExtractionResponse`)

Your function must return a **`ScanExtractionResponse`** instance (defined in [`backend/schemas.py`](file:///c:/Users/ashen/Work/personal-health-monitor/backend/schemas.py)).

### A. Python Model Structure

```python
class ImageQualityReport(BaseModel):
    is_readable: bool = True               # False if numbers cannot be deciphered
    glare_detected: bool = False           # True if flash/reflection covers digits
    display_cut_off: bool = False          # True if numbers are cut off by frame edge
    issues: List[str] = []                 # Actionable hints e.g. ["glare on bottom digit"]

class BloodPressureValues(BaseModel):
    systolic: int                          # 40 to 300 mmHg
    diastolic: int                         # 30 to 200 mmHg
    pulse: Optional[int] = None            # 30 to 250 bpm (null if not on screen)

    # ⚠️ CRITICAL VALIDATION: systolic MUST be strictly greater than diastolic!

class ScanExtractionResponse(BaseModel):
    scan_id: str                           # Unique string e.g. f"scan_{uuid.uuid4().hex[:12]}"
    detected_type: str = "blood_pressure"  # "blood_pressure" (extensible to glucose, spo2)
    values: BloodPressureValues            # Validated BP values object (systolic, diastolic, pulse)
    confidence: float                      # 0.0 to 1.0 based on readability
    quality: ImageQualityReport            # Quality report object
    raw_detected_text: Optional[str] = None# Visible OCR tokens e.g. "SYS 138 DIA 88 PUL 74"
```

---

### B. Example Expected JSON (What Gemini should produce)

Your Gemini prompt should return JSON strictly matching this shape:

```json
{
  "detected_type": "blood_pressure",
  "confidence": 0.98,
  "values": {
    "systolic": 138,
    "diastolic": 88,
    "pulse": 74
  },
  "quality": {
    "is_readable": true,
    "glare_detected": false,
    "display_cut_off": false,
    "issues": []
  },
  "raw_detected_text": "SYS 138 DIA 88 PULSE 74"
}
```

---

## 4. Clinical Guardrails & Validation Rules

1. **Systolic vs Diastolic Constraint**:
   - `systolic` must be strictly greater than `diastolic`. If `systolic <= diastolic`, the Pydantic schema will raise a `ValidationError`.
2. **Confidence Calibration**:
   - **High ($\ge 0.90$)**: Digits are crystal clear and fully framed.
   - **Medium ($0.70 - 0.89$)**: Slight glare or angle, but values are deduced reliably.
   - **Low ($< 0.70$)**: Heavy reflection, missing digit segments, or motion blur.
3. **Device Brand/Name**:
   - Not required. Do not waste prompt tokens trying to detect the casing or manufacturer brand; focus strictly on reading the display digits and assessing image clarity.


---

## 5. Development Fallback (Offline Mode)

If `GEMINI_API_KEY` is not present in `.env`, your service should not crash. An automatic mock fallback is already in place in `vision_service.py` to allow other team members to test frontend and API flows without needing an API key.

---

## 6. How to Test Your Service

### Method 1: Direct Python Test Script
You can test your function directly in a quick Python script:

```python
from services.vision_service import detect_and_extract_measurement

with open("path/to/test_bp_monitor.jpg", "rb") as f:
    img_bytes = f.read()

result = detect_and_extract_measurement(img_bytes, mime_type="image/jpeg")
print("Detected Type:", result.detected_type)
print("Values:", result.values.systolic, "/", result.values.diastolic, "Pulse:", result.values.pulse)
print("Confidence:", result.confidence)
print("Quality:", result.quality.model_dump())

```

### Method 2: Swagger UI (Interactive API)
1. Start the backend:
   ```bash
   cd backend
   .\venv\Scripts\python main.py
   ```
2. Open your browser to: `http://localhost:8000/docs`
3. Locate `POST /api/scan/extract`, upload an image, and test the response live!

---

## 7. What Is Already Handled For You

You do **not** need to implement:
- ❌ Natural language symptom & lifestyle context extraction (handled by `/api/scan/extract-issues`).
- ❌ AHA/ACC clinical stage classification & emergency crisis alerts (handled by `clinical_service.py`).
- ❌ Firestore database storage & user authentication (handled by `routes/measurements.py`).

Your entire focus is crafting the best possible computer vision prompt and parsing in [`backend/services/vision_service.py`](file:///c:/Users/ashen/Work/personal-health-monitor/backend/services/vision_service.py).

---

## 8. Strict Rules & Constraints (Do's and Don'ts)

> [!IMPORTANT]
> To prevent breaking the frontend and backend integration, please follow these strict rules:

1. **DO NOT change the function signature**:
   The function MUST remain `def detect_and_extract_measurement(image_bytes: bytes, mime_type: str = "image/jpeg") -> ScanExtractionResponse`.
2. **DO NOT modify the return type**:
   The return type MUST be a valid `ScanExtractionResponse` object. Do not return raw dictionaries or strings.
3. **DO NOT modify other backend files**:
   Confine your work to `backend/services/vision_service.py`. Do NOT edit `backend/routes/measurements.py`, `backend/schemas.py`, or `backend/services/clinical_service.py`.
4. **DO NOT hardcode API keys or secrets**:
   Always read the key using `os.getenv("GEMINI_API_KEY")`. Never commit `.env` or any secret keys.
5. **ENFORCE `systolic > diastolic`**:
   The `BloodPressureValues` schema will throw a validation error if `systolic <= diastolic`. Ensure your logic handles edge cases (e.g. if an inverted reading or garbage number is read, raise a clear `ValueError` or set `quality.is_readable = False` with `confidence < 0.5`).
6. **PRESERVE the mock fallback**:
   Keep the `if not client:` fallback block intact so teammates can run the server and test API/frontend workflows even if they don't have an active Gemini API key set up.

