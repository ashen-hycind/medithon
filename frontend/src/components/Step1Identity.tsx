import React from 'react';
import { Check } from 'lucide-react';
import { BloodGroupType, SexType } from '../types';
import { ModernCalendarPicker } from './ModernCalendarPicker';

interface Props {
  dob: string;
  setDob: (v: string) => void;
  currentAge: number;
  sex: SexType;
  setSex: (v: SexType) => void;
  bloodGroup: BloodGroupType;
  setBloodGroup: (v: BloodGroupType) => void;
  onBack: () => void;
  onNext: () => void;
}

export const Step1Identity: React.FC<Props> = ({
  dob,
  setDob,
  currentAge,
  sex,
  setSex,
  bloodGroup,
  setBloodGroup,
  onBack,
  onNext
}) => {
  const bloodGroups: BloodGroupType[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'Unknown'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* Left Column: Form Controls */}
      <div className="lg:col-span-7 bg-white rounded-[20px] p-8 shadow-[0_4px_30px_rgba(0,0,0,0.04)] border border-[#edf2f4]">
        <div className="mb-6">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#6b855d] bg-[#f0f6ee] px-2 py-0.5 rounded">
            STEP 1 OF 3 • BASELINE HEALTH PROFILE
          </span>
          <h2 className="font-serif text-[28px] font-bold text-[#1b5879] tracking-tight mt-2">
            Tell us about yourself
          </h2>
          <p className="text-[13px] text-slate-500 mt-1 leading-relaxed">
            We use this clinical data to calibrate your vital ranges and establish physiological baselines.
          </p>
        </div>

        <div className="space-y-6">
          {/* Date of Birth with Modern Calendar Picker */}
          <div>
            <div className="flex justify-between items-baseline mb-1.5">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                DATE OF BIRTH *
              </label>
              <span className="text-[11px] text-slate-400">
                Used for pediatric vs geriatric clinical risk algorithms
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
              <div className="sm:col-span-8">
                <ModernCalendarPicker value={dob} onChange={setDob} />
              </div>
              <div className="sm:col-span-4 px-3.5 py-2.5 bg-[#e7f8fa] border border-[#c4edf2] rounded-[12px] text-[13px] font-bold text-[#1b5879] flex items-center justify-center h-[46px] shadow-xs">
                {currentAge} Years Old
              </div>
            </div>
          </div>

          {/* Biological Sex */}
          <div>
            <div className="flex justify-between items-baseline mb-1.5">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                BIOLOGICAL SEX *
              </label>
              <span className="text-[11px] text-slate-400">
                Required for sex-specific arterial stiffness &amp; hemoglobin ranges
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSex('male')}
                className={`p-3.5 rounded-[12px] border text-left transition ${
                  sex === 'male'
                    ? 'border-[#1b5879] bg-[#f0f9fa] shadow-sm'
                    : 'border-[#e2e8f0] hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-bold text-[#1b5879]">Male</span>
                  {sex === 'male' && <Check className="w-4 h-4 text-[#1b5879]" />}
                </div>
                <span className="text-[11px] text-slate-400 block mt-0.5">At birth</span>
              </button>

              <button
                type="button"
                onClick={() => setSex('female')}
                className={`p-3.5 rounded-[12px] border text-left transition ${
                  sex === 'female'
                    ? 'border-[#1b5879] bg-[#f0f9fa] shadow-sm'
                    : 'border-[#e2e8f0] hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-bold text-[#1b5879]">Female</span>
                  {sex === 'female' && <Check className="w-4 h-4 text-[#1b5879]" />}
                </div>
                <span className="text-[11px] text-slate-400 block mt-0.5">At birth</span>
              </button>
            </div>
          </div>

          {/* Blood Group */}
          <div>
            <div className="flex justify-between items-baseline mb-2">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                BLOOD GROUP *
              </label>
              <span className="text-[11px] text-slate-400">
                Essential for hospital emergency EHR exchange
              </span>
            </div>
            <div className="grid grid-cols-5 sm:grid-cols-9 gap-2">
              {bloodGroups.map((bg) => (
                <button
                  key={bg}
                  type="button"
                  onClick={() => setBloodGroup(bg)}
                  className={`py-2 px-1 text-[12px] font-bold rounded-[8px] border transition ${
                    bloodGroup === bg
                      ? 'border-[#1b5879] bg-[#1b5879] text-white shadow-xs'
                      : 'border-[#e2e8f0] bg-white text-slate-700 hover:border-slate-300'
                  }`}
                >
                  {bg === 'Unknown' ? 'Unsure' : bg}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onBack}
              className="px-4 py-2.5 text-[13px] font-semibold text-slate-500 hover:text-slate-800 transition"
            >
              ← Back
            </button>
            <button
              type="button"
              onClick={onNext}
              className="px-6 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] shadow transition flex items-center gap-1.5"
            >
              <span>Continue to Step 2 →</span>
            </button>
          </div>
        </div>
      </div>

      {/* Right Column: Rationale & Privacy Sidebar */}
      <div className="lg:col-span-5 space-y-5">
        <div className="bg-[#f0f9fa] rounded-[20px] p-6 border border-[#d2f0f4]">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-5 h-5 rounded-full bg-[#1b5879] text-white text-[11px] font-bold flex items-center justify-center">
              i
            </span>
            <h3 className="font-serif text-[17px] font-bold text-[#1b5879]">
              Why Baseline Data Matters
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mb-4">Clinical rationale behind this step</p>

          <div className="space-y-3.5 text-[12px]">
            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-white text-[#1b5879] font-bold text-[11px] flex items-center justify-center flex-shrink-0 shadow-xs">
                1
              </span>
              <div>
                <div className="font-bold text-slate-700">Age-Adjusted Vital Targets</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Systolic and diastolic thresholds automatically calibrate to your precise chronological demographic.
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-white text-[#1b5879] font-bold text-[11px] flex items-center justify-center flex-shrink-0 shadow-xs">
                2
              </span>
              <div>
                <div className="font-bold text-slate-700">Biological Baselines</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Resting metabolic rate, vital capacity, and arterial compliance vary across sexes.
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-white text-[#1b5879] font-bold text-[11px] flex items-center justify-center flex-shrink-0 shadow-xs">
                3
              </span>
              <div>
                <div className="font-bold text-slate-700">Emergency EHR Interoperability</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Exportable in HL7 FHIR standard for rapid hospital intake during acute care situations.
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[16px] p-5 border border-[#edf2f4]">
          <div className="font-bold text-[12px] text-slate-800 mb-1">Zero Cloud Storage of Raw ID</div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            MediBridge uses deterministic local-first tokenization. Your personal identification parameters are bound cryptographically to your client session.
          </p>
          <div className="mt-3 space-y-1 text-[11px] font-semibold text-[#6b855d]">
            <div>✓ 256-Bit TLS In-Transit Encryption</div>
            <div>✓ HIPAA Security Rule § 164.312 Compliant</div>
          </div>
        </div>
      </div>
    </div>
  );
};
