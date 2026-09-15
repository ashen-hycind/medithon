from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from schemas import ProfileCreate, ProfileUpdate, ProfileResponse, WeightUpdate, UserAuthResponse
from security import get_current_user
from firebase_config import get_firestore_db

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserAuthResponse)
async def get_user_status(current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    uid = current_user["uid"]
    has_profile = False
    
    if db is not None:
        doc = db.collection("profiles").document(uid).get()
        has_profile = doc.exists

    return UserAuthResponse(
        uid=uid,
        email=current_user.get("email"),
        has_profile=has_profile
    )

@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(profile_data: ProfileCreate, current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected. Please configure Firebase credentials."
        )

    uid = current_user["uid"]
    doc_ref = db.collection("profiles").document(uid)
    existing = doc_ref.get()
    
    if existing.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile already exists. Use PUT /api/users/profile to update."
        )

    now = datetime.now(timezone.utc).isoformat()
    record = profile_data.model_dump()
    record.update({
        "user_id": uid,
        "created_at": now,
        "updated_at": now
    })

    doc_ref.set(record)

    # Automatically record the starting weight into weight_history subcollection
    weight_entry = {
        "weight_kg": profile_data.weight_kg,
        "recorded_at": now,
        "source": "onboarding"
    }
    doc_ref.collection("weight_history").add(weight_entry)

    return ProfileResponse(**record)

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    doc = db.collection("profiles").document(uid).get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please complete onboarding first."
        )

    return ProfileResponse(**doc.to_dict())

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(update_data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore database is not connected."
        )

    uid = current_user["uid"]
    doc_ref = db.collection("profiles").document(uid)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    data = doc.to_dict()
    updates = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Check pregnancy vs sex
    if "pregnancy_status" in updates and updates["pregnancy_status"]:
        if data.get("sex") != "female":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pregnancy status cannot be set to true for non-female sex."
            )
            
    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now
    
    doc_ref.update(updates)
    data.update(updates)
    return ProfileResponse(**data)

@router.post("/weight", status_code=status.HTTP_200_OK)
async def update_weight(weight_data: WeightUpdate, current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore database is not connected.")

    uid = current_user["uid"]
    doc_ref = db.collection("profiles").document(uid)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    timestamp = (weight_data.recorded_at or datetime.now(timezone.utc)).isoformat()
    
    # Update current weight on profile
    doc_ref.update({
        "weight_kg": weight_data.weight_kg,
        "updated_at": timestamp
    })

    # Append to weight history subcollection
    doc_ref.collection("weight_history").add({
        "weight_kg": weight_data.weight_kg,
        "recorded_at": timestamp,
        "source": "manual_update"
    })

    return {"status": "success", "weight_kg": weight_data.weight_kg, "recorded_at": timestamp}

@router.get("/weight/history", status_code=status.HTTP_200_OK)
async def get_weight_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    db = get_firestore_db()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore database is not connected.")

    uid = current_user["uid"]
    doc_ref = db.collection("profiles").document(uid)
    history_ref = doc_ref.collection("weight_history")
    
    results = []
    try:
        docs = history_ref.order_by("recorded_at", direction="DESCENDING").limit(limit).stream()
        for doc in docs:
            item = doc.to_dict()
            item["id"] = doc.id
            results.append(item)
    except Exception:
        # Fallback if composite index is pending
        try:
            docs = history_ref.limit(limit).stream()
            for doc in docs:
                item = doc.to_dict()
                item["id"] = doc.id
                results.append(item)
            results.sort(key=lambda x: x.get("recorded_at", ""), reverse=True)
        except Exception:
            results = []

    # If history is empty, check profile for baseline weight
    if not results:
        profile_doc = doc_ref.get()
        if profile_doc.exists:
            p_data = profile_doc.to_dict()
            if p_data.get("weight_kg"):
                results.append({
                    "id": "baseline_weight",
                    "weight_kg": p_data["weight_kg"],
                    "recorded_at": p_data.get("updated_at") or p_data.get("created_at") or datetime.now(timezone.utc).isoformat(),
                    "source": "initial_profile"
                })

    return results
