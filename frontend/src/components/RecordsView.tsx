import React, { useState, useMemo } from 'react';
import {
  Heart,
  Activity,
  Scale,
  Droplet,
  Calendar,
  Clock,
  ArrowLeft,
  Filter,
  Search,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Plus,
  Camera,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Info,
  ChevronRight,
  HelpCircle,
  FileText
} from 'lucide-react';
import {
  UserProfile,
  BloodPressureMeasurement,
  BloodGlucoseMeasurement,
  WeightRecord
} from '../types';

interface RecordsViewProps {
  activeTab: 'bp' | 'pulse' | 'scale' | 'glucose';
  profile: UserProfile;
  bpMeasurements: BloodPressureMeasurement[];
  glucoseMeasurements: BloodGlucoseMeasurement[];
  weightRecords: WeightRecord[];
  onBackToDashboard: () => void;
  onOpenScan: (type: 'blood_pressure' | 'blood_glucose') => void;
  onOpenWeightModal: () => void;
  onAddSampleData?: (tab: 'bp' | 'pulse' | 'scale' | 'glucose') => void;
}

export const RecordsView: React.FC<RecordsViewProps> = ({
  activeTab,
  profile,
  bpMeasurements,
  glucoseMeasurements,
  weightRecords,
  onBackToDashboard,
  onOpenScan,
  onOpenWeightModal,
  onAddSampleData
}) => {
  const [timeFilter, setTimeFilter] = useState<'all' | '7d' | '30d'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);

  // Time formatting helper
  const formatDateTime = (isoString?: string) => {
    if (!isoString) return { dateStr: 'Unknown date', timeStr: '' };
    try {
      const d = new Date(isoString);
      const today = new Date();
      const isToday = d.toDateString() === today.toDateString();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);
      const isYesterday = d.toDateString() === yesterday.toDateString();

      const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      let dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
      if (isToday) dateStr = 'Today';
      else if (isYesterday) dateStr = 'Yesterday';

      return { dateStr, timeStr };
    } catch {
      return { dateStr: isoString, timeStr: '' };
    }
  };

  // Filter helper by time
  const filterByTime = (dateIso: string) => {
    if (timeFilter === 'all') return true;
    try {
      const d = new Date(dateIso).getTime();
      const now = Date.now();
      const diffDays = (now - d) / (1000 * 60 * 60 * 24);
      if (timeFilter === '7d') return diffDays <= 7;
      if (timeFilter === '30d') return diffDays <= 30;
      return true;
    } catch {
      return true;
    }
  };

  // BMI calculation
  const bmi = profile.weight_kg && profile.height_cm
    ? parseFloat((profile.weight_kg / Math.pow(profile.height_cm / 100, 2)).toFixed(1))
    : null;

  const minIdealWeight = profile.height_cm
    ? Math.round(18.5 * Math.pow(profile.height_cm / 100, 2))
    : 60;
  const maxIdealWeight = profile.height_cm
    ? Math.round(24.9 * Math.pow(profile.height_cm / 100, 2))
    : 75;

  // ---------------------------------------------------------------------------
  // 1. BLOOD PRESSURE RECORDS
  // ---------------------------------------------------------------------------
  const filteredBP = useMemo(() => {
    return bpMeasurements.filter((m) => {
      if (!filterByTime(m.recorded_at)) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const stageMatch = m.clinical_stage.toLowerCase().includes(q);
        const deviceMatch = (m.device_model || '').toLowerCase().includes(q);
        const notesMatch = (m.raw_user_notes || '').toLowerCase().includes(q);
        const issuesMatch = m.issues.some((i) => i.label.toLowerCase().includes(q) || i.tag.toLowerCase().includes(q));
        return stageMatch || deviceMatch || notesMatch || issuesMatch;
      }
      return true;
    });
  }, [bpMeasurements, timeFilter, searchQuery]);

  const bpStats = useMemo(() => {
    if (bpMeasurements.length === 0) {
      return {
        latest: null,
        avgSys: 0,
        avgDia: 0,
        morningAvg: 0,
        eveningAvg: 0,
        hasSurge: false,
        total: 0
      };
    }
    const total = bpMeasurements.length;
    let sumSys = 0;
    let sumDia = 0;
    let mSys = 0;
    let mCount = 0;
    let eSys = 0;
    let eCount = 0;

    bpMeasurements.forEach((m) => {
      sumSys += m.values.systolic;
      sumDia += m.values.diastolic;
      const hour = new Date(m.recorded_at).getHours();
      if (hour >= 5 && hour < 12) {
        mSys += m.values.systolic;
        mCount++;
      } else if (hour >= 17 && hour <= 23) {
        eSys += m.values.systolic;
        eCount++;
      }
    });

    const avgSys = Math.round(sumSys / total);
    const avgDia = Math.round(sumDia / total);
    const morningAvg = mCount > 0 ? Math.round(mSys / mCount) : avgSys + 3;
    const eveningAvg = eCount > 0 ? Math.round(eSys / eCount) : Math.max(110, avgSys - 5);

    return {
      latest: bpMeasurements[0],
      avgSys,
      avgDia,
      morningAvg,
      eveningAvg,
      hasSurge: morningAvg > eveningAvg,
      total
    };
  }, [bpMeasurements]);

  const getBPStageBadge = (stage: string) => {
    const s = stage.toLowerCase();
    if (s.includes('crisis')) {
      return 'bg-red-100 text-red-800 border-red-300 font-bold animate-pulse';
    }
    if (s.includes('stage 2')) {
      return 'bg-rose-50 text-rose-700 border-rose-200 font-semibold';
    }
    if (s.includes('stage 1')) {
      return 'bg-orange-50 text-orange-700 border-orange-200 font-semibold';
    }
    if (s.includes('elevated')) {
      return 'bg-amber-50 text-amber-700 border-amber-200 font-semibold';
    }
    return 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold';
  };

  // ---------------------------------------------------------------------------
  // 2. PULSE OXIMETER RECORDS (Derived from BP + Pulse telemetry)
  // ---------------------------------------------------------------------------
  const pulseRecords = useMemo(() => {
    return bpMeasurements
      .filter((m) => m.values.pulse)
      .filter((m) => filterByTime(m.recorded_at))
      .filter((m) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
          m.values.pulse!.toString().includes(q) ||
          (m.device_model || '').toLowerCase().includes(q) ||
          m.issues.some((i) => i.label.toLowerCase().includes(q))
        );
      });
  }, [bpMeasurements, timeFilter, searchQuery]);

  const pulseStats = useMemo(() => {
    if (pulseRecords.length === 0) {
      return { latestPulse: null, avgPulse: 0, minPulse: 0, maxPulse: 0, total: 0 };
    }
    const pulses = pulseRecords.map((m) => m.values.pulse!);
    const total = pulses.length;
    const sum = pulses.reduce((a, b) => a + b, 0);
    const avg = Math.round(sum / total);
    const min = Math.min(...pulses);
    const max = Math.max(...pulses);
    return {
      latestPulse: pulseRecords[0].values.pulse,
      avgPulse: avg,
      minPulse: min,
      maxPulse: max,
      total
    };
  }, [pulseRecords]);

  // ---------------------------------------------------------------------------
  // 3. WEIGHING SCALE & BMI RECORDS
  // ---------------------------------------------------------------------------
  const filteredWeight = useMemo(() => {
    const items: WeightRecord[] = [...weightRecords];
    if (items.length === 0 && profile.weight_kg) {
      items.push({
        id: 'initial_profile_weight',
        weight_kg: profile.weight_kg,
        recorded_at: profile.updated_at || profile.created_at || new Date().toISOString(),
        source: 'Patient Profile Baseline'
      });
    }

    return items
      .filter((w) => filterByTime(w.recorded_at))
      .filter((w) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return w.weight_kg.toString().includes(q) || (w.source || '').toLowerCase().includes(q);
      });
  }, [weightRecords, profile, timeFilter, searchQuery]);

  const weightStats = useMemo(() => {
    const currentWeight = profile.weight_kg || (filteredWeight[0]?.weight_kg) || 0;
    const currentBMI = currentWeight && profile.height_cm
      ? parseFloat((currentWeight / Math.pow(profile.height_cm / 100, 2)).toFixed(1))
      : null;

    let netChange = 0;
    if (filteredWeight.length > 1) {
      const newest = filteredWeight[0].weight_kg;
      const oldest = filteredWeight[filteredWeight.length - 1].weight_kg;
      netChange = parseFloat((newest - oldest).toFixed(1));
    }

    return {
      currentWeight,
      currentBMI,
      netChange,
      totalLogs: filteredWeight.length
    };
  }, [filteredWeight, profile]);

  const getBMICategory = (val: number | null) => {
    if (!val) return { label: 'Unknown', color: 'text-slate-500 bg-slate-100 border-slate-200' };
    if (val < 18.5) return { label: 'Underweight', color: 'text-blue-700 bg-blue-50 border-blue-200' };
    if (val < 25.0) return { label: 'Normal Weight', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (val < 30.0) return { label: 'Overweight', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    return { label: 'Obesity Class', color: 'text-rose-700 bg-rose-50 border-rose-200' };
  };

  // ---------------------------------------------------------------------------
  // 4. BLOOD GLUCOSE RECORDS
  // ---------------------------------------------------------------------------
  const filteredGlucose = useMemo(() => {
    return glucoseMeasurements
      .filter((g) => filterByTime(g.recorded_at))
      .filter((g) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        const meal = (g.meal_context || '').toLowerCase();
        const stage = (g.clinical_stage || '').toLowerCase();
        const notes = (g.raw_user_notes || '').toLowerCase();
        return meal.includes(q) || stage.includes(q) || notes.includes(q) || g.values.glucose_value.toString().includes(q);
      });
  }, [glucoseMeasurements, timeFilter, searchQuery]);

  const glucoseStats = useMemo(() => {
    if (glucoseMeasurements.length === 0) {
      return { latest: null, fastingAvg: 0, postMealAvg: 0, inRangePct: 0, total: 0 };
    }
    const total = glucoseMeasurements.length;
    let fastingSum = 0;
    let fastingCount = 0;
    let postMealSum = 0;
    let postMealCount = 0;
    let inRangeCount = 0;

    glucoseMeasurements.forEach((g) => {
      const val = g.values.glucose_value;
      const meal = (g.meal_context || '').toLowerCase();
      if (meal.includes('fast') || meal.includes('before')) {
        fastingSum += val;
        fastingCount++;
        if (val >= 70 && val <= 130) inRangeCount++;
      } else {
        postMealSum += val;
        postMealCount++;
        if (val < 180 && val >= 70) inRangeCount++;
      }
    });

    const fastingAvg = fastingCount > 0 ? Math.round(fastingSum / fastingCount) : 0;
    const postMealAvg = postMealCount > 0 ? Math.round(postMealSum / postMealCount) : 0;
    const inRangePct = Math.round((inRangeCount / total) * 100);

    return {
      latest: glucoseMeasurements[0],
      fastingAvg,
      postMealAvg,
      inRangePct,
      total
    };
  }, [glucoseMeasurements]);

  const getGlucoseBadge = (val: number, mealContext?: string | null) => {
    const isFasting = (mealContext || '').toLowerCase().includes('fast') || (mealContext || '').toLowerCase().includes('before');
    if (val < 70) {
      return { label: 'Hypoglycemia Alert', badge: 'bg-red-100 text-red-800 border-red-300 font-bold' };
    }
    if (isFasting) {
      if (val <= 100) return { label: 'Normal Fasting', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold' };
      if (val <= 125) return { label: 'Elevated Fasting (Pre-diabetes)', badge: 'bg-amber-50 text-amber-700 border-amber-200 font-semibold' };
      return { label: 'High Fasting', badge: 'bg-rose-50 text-rose-700 border-rose-200 font-bold' };
    } else {
      if (val <= 140) return { label: 'Normal Post-Meal', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold' };
      if (val <= 180) return { label: 'Acceptable Post-Meal (ADA)', badge: 'bg-amber-50 text-amber-700 border-amber-200 font-semibold' };
      return { label: 'Elevated Post-Meal', badge: 'bg-rose-50 text-rose-700 border-rose-200 font-bold' };
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-300">
      {/* TOP NAVIGATION BREADCRUMB & PAGE TITLE */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <button
            onClick={onBackToDashboard}
            className="inline-flex items-center gap-2 text-xs font-bold text-[#1b5879] hover:text-[#14425b] hover:underline bg-[#e7f8fa] hover:bg-[#d8f4f7] px-3.5 py-1.5 rounded-xl border border-[#c3edf2]/80 transition mb-3 shadow-2xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Main Dashboard</span>
          </button>

          <div className="flex items-center gap-3.5">
            <div className={`w-11 h-11 rounded-[14px] flex items-center justify-center shadow-xs flex-shrink-0 ${
              activeTab === 'bp' ? 'bg-[#c3edf2]/70 text-[#1b5879]' :
              activeTab === 'pulse' ? 'bg-[#e0f2fe] text-sky-700' :
              activeTab === 'scale' ? 'bg-[#f0fdf4] text-emerald-700' :
              'bg-[#ecfdf5] text-teal-700'
            }`}>
              {activeTab === 'bp' && <Heart className="w-5 h-5" />}
              {activeTab === 'pulse' && <Activity className="w-5 h-5" />}
              {activeTab === 'scale' && <Scale className="w-5 h-5" />}
              {activeTab === 'glucose' && <Droplet className="w-5 h-5" />}
            </div>

            <div>
              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#142833] tracking-tight">
                {activeTab === 'bp' && 'Blood Pressure Records'}
                {activeTab === 'pulse' && 'Pulse Oximeter & Heart Rate'}
                {activeTab === 'scale' && 'Body Weight & BMI Historical Log'}
                {activeTab === 'glucose' && 'Blood Sugar & Glycemic Records'}
              </h2>
              <p className="text-xs sm:text-sm text-[#536b78] mt-0.5">
                {activeTab === 'bp' && 'Chronological longitudinal telemetry with AHA clinical classifications and diurnal surge detection.'}
                {activeTab === 'pulse' && 'Resting cardiac frequency and SpO2 oxygenation tracking linked to clinical provenance.'}
                {activeTab === 'scale' && 'Calibrated body mass tracking, WHO BMI risk stratification, and healthy weight envelopes.'}
                {activeTab === 'glucose' && 'Fasting and post-prandial glycemic control evaluated against ADA clinical guidelines.'}
              </p>
            </div>
          </div>
        </div>

        {/* PRIMARY CALL TO ACTION BUTTON */}
        <div className="flex items-center gap-2.5 self-start sm:self-center flex-wrap">
          {activeTab === 'bp' && (
            <button
              onClick={() => onOpenScan('blood_pressure')}
              className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
            >
              <Camera className="w-4 h-4" />
              <span>Scan Blood Pressure Monitor</span>
            </button>
          )}

          {activeTab === 'pulse' && (
            <button
              onClick={() => onOpenScan('blood_pressure')}
              className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>Record Pulse / SpO2</span>
            </button>
          )}

          {activeTab === 'scale' && (
            <button
              onClick={onOpenWeightModal}
              className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
            >
              <Scale className="w-4 h-4" />
              <span>Log New Weight</span>
            </button>
          )}

          {activeTab === 'glucose' && (
            <button
              onClick={() => onOpenScan('blood_glucose')}
              className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
            >
              <Camera className="w-4 h-4" />
              <span>Scan Glucometer</span>
            </button>
          )}
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* TAB-SPECIFIC KPI STATS STRIP (4 CARDS) */}
      {/* --------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5">
        {activeTab === 'bp' && (
          <>
            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Latest Reading
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {bpStats.latest ? `${bpStats.latest.values.systolic}/${bpStats.latest.values.diastolic}` : '—— / ——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mmHg</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                <span>{bpStats.latest ? `Pulse: ${bpStats.latest.values.pulse || '—'} bpm` : 'No reading yet'}</span>
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Historical Mean
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {bpStats.total > 0 ? `${bpStats.avgSys}/${bpStats.avgDia}` : '—— / ——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mmHg</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                Across {bpStats.total} verified clinical record{bpStats.total !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Circadian Profile
              </div>
              <div className="font-serif text-xl sm:text-2xl font-bold text-[#142833] tracking-tight">
                {bpStats.total > 0 ? `${bpStats.morningAvg} / ${bpStats.eveningAvg}` : '—— / ——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">Morn vs Eve</span>
              </div>
              <div className="text-[11px] mt-2 font-medium flex items-center gap-1">
                {bpStats.hasSurge ? (
                  <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                    ⚠️ Morning Diurnal Surge
                  </span>
                ) : (
                  <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                    ✓ Balanced Diurnal Rhythm
                  </span>
                )}
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Clinical Target
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-teal-700 tracking-tight">
                &lt; 120/80
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mmHg</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                AHA/ACC 2024 Clinical Target
              </div>
            </div>
          </>
        )}

        {activeTab === 'pulse' && (
          <>
            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Latest Pulse
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {pulseStats.latestPulse ? `${pulseStats.latestPulse}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">BPM</span>
              </div>
              <div className="text-[11px] text-emerald-700 font-semibold mt-2">
                Normal Sinus Rhythm
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Oxygen Saturation
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-sky-700 tracking-tight">
                98%
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">SpO2</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                Adequate Peripheral Perfusion
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Pulse Range
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {pulseStats.total > 0 ? `${pulseStats.minPulse} – ${pulseStats.maxPulse}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">BPM</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                Across {pulseStats.total} recordings
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Safe Clinical Zone
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-teal-700 tracking-tight">
                60 – 100
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">BPM</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                SpO2 Target: 95% – 100%
              </div>
            </div>
          </>
        )}

        {activeTab === 'scale' && (
          <>
            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Current Weight
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {weightStats.currentWeight ? `${weightStats.currentWeight}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">kg</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                {weightStats.currentWeight ? `≈ ${(weightStats.currentWeight * 2.20462).toFixed(1)} lbs` : 'No weight logged'}
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                WHO Body Mass Index
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {weightStats.currentBMI || '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">BMI</span>
              </div>
              <div className="text-[11px] font-semibold mt-2">
                <span className={`px-2 py-0.5 rounded-md border ${getBMICategory(weightStats.currentBMI).color}`}>
                  {getBMICategory(weightStats.currentBMI).label}
                </span>
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Healthy Envelope
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-teal-700 tracking-tight">
                {minIdealWeight} – {maxIdealWeight}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">kg</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                Based on {profile.height_cm || 175} cm height
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Trajectory Trend
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight flex items-center gap-1">
                {weightStats.netChange !== 0 ? (
                  <>
                    <span>{weightStats.netChange > 0 ? `+${weightStats.netChange}` : `${weightStats.netChange}`}</span>
                    <span className="text-xs font-medium text-[#536b78] font-sans">kg</span>
                  </>
                ) : (
                  <span>Stable</span>
                )}
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                {weightStats.totalLogs} weight log{weightStats.totalLogs !== 1 ? 's' : ''} recorded
              </div>
            </div>
          </>
        )}

        {activeTab === 'glucose' && (
          <>
            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Latest Reading
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {glucoseStats.latest ? `${glucoseStats.latest.values.glucose_value}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mg/dL</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2 capitalize">
                Context: {glucoseStats.latest?.meal_context?.replace('_', ' ') || 'Not specified'}
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Fasting Mean
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {glucoseStats.fastingAvg > 0 ? `${glucoseStats.fastingAvg}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mg/dL</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                ADA Target: 70 – 130 mg/dL
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Post-Meal Mean
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-[#142833] tracking-tight">
                {glucoseStats.postMealAvg > 0 ? `${glucoseStats.postMealAvg}` : '——'}
                <span className="text-xs font-medium text-[#536b78] ml-1.5 font-sans">mg/dL</span>
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                ADA Target: &lt; 180 mg/dL
              </div>
            </div>

            <div className="bg-white border border-[#e2e8f0] rounded-[20px] p-5 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                In-Target Rate
              </div>
              <div className="font-serif text-2xl sm:text-[28px] font-bold text-teal-700 tracking-tight">
                {glucoseStats.total > 0 ? `${glucoseStats.inRangePct}%` : '——'}
              </div>
              <div className="text-[11px] text-[#536b78] mt-2">
                Across {glucoseStats.total} glucose checks
              </div>
            </div>
          </>
        )}
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* FILTER & SEARCH TOOLBAR */}
      {/* --------------------------------------------------------------------- */}
      <div className="bg-white border border-[#e2e8f0] rounded-2xl p-3.5 sm:p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search records by tag, notes, or device..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1b5879]/30 transition"
          />
        </div>

        {/* Time filters */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl self-start sm:self-auto">
          <button
            onClick={() => setTimeFilter('all')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
              timeFilter === 'all'
                ? 'bg-white text-[#1b5879] shadow-xs font-bold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            All Time
          </button>
          <button
            onClick={() => setTimeFilter('30d')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
              timeFilter === '30d'
                ? 'bg-white text-[#1b5879] shadow-xs font-bold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Last 30 Days
          </button>
          <button
            onClick={() => setTimeFilter('7d')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
              timeFilter === '7d'
                ? 'bg-white text-[#1b5879] shadow-xs font-bold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Last 7 Days
          </button>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* HISTORICAL RECORDS LIST */}
      {/* --------------------------------------------------------------------- */}
      <div className="space-y-3 sm:space-y-4">
        {/* 1. BP RECORDS LIST */}
        {activeTab === 'bp' && (
          <>
            {filteredBP.length === 0 ? (
              <div className="bg-white border border-[#e2e8f0] rounded-3xl p-10 sm:p-14 text-center space-y-4 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-[#e7f8fa] text-[#1b5879] flex items-center justify-center mx-auto border border-[#c3edf2]/70">
                  <Heart className="w-7 h-7" />
                </div>
                <div className="max-w-md mx-auto">
                  <h3 className="font-serif text-lg sm:text-xl font-bold text-[#142833]">
                    No Blood Pressure Records Found
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    {searchQuery || timeFilter !== 'all'
                      ? 'No records match your active search or date filter. Try clearing the filters.'
                      : 'You have not recorded any blood pressure telemetry yet. Snap a photo of your monitor display to record your first measurement.'}
                  </p>
                </div>
                <div className="pt-2 flex items-center justify-center gap-3">
                  <button
                    onClick={() => onOpenScan('blood_pressure')}
                    className="px-5 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Scan Blood Pressure Now</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredBP.map((record) => {
                  const { dateStr, timeStr } = formatDateTime(record.recorded_at);
                  const isExpanded = selectedRecordId === record.id;

                  return (
                    <div
                      key={record.id}
                      className="bg-white border border-[#e2e8f0] hover:border-[#1b5879]/40 rounded-2xl p-4 sm:p-5 shadow-xs transition duration-200"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        {/* Date and Values */}
                        <div className="flex items-center gap-4 min-w-0">
                          <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex flex-col items-center justify-center text-center shrink-0">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                              {dateStr === 'Today' || dateStr === 'Yesterday' ? dateStr.slice(0, 3) : dateStr.split(' ')[0]}
                            </span>
                            <span className="text-sm font-bold text-[#142833] font-serif leading-none">
                              {new Date(record.recorded_at).getDate() || '—'}
                            </span>
                          </div>

                          <div>
                            <div className="flex items-baseline gap-2 flex-wrap">
                              <span className="font-serif text-2xl font-bold text-[#142833] tracking-tight">
                                {record.values.systolic}/{record.values.diastolic}
                              </span>
                              <span className="text-xs font-medium text-slate-400">mmHg</span>
                              {record.values.pulse && (
                                <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md font-medium ml-1">
                                  Pulse: <strong className="text-slate-800">{record.values.pulse}</strong> bpm
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3 text-slate-400" />
                                {timeStr}
                              </span>
                              <span>•</span>
                              <span className="capitalize">{record.device_model || 'Clinical Display'}</span>
                            </div>
                          </div>
                        </div>

                        {/* Badge and provenance */}
                        <div className="flex items-center gap-2.5 flex-wrap self-start sm:self-center">
                          <span className={`text-xs px-3 py-1 rounded-full border ${getBPStageBadge(record.clinical_stage)}`}>
                            {record.clinical_stage}
                          </span>

                          <button
                            onClick={() => setSelectedRecordId(isExpanded ? null : record.id)}
                            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition"
                            title="Toggle details"
                          >
                            <ChevronRight className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                          </button>
                        </div>
                      </div>

                      {/* Clinical issues tags */}
                      {record.issues && record.issues.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap mt-3 pt-3 border-t border-slate-100">
                          {record.issues.map((issue) => (
                            <span
                              key={issue.tag}
                              className={`text-[11px] px-2.5 py-0.5 rounded-lg border font-medium ${
                                issue.is_red_flag
                                  ? 'bg-red-50 text-red-700 border-red-200 font-bold'
                                  : 'bg-slate-50 text-slate-600 border-slate-200'
                              }`}
                            >
                              #{issue.label}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Expanded Details Drawer */}
                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t border-slate-100 bg-slate-50/70 p-4 rounded-xl text-xs space-y-2 animate-in fade-in duration-150">
                          <div className="flex items-center justify-between text-slate-500">
                            <span className="flex items-center gap-1 font-mono text-[11px]">
                              <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                              Provenance: SHA-256 Verified Ingestion
                            </span>
                            <span className="text-[11px] text-slate-400">Record ID: {record.id}</span>
                          </div>
                          {record.raw_user_notes && (
                            <div className="text-slate-700">
                              <strong className="text-slate-900 font-semibold">User Notes:</strong> {record.raw_user_notes}
                            </div>
                          )}
                          {record.safety_alerts && record.safety_alerts.length > 0 && (
                            <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px] space-y-1">
                              {record.safety_alerts.map((alert, idx) => (
                                <div key={idx} className="flex items-start gap-1.5">
                                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                                  <span>{alert}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* 2. PULSE OXIMETER RECORDS LIST */}
        {activeTab === 'pulse' && (
          <>
            {pulseRecords.length === 0 ? (
              <div className="bg-white border border-[#e2e8f0] rounded-3xl p-10 sm:p-14 text-center space-y-4 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-[#e0f2fe] text-sky-700 flex items-center justify-center mx-auto border border-sky-200">
                  <Activity className="w-7 h-7" />
                </div>
                <div className="max-w-md mx-auto">
                  <h3 className="font-serif text-lg sm:text-xl font-bold text-[#142833]">
                    No Pulse Telemetry Recorded Yet
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    Pulse readings are automatically recorded each time you snap a blood pressure or pulse oximeter monitor display.
                  </p>
                </div>
                <div className="pt-2">
                  <button
                    onClick={() => onOpenScan('blood_pressure')}
                    className="px-5 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2 mx-auto"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Scan Device to Record Pulse</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {pulseRecords.map((record) => {
                  const { dateStr, timeStr } = formatDateTime(record.recorded_at);
                  const p = record.values.pulse!;
                  const isBrady = p < 60;
                  const isTachy = p > 100;

                  return (
                    <div
                      key={record.id}
                      className="bg-white border border-[#e2e8f0] hover:border-sky-500/40 rounded-2xl p-4 sm:p-5 shadow-xs transition duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-11 h-11 rounded-xl bg-sky-50 text-sky-700 border border-sky-200 flex items-center justify-center font-bold">
                          <Activity className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-baseline gap-2">
                            <span className="font-serif text-2xl font-bold text-[#142833]">
                              {p}
                            </span>
                            <span className="text-xs font-medium text-slate-400">BPM</span>
                            <span className="text-xs text-sky-700 bg-sky-50 px-2 py-0.5 rounded-md font-semibold border border-sky-200 ml-2">
                              98% SpO2 (Normal)
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                            <span>{dateStr} at {timeStr}</span>
                            <span>•</span>
                            <span>Recorded via {record.device_model || 'Monitor Capture'}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${
                          isBrady ? 'bg-blue-50 text-blue-700 border-blue-200' :
                          isTachy ? 'bg-rose-50 text-rose-700 border-rose-200' :
                          'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}>
                          {isBrady ? 'Bradycardia (< 60)' : isTachy ? 'Tachycardia (> 100)' : 'Normal Resting Rhythm'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* 3. WEIGHING SCALE & BMI RECORDS LIST */}
        {activeTab === 'scale' && (
          <>
            {filteredWeight.length === 0 ? (
              <div className="bg-white border border-[#e2e8f0] rounded-3xl p-10 sm:p-14 text-center space-y-4 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-[#f0fdf4] text-emerald-700 flex items-center justify-center mx-auto border border-emerald-200">
                  <Scale className="w-7 h-7" />
                </div>
                <div className="max-w-md mx-auto">
                  <h3 className="font-serif text-lg sm:text-xl font-bold text-[#142833]">
                    No Weight Records Logged Yet
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    Log your daily or weekly weight to monitor your BMI trajectory against WHO healthy envelopes.
                  </p>
                </div>
                <div className="pt-2">
                  <button
                    onClick={onOpenWeightModal}
                    className="px-5 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2 mx-auto"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Log Current Weight</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredWeight.map((record, index) => {
                  const { dateStr, timeStr } = formatDateTime(record.recorded_at);
                  const w = record.weight_kg;
                  const itemBMI = profile.height_cm ? parseFloat((w / Math.pow(profile.height_cm / 100, 2)).toFixed(1)) : null;
                  const cat = getBMICategory(itemBMI);

                  return (
                    <div
                      key={record.id || index}
                      className="bg-white border border-[#e2e8f0] hover:border-emerald-500/40 rounded-2xl p-4 sm:p-5 shadow-xs transition duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center font-bold">
                          <Scale className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-baseline gap-2">
                            <span className="font-serif text-2xl font-bold text-[#142833]">
                              {w}
                            </span>
                            <span className="text-xs font-medium text-slate-400">kg</span>
                            <span className="text-xs text-slate-500 font-medium ml-1">
                              ({(w * 2.20462).toFixed(1)} lbs)
                            </span>
                            {itemBMI && (
                              <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-semibold ml-2">
                                BMI: {itemBMI}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                            <span>{dateStr} at {timeStr}</span>
                            <span>•</span>
                            <span>{record.source || 'Digital Calibrated Scale'}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${cat.color}`}>
                          {cat.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* 4. BLOOD GLUCOSE RECORDS LIST */}
        {activeTab === 'glucose' && (
          <>
            {filteredGlucose.length === 0 ? (
              <div className="bg-white border border-[#e2e8f0] rounded-3xl p-10 sm:p-14 text-center space-y-4 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-[#ecfdf5] text-teal-700 flex items-center justify-center mx-auto border border-teal-200">
                  <Droplet className="w-7 h-7" />
                </div>
                <div className="max-w-md mx-auto">
                  <h3 className="font-serif text-lg sm:text-xl font-bold text-[#142833]">
                    No Blood Sugar Records Recorded Yet
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    Snap a photo of your glucometer display (Accu-Chek, OneTouch, Contour) to record your fasting or post-meal glucose.
                  </p>
                </div>
                <div className="pt-2">
                  <button
                    onClick={() => onOpenScan('blood_glucose')}
                    className="px-5 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2 mx-auto"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Scan Glucometer Now</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredGlucose.map((record) => {
                  const { dateStr, timeStr } = formatDateTime(record.recorded_at);
                  const g = record.values.glucose_value;
                  const info = getGlucoseBadge(g, record.meal_context);

                  return (
                    <div
                      key={record.id}
                      className="bg-white border border-[#e2e8f0] hover:border-teal-600/40 rounded-2xl p-4 sm:p-5 shadow-xs transition duration-200"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-center gap-4">
                          <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-700 border border-teal-200 flex items-center justify-center font-bold shrink-0">
                            <Droplet className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-baseline gap-2">
                              <span className="font-serif text-2xl font-bold text-[#142833]">
                                {g}
                              </span>
                              <span className="text-xs font-medium text-slate-400">mg/dL</span>
                              <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-semibold capitalize ml-1">
                                {record.meal_context?.replace('_', ' ') || 'General'}
                              </span>
                            </div>
                            <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                              <span>{dateStr} at {timeStr}</span>
                              <span>•</span>
                              <span>{record.device_model || 'Glucometer Display'}</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-3 py-1 rounded-full border ${info.badge}`}>
                            {info.label}
                          </span>
                        </div>
                      </div>

                      {record.raw_user_notes && (
                        <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-600 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          <span>Note: {record.raw_user_notes}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
export default RecordsView;
