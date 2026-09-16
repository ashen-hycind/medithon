import React, { useState } from 'react';
import { ShieldCheck, Check } from 'lucide-react';
import { UserProfile, BloodGroupType, SexType } from '../types';
import { Step1Identity } from './Step1Identity';
import { Step2Vitals } from './Step2Vitals';
import { Step3Parameters } from './Step3Parameters';
import { Step4Review } from './Step4Review';
import { saveUserProfile } from '../services/measurementService';

interface OnboardingFlowProps {
  token: string;
  initialName?: string;
  onBackToRegister: () => void;
  onComplete: (profile: UserProfile) => void;
}

export const OnboardingFlow: React.FC<OnboardingFlowProps> = ({
  token,
  initialName = 'Madhav Sharma',
  onBackToRegister,
  onComplete
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  const [dob, setDob] = useState('2007-05-28');
  const [sex, setSex] = useState<SexType>('female');
  const [bloodGroup, setBloodGroup] = useState<BloodGroupType>('B+');

  const [heightCm, setHeightCm] = useState<number>(168);
  const [heightUnit, setHeightUnit] = useState<'cm' | 'ft'>('cm');
  const [weightKg, setWeightKg] = useState<number>(62.0);
  const [weightUnit, setWeightUnit] = useState<'kg' | 'lbs'>('kg');
  const [activityLevel, setActivityLevel] = useState<number>(5);
  const [occupation, setOccupation] = useState('Software Engineer / Desk Worker');

  const [isPregnant, setIsPregnant] = useState<boolean>(true);
  const [gestationalWeeks, setGestationalWeeks] = useState<number>(24);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateAge = (dobString: string) => {
    if (!dobString) return 19;
    const diff = Date.now() - new Date(dobString).getTime();
    return Math.abs(new Date(diff).getUTCFullYear() - 1970);
  };
  const currentAge = calculateAge(dob);

  const bmi = parseFloat((weightKg / Math.pow(heightCm / 100, 2)).toFixed(1));

  const getBmiCategory = (val: number) => {
    if (val < 18.5) return { label: 'UNDERWEIGHT', color: 'text-amber-600 bg-amber-50' };
    if (val <= 24.9) return { label: 'NORMAL WEIGHT', color: 'text-[#6b855d] bg-[#f0f6ee]' };
    if (val <= 29.9) return { label: 'OVERWEIGHT', color: 'text-amber-600 bg-amber-50' };
    return { label: 'OBESE', color: 'text-rose-600 bg-rose-50' };
  };
  const bmiInfo = getBmiCategory(bmi);

  const getActivityLabel = (lvl: number) => {
    if (lvl <= 3) return 'Sedentary • Desk Bound';
    if (lvl <= 6) return 'Moderately Active • 3-5 sessions/wk';
    if (lvl <= 8) return 'Very Active • Daily workouts';
    return 'Athletic Training • High Intensity';
  };

  const getTrimester = (weeks: number) => {
    if (weeks <= 12) return 'First Trimester (Wk 1–12)';
    if (weeks <= 27) return 'Second Trimester (Wk 13–27)';
    return 'Third Trimester (Wk 28–40+)';
  };

  const handleNextFromStep2 = () => {
    if (sex === 'female') {
      setStep(3);
    } else {
      setStep(4);
    }
  };

  const handleFinalSubmit = async () => {
    setError(null);
    const payload: UserProfile = {
      name: initialName,
      dob,
      blood_group: bloodGroup,
      sex,
      height_cm: heightCm,
      weight_kg: weightKg,
      activity_level: activityLevel,
      occupation: occupation || undefined,
    };

    if (sex === 'female') {
      payload.pregnancy_status = isPregnant;
      if (isPregnant) {
        payload.gestational_age_weeks = gestationalWeeks;
      }
    } else {
      payload.pregnancy_status = false;
      payload.gestational_age_weeks = null;
    }

    try {
      setLoading(true);
      const saved = await saveUserProfile(payload, token);
      onComplete(saved);
    } catch (err: any) {
      setError(err.message || 'Error saving health profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans selection:bg-[#e7f8fa] selection:text-[#1b5879]">
      {/* Top Header */}
      <header className="w-full bg-white border-b border-[#edf2f4] py-3 px-6 sm:px-12 sticky top-0 z-30">
        <div className="max-w-[1240px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-[30px] h-[30px] rounded-[8px] bg-[#1b5879] flex items-center justify-center text-white text-base font-bold shadow-sm">
              <span className="leading-none pb-0.5">+</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[18px] font-bold text-[#1b5879] tracking-tight">MediBridge</span>
              <span className="text-[9px] font-extrabold tracking-wider text-teal-800 bg-[#c4edf2] px-1.5 py-0.5 rounded-[3px] uppercase">
                {step === 4 ? 'FINAL PROFILE VERIFICATION' : 'PATIENT ONBOARDING'}
              </span>
            </div>
          </div>

          {/* Stepper tracker */}
          <div className="hidden md:flex items-center gap-6 text-[12px] font-semibold text-slate-500">
            <span className={`flex items-center gap-1.5 ${step === 1 ? 'text-[#1b5879] font-bold' : ''}`}>
              {step > 1 ? <Check className="w-3.5 h-3.5 text-[#6b855d]" /> : null} 1. Identity
            </span>
            <span className={`flex items-center gap-1.5 ${step === 2 ? 'text-[#1b5879] font-bold' : ''}`}>
              {step > 2 ? <Check className="w-3.5 h-3.5 text-[#6b855d]" /> : null} 2. Vitals
            </span>
            {sex === 'female' && (
              <span className={`flex items-center gap-1.5 ${step === 3 ? 'text-[#1b5879] font-bold' : ''}`}>
                {step > 3 ? <Check className="w-3.5 h-3.5 text-[#6b855d]" /> : null} 3. Parameters
              </span>
            )}
            {step === 4 && (
              <span className="text-[#1b5879] font-bold">
                Step 4: Review &amp; Confirm
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#1b5879] bg-[#e7f8fa] px-2.5 py-1 rounded-md border border-[#c4edf2]">
            <ShieldCheck className="w-3.5 h-3.5 text-[#1b5879]" />
            <span>HIPAA ENCRYPTED</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1240px] mx-auto w-full px-4 sm:px-8 py-8 flex-1">
        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-[13px] rounded-xl">
            {error}
          </div>
        )}

        {step === 1 && (
          <Step1Identity
            dob={dob}
            setDob={setDob}
            currentAge={currentAge}
            sex={sex}
            setSex={setSex}
            bloodGroup={bloodGroup}
            setBloodGroup={setBloodGroup}
            onBack={onBackToRegister}
            onNext={() => setStep(2)}
          />
        )}

        {step === 2 && (
          <Step2Vitals
            heightCm={heightCm}
            setHeightCm={setHeightCm}
            heightUnit={heightUnit}
            setHeightUnit={setHeightUnit}
            weightKg={weightKg}
            setWeightKg={setWeightKg}
            weightUnit={weightUnit}
            setWeightUnit={setWeightUnit}
            activityLevel={activityLevel}
            setActivityLevel={setActivityLevel}
            occupation={occupation}
            setOccupation={setOccupation}
            bmi={bmi}
            bmiInfo={bmiInfo}
            activityLabel={getActivityLabel(activityLevel)}
            isFemale={sex === 'female'}
            onBack={() => setStep(1)}
            onNext={handleNextFromStep2}
          />
        )}

        {step === 3 && sex === 'female' && (
          <Step3Parameters
            isPregnant={isPregnant}
            setIsPregnant={setIsPregnant}
            gestationalWeeks={gestationalWeeks}
            setGestationalWeeks={setGestationalWeeks}
            trimesterLabel={getTrimester(gestationalWeeks)}
            onBack={() => setStep(2)}
            onNext={() => setStep(4)}
          />
        )}

        {step === 4 && (
          <Step4Review
            dob={dob}
            currentAge={currentAge}
            sex={sex}
            bloodGroup={bloodGroup}
            heightCm={heightCm}
            weightKg={weightKg}
            bmi={bmi}
            bmiInfo={bmiInfo}
            activityLevel={activityLevel}
            activityLabel={getActivityLabel(activityLevel)}
            occupation={occupation}
            isPregnant={isPregnant}
            gestationalWeeks={gestationalWeeks}
            trimesterLabel={getTrimester(gestationalWeeks)}
            loading={loading}
            onEditStep={(s) => setStep(s)}
            onBack={() => setStep(sex === 'female' ? 3 : 2)}
            onSubmit={handleFinalSubmit}
          />
        )}
      </main>
    </div>
  );
};
