export type BloodGroupType = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-' | 'Unknown';
export type SexType = 'male' | 'female';

export interface UserProfile {
  name: string;
  dob: string;
  blood_group: BloodGroupType;
  sex: SexType;
  height_cm: number;
  weight_kg: number;
  pregnancy_status?: boolean;
  gestational_age_weeks?: number | null;
  activity_level: number;
  occupation?: string;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface UserStatus {
  uid: string;
  email?: string;
  has_profile: boolean;
}

export type IssueCategory =
  | 'symptom'
  | 'lifestyle'
  | 'medication'
  | 'testing_condition'
  | 'device_problem'
  | 'other';

export interface ExtractedIssue {
  category: IssueCategory;
  tag: string;
  label: string;
  user_detail?: string | null;
  is_red_flag: boolean;
  severity?: 'mild' | 'moderate' | 'severe' | null;
}

export interface BloodPressureValues {
  systolic: number;
  diastolic: number;
  pulse?: number | null;
}

export type GlucoseUnit = 'mg/dL' | 'mmol/L';
export type MealContext = 'fasting' | 'before_meal' | 'after_meal' | 'post_meal' | 'bedtime' | 'random';

export interface BloodGlucoseValues {
  glucose_value: number;
  unit: GlucoseUnit;
  meal_context?: MealContext | null;
}

export interface ImageQualityReport {
  is_readable: boolean;
  glare_detected: boolean;
  display_cut_off: boolean;
  issues: string[];
}

export interface ScanExtractionResponse {
  scan_id: string;
  detected_type: 'blood_pressure' | 'blood_glucose' | string;
  device_name?: string | null;
  values: BloodPressureValues | BloodGlucoseValues | any;
  confidence: number;
  quality: ImageQualityReport;
  raw_detected_text?: string | null;
}

export interface BloodPressureMeasurementCreate {
  recorded_at?: string;
  values: BloodPressureValues;
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source?: 'camera' | 'screenshot' | 'manual';
  scan_id?: string;
  device_model?: string | null;
}

export interface BloodPressureMeasurement {
  id: string;
  user_id: string;
  recorded_at: string;
  values: BloodPressureValues;
  units: { systolic: string; diastolic: string; pulse: string };
  clinical_stage: 'Normal' | 'Elevated' | 'Hypertension Stage 1' | 'Hypertension Stage 2' | 'Hypertensive Crisis' | string;
  has_red_flags: boolean;
  safety_alerts: string[];
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source: string;
  scan_id?: string;
  device_model?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WeightRecord {
  id?: string;
  weight_kg: number;
  recorded_at: string;
  source?: string;
}
export interface BloodGlucoseMeasurementCreate {
  recorded_at?: string;
  values: BloodGlucoseValues;
  meal_context?: MealContext | null;
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source?: 'camera' | 'screenshot' | 'manual';
  scan_id?: string;
  device_model?: string | null;
}

export interface BloodGlucoseMeasurement {
  id: string;
  user_id: string;
  recorded_at: string;
  values: BloodGlucoseValues;
  meal_context?: MealContext | null;
  units: { glucose: string };
  clinical_stage: 'Severe Hypoglycemia' | 'Hypoglycemia Alert' | 'Normal' | 'Elevated' | 'Hyperglycemia' | 'Hyperglycemic Crisis' | string;
  has_red_flags: boolean;
  safety_alerts: string[];
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source: string;
  scan_id?: string;
  device_model?: string | null;
  created_at: string;
  updated_at: string;
}

