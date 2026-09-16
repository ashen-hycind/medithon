"""
Doctor Health Report API Routes
===============================
Provides authenticated endpoints for generating and retrieving the dynamic,
clinician-facing Doctor Health PDF Report.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from security import get_current_user
from firebase_config import get_firestore_db
from services.report_service import generate_doctor_report_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/doctor")
async def generate_doctor_report(
    current_user: dict = Depends(get_current_user)
):
    """
    Generates a dynamic, multi-page clinician-facing Doctor Health PDF Report
    from the current real stored data in Firestore.

    - Computes deterministic statistics (averages, min/max, baselines, deltas)
    - Generates vector-quality trend charts (Matplotlib)
    - Integrates existing AI clinical insights (MedGemma reasoning)
    - Produces a fresh PDF every single time it is called.
    """
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )

    db = get_firestore_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable."
        )

    try:
        pdf_bytes = generate_doctor_report_pdf(user_id=uid, db=db)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"Doctor_Health_Report_{uid[:8]}_{timestamp_str}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        print(f"[ReportsRoute] Error generating Doctor Health Report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate doctor report: {str(e)}"
        )


@router.get("/doctor")
async def get_doctor_report(
    current_user: dict = Depends(get_current_user)
):
    """
    Convenience GET endpoint supporting direct browser link previews.
    Always generates a fresh PDF from the current stored health data.
    """
    return await generate_doctor_report(current_user=current_user)
