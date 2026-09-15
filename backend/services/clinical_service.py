from typing import List, Tuple
from schemas import BloodPressureValues, ExtractedIssue

def classify_blood_pressure(values: BloodPressureValues) -> str:
    """
    Classifies blood pressure according to AHA/ACC 2017 Guidelines:
    - Normal: <120 and <80 mmHg
    - Elevated: 120-129 and <80 mmHg
    - Hypertension Stage 1: 130-139 or 80-89 mmHg
    - Hypertension Stage 2: >=140 or >=90 mmHg
    - Hypertensive Crisis: >180 and/or >120 mmHg
    """
    sys = values.systolic
    dia = values.diastolic

    if sys > 180 or dia > 120:
        return "Hypertensive Crisis"
    elif sys >= 140 or dia >= 90:
        return "Hypertension Stage 2"
    elif (130 <= sys <= 139) or (80 <= dia <= 89):
        return "Hypertension Stage 1"
    elif (120 <= sys <= 129) and dia < 80:
        return "Elevated"
    else:
        return "Normal"

def evaluate_clinical_alerts(values: BloodPressureValues, issues: List[ExtractedIssue]) -> Tuple[str, bool, List[str]]:
    """
    Evaluates stage and produces safety warnings based on clinical issues and thresholds.
    Returns: (clinical_stage, has_red_flags, safety_alerts)
    """
    stage = classify_blood_pressure(values)
    alerts: List[str] = []
    
    # Check for red flag symptoms
    has_red_flags = any(issue.is_red_flag for issue in issues)
    red_flag_labels = [issue.label for issue in issues if issue.is_red_flag]

    # Crisis check
    if stage == "Hypertensive Crisis":
        if has_red_flags:
            alerts.append(
                f"EMERGENCY WARNING: Blood pressure is dangerously high ({values.systolic}/{values.diastolic} mmHg) "
                f"with acute symptoms reported ({', '.join(red_flag_labels)}). "
                f"Please seek emergency medical attention or call emergency services immediately."
            )
        else:
            alerts.append(
                f"Hypertensive Crisis Alert: Reading exceeds 180/120 mmHg. "
                f"Rest quietly for 5 minutes and re-test. If still elevated, contact your doctor immediately."
            )

    # Condition & substance notes
    temp_elevation_factors = []
    for issue in issues:
        if issue.tag in ("caffeine_intake", "nicotine_intake", "recent_exercise", "anxious_rushed"):
            temp_elevation_factors.append(issue.label)
        elif issue.category == "medication" and issue.tag in ("otc_nsaid", "decongestant"):
            temp_elevation_factors.append(issue.label)

    if temp_elevation_factors and stage != "Hypertensive Crisis":
        alerts.append(
            f"Note: Reported conditions ({', '.join(temp_elevation_factors)}) may temporarily raise blood pressure."
        )

    return stage, has_red_flags, alerts
