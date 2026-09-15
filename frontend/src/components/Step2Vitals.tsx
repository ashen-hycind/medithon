import React from 'react';
import { Scale } from 'lucide-react';

interface Props {
  heightCm: number;
  setHeightCm: (v: number) => void;
  heightUnit: 'cm' | 'ft';
  setHeightUnit: (v: 'cm' | 'ft') => void;
  weightKg: number;
  setWeightKg: (v: number) => void;
  weightUnit: 'kg' | 'lbs';
  setWeightUnit: (v: 'kg' | 'lbs') => void;
  activityLevel: number;
  setActivityLevel: (v: number) => void;
  occupation: string;
  setOccupation: (v: string) => void;
  bmi: number;
  bmiInfo: { label: string; color: string };
  activityLabel: string;
  isFemale: boolean;
  onBack: () => void;
  onNext: () => void;
}

export const Step2Vitals: React.FC<Props> = ({
  heightCm,
  setHeightCm,
  heightUnit,
  setHeightUnit,
  weightKg,
  setWeightKg,
  weightUnit,
  setWeightUnit,
  activityLevel,
  setActivityLevel,
  occupation,
  setOccupation,
  bmi,
  bmiInfo,
  activityLabel,
  isFemale,
  onBack,
  onNext
}) => {
  // Height display & toggle
  const displayHeight = heightUnit === 'ft' ? (heightCm / 30.48).toFixed(1) : heightCm;
  const displayWeight = weightUnit === 'lbs' ? (weightKg * 2.20462).toFixed(1) : weightKg;

  const handleHeightChange = (val: string) => {
    const num = parseFloat(val) || 0;
    if (heightUnit === 'ft') {
      setHeightCm(Math.round(num * 30.48));
    } else {
      setHeightCm(num);
    }
  };

  const handleWeightChange = (val: string) => {
    const num = parseFloat(val) || 0;
    if (weightUnit === 'lbs') {
      setWeightKg(parseFloat((num / 2.20462).toFixed(1)));
    } else {
      setWeightKg(num);
    }
  };

  const minIdealWeight = ((18.5 * Math.pow(heightCm / 100, 2))).toFixed(1);
  const maxIdealWeight = ((24.9 * Math.pow(heightCm / 100, 2))).toFixed(1);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* Left Column: Inputs */}
      <div className="lg:col-span-7 bg-white rounded-[20px] p-8 shadow-[0_4px_30px_rgba(0,0,0,0.04)] border border-[#edf2f4]">
        <div className="mb-6">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#6b855d] bg-[#f0f6ee] px-2 py-0.5 rounded">
            STEP 2 OF 3 • BODY &amp; PHYSICAL PROFILE
          </span>
          <h2 className="font-serif text-[28px] font-bold text-[#1b5879] tracking-tight mt-2">
            Body measurements &amp; lifestyle
          </h2>
          <p className="text-[13px] text-slate-500 mt-1 leading-relaxed">
            Required to compute precise Body Mass Index (BMI) and tailor diurnal cardiovascular thresholds.
          </p>
        </div>

        <div className="space-y-6">
          {/* Height and Weight Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wide mb-1">
                HEIGHT *
              </label>
              <div className="relative flex items-center">
                <input
                  type="number"
                  step={heightUnit === 'ft' ? '0.1' : '1'}
                  value={displayHeight}
                  onChange={(e) => handleHeightChange(e.target.value)}
                  className="w-full pl-3.5 pr-16 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white font-medium"
                />
                <div className="absolute right-1.5 flex gap-1">
                  <button
                    type="button"
                    onClick={() => setHeightUnit('cm')}
                    className={`px-2 py-1 text-[11px] font-bold rounded transition ${
                      heightUnit === 'cm'
                        ? 'bg-[#1b5879] text-white shadow-xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    cm
                  </button>
                  <button
                    type="button"
                    onClick={() => setHeightUnit('ft')}
                    className={`px-2 py-1 text-[11px] font-bold rounded transition ${
                      heightUnit === 'ft'
                        ? 'bg-[#1b5879] text-white shadow-xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    ft
                  </button>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wide mb-1">
                WEIGHT *
              </label>
              <div className="relative flex items-center">
                <input
                  type="number"
                  step="0.1"
                  value={displayWeight}
                  onChange={(e) => handleWeightChange(e.target.value)}
                  className="w-full pl-3.5 pr-16 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white font-medium"
                />
                <div className="absolute right-1.5 flex gap-1">
                  <button
                    type="button"
                    onClick={() => setWeightUnit('kg')}
                    className={`px-2 py-1 text-[11px] font-bold rounded transition ${
                      weightUnit === 'kg'
                        ? 'bg-[#1b5879] text-white shadow-xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    kg
                  </button>
                  <button
                    type="button"
                    onClick={() => setWeightUnit('lbs')}
                    className={`px-2 py-1 text-[11px] font-bold rounded transition ${
                      weightUnit === 'lbs'
                        ? 'bg-[#1b5879] text-white shadow-xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    lbs
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Computed BMI Banner */}
          <div className="p-4 bg-[#f8fafc] border border-[#e2e8f0] rounded-[14px]">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[13px] font-bold text-slate-700">
                Computed Baseline BMI: <span className="text-[#1b5879]">{bmi} kg/m²</span>
              </span>
              <span className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase ${bmiInfo.color}`}>
                {bmiInfo.label}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Standard clinical range: 18.5 – 24.9 kg/m² (WHO Criteria)
            </p>
          </div>

          {/* Physical Activity Slider */}
          <div>
            <div className="flex justify-between items-baseline mb-1">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                PHYSICAL ACTIVITY LEVEL *
              </label>
              <span className="text-[11px] text-slate-400">
                Adjust slider from 1 (sedentary) to 10 (intense athletic training)
              </span>
            </div>
            <div className="p-4 bg-slate-50 border border-[#e2e8f0] rounded-[12px] space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-[13px] font-bold text-[#1b5879]">
                  Level {activityLevel} / 10 • {activityLabel}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={activityLevel}
                onChange={(e) => setActivityLevel(parseInt(e.target.value, 10))}
                className="w-full accent-[#1b5879] cursor-pointer"
              />
              <p className="text-[11px] text-slate-500">
                Moderate physical exercise, gym sessions, or brisk walking 3–5 days per week.
              </p>
            </div>
          </div>

          {/* Primary Occupation */}
          <div>
            <div className="flex justify-between items-baseline mb-1">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                PRIMARY OCCUPATION
              </label>
              <span className="text-[11px] text-slate-400">
                Assists in detecting ergonomic and sedentary posture patterns
              </span>
            </div>
            <input
              type="text"
              value={occupation}
              onChange={(e) => setOccupation(e.target.value)}
              placeholder="Student / Desk Researcher"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onBack}
              className="px-4 py-2.5 text-[13px] font-semibold text-slate-500 hover:text-slate-800 transition"
            >
              ← Back to Step 1
            </button>
            <button
              type="button"
              onClick={onNext}
              className="px-6 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] shadow transition flex items-center gap-1.5"
            >
              <span>{isFemale ? 'Continue to Step 3 →' : 'Review Profile Details →'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Right Column: Metabolic Calibration Sidebar */}
      <div className="lg:col-span-5 space-y-5">
        <div className="bg-[#f0f9fa] rounded-[20px] p-6 border border-[#d2f0f4]">
          <div className="flex items-center gap-2 mb-1">
            <Scale className="w-5 h-5 text-[#1b5879]" />
            <h3 className="font-serif text-[17px] font-bold text-[#1b5879]">
              Metabolic Calibration
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mb-4">How body metrics power AI diagnostics</p>

          <div className="space-y-3.5 text-[12px]">
            <div className="flex gap-3">
              <span className="w-7 h-6 rounded bg-[#1b5879] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                BP
              </span>
              <div>
                <div className="font-bold text-slate-700">Vascular Resistance Offset</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Body height affects hydrostatic blood column calculations when measuring sitting blood pressure.
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="w-7 h-6 rounded bg-[#6b855d] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                HR
              </span>
              <div>
                <div className="font-bold text-slate-700">Resting Heart Rate Calibration</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Active individuals naturally present lower resting pulse rates (bradycardia envelope adjustments).
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="w-7 h-6 rounded bg-[#1b5879] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                AI
              </span>
              <div>
                <div className="font-bold text-slate-700">Personalized Clinical Insights</div>
                <div className="text-slate-500 text-[11px] mt-0.5">
                  Automated recommendations reference your body profile to suggest actionable diet and activity modifications.
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[16px] p-5 border border-[#edf2f4]">
          <div className="font-bold text-[12px] text-slate-800 mb-2">Target Weight &amp; BMI Range</div>
          <div className="h-2 w-full bg-slate-100 rounded-full flex overflow-hidden mb-2">
            <div className="w-1/4 bg-amber-200"></div>
            <div className="w-2/4 bg-[#6b855d]"></div>
            <div className="w-1/4 bg-rose-200"></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 mb-2">
            <span>&lt; 18.5</span>
            <span className="font-bold text-[#6b855d]">18.5 - 24.9 (You: {bmi})</span>
            <span>&gt; 25.0</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Calculated Ideal Weight Envelope: {minIdealWeight} – {maxIdealWeight} kg for your height of {heightCm} cm.
          </p>
          <div className="text-[11px] font-semibold text-[#6b855d] mt-1.5">
            ✓ Baseline classified as optimal physiological condition.
          </div>
        </div>
      </div>
    </div>
  );
};
