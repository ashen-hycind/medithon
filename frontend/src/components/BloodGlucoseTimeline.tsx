import React, { useState } from 'react';
import {
  Droplet,
  TrendingUp,
  Calendar,
  AlertTriangle,
  Camera,
  ChevronDown,
  ChevronUp,
  PlusCircle,
  Utensils,
  Clock,
  Sparkles
} from 'lucide-react';
import { BloodGlucoseMeasurement } from '../types';

interface BloodGlucoseTimelineProps {
  measurements: BloodGlucoseMeasurement[];
  onAddNew: () => void;
}

export function BloodGlucoseTimeline({ measurements, onAddNew }: BloodGlucoseTimelineProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  const getStageBadgeColor = (stage: string) => {
    switch (stage) {
      case 'Normal':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'Elevated':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Hypoglycemia Alert':
        return 'bg-orange-50 text-orange-700 border-orange-200 font-semibold';
      case 'Severe Hypoglycemia':
        return 'bg-red-100 text-red-800 border-red-300 font-bold animate-pulse';
      case 'Hyperglycemia':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Hyperglycemic Crisis':
        return 'bg-red-100 text-red-800 border-red-300 font-bold animate-pulse';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getMealBadge = (mealContext?: string | null) => {
    switch (mealContext) {
      case 'fasting':
        return { label: 'Fasting', icon: '🌅', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
      case 'before_meal':
        return { label: 'Pre-Meal', icon: '🥗', color: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'after_meal':
      case 'post_meal':
        return { label: 'Post-Meal', icon: '🍽️', color: 'bg-purple-50 text-purple-700 border-purple-200' };
      case 'bedtime':
        return { label: 'Bedtime', icon: '🌙', color: 'bg-slate-100 text-slate-700 border-slate-200' };
      case 'random':
        return { label: 'Random', icon: '⏱️', color: 'bg-slate-50 text-slate-600 border-slate-200' };
      default:
        return { label: 'General', icon: '💧', color: 'bg-slate-50 text-slate-600 border-slate-200' };
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  if (measurements.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center shadow-xs">
        <div className="w-16 h-16 bg-[#e7f8fa] text-[#1b5879] rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-inner">
          <Droplet className="w-8 h-8" />
        </div>
        <h3 className="text-base font-bold text-slate-800">No Blood Glucose Readings Yet</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1.5 mb-6">
          Snap a photo of your glucometer display (Accu-Chek, OneTouch, Contour) or enter your reading manually to track fasting and postprandial trends.
        </p>
        <button
          onClick={onAddNew}
          className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-semibold rounded-xl inline-flex items-center gap-2 transition shadow-sm"
        >
          <Camera className="w-4 h-4" />
          <span>Scan Glucometer</span>
        </button>
      </div>
    );
  }

  // Calculate quick average
  const mgdlReadings = measurements.map(m => 
    m.values.unit === 'mmol/L' ? m.values.glucose_value * 18.018 : m.values.glucose_value
  );
  const avgMgdl = Math.round(mgdlReadings.reduce((a, b) => a + b, 0) / mgdlReadings.length);

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Average Glucose</h4>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-extrabold text-slate-800">{avgMgdl}</span>
              <span className="text-xs font-semibold text-slate-500">mg/dL</span>
              <span className="text-[11px] text-slate-400 ml-2">({measurements.length} logged)</span>
            </div>
          </div>
        </div>

        <button
          onClick={onAddNew}
          className="px-3.5 py-2 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow-2xs"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Reading</span>
        </button>
      </div>

      {/* Timeline List */}
      <div className="space-y-3">
        {measurements.map((m) => {
          const isExpanded = expandedId === m.id;
          const mealInfo = getMealBadge(m.meal_context || m.values.meal_context);

          return (
            <div
              key={m.id}
              className={`bg-white rounded-2xl border transition shadow-xs ${
                m.has_red_flags ? 'border-red-300 ring-1 ring-red-200' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div
                onClick={() => toggleExpand(m.id)}
                className="p-4 sm:p-5 flex items-center justify-between cursor-pointer select-none"
              >
                <div className="flex items-center gap-3.5">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                    m.clinical_stage.includes('Hypoglycemia') 
                      ? 'bg-orange-100 text-orange-700' 
                      : m.clinical_stage.includes('Hyper') 
                      ? 'bg-rose-100 text-rose-700' 
                      : 'bg-[#e7f8fa] text-[#1b5879]'
                  }`}>
                    <Droplet className="w-5 h-5" />
                  </div>

                  <div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-xl sm:text-2xl font-black text-slate-900">
                        {m.values.glucose_value}
                      </span>
                      <span className="text-xs font-bold text-slate-500">
                        {m.values.unit || m.units?.glucose || 'mg/dL'}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(m.recorded_at)}</span>
                      {m.device_model && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-[130px]">{m.device_model}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:gap-3">
                  {/* Meal Badge */}
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border hidden sm:inline-flex items-center gap-1 ${mealInfo.color}`}>
                    <span>{mealInfo.icon}</span>
                    <span>{mealInfo.label}</span>
                  </span>

                  {/* Stage Badge */}
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg border ${getStageBadgeColor(m.clinical_stage)}`}>
                    {m.clinical_stage}
                  </span>

                  <button
                    type="button"
                    className="text-slate-400 hover:text-slate-600 p-1"
                    aria-label="Toggle details"
                  >
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Collapsible Details Panel */}
              {isExpanded && (
                <div className="px-5 pb-5 pt-2 border-t border-slate-100 space-y-3 bg-slate-50/50 rounded-b-2xl text-xs">
                  {/* Safety Alerts */}
                  {m.safety_alerts && m.safety_alerts.length > 0 && (
                    <div className="space-y-1.5">
                      {m.safety_alerts.map((alert, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 flex items-start gap-2 text-xs leading-relaxed"
                        >
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                          <span>{alert}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* User Notes */}
                  {m.raw_user_notes && (
                    <div>
                      <span className="font-semibold text-slate-500 block mb-0.5">Reported Context:</span>
                      <p className="text-slate-700 italic bg-white p-2.5 rounded-xl border border-slate-200">
                        "{m.raw_user_notes}"
                      </p>
                    </div>
                  )}

                  {/* Extracted Clinical Tags */}
                  {m.issues && m.issues.length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-500 block mb-1.5">Associated Factors:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {m.issues.map((issue, idx) => (
                          <span
                            key={idx}
                            className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                              issue.is_red_flag
                                ? 'bg-red-50 text-red-700 border-red-200'
                                : 'bg-white text-slate-700 border-slate-200'
                            }`}
                          >
                            {issue.label}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Source Metadata */}
                  <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1">
                    <span>Source: {m.source === 'camera' ? 'Camera OCR' : m.source === 'screenshot' ? 'Screenshot' : 'Manual Entry'}</span>
                    {m.scan_id && <span>Scan ID: {m.scan_id}</span>}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
