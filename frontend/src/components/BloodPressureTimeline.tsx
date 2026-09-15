import React, { useState } from 'react';
import {
  Heart,
  TrendingUp,
  Calendar,
  AlertTriangle,
  Camera,
  FileEdit,
  ChevronDown,
  ChevronUp,
  PlusCircle
} from 'lucide-react';
import { BloodPressureMeasurement } from '../types';

interface BloodPressureTimelineProps {
  measurements: BloodPressureMeasurement[];
  onAddNew: () => void;
}

export function BloodPressureTimeline({ measurements, onAddNew }: BloodPressureTimelineProps) {
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
      case 'Hypertension Stage 1':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'Hypertension Stage 2':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Hypertensive Crisis':
        return 'bg-red-100 text-red-800 border-red-300 font-bold animate-pulse';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
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
      <div className="py-12 px-4 border-2 border-dashed border-slate-200 rounded-2xl text-center flex flex-col items-center">
        <div className="w-14 h-14 bg-[#e4f3f6] text-[#174968] rounded-2xl flex items-center justify-center mb-3">
          <Camera className="w-7 h-7" />
        </div>
        <h4 className="text-base font-semibold text-slate-700">No blood pressure readings recorded yet</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Take a photo of your blood pressure cuff or upload a screenshot to start tracking your clinical trends.
        </p>
        <button
          onClick={onAddNew}
          className="px-4 py-2 bg-[#174968] hover:bg-[#123952] text-white text-xs font-semibold rounded-xl flex items-center gap-2 transition shadow-xs"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Add First Reading</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Logged Readings ({measurements.length})
          </span>
        </div>
        <button
          onClick={onAddNew}
          className="text-xs font-bold text-[#174968] hover:underline flex items-center gap-1"
        >
          <PlusCircle className="w-3.5 h-3.5" /> Log Another
        </button>
      </div>

      <div className="space-y-3">
        {measurements.map((m) => {
          const isExpanded = expandedId === m.id;
          const stageColor = getStageBadgeColor(m.clinical_stage);

          return (
            <div
              key={m.id}
              className="bg-white rounded-2xl p-4 border border-slate-200 shadow-2xs hover:shadow-xs transition"
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-[#174968]">
                    <Heart className="w-5 h-5 text-rose-500 fill-rose-100" />
                  </div>
                  <div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-black text-slate-800 tracking-tight">
                        {m.values.systolic} / {m.values.diastolic}
                      </span>
                      <span className="text-xs font-semibold text-slate-400">mmHg</span>
                      {m.values.pulse && (
                        <span className="text-xs text-slate-500 font-medium ml-2">
                          • {m.values.pulse} bpm
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(m.recorded_at)}
                      </span>
                      <span>•</span>
                      <span className="capitalize flex items-center gap-1">
                        {m.source === 'camera' ? <Camera className="w-3 h-3" /> : <FileEdit className="w-3 h-3" />}
                        {m.source}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-center">
                  <span className={`text-[11px] px-2.5 py-1 rounded-lg border font-semibold ${stageColor}`}>
                    {m.clinical_stage}
                  </span>
                  {(m.raw_user_notes || m.safety_alerts.length > 0) && (
                    <button
                      onClick={() => toggleExpand(m.id)}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded-md hover:bg-slate-50 transition"
                      title="View Details"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  )}
                </div>
              </div>

              {/* Context Tag Chips */}
              {m.issues && m.issues.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5 pt-2.5 border-t border-slate-100">
                  {m.issues.map((issue) => (
                    <span
                      key={issue.tag}
                      className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md font-medium border ${
                        issue.is_red_flag
                          ? 'bg-red-50 text-red-700 border-red-200'
                          : 'bg-slate-50 text-slate-600 border-slate-200'
                      }`}
                    >
                      {issue.label}
                    </span>
                  ))}
                </div>
              )}

              {/* Expandable Details (Safety Alerts & Raw Notes) */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-100 text-xs space-y-2 animate-in fade-in duration-150">
                  {m.safety_alerts && m.safety_alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 flex items-start gap-2 text-xs"
                    >
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <div>{alert}</div>
                    </div>
                  ))}

                  {m.raw_user_notes && (
                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-slate-600">
                      <strong className="block text-[10px] uppercase font-bold text-slate-400 mb-0.5">
                        Patient Note:
                      </strong>
                      "{m.raw_user_notes}"
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
