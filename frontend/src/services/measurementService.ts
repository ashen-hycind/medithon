import {
  ScanExtractionResponse,
  ExtractedIssue,
  BloodPressureMeasurementCreate,
  BloodPressureMeasurement,
  BloodGlucoseMeasurementCreate,
  BloodGlucoseMeasurement,
  HealthAnalysisResponse
} from '../types';

export async function scanBloodPressureImage(file: File): Promise<ScanExtractionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/scan/extract', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to scan blood pressure monitor.');
  }

  return res.json();
}

export async function extractClinicalIssues(text: string): Promise<{
  raw_text: string;
  issues: ExtractedIssue[];
  has_red_flags: boolean;
}> {
  const res = await fetch('/api/scan/extract-issues', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to extract clinical issues.');
  }

  return res.json();
}

export async function createBloodPressureMeasurement(
  data: BloodPressureMeasurementCreate,
  token: string
): Promise<BloodPressureMeasurement> {
  const res = await fetch('/api/measurements/blood-pressure', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save measurement.');
  }

  return res.json();
}

export async function getBloodPressureMeasurements(
  token: string,
  limit: number = 50
): Promise<BloodPressureMeasurement[]> {
  const res = await fetch(`/api/measurements/blood-pressure?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch blood pressure history.');
  }

  return res.json();
}

export async function createBloodGlucoseMeasurement(
  data: BloodGlucoseMeasurementCreate,
  token: string
): Promise<BloodGlucoseMeasurement> {
  const res = await fetch('/api/measurements/blood-glucose', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save glucose measurement.');
  }

  return res.json();
}

export async function getBloodGlucoseMeasurements(
  token: string,
  limit: number = 50
): Promise<BloodGlucoseMeasurement[]> {
  const res = await fetch(`/api/measurements/blood-glucose?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch blood glucose history.');
  }

  return res.json();
}

export async function getHealthCorrelations(
  token: string,
  forceRefresh: boolean = false
): Promise<HealthAnalysisResponse> {
  const url = `/api/analysis/correlations${forceRefresh ? '?force_refresh=true' : ''}`;
  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch clinical correlation analysis.');
  }

  return res.json();
}

export async function triggerFreshAnalysis(
  token: string
): Promise<HealthAnalysisResponse> {
  const res = await fetch('/api/analysis/generate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to trigger fresh clinical analysis.');
  }

  return res.json();
}

export async function createSpO2Measurement(
  data: any,
  token: string
): Promise<any> {
  const res = await fetch('/api/measurements/spo2', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save SpO2 measurement.');
  }

  return res.json();
}

export async function createWeightMeasurement(
  data: any,
  token: string
): Promise<any> {
  const res = await fetch('/api/measurements/weight', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save weight measurement.');
  }

  return res.json();
}

export async function generateDoctorReportPdf(token: string): Promise<Blob> {
  const res = await fetch('/api/reports/doctor', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate Doctor Health Report PDF.');
  }

  return res.blob();
}

