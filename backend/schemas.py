from typing import Optional, Literal
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
