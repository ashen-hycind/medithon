import React from 'react';
import { Baby, Check, Plus, Minus } from 'lucide-react';

interface Props {
  isPregnant: boolean;
  setIsPregnant: (v: boolean) => void;
  gestationalWeeks: number;
  setGestationalWeeks: (v: number) => void;
  trimesterLabel: string;
  onBack: () => void;
  onNext: () => void;
}

export const Step3Parameters: React.FC<Props> = ({
  isPregnant,
  setIsPregnant,
  gestationalWeeks,
  setGestationalWeeks,
  trimesterLabel,
  onBack,
  onNext
}) => (
  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
    {/* Left Column: Form Controls */}
    <div className="lg:col-span-7 bg-white rounded-[20px] p-8 shadow-[0_4px_30px_rgba(0,0,0,0.04)] border border-[#edf2f4]">
      <div className="mb-6">
        <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#6b855d] bg-[#f0f6ee] px-2 py-0.5 rounded">
          STEP 3 OF 3 • PROFILE PARAMETERS
        </span>
        <h2 className="font-serif text-[28px] font-bold text-[#1b5879] tracking-tight mt-2">
          Specific health factors
        </h2>
        <p className="text-[13px] text-slate-500 mt-1 leading-relaxed">
          Special biological parameters enable specialized clinical diagnostic pathways and safety thresholds.
        </p>
      </div>

      <div className="space-y-6">
        {/* Pregnancy Status Switch */}
        <div>
          <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wide mb-1">
            ARE YOU CURRENTLY PREGNANT? *
          </label>
          <p className="text-[11px] text-slate-400 mb-3">
            Activates obstetric hemodynamic monitoring and preeclampsia early warning tracking
          </p>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setIsPregnant(true)}
              className={`p-4 rounded-[12px] border text-left transition ${
                isPregnant
                  ? 'border-[#1b5879] bg-[#f0f9fa] shadow-sm'
                  : 'border-[#e2e8f0] hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-bold text-[#1b5879]">Yes, Currently Pregnant</span>
                {isPregnant && <Check className="w-4 h-4 text-[#1b5879]" />}
              </div>
              <span className="text-[11px] text-slate-400 block mt-0.5">Enable trimester clinical envelope</span>
            </button>

            <button
              type="button"
              onClick={() => setIsPregnant(false)}
              className={`p-4 rounded-[12px] border text-left transition ${
                !isPregnant
                  ? 'border-[#1b5879] bg-[#f0f9fa] shadow-sm'
                  : 'border-[#e2e8f0] hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-bold text-[#1b5879]">No</span>
                {!isPregnant && <Check className="w-4 h-4 text-[#1b5879]" />}
              </div>
              <span className="text-[11px] text-slate-400 block mt-0.5">Standard adult physiology</span>
            </button>
          </div>
        </div>

        {/* Gestational Age Stepper (if pregnant) */}
        {isPregnant && (
          <div className="p-5 bg-slate-50 border border-[#e2e8f0] rounded-[14px] space-y-3">
            <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wide">
              GESTATIONAL AGE (WEEKS) *
            </label>
            <p className="text-[11px] text-slate-400">
              Required to benchmark gestational diabetes and trimester blood pressure shifts
            </p>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setGestationalWeeks(Math.max(1, gestationalWeeks - 1))}
                className="w-10 h-10 rounded-[10px] bg-white border border-[#e2e8f0] hover:bg-slate-100 flex items-center justify-center text-slate-700 transition shadow-xs"
              >
                <Minus className="w-4 h-4" />
              </button>
              <div className="px-6 py-2 bg-white border border-[#e2e8f0] rounded-[10px] font-serif text-[22px] font-bold text-[#1b5879]">
                {gestationalWeeks} Weeks
              </div>
              <button
                type="button"
                onClick={() => setGestationalWeeks(Math.min(42, gestationalWeeks + 1))}
                className="w-10 h-10 rounded-[10px] bg-white border border-[#e2e8f0] hover:bg-slate-100 flex items-center justify-center text-slate-700 transition shadow-xs"
              >
                <Plus className="w-4 h-4" />
              </button>
              <span className="text-[12px] font-semibold text-slate-600">
                {trimesterLabel}
              </span>
            </div>

            <div className="text-[11px] text-[#6b855d] font-semibold pt-1">
              ✓ Normal gestational systolic range: 90–120 mmHg • Blood glucose targets automatically calibrated
            </div>
          </div>
        )}

        <div className="p-4 bg-[#f0f9fa] border border-[#d2f0f4] rounded-[12px]">
          <div className="font-bold text-[12px] text-[#1b5879] mb-0.5">Obstetric Protocol Ready</div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            The MediBridge system will flag gestational hypertension thresholds (&gt;140/90 mmHg) with high-priority warnings.
          </p>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onBack}
            className="px-4 py-2.5 text-[13px] font-semibold text-slate-500 hover:text-slate-800 transition"
          >
            ← Back to Step 2
          </button>
          <button
            type="button"
            onClick={onNext}
            className="px-6 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] shadow transition flex items-center gap-1.5"
          >
            <span>Review Profile Details →</span>
          </button>
        </div>
      </div>
    </div>

    {/* Right Column: Protocols Sidebar */}
    <div className="lg:col-span-5 space-y-5">
      <div className="bg-[#f0f9fa] rounded-[20px] p-6 border border-[#d2f0f4]">
        <div className="flex items-center gap-2 mb-1">
          <Baby className="w-5 h-5 text-[#1b5879]" />
          <h3 className="font-serif text-[17px] font-bold text-[#1b5879]">
            Specialized Risk Protocols
          </h3>
        </div>
        <p className="text-[11px] text-slate-500 mb-4">Maternal &amp; clinical monitoring safeguards</p>

        <div className="space-y-3.5 text-[12px]">
          <div className="flex gap-3">
            <span className="w-7 h-6 rounded bg-[#1b5879] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              BP
            </span>
            <div>
              <div className="font-bold text-slate-700">Preeclampsia Detection</div>
              <div className="text-slate-500 text-[11px] mt-0.5">
                Monitors sudden diastolic elevations (&gt;15 mmHg from baseline) during weeks 20–40.
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <span className="w-7 h-6 rounded bg-[#6b855d] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              GL
            </span>
            <div>
              <div className="font-bold text-slate-700">Gestational Glucose Targets</div>
              <div className="text-slate-500 text-[11px] mt-0.5">
                Tighter fasting sugar targets (&lt;95 mg/dL) applied to protect maternal and fetal safety.
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <span className="w-7 h-6 rounded bg-[#1b5879] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              OB
            </span>
            <div>
              <div className="font-bold text-slate-700">OB-GYN Clinical PDF Report</div>
              <div className="text-slate-500 text-[11px] mt-0.5">
                Weekly vitals logs can be compiled into a single formatted PDF export for prenatal appointments.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-[16px] p-5 border border-[#edf2f4]">
        <div className="font-bold text-[12px] text-slate-800 mb-2">Active Diagnostic Envelopes</div>
        <div className="space-y-1.5 text-[11px] text-slate-600 font-medium">
          <div className="flex items-center gap-2">
            <Check className="w-3.5 h-3.5 text-[#6b855d]" />
            <span>Baseline Blood Pressure Calibration</span>
          </div>
          <div className="flex items-center gap-2">
            <Check className="w-3.5 h-3.5 text-[#6b855d]" />
            <span>Pulse Oximetry Nocturnal Screening</span>
          </div>
          <div className="flex items-center gap-2">
            <Check className="w-3.5 h-3.5 text-[#6b855d]" />
            <span>Weight Gain Trend Monitoring (2nd Trimester)</span>
          </div>
          <div className="flex items-center gap-2">
            <Check className="w-3.5 h-3.5 text-[#6b855d]" />
            <span>FHIR Observation Resource Ingestion</span>
          </div>
        </div>
      </div>
    </div>
  </div>
);
