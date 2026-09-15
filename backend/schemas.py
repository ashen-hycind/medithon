from typing import Optional, Literal, Union, Dict, Any, List
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

BloodGroupType = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"]
SexType = Literal["male", "female"]

class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    blood_group: BloodGroupType
    sex: SexType = Field(..., description="Sex assigned at birth according to medical records: 'male' or 'female'")
    height_cm: float = Field(..., ge=40.0, le=260.0, description="Height in centimeters")
    weight_kg: float = Field(..., ge=15.0, le=400.0, description="Weight in kilograms")
    pregnancy_status: Optional[bool] = Field(default=False, description="Only applicable if sex is female")
    gestational_age_weeks: Optional[int] = Field(default=None, ge=1, le=45, description="Gestational age in weeks if pregnant")
    activity_level: int = Field(..., ge=1, le=10, description="Activity level on a scale from 1 (sedentary) to 10 (extremely active)")
    occupation: Optional[str] = Field(default=None, max_length=120, description="Optional occupation")

    @model_validator(mode="after")
    def validate_pregnancy_and_sex(self):
        if self.sex == "male":
            if self.pregnancy_status:
                raise ValueError("Pregnancy status cannot be true when sex is male.")
            if self.gestational_age_weeks is not None:
                raise ValueError("Gestational age is only applicable for pregnant females.")
        elif self.sex == "female":
            if not self.pregnancy_status and self.gestational_age_weeks is not None:
                raise ValueError("Gestational age can only be specified if pregnancy_status is true.")
        return self

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    height_cm: Optional[float] = Field(default=None, ge=40.0, le=260.0)
    pregnancy_status: Optional[bool] = None
    gestational_age_weeks: Optional[int] = Field(default=None, ge=1, le=45)
    activity_level: Optional[int] = Field(default=None, ge=1, le=10)
    occupation: Optional[str] = Field(default=None, max_length=120)

class WeightUpdate(BaseModel):
    weight_kg: float = Field(..., ge=15.0, le=400.0, description="Updated weight in kg")
    recorded_at: Optional[datetime] = None

class ProfileResponse(ProfileBase):
    user_id: str
    created_at: str
    updated_at: str

class UserAuthResponse(BaseModel):
    uid: str
    email: Optional[str]
    has_profile: bool


# =====================================================================
# Blood Pressure & Clinical Issues Schemas
# =====================================================================

IssueCategory = Literal[
    "symptom",              # headache, dizziness, vision change, chest pain
    "lifestyle",            # poor sleep, high stress, high salt
    "medication",           # OTC NSAIDs (Advil), decongestants, BP meds, supplements
    "testing_condition",    # caffeine <30m, smoked, exercised, anxious/rushed
    "device_problem",       # cuff too loose, battery low
    "other"
]

class BloodPressureValues(BaseModel):
    systolic: int = Field(..., ge=40, le=300, description="Systolic blood pressure in mmHg")
    diastolic: int = Field(..., ge=30, le=200, description="Diastolic blood pressure in mmHg")
    pulse: Optional[int] = Field(None, ge=30, le=250, description="Pulse rate in bpm")

    @model_validator(mode="after")
    def validate_pressure_differential(self):
        if self.systolic <= self.diastolic:
            raise ValueError("Systolic pressure must be strictly greater than diastolic pressure.")
        return self

class ExtractedIssue(BaseModel):
    category: IssueCategory = Field(..., description="Classification category")
    tag: str = Field(..., description="Standardized machine tag e.g. 'caffeine_intake', 'headache', 'otc_nsaid'")
    label: str = Field(..., description="User-friendly display label e.g. 'Caffeine within 30 min', 'Headache'")
    user_detail: Optional[str] = Field(None, description="Extracted detail or snippet from user text")
    is_red_flag: bool = Field(False, description="True if symptom represents an acute hypertensive crisis emergency warning")
    severity: Optional[Literal["mild", "moderate", "severe"]] = None

GlucoseUnit = Literal["mg/dL", "mmol/L"]
MealContext = Literal["fasting", "before_meal", "after_meal", "post_meal", "bedtime", "random"]

class BloodGlucoseValues(BaseModel):
    glucose_value: float = Field(..., description="Measured glucose concentration")
    unit: GlucoseUnit = Field(default="mg/dL", description="Measurement unit ('mg/dL' or 'mmol/L')")
    meal_context: Optional[MealContext] = Field(default=None, description="Meal timing context e.g. fasting, after_meal")

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.unit == "mg/dL":
            if not (10.0 <= self.glucose_value <= 700.0):
                raise ValueError(f"Glucose value {self.glucose_value} mg/dL is outside valid physiological bounds (10 - 700 mg/dL).")
        elif self.unit == "mmol/L":
            if not (0.5 <= self.glucose_value <= 40.0):
                raise ValueError(f"Glucose value {self.glucose_value} mmol/L is outside valid physiological bounds (0.5 - 40.0 mmol/L).")
        return self

class ImageQualityReport(BaseModel):
    is_readable: bool = True
    glare_detected: bool = False
    display_cut_off: bool = False
    issues: list[str] = Field(default_factory=list)

class ScanExtractionResponse(BaseModel):
    scan_id: str
    detected_type: Literal["blood_pressure", "blood_glucose", "unknown"] = "blood_pressure"
    device_name: Optional[str] = Field(None, description="e.g. Omron HEM-7120, Accu-Chek Guide")
    values: Union[BloodPressureValues, BloodGlucoseValues, Dict[str, Any]]
    confidence: float = Field(..., ge=0.0, le=1.0)
    quality: ImageQualityReport
    raw_detected_text: Optional[str] = None

class ExtractIssuesRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Free-form user note about symptoms, lifestyle, medications, or testing conditions")

class ExtractIssuesResponse(BaseModel):
    raw_text: str
    issues: list[ExtractedIssue] = Field(default_factory=list)
    has_red_flags: bool = False

class BloodPressureMeasurementCreate(BaseModel):
    recorded_at: Optional[str] = Field(None, description="ISO 8601 timestamp of measurement")
    values: BloodPressureValues
    raw_user_notes: Optional[str] = Field(None, description="Unfiltered user notes/sentences")
    issues: list[ExtractedIssue] = Field(default_factory=list, description="Extracted or user-confirmed clinical issues")
    source: Literal["camera", "screenshot", "manual"] = "camera"
    scan_id: Optional[str] = None
    device_model: Optional[str] = None

class BloodPressureMeasurementResponse(BaseModel):
    id: str
    user_id: str
    recorded_at: str
    values: BloodPressureValues
    units: dict[str, str] = Field(default_factory=lambda: {"systolic": "mmHg", "diastolic": "mmHg", "pulse": "bpm"})
    clinical_stage: str # "Normal", "Elevated", "Stage 1", "Stage 2", "Hypertensive Crisis"
    has_red_flags: bool = False
    safety_alerts: list[str] = Field(default_factory=list)
    raw_user_notes: Optional[str] = None
    issues: list[ExtractedIssue] = Field(default_factory=list)
    source: str
    scan_id: Optional[str] = None
    device_model: Optional[str] = None
    created_at: str
    updated_at: str

class BloodGlucoseMeasurementCreate(BaseModel):
    recorded_at: Optional[str] = Field(None, description="ISO 8601 timestamp of measurement")
    values: BloodGlucoseValues
    meal_context: Optional[MealContext] = Field(None, description="fasting, before_meal, after_meal, bedtime, random")
    raw_user_notes: Optional[str] = Field(None, description="Unfiltered user notes/sentences")
    issues: list[ExtractedIssue] = Field(default_factory=list, description="Extracted or user-confirmed clinical issues")
    source: Literal["camera", "screenshot", "manual"] = "camera"
    scan_id: Optional[str] = None
    device_model: Optional[str] = None

class BloodGlucoseMeasurementResponse(BaseModel):
    id: str
    user_id: str
    recorded_at: str
    values: BloodGlucoseValues
    meal_context: Optional[MealContext] = None
    units: dict[str, str] = Field(default_factory=lambda: {"glucose": "mg/dL"})
    clinical_stage: str # "Severe Hypoglycemia", "Hypoglycemia Alert", "Normal", "Elevated", "Hyperglycemia", "Hyperglycemic Crisis"
    has_red_flags: bool = False
    safety_alerts: list[str] = Field(default_factory=list)
    raw_user_notes: Optional[str] = None
    issues: list[ExtractedIssue] = Field(default_factory=list)
    source: str
    scan_id: Optional[str] = None
    device_model: Optional[str] = None
    created_at: str
    updated_at: str


# =====================================================================
# AI Clinical Correlation Schemas
# =====================================================================

CorrelationCategory = Literal[
    "lifestyle_trigger",
    "metabolic_cardiovascular",
    "symptom_spike",
    "longitudinal_trend",
    "medication_response",
    "fluid_weight_shift",
    "other"
]

CorrelationConfidence = Literal["high", "moderate", "low"]

class CorrelationItem(BaseModel):
    category: CorrelationCategory = Field(..., description="Categorization of correlation pattern")
    confidence: CorrelationConfidence = Field(..., description="Confidence level: high, moderate, low")
    headline: str = Field(..., min_length=1, description="Concise clinical title")
    explanation: str = Field(..., min_length=1, description="Detailed explanation grounded in factual evidence")
    evidence_count: int = Field(default=1, ge=0, description="Number of supporting measurement occurrences")
    clinical_suggestion: str = Field(..., min_length=1, description="Actionable, non-diagnostic guidance")

class AnalysisStats(BaseModel):
    total_bp_readings: int = Field(default=0, ge=0)
    total_glucose_readings: int = Field(default=0, ge=0)
    avg_systolic: Optional[float] = None
    avg_diastolic: Optional[float] = None
    avg_pulse: Optional[float] = None
    avg_glucose_mg_dl: Optional[float] = None
    morning_avg_bp: Optional[dict[str, float]] = None
    evening_avg_bp: Optional[dict[str, float]] = None
    fasting_avg_glucose: Optional[float] = None
    post_meal_avg_glucose: Optional[float] = None

class HealthAnalysisResponse(BaseModel):
    user_id: str
    generated_at: str
    is_cached: bool = False
    stats: AnalysisStats
    correlations: list[CorrelationItem] = Field(default_factory=list)
    urgent_alerts: list[str] = Field(default_factory=list)
    doctor_summary: str



