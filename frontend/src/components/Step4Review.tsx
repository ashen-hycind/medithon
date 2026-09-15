import React from 'react';
import { BloodGroupType, SexType } from '../types';

interface Props {
  dob: string;
  currentAge: number;
  sex: SexType;
  bloodGroup: BloodGroupType;
  heightCm: number;
  weightKg: number;
  bmi: number;
  bmiInfo: { label: string };
  activityLevel: number;
  activityLabel: string;
  occupation: string;
  isPregnant: boolean;
  gestationalWeeks: number;
  trimesterLabel: string;
  loading: boolean;
  onEditStep: (step: 1 | 2 | 3) => void;
  onBack: () => void;
  onSubmit: () => void;
}

export const Step4Review: React.FC<Props> = ({
  dob,
  currentAge,
  sex,
  bloodGroup,
  heightCm,
  weightKg,
  bmi,
  bmiInfo,
  activityLevel,
  activityLabel,
  occupation,
  isPregnant,
  gestationalWeeks,
  trimesterLabel,
  loading,
  onEditStep,
  onBack,
  onSubmit
}) => {
  // Format DOB nicely if possible (e.g. 28 May 2007)
  const formatDob = (dobStr: string) => {
    try {
      const d = new Date(dobStr);
      if (isNaN(d.getTime())) return dobStr;
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return dobStr;
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-white rounded-[24px] p-8 sm:p-10 shadow-[0_4px_30px_rgba(0,0,0,0.06)] border border-[#edf2f4]">
      {/* Header */}
      <div className="text-center mb-8">
        <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#6b855d] bg-[#f0f6ee] px-2.5 py-1 rounded">
          FINAL VERIFICATION
        </span>
        <h2 className="font-serif text-[32px] font-bold text-[#1b5879] tracking-tight mt-2">
          Review Your Health Profile
        </h2>
        <p className="text-[13px] text-slate-500 mt-1">
          Confirm your baseline parameters. You can click Edit on any row to change values before saving.
        </p>
      </div>

      <div className="space-y-6">
        {/* 1. Baseline Identity */}
        <div className="border border-[#edf2f4] rounded-[16px] overflow-hidden">
          <div className="bg-slate-50/80 px-5 py-2.5 border-b border-[#edf2f4] text-[11px] font-bold text-slate-600 uppercase tracking-wide">
            1. BASELINE IDENTITY
          </div>
          <div className="divide-y divide-[#edf2f4] text-[13px]">
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Date of Birth</span>
                <span className="font-semibold text-slate-800">
                  {formatDob(dob)} ({currentAge} yrs)
                </span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(1)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Biological Sex</span>
                <span className="font-semibold text-slate-800 capitalize">{sex}</span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(1)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Blood Group</span>
                <span className="font-semibold text-slate-800">
                  {bloodGroup === 'Unknown' ? 'Unsure' : bloodGroup + ' (Rh ' + (bloodGroup.includes('+') ? 'Positive' : 'Negative') + ')'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(1)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
          </div>
        </div>

        {/* 2. Body Measurements & Activity */}
        <div className="border border-[#edf2f4] rounded-[16px] overflow-hidden">
          <div className="bg-slate-50/80 px-5 py-2.5 border-b border-[#edf2f4] text-[11px] font-bold text-slate-600 uppercase tracking-wide">
            2. BODY MEASUREMENTS &amp; ACTIVITY
          </div>
          <div className="divide-y divide-[#edf2f4] text-[13px]">
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Height &amp; Weight</span>
                <span className="font-semibold text-slate-800">
                  {heightCm} cm • {weightKg} kg (BMI {bmi} - {bmiInfo.label})
                </span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(2)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Physical Activity</span>
                <span className="font-semibold text-slate-800">
                  Level {activityLevel} / 10 • {activityLabel}
                </span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(2)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Primary Occupation</span>
                <span className="font-semibold text-slate-800">{occupation || 'Not specified'}</span>
              </div>
              <button
                type="button"
                onClick={() => onEditStep(2)}
                className="text-[12px] font-bold text-[#1b5879] hover:underline"
              >
                Edit
              </button>
            </div>
          </div>
        </div>

        {/* 3. Specific Health Parameters (Females only) */}
        {sex === 'female' && (
          <div className="border border-[#edf2f4] rounded-[16px] overflow-hidden">
            <div className="bg-slate-50/80 px-5 py-2.5 border-b border-[#edf2f4] text-[11px] font-bold text-slate-600 uppercase tracking-wide">
              3. SPECIFIC HEALTH PARAMETERS
            </div>
            <div className="divide-y divide-[#edf2f4] text-[13px]">
              <div className="px-5 py-3 flex items-center justify-between">
                <div>
                  <span className="text-slate-400 block text-[11px]">Pregnancy Status</span>
                  <span className="font-semibold text-slate-800">
                    {isPregnant ? `Yes • ${gestationalWeeks} Weeks (${trimesterLabel})` : 'No'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onEditStep(3)}
                  className="text-[12px] font-bold text-[#1b5879] hover:underline"
                >
                  Edit
                </button>
              </div>
              {isPregnant && (
                <div className="px-5 py-3 flex items-center justify-between bg-[#f0f9fa]">
                  <div className="text-[12px] text-[#1b5879] font-bold">
                    ✓ Preeclampsia Alerting &amp; Trimester BP Envelope Active
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-6 border-t border-slate-100">
          <button
            type="button"
            onClick={onBack}
            className="px-4 py-2.5 text-[13px] font-semibold text-slate-500 hover:text-slate-800 transition"
          >
            ← Back
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={loading}
            className="px-8 py-3.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[12px] shadow-lg transition flex items-center gap-2 disabled:opacity-60 cursor-pointer"
          >
            <span>{loading ? 'Saving Profile...' : 'Confirm & Save Profile →'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
