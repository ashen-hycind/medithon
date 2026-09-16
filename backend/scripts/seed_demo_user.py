"""
Seed Demo User Script
Creates or updates demo user 'demo@user.com' with password 'abc123'
and seeds 14-day multi-device longitudinal health records into Firestore:
- Sphygmomanometer (Blood Pressure & Pulse)
- Glucometer (Blood Glucose)
- Pulse Oximeter (SpO2 & Pulse)
- Digital Scale (Weight & Fluid History)
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from firebase_config import init_firebase, get_firestore_db
from firebase_admin import auth
from services.clinical_service import evaluate_clinical_alerts, evaluate_glucose_alerts
from schemas import BloodPressureValues, BloodGlucoseValues

def seed_demo():
    print("=== SEEDING DEMO USER: demo@user.com ===")
    init_firebase()
    db = get_firestore_db()
    if db is None:
        print("[Error] Firestore db is not initialized!")
        return

    # 1. Create or get user in Firebase Auth
    email = "demo@user.com"
    password = "abc123"
    display_name = "Madhav Sharma"

    try:
        user = auth.get_user_by_email(email)
        print(f"[Auth] Found existing user: {user.uid} ({user.email})")
        # Ensure password is abc123
        auth.update_user(user.uid, password=password, display_name=display_name)
    except Exception:
        user = auth.create_user(email=email, password=password, display_name=display_name)
        print(f"[Auth] Created new user: {user.uid} ({user.email})")

    uid = user.uid

    # 2. Seed User Profile
    now = datetime.now(timezone.utc)
    profile_data = {
        "user_id": uid,
        "name": "Madhav Sharma",
        "dob": "1976-08-14",
        "blood_group": "B+",
        "sex": "male",
        "height_cm": 175.0,
        "weight_kg": 78.5,
        "pregnancy_status": False,
        "gestational_age_weeks": None,
        "activity_level": 5,
        "occupation": "Financial Analyst",
        "created_at": (now - timedelta(days=20)).isoformat(),
        "updated_at": now.isoformat()
    }
    db.collection("profiles").document(uid).set(profile_data)
    print("[Firestore] Profile established for Madhav Sharma.")

    # 3. Clean up existing demo measurements to prevent stale/duplicate data
    measurements_ref = db.collection("profiles").document(uid).collection("measurements")
    for doc in measurements_ref.stream():
        doc.reference.delete()

    weight_ref = db.collection("profiles").document(uid).collection("weight_history")
    for doc in weight_ref.stream():
        doc.reference.delete()

    analysis_ref = db.collection("profiles").document(uid).collection("analysis")
    for doc in analysis_ref.stream():
        doc.reference.delete()

    print("[Firestore] Cleaned prior measurements and analysis cache.")

    # 4. Generate 14-Day Multi-Device Records
    # Timeline anchors: Days 1 to 14 in the past
    bp_records = []
    glucose_records = []
    weight_records = []

    # --- Day 14 (Oldest) to Day 8: Prior window (Avg SYS ~143 mmHg, Stage 1 / Stage 2) ---
    day14 = now - timedelta(days=14)
    # Day 14 morning BP
    bp_records.append({
        "time": day14.replace(hour=7, minute=45),
        "sys": 146, "dia": 92, "pulse": 78, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": [{"category": "symptom", "tag": "headache", "label": "Mild Morning Headache", "is_red_flag": False}]
    })
    # Day 14 morning fasting glucose
    glucose_records.append({
        "time": day14.replace(hour=8, minute=5),
        "val": 104.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })
    # Day 14 evening BP
    bp_records.append({
        "time": day14.replace(hour=19, minute=30),
        "sys": 136, "dia": 86, "pulse": 72, "spo2": 99,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })

    # Day 12
    day12 = now - timedelta(days=12)
    bp_records.append({
        "time": day12.replace(hour=8, minute=15),
        "sys": 144, "dia": 90, "pulse": 76, "spo2": 97,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": [{"category": "lifestyle", "tag": "poor_sleep", "label": "Poor Sleep (5 hours)", "is_red_flag": False}]
    })
    glucose_records.append({
        "time": day12.replace(hour=8, minute=30),
        "val": 99.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })
    # Day 12 Post-Lunch Pairing: Glucose spike + BP surge
    glucose_records.append({
        "time": day12.replace(hour=13, minute=45),
        "val": 168.0, "meal_context": "after_meal",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })
    bp_records.append({
        "time": day12.replace(hour=14, minute=15),
        "sys": 142, "dia": 88, "pulse": 88, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": [{"category": "testing_condition", "tag": "caffeine_intake", "label": "Espresso 20 min prior", "is_red_flag": False}]
    })

    # Day 10
    day10 = now - timedelta(days=10)
    bp_records.append({
        "time": day10.replace(hour=8, minute=0),
        "sys": 145, "dia": 91, "pulse": 77, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    bp_records.append({
        "time": day10.replace(hour=19, minute=45),
        "sys": 135, "dia": 85, "pulse": 71, "spo2": 99,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })

    # Day 8
    day8 = now - timedelta(days=8)
    bp_records.append({
        "time": day8.replace(hour=7, minute=50),
        "sys": 141, "dia": 88, "pulse": 75, "spo2": 97,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    glucose_records.append({
        "time": day8.replace(hour=8, minute=10),
        "val": 101.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })

    # --- Day 6 to Day 1: Recent window (Avg SYS ~132 mmHg, Showing 11 mmHg Improvement) ---
    day6 = now - timedelta(days=6)
    bp_records.append({
        "time": day6.replace(hour=8, minute=10),
        "sys": 136, "dia": 86, "pulse": 74, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    glucose_records.append({
        "time": day6.replace(hour=8, minute=25),
        "val": 96.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })

    # Day 5 Post-Dinner Pairing: Glucose excursion + Sphygmomanometer reading
    day5 = now - timedelta(days=5)
    glucose_records.append({
        "time": day5.replace(hour=20, minute=10),
        "val": 172.0, "meal_context": "after_meal",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })
    bp_records.append({
        "time": day5.replace(hour=20, minute=45),
        "sys": 138, "dia": 86, "pulse": 86, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })

    # Day 4
    day4 = now - timedelta(days=4)
    bp_records.append({
        "time": day4.replace(hour=7, minute=40),
        "sys": 134, "dia": 84, "pulse": 73, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    bp_records.append({
        "time": day4.replace(hour=19, minute=20),
        "sys": 126, "dia": 80, "pulse": 69, "spo2": 99,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    glucose_records.append({
        "time": day4.replace(hour=8, minute=0),
        "val": 95.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })

    # Day 2
    day2 = now - timedelta(days=2)
    bp_records.append({
        "time": day2.replace(hour=8, minute=5),
        "sys": 132, "dia": 83, "pulse": 72, "spo2": 98,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    glucose_records.append({
        "time": day2.replace(hour=8, minute=20),
        "val": 94.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })
    glucose_records.append({
        "time": day2.replace(hour=13, minute=30),
        "val": 138.0, "meal_context": "after_meal",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })

    # Day 1 (Yesterday)
    day1 = now - timedelta(days=1)
    bp_records.append({
        "time": day1.replace(hour=8, minute=0),
        "sys": 130, "dia": 82, "pulse": 70, "spo2": 99,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    bp_records.append({
        "time": day1.replace(hour=19, minute=30),
        "sys": 124, "dia": 78, "pulse": 68, "spo2": 99,
        "device_type": "Sphygmomanometer", "device_model": "Digital Upper-Arm Sphygmomanometer",
        "issues": []
    })
    glucose_records.append({
        "time": day1.replace(hour=8, minute=15),
        "val": 93.0, "meal_context": "fasting",
        "device_type": "Glucometer", "device_model": "Clinical Glucometer",
        "issues": []
    })

    # --- Weight Records (Digital Scale) with a 2.3 kg transient fluid retention event ---
    weight_records.append({
        "recorded_at": (now - timedelta(days=14)).replace(hour=7, minute=30).isoformat(),
        "weight_kg": 78.2,
        "device_type": "Digital Scale"
    })
    weight_records.append({
        "recorded_at": (now - timedelta(days=9)).replace(hour=7, minute=30).isoformat(),
        "weight_kg": 78.4,
        "device_type": "Digital Scale"
    })
    weight_records.append({
        "recorded_at": (now - timedelta(days=7)).replace(hour=7, minute=30).isoformat(),
        "weight_kg": 80.7,  # +2.3 kg surge over 48 hours
        "device_type": "Digital Scale"
    })
    weight_records.append({
        "recorded_at": (now - timedelta(days=1)).replace(hour=7, minute=30).isoformat(),
        "weight_kg": 78.5,  # normalized
        "device_type": "Digital Scale"
    })

    from schemas import ExtractedIssue
    # Save BP records to Firestore
    for i, bp in enumerate(bp_records):
        m_id = f"bp_demo_{i+1:02d}"
        iso_time = bp["time"].isoformat()
        bp_val = BloodPressureValues(
            systolic=bp["sys"],
            diastolic=bp["dia"],
            pulse=bp["pulse"],
            spo2=bp["spo2"]
        )
        parsed_issues = [ExtractedIssue(**iss) for iss in bp["issues"]]
        stage, has_red, alerts = evaluate_clinical_alerts(bp_val, parsed_issues)
        rec = {
            "id": m_id,
            "user_id": uid,
            "measurement_type": "blood_pressure",
            "recorded_at": iso_time,
            "values": bp_val.model_dump(),
            "units": {"systolic": "mmHg", "diastolic": "mmHg", "pulse": "bpm", "spo2": "%"},
            "clinical_stage": stage,
            "has_red_flags": has_red,
            "safety_alerts": alerts,
            "raw_user_notes": "Routine telemetry check",
            "issues": bp["issues"],
            "source": "camera",
            "device_model": bp["device_model"],
            "device_type": bp["device_type"],
            "created_at": iso_time,
            "updated_at": iso_time
        }
        db.collection("profiles").document(uid).collection("measurements").document(m_id).set(rec)

    print(f"[Firestore] Seeded {len(bp_records)} Sphygmomanometer & Pulse Oximeter readings.")

    # Save Glucose records to Firestore
    for i, g in enumerate(glucose_records):
        m_id = f"bg_demo_{i+1:02d}"
        iso_time = g["time"].isoformat()
        g_val = BloodGlucoseValues(
            glucose_value=g["val"],
            unit="mg/dL",
            meal_context=g["meal_context"]
        )
        parsed_glu_issues = [ExtractedIssue(**iss) for iss in g["issues"]]
        stage, has_red, alerts = evaluate_glucose_alerts(g_val, parsed_glu_issues)
        rec = {
            "id": m_id,
            "user_id": uid,
            "measurement_type": "blood_glucose",
            "recorded_at": iso_time,
            "values": g_val.model_dump(),
            "meal_context": g["meal_context"],
            "units": {"glucose": "mg/dL"},
            "clinical_stage": stage,
            "has_red_flags": has_red,
            "safety_alerts": alerts,
            "raw_user_notes": f"Recorded via {g['device_type']}",
            "issues": g["issues"],
            "source": "camera",
            "device_model": g["device_model"],
            "device_type": g["device_type"],
            "created_at": iso_time,
            "updated_at": iso_time
        }
        db.collection("profiles").document(uid).collection("measurements").document(m_id).set(rec)

    print(f"[Firestore] Seeded {len(glucose_records)} Glucometer readings.")

    # Save Weight records to Firestore
    for i, w in enumerate(weight_records):
        w_id = f"w_demo_{i+1:02d}"
        rec = {
            "id": w_id,
            "user_id": uid,
            "weight_kg": w["weight_kg"],
            "device_type": w["device_type"],
            "recorded_at": w["recorded_at"],
            "created_at": w["recorded_at"]
        }
        db.collection("profiles").document(uid).collection("weight_history").document(w_id).set(rec)

    print(f"[Firestore] Seeded {len(weight_records)} Digital Scale weight readings.")

    # 5. Pre-compute and store AI Analysis Cache
    from services.analysis_service import get_or_compute_analysis
    analysis = get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
    print(f"[Analysis] Pre-computed AI health analysis with {len(analysis.correlations)} correlations:")
    for c in analysis.correlations:
        print(f"  • [{c.category.upper()}] {c.headline} ({c.confidence} confidence)")
    print("\n[Analysis Doctor Summary]:")
    print(f"  {analysis.doctor_summary}")

    print("\n=== DEMO USER SEEDING COMPLETE! ===")
    print(f"   Email:    {email}")
    print(f"   Password: {password}")
    print(f"   UID:      {uid}")

if __name__ == "__main__":
    seed_demo()
