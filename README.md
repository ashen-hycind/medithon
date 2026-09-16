# MediBridge 🩺
> **Intelligent Longitudinal Health Telemetry & Clinical Decision Support Platform**

MediBridge bridges home vital monitoring with clinical care. It captures, digitizes, and correlates multi-device physiological streams—including Blood Pressure, Blood Glucose, Oxygen Saturation (SpO2), and Body Weight—transforming raw patient readings into actionable clinical insights and comprehensive doctor health reports.

---

## 🌐 Live Application (Firebase Hosted)

The application is deployed live on Firebase Hosting with full Firebase Authentication, Cloud Firestore telemetry synchronization, and client-side AI analysis:

* **Live URL:** [https://v-medithon.web.app](https://v-medithon.web.app)
* **Demo Account:**
  * **Email:** `demo@user.com`
  * **Password:** `abc123`
  * *Includes pre-seeded 14-day longitudinal health records across Sphygmomanometer, Glucometer, Pulse Oximeter, and Weight Scale.*

---

## 🌟 Key Features

### 1. 📷 Multimodal Clinical Device Scanning
* **AI-Powered OCR**: Instant digit extraction and clinical calibration from camera photos or screenshots using Google Gemini Multimodal Vision.
* **Supported Modalities**:
  * **Sphygmomanometer** (Systolic, Diastolic, Pulse)
  * **Digital Glucometer** (Blood Sugar, Unit mg/dL or mmol/L, Meal Context)
  * **Fingertip Pulse Oximeter** (SpO2%, PR bpm)
  * **Digital Scale** (Weight kg/lbs)
* **Clinical Verification Modal**: Real-time display boundary detection, glare suppression, physiological sanity checking, and manual adjustment before persistence.

### 2. 📈 Longitudinal Trend Analytics & Dynamic Cycling
* **Multi-Modal Trend Views**: Interactive 14-day trajectory charts, baseline moving averages, and circadian variation analysis.
* **Dynamic Modality Refresh**: Refresh buttons beside Blood Pressure, Blood Glucose, and Pulse Oximeter cards allowing patients and clinicians to cycle through longitudinal perspectives (14-day baseline vs prior 7 days, morning vs evening delta, post-prandial impact).

### 3. 🧠 Cross-Stream AI Clinical Correlation Engine
* **Temporal Pairing**: Automatically aligns biometric readings captured within temporal windows (+/- 2 hours) to detect cross-stream physiological anomalies.
* **Lifestyle & Symptom Context**: Links clinical spikes with user-reported contextual confounders (high sodium dinners, missed medications, acute headache, caffeine intake, acute stress).
* **Clinical Boundary Adherence**: Follows strict non-diagnostic clinical boundaries (AHA/ACC and ADA guidelines).

### 4. 🧾 Dynamic Doctor Health PDF Report
* **Clinician-Facing PDF**: Complete multi-page clinical health report generated directly from stored Firestore telemetry.
* **Deterministic Calculations**: Strict statistical rigor (means, ranges, standard deviation, percentage change from baseline).
* **Integrated Sections**:
  * Patient Demographics & Profile Summary
  * Longitudinal Modality Statistics & AHA/ADA Risk Stratification
  * Chronological Measurement Log with Patient Context
  * Cross-Stream AI Correlation Findings & Clinical Insights
  * Treating Physician Review, Notes, and Sign-off Block

---

## 🏗️ Architecture & Technology Stack

* **Frontend**:
  * React 18 & TypeScript
  * Tailwind CSS & Lucide Icons
  * Recharts (Longitudinal trajectory visualizations)
  * jsPDF & jspdf-autotable (Client-side Doctor Report generation)
  * Firebase SDK v10 (Auth & Firestore)
  * Vite
* **Backend**:
  * Python 3.12 & FastAPI
  * Google Generative AI (Gemini 3.5 / Flash-Lite)
  * ReportLab & Matplotlib (Backend vector PDF compilation)
  * Firebase Admin SDK (Cloud Firestore & Authentication)
  * Pydantic v2 schemas
* **Cloud Infrastructure**:
  * Firebase Hosting ([v-medithon.web.app](https://v-medithon.web.app))
  * Google Cloud Firestore (NoSQL longitudinal document database)
  * Firebase Authentication

---

## 🚀 Local Development Setup

### Prerequisites
* Node.js (v18+)
* Python (v3.10+)
* Firebase CLI (`npm install -g firebase-tools`)

### 1. Clone the Repository
```bash
git clone https://github.com/ashen-hycind/medithon.git
cd medithon
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` with:
```env
FIREBASE_PROJECT_ID=v-medithon
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
DEV_MODE=true
GEMINI_API_KEY=your_gemini_api_key_here
```

Seed the demo patient dataset:
```bash
python scripts/seed_demo_user.py
```

Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

Create `frontend/.env` with your Firebase config:
```env
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=v-medithon.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=v-medithon
VITE_FIREBASE_STORAGE_BUCKET=v-medithon.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=632360377954
VITE_FIREBASE_APP_ID=your_firebase_app_id
VITE_GEMINI_API_KEY=your_gemini_api_key
```

Start Vite dev server:
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🔒 Security & Privacy Notice
* Patient health records in Firestore are scoped under authenticated user IDs (`profiles/{uid}`).
* API keys are isolated: Firebase public keys are limited by Firebase Security Rules; private backend Gemini API keys remain strictly server-side.
* All generated health reports include mandatory clinical safety disclaimers adhering to observational telehealth best practices.
