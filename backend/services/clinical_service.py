from typing import List, Tuple, Optional
from schemas import BloodPressureValues, BloodGlucoseValues, ExtractedIssue

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


# =====================================================================
# Blood Glucose / Diabetes Clinical Engine (ADA Standards of Care)
# =====================================================================

def classify_blood_glucose(values: BloodGlucoseValues) -> str:
    """
    Classifies blood glucose reading based on ADA (American Diabetes Association) Standards of Care:
    - Normalizes mmol/L to mg/dL (1 mmol/L = 18.018 mg/dL)
    - Severe Hypoglycemia: <54 mg/dL (<3.0 mmol/L)
    - Hypoglycemia Alert: <70 mg/dL (<3.9 mmol/L)
    - Normal:
        * Fasting/Pre-meal: 70 - 99 mg/dL
        * Post-meal / Random: 70 - 139 mg/dL
    - Elevated:
        * Fasting/Pre-meal: 100 - 125 mg/dL (Pre-diabetes range)
        * Post-meal / Random: 140 - 199 mg/dL (Impaired glucose tolerance)
    - Hyperglycemia: 200 - 299 mg/dL
    - Hyperglycemic Crisis: >=300 mg/dL (DKA/HHS acute risk)
    """
    val = values.glucose_value
    mgdl = val * 18.018 if values.unit == "mmol/L" else val

    if mgdl < 54.0:
        return "Severe Hypoglycemia"
    elif mgdl < 70.0:
        return "Hypoglycemia Alert"
    elif mgdl >= 300.0:
        return "Hyperglycemic Crisis"
    elif mgdl >= 200.0:
        return "Hyperglycemia"
    elif values.meal_context in ("post_meal", "after_meal"):
        return "Normal" if mgdl < 140.0 else "Elevated"
    elif values.meal_context in ("fasting", "before_meal"):
        return "Normal" if mgdl <= 99.0 else "Elevated"
    else:
        # General / Random / Bedtime reading
        return "Normal" if mgdl <= 140.0 else "Elevated"


def evaluate_glucose_alerts(
    values: BloodGlucoseValues, 
    issues: List[ExtractedIssue]
) -> Tuple[str, bool, List[str]]:
    """
    Evaluates glucose clinical stage, red-flag symptoms, and actionable guidance.
    Returns: (clinical_stage, has_red_flags, safety_alerts)
    """
    stage = classify_blood_glucose(values)
    alerts: List[str] = []
    has_red_flags = any(issue.is_red_flag for issue in issues)

    # Hypoglycemia guidance (Rule of 15)
    if stage == "Severe Hypoglycemia":
        has_red_flags = True
        alerts.append(
            "CRITICAL EMERGENCY: Blood glucose is dangerously low (<54 mg/dL / <3.0 mmol/L). "
            "Consume 15-20g of fast-acting carbohydrates immediately (juice, soda, glucose tablets). "
            "If the person is confused, uncooperative, or unconscious, administer glucagon and call emergency services (911) immediately. Do not put food into an unconscious person's mouth."
        )
    elif stage == "Hypoglycemia Alert":
        alerts.append(
            "Hypoglycemia Alert: Reading is below 70 mg/dL (3.9 mmol/L). Follow the Rule of 15: "
            "consume 15 grams of fast-acting carbohydrates (4 oz fruit juice, 3-4 glucose tablets, or 1 tablespoon sugar), "
            "rest quietly, and recheck your blood sugar in 15 minutes."
        )

    # Hyperglycemic Emergency guidance
    if stage == "Hyperglycemic Crisis":
        has_red_flags = True
        alerts.append(
            "CRITICAL ALERT: Blood glucose is severely elevated (>=300 mg/dL / >=16.7 mmol/L). "
            "Check for urine/blood ketones immediately if you have Type 1 Diabetes. "
            "Drink plenty of water and contact your physician or seek urgent medical evaluation."
        )
    elif stage == "Hyperglycemia":
        alerts.append(
            "Hyperglycemia Alert: Blood sugar is elevated (>=200 mg/dL). Drink water, verify whether medications were taken, and consult your diabetes care plan."
        )

    return stage, has_red_flags, alerts

