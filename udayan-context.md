# Udayan's AI Correlation & Clinical Analysis Guide (`udayan-context.md`)

Welcome back, Udayan! 👋 

The device vision scan (Blood Pressure & Glucometer) and the full React dashboard UI are complete and deployed on `feat/vision-detection`. 

Your next mission is to build the **AI Clinical Correlation Engine**: analyzing recorded biometric streams (Blood Pressure & Blood Sugar), cross-referencing pre-test symptoms/lifestyle factors, and uncovering grounded clinical correlations for both the patient and their physician.

---

## 🌿 1. Git Branching Workflow

Please work on a dedicated feature branch so the stable backend and UI remain protected:

```bash
# 1. Fetch latest changes and switch to feat/vision-detection
git fetch origin
git checkout feat/vision-detection
git pull origin feat/vision-detection

# 2. Create your new feature branch
git checkout -b feat/ai-correlation-analysis

# 3. Work only within your permitted files (see Section 2)

# 4. Commit and push when ready for review
git push -u origin feat/ai-correlation-analysis
```

---

## 🛡️ 2. File Restrictions & Boundaries

To prevent merge conflicts and avoid breaking the existing frontend and OCR pipelines, strictly observe these boundaries:

### ✅ Permitted Files (Your Workspace)
- **`backend/services/analysis_service.py`** (NEW): Core clinical correlation logic, statistical grouping, and Gemini reasoning.
- **`backend/routes/analysis.py`** (NEW): API endpoints (`GET /api/analysis/correlations`, `POST /api/analysis/generate`).
- **`backend/tests/test_analysis_service.py`** (NEW): Unit tests for statistical processing and correlation parsing (mocked!).
- **`backend/schemas.py`**: You may **APPEND** new Pydantic models for correlation output (e.g., `CorrelationItem`, `HealthAnalysisResponse`).
- **`backend/main.py`**: Register your new router:
  ```python
  from routes import analysis
  app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
  ```

### 🚫 Strictly Prohibited Files (DO NOT MODIFY)
- ❌ **`frontend/`**: Do not edit any files in `frontend/`. The UI timeline and dashboard cards are already wired to consume `/api/analysis`.
- ❌ **`backend/services/vision_service.py`**: The multimodal OCR pipeline is locked and working.
- ❌ **`backend/services/clinical_service.py`**: The AHA and ADA deterministic staging rules must remain intact.
- ❌ **`backend/routes/measurements.py` & `backend/routes/users.py`**: Working database persistence endpoints.
- ❌ **Existing schemas in `backend/schemas.py`**: Never delete or change fields in `BloodPressure*`, `BloodGlucose*`, `UserProfile`, or `ScanExtractionResponse`.

---

## 🎯 3. What Correlations You Need to Detect

You are correlating three primary data layers:
1. **Biometric Stream A**: Blood Pressure (`systolic`, `diastolic`, `pulse`, `recorded_at`)
2. **Biometric Stream B**: Blood Glucose (`glucose_value`, `unit`, `meal_context`, `recorded_at`)
3. **Contextual Issues**: Symptoms, testing conditions, medications, lifestyle (`issues` array attached to each reading)

### Key Clinical Correlations to Identify:
| Correlation Pattern | Trigger Inputs | Clinical Finding Example |
| :--- | :--- | :--- |
| **Testing Confounders $\leftrightarrow$ BP Spike** | `caffeine_intake`, `nicotine_intake`, `recent_exercise`, `otc_nsaid`, `decongestant` | *"Systolic readings average 14 mmHg higher within 30 min of caffeine/NSAID intake compared to baseline."* |
| **Symptom $\leftrightarrow$ Acute Alert** | `chest_pain`, `vision_changes`, `dizziness` + Crisis values | **URGENT**: *"Reported chest tightness coincides with Hypertensive Crisis reading (185/110 mmHg)."* |
| **Metabolic $\leftrightarrow$ Cardiovascular** | Paired Blood Glucose & BP readings within $\pm 2$ hours | *"Post-meal glucose spikes (>180 mg/dL) consistently coincide with elevated pulse (>95 bpm) and systolic elevation."* |
| **Lifestyle $\leftrightarrow$ Glycemic Stability** | `poor_sleep`, `high_stress`, `high_salt` + Fasting Sugar | *"Fasting blood glucose is 15% higher following nights where poor sleep (<5 hours) was logged."* |
| **Fluid Shift / Weight $\leftrightarrow$ BP** | Rapid $\Delta$ Weight ($>2$ kg in 48h) + SYS | *"Weight increase of 2.2 kg over 3 days accompanied by rising diastolic pressure — potential fluid retention."* |

---

## 🏗️ 4. Technical Architecture: How to Build It

### Step 1: Deterministic Pre-aggregation First (Do NOT rely on LLM for math!)
Before calling Gemini, compute factual statistics in Python:
- Morning vs Evening average BP.
- Fasting average vs Post-meal average glucose.
- Count of co-occurring events: e.g. how many times `caffeine_intake` occurred, and what the mean SYS was during those readings vs without caffeine.
- Time-window pairing: Group BP and Glucose measurements taken within $\pm 2\text{ hours}$ of each other.

### Step 2: Structured Gemini Reasoning (`gemini-flash-latest`)
Use `gemini-flash-latest` with fallback to `gemini-3.5-flash-lite` (avoids rate limits):

```python
import os
import json
import google.generativeai as genai

ANALYSIS_PROMPT = """
You are an expert clinical data analyst and chronic condition specialist.
You are provided with a patient's deterministic health timeline statistics (Blood Pressure, Blood Glucose, Weight, and Symptoms/Context).

Analyze the data and identify:
1. Correlations between symptoms/testing conditions (caffeine, sleep, NSAIDs) and blood pressure spikes.
2. Correlations between blood glucose levels and cardiovascular metrics (metabolic-vascular interactions).
3. Longitudinal trends over time.

Clinical Rules:
- NEVER state an unauthorized definitive diagnosis (e.g. do NOT say "You have Type 2 Diabetes" or "You have Kidney Failure").
- Use objective, grounded language: "Data indicates...", "Readings show a correlation between...", "Consider discussing with your clinician...".
- Flag any acute danger signs as high priority.

Return strictly JSON matching this structure:
{
  "correlations": [
    {
      "category": "lifestyle_trigger" | "metabolic_cardiovascular" | "symptom_spike",
      "confidence": "high" | "moderate" | "low",
      "headline": "Short title",
      "explanation": "Clear explanation of the correlation with specific data points",
      "evidence_count": number,
      "clinical_suggestion": "Actionable non-diagnostic guidance"
    }
  ],
  "urgent_alerts": ["string"],
  "doctor_summary": "1-2 paragraphs synthesized clinical summary for their doctor"
}
"""
```

### Step 3: Caching in Firestore (Prevent Rate Limits!)
Do not call Gemini on every page load. Cache the generated analysis in Firestore:
- Store at `users/{uid}/analysis/latest` with `generated_at`.
- If `generated_at` is less than 1 hour old AND no new measurements were logged since, return the cached analysis immediately!

---

## 🔌 5. Expected API Contract

### Route: `GET /api/analysis/correlations`
**Headers**: `Authorization: Bearer <Firebase_ID_Token>`

**Response Model (`HealthAnalysisResponse`)**:
```json
{
  "user_id": "user_abc123",
  "generated_at": "2026-09-16T01:30:00Z",
  "is_cached": false,
  "stats": {
    "total_bp_readings": 12,
    "total_glucose_readings": 8,
    "avg_systolic": 132,
    "avg_diastolic": 84,
    "avg_glucose_mg_dl": 118.5
  },
  "correlations": [
    {
      "category": "lifestyle_trigger",
      "confidence": "high",
      "headline": "Caffeine Associated with Morning BP Elevation",
      "explanation": "On 4 occasions where caffeine within 30 min was reported, systolic pressure averaged 142 mmHg compared to your non-caffeine baseline of 126 mmHg.",
      "evidence_count": 4,
      "clinical_suggestion": "Allow at least 30 to 45 minutes after morning coffee before taking your resting blood pressure."
    },
    {
      "category": "metabolic_cardiovascular",
      "confidence": "moderate",
      "headline": "Post-Prandial Sugar Spikes Correlate with Pulse Elevation",
      "explanation": "When post-meal glucose exceeds 160 mg/dL, resting heart rate averages 88 bpm vs 72 bpm baseline.",
      "evidence_count": 3,
      "clinical_suggestion": "Log meal composition (carbohydrate proportion) to evaluate glycemic impact on autonomic response."
    }
  ],
  "urgent_alerts": [],
  "doctor_summary": "Patient demonstrates stage 1 systolic hypertension with significant reactivity to caffeine and sleep deficits. Glycemic control is generally within target with isolated post-meal elevations."
}
```

---

## 🧪 6. Testing & Rate Limit Rules

> [!IMPORTANT]
> **NEVER call live Gemini API in unit tests!**
> The Gemini free tier has a limit of 5 requests/min. Calling live Gemini in `unittest` or `pytest` will burn the quota and fail with HTTP 429.

In `backend/tests/test_analysis_service.py`:
- Use `unittest.mock.patch` to mock `genai.GenerativeModel.generate_content`.
- Verify statistical aggregation, JSON parsing, fallback heuristic extraction, and error handling.
- Run tests:
  ```bash
  cd backend
  .\venv\Scripts\python -m unittest discover tests
  ```

---

## 🚀 7. Checklist for Definition of Done

- [ ] Created feature branch `feat/ai-correlation-analysis`.
- [ ] Statistical pre-aggregation computes averages, co-occurrences, and paired readings without LLM.
- [ ] Gemini client uses `gemini-flash-latest` with fallback to `gemini-3.5-flash-lite`.
- [ ] Responses adhere strictly to the JSON schema.
- [ ] Firestore caching prevents redundant API calls.
- [ ] `GET /api/analysis/correlations` returns 200 with typed response.
- [ ] Unit tests pass with `unittest` in $<1$ second with zero live API calls.
- [ ] Branch pushed and ready to merge into `feat/vision-detection`.
