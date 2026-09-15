import React, { useState, useRef } from 'react';
import {
  X,
  Camera,
  Upload,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Activity,
  RefreshCw,
  Droplet,
  Heart,
  Clock,
  Utensils
} from 'lucide-react';
import {
  ExtractedIssue,
  ScanExtractionResponse,
  BloodPressureMeasurement,
  BloodPressureValues,
  BloodGlucoseMeasurement,
  BloodGlucoseValues,
  BloodGlucoseMeasurementCreate,
  GlucoseUnit,
  MealContext
} from '../types';
import {
  scanBloodPressureImage,
  extractClinicalIssues,
  createBloodPressureMeasurement,
  createBloodGlucoseMeasurement
} from '../services/measurementService';

interface ScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string;
  defaultDeviceType?: 'blood_pressure' | 'blood_glucose';
  onMeasurementSaved?: (measurement: BloodPressureMeasurement | BloodGlucoseMeasurement) => void;
}

export function ScanModal({
  isOpen,
  onClose,
  token,
  defaultDeviceType = 'blood_pressure',
  onMeasurementSaved
}: ScanModalProps) {
  const [deviceType, setDeviceType] = useState<'blood_pressure' | 'blood_glucose'>(defaultDeviceType);
  const [step, setStep] = useState<'upload' | 'scanning' | 'review'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanExtractionResponse | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Blood Pressure values
  const [systolic, setSystolic] = useState<number>(120);
  const [diastolic, setDiastolic] = useState<number>(80);
  const [pulse, setPulse] = useState<number | ''>(72);

  // Blood Glucose values
  const [glucoseValue, setGlucoseValue] = useState<number | ''>(104);
  const [glucoseUnit, setGlucoseUnit] = useState<GlucoseUnit>('mg/dL');
  const [mealContext, setMealContext] = useState<MealContext>('fasting');

  // Clinical issues & notes
  const [rawNotes, setRawNotes] = useState('');
  const [issues, setIssues] = useState<ExtractedIssue[]>([]);
  const [isExtractingNotes, setIsExtractingNotes] = useState(false);

  // Form submission state
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleReset = () => {
    setStep('upload');
    setSelectedFile(null);
    setPreviewUrl(null);
    setScanResult(null);
    setSystolic(120);
    setDiastolic(80);
    setPulse(72);
    setGlucoseValue(104);
    setGlucoseUnit('mg/dL');
    setMealContext('fasting');
    setRawNotes('');
    setIssues([]);
    setError(null);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const processFile = async (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setStep('scanning');
    setError(null);

    try {
      const result = await scanBloodPressureImage(file);
      setScanResult(result);

      if (result.detected_type === 'blood_glucose') {
        setDeviceType('blood_glucose');
        const gVals = result.values as BloodGlucoseValues;
        if (gVals) {
          setGlucoseValue(gVals.glucose_value);
          if (gVals.unit) setGlucoseUnit(gVals.unit);
          if (gVals.meal_context) setMealContext(gVals.meal_context);
        }
      } else {
        setDeviceType('blood_pressure');
        const bpVals = result.values as BloodPressureValues;
        if (bpVals) {
          setSystolic(bpVals.systolic);
          setDiastolic(bpVals.diastolic);
          setPulse(bpVals.pulse ?? '');
        }
      }

      setStep('review');
    } catch (err: any) {
      console.error('Scan error:', err);
      setError(err.message || 'Could not analyze device display. You can enter your reading manually.');
      setStep('review');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleExtractNotes = async () => {
    if (!rawNotes.trim()) return;
    try {
      setIsExtractingNotes(true);
      setError(null);
      const res = await extractClinicalIssues(rawNotes);
      const existingTags = new Set(issues.map(i => i.tag));
      const newIssues = res.issues.filter(i => !existingTags.has(i.tag));
      setIssues(prev => [...prev, ...newIssues]);
    } catch (err: any) {
      console.error('Notes extraction failed:', err);
    } finally {
      setIsExtractingNotes(false);
    }
  };

  const removeIssue = (tag: string) => {
    setIssues(prev => prev.filter(i => i.tag !== tag));
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);

      // Auto-extract notes if user typed without previewing
      let finalIssues = issues;
      if (rawNotes.trim() && issues.length === 0) {
        try {
          const res = await extractClinicalIssues(rawNotes.trim());
          finalIssues = res.issues;
        } catch (extractErr) {
          console.error('Auto-extraction during save failed:', extractErr);
        }
      }

      if (deviceType === 'blood_pressure') {
        if (systolic <= diastolic) {
          setError('Systolic pressure must be higher than diastolic pressure.');
          setIsSaving(false);
          return;
        }

        const payload = {
          values: {
            systolic,
            diastolic,
            pulse: typeof pulse === 'number' ? pulse : null,
          },
          raw_user_notes: rawNotes.trim() || null,
          issues: finalIssues,
          source: selectedFile ? ('camera' as const) : ('manual' as const),
          scan_id: scanResult?.scan_id,
          device_model: scanResult?.device_name || null,
        };

        const saved = await createBloodPressureMeasurement(payload, token);
        onMeasurementSaved?.(saved);
        handleClose();
      } else {
        // Blood Glucose Save
        if (!glucoseValue || Number(glucoseValue) <= 0) {
          setError('Please enter a valid glucose reading.');
          setIsSaving(false);
          return;
        }

        const payload: BloodGlucoseMeasurementCreate = {
          values: {
            glucose_value: Number(glucoseValue),
            unit: glucoseUnit,
            meal_context: mealContext,
          },
          meal_context: mealContext,
          raw_user_notes: rawNotes.trim() || null,
          issues: finalIssues,
          source: selectedFile ? 'camera' : 'manual',
          scan_id: scanResult?.scan_id,
          device_model: scanResult?.device_name || null,
        };

        const saved = await createBloodGlucoseMeasurement(payload, token);
        onMeasurementSaved?.(saved);
        handleClose();
      }
    } catch (err: any) {
      console.error('Save measurement error:', err);
      setError(err.message || 'Failed to save measurement.');
    } finally {
      setIsSaving(false);
    }
  };

  // Real-time ADA Stage Calculation for Glucose
  const getGlucoseStageInfo = () => {
    const val = typeof glucoseValue === 'number' ? glucoseValue : parseFloat(glucoseValue) || 0;
    const mgdl = glucoseUnit === 'mmol/L' ? val * 18.018 : val;

    if (mgdl < 54) {
      return {
        stage: 'Severe Hypoglycemia',
        badge: 'bg-red-100 text-red-800 border-red-300 font-bold',
        alert: 'CRITICAL: Blood glucose <54 mg/dL. Consume 15g fast-acting carbs immediately and recheck in 15m.'
      };
    } else if (mgdl < 70) {
      return {
        stage: 'Hypoglycemia Alert',
        badge: 'bg-orange-100 text-orange-800 border-orange-200 font-semibold',
        alert: 'Low blood sugar (<70 mg/dL). Follow the Rule of 15: take 15g fast carbs and re-test.'
      };
    } else if (mgdl >= 300) {
      return {
        stage: 'Hyperglycemic Crisis',
        badge: 'bg-red-100 text-red-800 border-red-300 font-bold',
        alert: 'Severely elevated glucose (>=300 mg/dL). Hydrate, check ketones, and consult clinician.'
      };
    } else if (mgdl >= 200) {
      return {
        stage: 'Hyperglycemia',
        badge: 'bg-rose-50 text-rose-700 border-rose-200',
        alert: 'Blood glucose is elevated (>=200 mg/dL). Verify medication adherence.'
      };
    } else if (mealContext === 'after_meal' || mealContext === 'post_meal') {
      return mgdl < 140
        ? { stage: 'Normal (Post-Meal)', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', alert: null }
        : { stage: 'Elevated (Post-Meal)', badge: 'bg-amber-50 text-amber-700 border-amber-200', alert: null };
    } else if (mealContext === 'fasting' || mealContext === 'before_meal') {
      return mgdl <= 99
        ? { stage: 'Normal (Fasting)', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', alert: null }
        : { stage: 'Elevated (Fasting)', badge: 'bg-amber-50 text-amber-700 border-amber-200', alert: 'Pre-diabetic fasting range (100-125 mg/dL).' };
    } else {
      return mgdl <= 140
        ? { stage: 'Normal', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', alert: null }
        : { stage: 'Elevated', badge: 'bg-amber-50 text-amber-700 border-amber-200', alert: null };
    }
  };

  const glucoseStage = getGlucoseStageInfo();
  const isBPCrisis = systolic > 180 || diastolic > 120;
  const hasRedFlagSymptom = issues.some(i => i.is_red_flag);

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-100 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              deviceType === 'blood_pressure' ? 'bg-[#174968] text-white' : 'bg-teal-600 text-white'
            }`}>
              {deviceType === 'blood_pressure' ? <Heart className="w-4 h-4" /> : <Droplet className="w-4 h-4" />}
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                {deviceType === 'blood_pressure' ? 'Blood Pressure Measurement' : 'Blood Glucose Measurement'}
              </h3>
              <p className="text-[11px] text-slate-400">
                Universal Multimodal Scanner & Clinical Validation
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {/* STEP 1: UPLOAD */}
          {step === 'upload' && (
            <div className="space-y-5">
              {/* Device Selector Tabs */}
              <div className="flex p-1 bg-slate-100 rounded-xl">
                <button
                  type="button"
                  onClick={() => setDeviceType('blood_pressure')}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
                    deviceType === 'blood_pressure'
                      ? 'bg-white text-[#174968] shadow-xs'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Heart className="w-3.5 h-3.5 text-rose-500" />
                  <span>Blood Pressure Monitor</span>
                </button>

                <button
                  type="button"
                  onClick={() => setDeviceType('blood_glucose')}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
                    deviceType === 'blood_glucose'
                      ? 'bg-white text-teal-800 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Droplet className="w-3.5 h-3.5 text-teal-600" />
                  <span>Blood Sugar / Glucometer</span>
                </button>
              </div>

              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
                  isDragging ? 'border-[#174968] bg-[#e4f3f6]/40' : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                }`}
              >
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-inner ${
                  deviceType === 'blood_pressure' ? 'bg-[#c7edf3] text-[#174968]' : 'bg-teal-100 text-teal-700'
                }`}>
                  <Camera className="w-8 h-8" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-700">
                    Upload or Snap {deviceType === 'blood_pressure' ? 'Monitor Screen' : 'Glucometer Screen'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    Drag and drop a photo, click to browse, or take a picture using your camera. AI will auto-extract your reading.
                  </p>
                </div>
                <div className="flex gap-2 text-xs font-semibold text-[#174968] mt-2">
                  <span className="px-3 py-1 bg-white rounded-lg border border-slate-200 shadow-2xs flex items-center gap-1">
                    <Upload className="w-3.5 h-3.5" /> Choose Photo
                  </span>
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept="image/png,image/jpeg,image/jpg,image/webp,image/heic"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-100">
                <span>
                  Supports {deviceType === 'blood_pressure' ? 'Omron, Beurer, Microlife' : 'Accu-Chek, OneTouch, Contour, FreeStyle'}.
                </span>
                <button
                  type="button"
                  onClick={() => { setStep('review'); }}
                  className="text-[#174968] font-semibold hover:underline"
                >
                  Or enter manually →
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: SCANNING */}
          {step === 'scanning' && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-20 h-20 rounded-2xl bg-[#e4f3f6] text-[#174968] flex items-center justify-center animate-pulse shadow-inner">
                  <Activity className="w-10 h-10 animate-spin text-[#174968]" />
                </div>
                <Sparkles className="w-6 h-6 text-amber-400 absolute -top-1 -right-1 animate-bounce" />
              </div>
              <div>
                <h4 className="text-base font-bold text-slate-800">Analyzing Device Display</h4>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Gemini Multimodal Vision is reading digits, checking units, and diagnosing image quality...
                </p>
              </div>
            </div>
          )}

          {/* STEP 3: REVIEW & CONTEXT */}
          {step === 'review' && (
            <div className="space-y-6">
              
              {/* Emergency Alert for Blood Pressure Crisis */}
              {deviceType === 'blood_pressure' && isBPCrisis && hasRedFlagSymptom && (
                <div className="p-4 bg-red-600 text-white rounded-2xl shadow-md flex items-start gap-3 animate-pulse">
                  <AlertTriangle className="w-6 h-6 shrink-0 mt-0.5 text-amber-300" />
                  <div className="text-xs leading-relaxed">
                    <strong className="block text-sm font-bold mb-0.5">⚠️ URGENT MEDICAL ADVISORY</strong>
                    Your reading ({systolic}/{diastolic} mmHg) is in the Hypertensive Crisis range with acute symptoms reported. Please seek emergency medical care immediately.
                  </div>
                </div>
              )}

              {/* Emergency / Action Alert for Blood Glucose */}
              {deviceType === 'blood_glucose' && glucoseStage.alert && (
                <div className={`p-4 rounded-2xl shadow-xs flex items-start gap-3 ${
                  glucoseStage.stage.includes('Hypoglycemia')
                    ? 'bg-amber-500 text-white'
                    : glucoseStage.stage.includes('Crisis')
                    ? 'bg-red-600 text-white'
                    : 'bg-amber-50 text-amber-900 border border-amber-200'
                }`}>
                  <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                  <div className="text-xs leading-relaxed font-medium">
                    {glucoseStage.alert}
                  </div>
                </div>
              )}

              {/* Reading Card */}
              <div className="bg-gradient-to-br from-slate-50 to-white rounded-2xl p-5 border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#174968] uppercase tracking-wider flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-teal-600" />
                      {deviceType === 'blood_pressure' ? 'Blood Pressure Reading' : 'Blood Glucose Reading'}
                    </span>
                    {scanResult?.device_name && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md border border-slate-200">
                        {scanResult.device_name}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {scanResult && (
                      <span className="text-[11px] font-semibold text-slate-500 bg-white px-2.5 py-1 rounded-md border border-slate-200">
                        {Math.round(scanResult.confidence * 100)}% Confidence
                      </span>
                    )}
                    {deviceType === 'blood_glucose' && (
                      <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md border ${glucoseStage.badge}`}>
                        {glucoseStage.stage}
                      </span>
                    )}
                  </div>
                </div>

                {/* BLOOD PRESSURE INPUTS */}
                {deviceType === 'blood_pressure' && (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 text-center">
                      <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-1">
                        Systolic (SYS)
                      </label>
                      <div className="flex items-baseline justify-center gap-1">
                        <input
                          type="number"
                          min="40"
                          max="300"
                          required
                          value={systolic}
                          onChange={(e) => setSystolic(parseInt(e.target.value) || 0)}
                          className="w-20 text-center text-3xl font-extrabold text-slate-800 focus:outline-none focus:text-[#174968]"
                        />
                        <span className="text-xs font-semibold text-slate-400">mmHg</span>
                      </div>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 text-center">
                      <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-1">
                        Diastolic (DIA)
                      </label>
                      <div className="flex items-baseline justify-center gap-1">
                        <input
                          type="number"
                          min="30"
                          max="200"
                          required
                          value={diastolic}
                          onChange={(e) => setDiastolic(parseInt(e.target.value) || 0)}
                          className="w-20 text-center text-3xl font-extrabold text-slate-800 focus:outline-none focus:text-[#174968]"
                        />
                        <span className="text-xs font-semibold text-slate-400">mmHg</span>
                      </div>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-slate-200 text-center">
                      <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-1">
                        Pulse (PUL)
                      </label>
                      <div className="flex items-baseline justify-center gap-1">
                        <input
                          type="number"
                          min="30"
                          max="250"
                          value={pulse}
                          onChange={(e) => setPulse(e.target.value ? parseInt(e.target.value) : '')}
                          placeholder="--"
                          className="w-16 text-center text-3xl font-extrabold text-slate-800 focus:outline-none focus:text-[#174968]"
                        />
                        <span className="text-xs font-semibold text-slate-400">bpm</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* BLOOD GLUCOSE INPUTS */}
                {deviceType === 'blood_glucose' && (
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-1">
                          Blood Sugar Reading
                        </label>
                        <div className="flex items-baseline gap-2">
                          <input
                            type="number"
                            step={glucoseUnit === 'mmol/L' ? '0.1' : '1'}
                            min={glucoseUnit === 'mmol/L' ? '0.5' : '10'}
                            max={glucoseUnit === 'mmol/L' ? '40' : '700'}
                            required
                            value={glucoseValue}
                            onChange={(e) => setGlucoseValue(e.target.value ? parseFloat(e.target.value) : '')}
                            className="w-32 text-4xl font-black text-slate-800 focus:outline-none focus:text-teal-700"
                          />
                        </div>
                      </div>

                      {/* Unit Switcher */}
                      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl self-start sm:self-center">
                        <button
                          type="button"
                          onClick={() => {
                            if (glucoseUnit !== 'mg/dL' && glucoseValue) {
                              setGlucoseValue(Math.round(Number(glucoseValue) * 18.018));
                            }
                            setGlucoseUnit('mg/dL');
                          }}
                          className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
                            glucoseUnit === 'mg/dL'
                              ? 'bg-white text-teal-800 shadow-xs'
                              : 'text-slate-500 hover:text-slate-800'
                          }`}
                        >
                          mg/dL
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (glucoseUnit !== 'mmol/L' && glucoseValue) {
                              setGlucoseValue(parseFloat((Number(glucoseValue) / 18.018).toFixed(1)));
                            }
                            setGlucoseUnit('mmol/L');
                          }}
                          className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
                            glucoseUnit === 'mmol/L'
                              ? 'bg-white text-teal-800 shadow-xs'
                              : 'text-slate-500 hover:text-slate-800'
                          }`}
                        >
                          mmol/L
                        </button>
                      </div>
                    </div>

                    {/* Meal Timing Selector */}
                    <div>
                      <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1">
                        <Utensils className="w-3.5 h-3.5" /> Meal Timing Context
                      </label>
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                        {[
                          { id: 'fasting', label: 'Fasting', icon: '🌅' },
                          { id: 'before_meal', label: 'Pre-Meal', icon: '🥗' },
                          { id: 'after_meal', label: 'Post-Meal', icon: '🍽️' },
                          { id: 'bedtime', label: 'Bedtime', icon: '🌙' },
                          { id: 'random', label: 'Random', icon: '⏱️' },
                        ].map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setMealContext(item.id as MealContext)}
                            className={`py-2 px-2.5 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition ${
                              mealContext === item.id
                                ? 'bg-teal-50 text-teal-800 border-teal-300 ring-1 ring-teal-200 shadow-2xs'
                                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                            }`}
                          >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {selectedFile && (
                  <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400">
                    <span>Scanned from: {selectedFile.name}</span>
                    <button
                      type="button"
                      onClick={() => setStep('upload')}
                      className="text-[#174968] font-semibold hover:underline flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" /> Retake / change image
                    </button>
                  </div>
                )}
              </div>

              {/* Clinical Context & Symptoms Notes */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#174968]" />
                    Symptoms, Activity, or Meals? (Optional)
                  </label>
                  <span className="text-[11px] text-slate-400">Leave blank if routine</span>
                </div>

                <div className="relative">
                  <input
                    type="text"
                    value={rawNotes}
                    onChange={(e) => setRawNotes(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleExtractNotes();
                      }
                    }}
                    placeholder={
                      deviceType === 'blood_pressure'
                        ? "e.g. 'Had slight headache, rushed before test, drank coffee'..."
                        : "e.g. 'Ate high-carb lunch 1h ago, feeling slightly shaky'..."
                    }
                    className="w-full pl-3.5 pr-28 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#174968] focus:bg-white text-slate-800 placeholder:text-slate-400 transition"
                  />
                  {rawNotes.trim() && (
                    <button
                      type="button"
                      onClick={handleExtractNotes}
                      disabled={isExtractingNotes}
                      className="absolute right-1.5 top-1.5 bottom-1.5 px-3 bg-[#174968] hover:bg-[#123952] disabled:bg-slate-200 text-white disabled:text-slate-400 text-xs font-semibold rounded-lg flex items-center gap-1 transition shadow-2xs"
                    >
                      {isExtractingNotes ? (
                        <Activity className="w-3 h-3 animate-spin" />
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3 text-teal-300" /> Preview Tags
                        </>
                      )}
                    </button>
                  )}
                </div>

                {issues.length > 0 && (
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 animate-in fade-in duration-150">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                        Detected Clinical Tags ({issues.length})
                      </span>
                      <button
                        type="button"
                        onClick={() => setIssues([])}
                        className="text-[10px] font-semibold text-slate-400 hover:text-slate-600"
                      >
                        Clear all
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {issues.map((issue) => (
                        <span
                          key={issue.tag}
                          className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border shadow-2xs ${
                            issue.is_red_flag
                              ? 'bg-red-50 text-red-700 border-red-200 font-semibold'
                              : 'bg-white text-slate-700 border-slate-200'
                          }`}
                        >
                          <span>{issue.label}</span>
                          <button
                            type="button"
                            onClick={() => removeIssue(issue.tag)}
                            className="text-slate-400 hover:text-slate-600 p-0.5"
                            title="Remove tag"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-6 py-2.5 bg-[#174968] hover:bg-[#123952] disabled:bg-slate-300 text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <Activity className="w-3.5 h-3.5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Confirm & Save Reading'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
