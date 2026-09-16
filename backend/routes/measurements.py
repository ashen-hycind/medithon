import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from schemas import (
    ScanExtractionResponse,
    ExtractIssuesRequest,
    ExtractIssuesResponse,
    BloodPressureMeasurementCreate,
    BloodPressureMeasurementResponse,
    BloodGlucoseMeasurementCreate,
    BloodGlucoseMeasurementResponse,
    SpO2MeasurementCreate,
    SpO2MeasurementResponse,
    WeightMeasurementCreate,
    WeightMeasurementResponse
)
from security import get_current_user
from firebase_config import get_firestore_db
from services.gemini_service import extract_issues_from_text
from services.vision_service import detect_and_extract_measurement
from services.clinical_service import evaluate_clinical_alerts, evaluate_glucose_alerts
from services.analysis_service import get_or_compute_analysis

router = APIRouter(prefix="/api", tags=["measurements"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/jpg"}

@router.post("/scan/extract", response_model=ScanExtractionResponse)
async def scan_blood_pressure_image(file: UploadFile = File(...)):
    """
    Extracts blood pressure values (systolic, diastolic, pulse) and detects image quality
    from an uploaded photo or screenshot of a blood pressure monitor.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES and not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Supported formats: JPEG, PNG, WEBP, HEIC."
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        extraction = detect_and_extract_measurement(image_bytes, file.content_type or "image/jpeg")
        return extraction
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract readable blood pressure reading: {str(e)}"
        )


@router.post("/scan/extract-issues", response_model=ExtractIssuesResponse)
async def extract_clinical_issues(request: ExtractIssuesRequest):
    """
    Extracts structured issues across the 4 clinical pillars (symptoms, lifestyle,
    medications, testing conditions) from free-form user notes.
    """
    issues = extract_issues_from_text(request.text)
    has_red_flags = any(issue.is_red_flag for issue in issues)

    return ExtractIssuesResponse(
        raw_text=request.text,
        issues=issues,
        has_red_flags=has_red_flags
    )

@router.post("/measurements/blood-pressure", response_model=BloodPressureMeasurementResponse, status_code=status.HTTP_201_CREATED)
async def create_blood_pressure_measurement(
    data: BloodPressureMeasurementCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Persists a verified or manually entered blood pressure measurement with clinical context and issues.
    Stored under profiles/{uid}/measurements/{id}.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    now_iso = datetime.now(timezone.utc).isoformat()
    recorded_at = data.recorded_at or now_iso
    measurement_id = f"bp_{uuid.uuid4().hex[:12]}"

    # Evaluate clinical stage and safety alerts
    clinical_stage, has_red_flags, safety_alerts = evaluate_clinical_alerts(data.values, data.issues)

    record = {
        "id": measurement_id,
        "user_id": uid,
        "measurement_type": "blood_pressure",
        "recorded_at": recorded_at,
        "values": data.values.model_dump(),
        "units": {"systolic": "mmHg", "diastolic": "mmHg", "pulse": "bpm", "spo2": "%"},
        "clinical_stage": clinical_stage,
        "has_red_flags": has_red_flags,
        "safety_alerts": safety_alerts,
        "raw_user_notes": data.raw_user_notes,
        "issues": [issue.model_dump() for issue in data.issues],
        "source": data.source,
        "scan_id": data.scan_id,
        "device_model": data.device_model,
        "device_type": data.device_type or "Sphygmomanometer",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    doc_ref = db.collection("profiles").document(uid).collection("measurements").document(measurement_id)
    doc_ref.set(record)

    # Immediately recalculate AI health analysis upon saving a new entity
    try:
        get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
    except Exception as ai_err:
        print(f"[MeasurementsRoute] Warning: Background AI re-run error: {ai_err}")

    return BloodPressureMeasurementResponse(**record)

@router.get("/measurements/blood-pressure", response_model=List[BloodPressureMeasurementResponse])
async def list_blood_pressure_measurements(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the longitudinal history of blood pressure measurements for the authenticated user.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    measurements_ref = db.collection("profiles").document(uid).collection("measurements")
    
    query = (
        measurements_ref
        .where("measurement_type", "==", "blood_pressure")
        .order_by("recorded_at", direction="DESCENDING")
        .limit(limit)
    )

    try:
        docs = query.stream()
        results = [BloodPressureMeasurementResponse(**doc.to_dict()) for doc in docs]
        return results
    except Exception as e:
        # Fallback without composite index if order_by requires an index not yet built
        fallback_docs = measurements_ref.where("measurement_type", "==", "blood_pressure").limit(limit).stream()
        results = [BloodPressureMeasurementResponse(**doc.to_dict()) for doc in fallback_docs]
        results.sort(key=lambda x: x.recorded_at, reverse=True)
        return results


@router.post("/measurements/blood-glucose", response_model=BloodGlucoseMeasurementResponse, status_code=status.HTTP_201_CREATED)
async def create_blood_glucose_measurement(
    data: BloodGlucoseMeasurementCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Persists a verified or manually entered blood glucose measurement with clinical context and issues.
    Stored under profiles/{uid}/measurements/{id}.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    now_iso = datetime.now(timezone.utc).isoformat()
    recorded_at = data.recorded_at or now_iso
    measurement_id = f"bg_{uuid.uuid4().hex[:12]}"

    # Evaluate clinical stage and safety alerts
    clinical_stage, has_red_flags, safety_alerts = evaluate_glucose_alerts(data.values, data.issues)

    record = {
        "id": measurement_id,
        "user_id": uid,
        "measurement_type": "blood_glucose",
        "recorded_at": recorded_at,
        "values": data.values.model_dump(),
        "meal_context": data.meal_context or data.values.meal_context,
        "units": {"glucose": data.values.unit},
        "clinical_stage": clinical_stage,
        "has_red_flags": has_red_flags,
        "safety_alerts": safety_alerts,
        "raw_user_notes": data.raw_user_notes,
        "issues": [issue.model_dump() for issue in data.issues],
        "source": data.source,
        "scan_id": data.scan_id,
        "device_model": data.device_model,
        "device_type": data.device_type or "Glucometer",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    doc_ref = db.collection("profiles").document(uid).collection("measurements").document(measurement_id)
    doc_ref.set(record)

    # Immediately recalculate AI health analysis upon saving a new entity
    try:
        get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
    except Exception as ai_err:
        print(f"[MeasurementsRoute] Warning: Background AI re-run error: {ai_err}")

    return BloodGlucoseMeasurementResponse(**record)


@router.get("/measurements/blood-glucose", response_model=List[BloodGlucoseMeasurementResponse])
async def list_blood_glucose_measurements(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the longitudinal history of blood glucose measurements for the authenticated user.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    measurements_ref = db.collection("profiles").document(uid).collection("measurements")
    
    query = (
        measurements_ref
        .where("measurement_type", "==", "blood_glucose")
        .order_by("recorded_at", direction="DESCENDING")
        .limit(limit)
    )

    try:
        docs = query.stream()
        results = [BloodGlucoseMeasurementResponse(**doc.to_dict()) for doc in docs]
        return results
    except Exception as e:
        # Fallback without composite index if order_by requires an index not yet built
        fallback_docs = measurements_ref.where("measurement_type", "==", "blood_glucose").limit(limit).stream()
        results = [BloodGlucoseMeasurementResponse(**doc.to_dict()) for doc in fallback_docs]
        results.sort(key=lambda x: x.recorded_at, reverse=True)
        return results


@router.post("/measurements/spo2", response_model=SpO2MeasurementResponse, status_code=status.HTTP_201_CREATED)
async def create_spo2_measurement(
    data: SpO2MeasurementCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Persists a verified or manually entered Pulse Oximeter SpO2 & Pulse measurement.
    Stored under profiles/{uid}/measurements/{id}.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    now_iso = datetime.now(timezone.utc).isoformat()
    recorded_at = data.recorded_at or now_iso
    measurement_id = f"spo2_{uuid.uuid4().hex[:12]}"

    spo2_val = data.values.spo2
    alerts = []
    clinical_stage = "Normal"
    has_red_flags = False

    if spo2_val < 85:
        clinical_stage = "Severe Hypoxemia"
        alerts.append(f"Critical oxygen desaturation ({spo2_val}%). Seek medical attention.")
        has_red_flags = True
    elif spo2_val < 95:
        clinical_stage = "Mild Hypoxemia"
        alerts.append(f"Sub-optimal oxygen saturation ({spo2_val}%). Clinical benchmark is 95-100%.")

    record = {
        "id": measurement_id,
        "user_id": uid,
        "measurement_type": "spo2",
        "recorded_at": recorded_at,
        "values": data.values.model_dump(),
        "units": {"spo2": "%", "pulse": "bpm"},
        "clinical_stage": clinical_stage,
        "has_red_flags": has_red_flags,
        "safety_alerts": alerts,
        "raw_user_notes": data.raw_user_notes,
        "issues": [issue.model_dump() for issue in data.issues],
        "source": data.source,
        "scan_id": data.scan_id,
        "device_model": data.device_model,
        "device_type": data.device_type or "Pulse Oximeter",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    doc_ref = db.collection("profiles").document(uid).collection("measurements").document(measurement_id)
    doc_ref.set(record)

    # Immediately recalculate AI health analysis upon saving a new entity
    try:
        get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
    except Exception as ai_err:
        print(f"[MeasurementsRoute] Warning: Background AI re-run error: {ai_err}")

    return SpO2MeasurementResponse(**record)


@router.get("/measurements/spo2", response_model=List[SpO2MeasurementResponse])
async def list_spo2_measurements(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the longitudinal history of SpO2 / Pulse Oximeter measurements for the authenticated user.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    measurements_ref = db.collection("profiles").document(uid).collection("measurements")

    try:
        docs = measurements_ref.where("measurement_type", "==", "spo2").limit(limit).stream()
        results = [SpO2MeasurementResponse(**doc.to_dict()) for doc in docs]
        results.sort(key=lambda x: x.recorded_at, reverse=True)
        return results
    except Exception:
        return []


@router.post("/measurements/weight", response_model=WeightMeasurementResponse, status_code=status.HTTP_201_CREATED)
async def create_weight_measurement(
    data: WeightMeasurementCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Persists a verified or manually entered digital scale weight measurement.
    Stored under profiles/{uid}/measurements/{id} and updates weight_history.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    now_iso = datetime.now(timezone.utc).isoformat()
    recorded_at = data.recorded_at or now_iso
    measurement_id = f"w_{uuid.uuid4().hex[:12]}"

    # Normalize to kg
    weight_kg = data.values.weight if data.values.unit == "kg" else round(data.values.weight * 0.45359237, 2)

    record = {
        "id": measurement_id,
        "user_id": uid,
        "measurement_type": "weight",
        "recorded_at": recorded_at,
        "values": data.values.model_dump(),
        "weight_kg": weight_kg,
        "units": {"weight": "kg"},
        "clinical_stage": "Recorded",
        "has_red_flags": False,
        "safety_alerts": [],
        "raw_user_notes": data.raw_user_notes,
        "issues": [issue.model_dump() for issue in data.issues],
        "source": data.source,
        "scan_id": data.scan_id,
        "device_model": data.device_model,
        "device_type": data.device_type or "Digital Scale",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    doc_ref = db.collection("profiles").document(uid).collection("measurements").document(measurement_id)
    doc_ref.set(record)

    # Sync with profile weight & weight_history
    profile_ref = db.collection("profiles").document(uid)
    profile_ref.update({
        "weight_kg": weight_kg,
        "updated_at": recorded_at
    })
    profile_ref.collection("weight_history").add({
        "weight_kg": weight_kg,
        "recorded_at": recorded_at,
        "source": data.source,
        "device_type": data.device_type or "Digital Scale"
    })

    # Immediately recalculate AI health analysis upon saving a new entity
    try:
        get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
    except Exception as ai_err:
        print(f"[MeasurementsRoute] Warning: Background AI re-run error: {ai_err}")

    return WeightMeasurementResponse(**record)


@router.get("/measurements/weight", response_model=List[WeightMeasurementResponse])
async def list_weight_measurements(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the longitudinal history of weight measurements for the authenticated user.
    """
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    measurements_ref = db.collection("profiles").document(uid).collection("measurements")

    try:
        docs = measurements_ref.where("measurement_type", "==", "weight").limit(limit).stream()
        results = [WeightMeasurementResponse(**doc.to_dict()) for doc in docs]
        results.sort(key=lambda x: x.recorded_at, reverse=True)
        return results
    except Exception:
        return []

