"""
AI Clinical Correlation & Analysis Routes
=========================================
Provides endpoints for retrieving and generating AI-driven clinical correlations,
longitudinal trends, confounder insights, and physician summaries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas import HealthAnalysisResponse
from security import get_current_user
from firebase_config import get_firestore_db
from services.analysis_service import get_or_compute_analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/correlations", response_model=HealthAnalysisResponse)
async def get_health_correlations(
    force_refresh: bool = Query(False, description="Bypass cache and generate fresh analysis"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the clinical correlation analysis for the authenticated user.
    Uses cached analysis if generated within the last 1 hour and no new measurements were logged.
    """
    db = get_firestore_db()
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials."
        )

    try:
        analysis = get_or_compute_analysis(user_id=uid, db=db, force_refresh=force_refresh)
        return analysis
    except Exception as e:
        print(f"[AnalysisRoute] Error generating correlation analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate clinical analysis: {str(e)}"
        )


@router.post("/generate", response_model=HealthAnalysisResponse)
async def trigger_fresh_analysis(
    current_user: dict = Depends(get_current_user)
):
    """
    Forces the computation of fresh clinical correlations and physician summaries,
    updating the Firestore cache.
    """
    db = get_firestore_db()
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials."
        )

    try:
        analysis = get_or_compute_analysis(user_id=uid, db=db, force_refresh=True)
        return analysis
    except Exception as e:
        print(f"[AnalysisRoute] Error generating correlation analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate fresh clinical analysis: {str(e)}"
        )
