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

export interface SpO2Values {
  spo2: number;
  pulse?: number | null;
}

export interface WeightValues {
  weight: number;
  unit: 'kg' | 'lb';
}

export interface ImageQualityReport {
  is_readable: boolean;
  glare_detected: boolean;
  display_cut_off: boolean;
  issues: string[];
}

export interface ScanExtractionResponse {
  scan_id: string;
  detected_type: 'blood_pressure' | 'pulse_oximeter' | 'blood_glucose' | 'weight' | string;
  device_name?: string | null;
  values: BloodPressureValues | BloodGlucoseValues | SpO2Values | WeightValues | any;
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
  device_type?: string | null;
}

export interface BloodPressureMeasurement {
  id: string;
  user_id: string;
  recorded_at: string;
  values: BloodPressureValues;
  units: { systolic: string; diastolic: string; pulse: string; spo2?: string };
  clinical_stage: 'Normal' | 'Elevated' | 'Hypertension Stage 1' | 'Hypertension Stage 2' | 'Hypertensive Crisis' | string;
  has_red_flags: boolean;
  safety_alerts: string[];
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source: string;
  scan_id?: string;
  device_model?: string | null;
  device_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WeightRecord {
  id?: string;
  weight_kg: number;
  recorded_at: string;
  source?: string;
  device_type?: string | null;
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
  device_type?: string | null;
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
  device_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SpO2MeasurementCreate {
  recorded_at?: string;
  values: SpO2Values;
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source?: 'camera' | 'screenshot' | 'manual';
  scan_id?: string;
  device_model?: string | null;
  device_type?: string | null;
}

export interface SpO2Measurement {
  id: string;
  user_id: string;
  recorded_at: string;
  values: SpO2Values;
  units: { spo2: string; pulse: string };
  clinical_stage: string;
  has_red_flags: boolean;
  safety_alerts: string[];
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source: string;
  scan_id?: string;
  device_model?: string | null;
  device_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WeightMeasurementCreate {
  recorded_at?: string;
  values: WeightValues;
  raw_user_notes?: string | null;
  issues: ExtractedIssue[];
  source?: 'camera' | 'screenshot' | 'manual';
  scan_id?: string;
  device_model?: string | null;
  device_type?: string | null;
}

export type CorrelationCategory =
  | 'lifestyle_trigger'
  | 'metabolic_cardiovascular'
  | 'symptom_spike'
  | 'longitudinal_trend'
  | 'medication_response'
  | 'fluid_weight_shift'
  | 'multi_device_correlation'
  | 'other';

export type CorrelationConfidence = 'high' | 'moderate' | 'low';

export interface CorrelationItem {
  category: CorrelationCategory;
  confidence: CorrelationConfidence;
  headline: string;
  explanation: string;
  evidence_count: number;
  clinical_suggestion: string;
}

export interface AnalysisStats {
  total_bp_readings: number;
  total_glucose_readings: number;
  total_weight_readings?: number;
  devices_detected?: string[];
  avg_systolic?: number | null;
  avg_diastolic?: number | null;
  avg_pulse?: number | null;
  avg_glucose_mg_dl?: number | null;
  avg_spo2?: number | null;
  morning_avg_bp?: { systolic: number; diastolic: number } | null;
  evening_avg_bp?: { systolic: number; diastolic: number } | null;
  fasting_avg_glucose?: number | null;
  post_meal_avg_glucose?: number | null;
  trajectory_7d_vs_14d?: any;
  dynamic_trends?: Record<string, any> | null;
}

export interface RoteMemoryState {
  session_resumed: boolean;
  last_checkpoint_at?: string | null;
  delta_readings_count: number;
  prior_baseline_systolic?: number | null;
  prior_baseline_glucose?: number | null;
  prior_trajectory_trend?: string | null;
  trajectory_shift_summary?: string | null;
  accumulators?: Record<string, any> | null;
  correlation_bank?: Record<string, any> | null;
  checkpoint_version: number;
}

export interface HealthAnalysisResponse {
  user_id: string;
  generated_at: string;
  is_cached: boolean;
  stats: AnalysisStats;
  patterns?: Record<string, any> | null;
  rote_memory?: RoteMemoryState | null;
  correlations: CorrelationItem[];
  urgent_alerts: string[];
  doctor_summary: string;
}

