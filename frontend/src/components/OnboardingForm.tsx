import React, { useState } from 'react';
import { UserProfile, BloodGroupType, SexType } from '../types';
import { Heart, Activity, User, Calendar, Droplets, Ruler, Weight, Baby, Briefcase, CheckCircle2 } from 'lucide-react';

interface OnboardingFormProps {
  token: string;
  onComplete: (profile: UserProfile) => void;
}

export const OnboardingForm: React.FC<OnboardingFormProps> = ({ token, onComplete }) => {
  const [name, setName] = useState('');
  const [dob, setDob] = useState('');
  const [bloodGroup, setBloodGroup] = useState<BloodGroupType>('Unknown');
  const [sex, setSex] = useState<SexType>('male');
  const [heightCm, setHeightCm] = useState<string>('170');
  const [weightKg, setWeightKg] = useState<string>('70');
  const [pregnancyStatus, setPregnancyStatus] = useState<boolean>(false);
  const [gestationalWeeks, setGestationalWeeks] = useState<string>('');
  const [activityLevel, setActivityLevel] = useState<number>(5);
  const [occupation, setOccupation] = useState<string>('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const payload: UserProfile = {
      name: name.trim(),
      dob,
      blood_group: bloodGroup,
      sex,
      height_cm: parseFloat(heightCm),
      weight_kg: parseFloat(weightKg),
      activity_level: activityLevel,
      occupation: occupation.trim() || undefined,
    };

    if (sex === 'female') {
      payload.pregnancy_status = pregnancyStatus;
      if (pregnancyStatus && gestationalWeeks) {
        payload.gestational_age_weeks = parseInt(gestationalWeeks, 10);
      }
    }

    try {
      setLoading(true);
      const res = await fetch('/api/users/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to save health profile');
      }

      const saved = await res.json();
      onComplete(saved);
    } catch (err: any) {
      setError(err.message || 'Error saving health profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-8 bg-white rounded-3xl shadow-xl border border-slate-100">
      <div className="flex items-center gap-3 pb-6 border-b border-slate-100 mb-6">
        <div className="w-12 h-12 bg-teal-50 text-teal-600 rounded-2xl flex items-center justify-center">
          <Heart className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-800">Health Profile Setup</h2>
          <p className="text-sm text-slate-500">
            Please provide your baseline medical parameters to personalize trend analytics.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              <User className="w-4 h-4 text-slate-400" /> Full Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dr. Jane Doe"
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            />
          </div>

          {/* DOB */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-slate-400" /> Date of Birth
            </label>
            <input
              type="date"
              required
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            />
          </div>

          {/* Sex assigned at birth */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              Sex (assigned at birth)
            </label>
            <select
              value={sex}
              onChange={(e) => {
                const val = e.target.value as SexType;
                setSex(val);
                if (val === 'male') {
                  setPregnancyStatus(false);
                  setGestationalWeeks('');
                }
              }}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
            <p className="text-[11px] text-slate-400 mt-1">Required for physiological baseline reference ranges.</p>
          </div>

          {/* Blood Group */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              <Droplets className="w-4 h-4 text-slate-400" /> Blood Group
            </label>
            <select
              value={bloodGroup}
              onChange={(e) => setBloodGroup(e.target.value as BloodGroupType)}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            >
              <option value="Unknown">Don't Know / Unknown</option>
              <option value="A+">A+</option>
              <option value="A-">A-</option>
              <option value="B+">B+</option>
              <option value="B-">B-</option>
              <option value="AB+">AB+</option>
              <option value="AB-">AB-</option>
              <option value="O+">O+</option>
              <option value="O-">O-</option>
            </select>
          </div>

          {/* Height */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              <Ruler className="w-4 h-4 text-slate-400" /> Height (cm)
            </label>
            <input
              type="number"
              step="0.1"
              min="40"
              max="260"
              required
              value={heightCm}
              onChange={(e) => setHeightCm(e.target.value)}
              placeholder="170"
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            />
            <span className="text-[11px] text-slate-400">Can be updated occasionally</span>
          </div>

          {/* Weight */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
              <Weight className="w-4 h-4 text-slate-400" /> Starting Weight (kg)
            </label>
            <input
              type="number"
              step="0.1"
              min="15"
              max="400"
              required
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
              placeholder="70"
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            />
            <span className="text-[11px] text-slate-400">Can be updated regularly</span>
          </div>
        </div>

        {/* Pregnancy Fields (Conditional for Female) */}
        {sex === 'female' && (
          <div className="p-4 bg-teal-50/60 border border-teal-100 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Baby className="w-5 h-5 text-teal-600" />
                <span className="text-sm font-semibold text-slate-800">Pregnancy Status</span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={pregnancyStatus}
                  onChange={(e) => setPregnancyStatus(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
              </label>
            </div>

            {pregnancyStatus && (
              <div className="pt-2">
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5">
                  Gestational Age (weeks)
                </label>
                <input
                  type="number"
                  min="1"
                  max="45"
                  required={pregnancyStatus}
                  value={gestationalWeeks}
                  onChange={(e) => setGestationalWeeks(e.target.value)}
                  placeholder="e.g. 18"
                  className="w-full px-4 py-2 bg-white border border-teal-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            )}
          </div>
        )}

        {/* Activity Level */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-xs font-semibold text-slate-600 uppercase flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-slate-400" /> Activity Level
            </label>
            <span className="text-xs font-bold text-teal-700 bg-teal-50 px-2.5 py-1 rounded-full border border-teal-100">
              Level {activityLevel} / 10
            </span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            value={activityLevel}
            onChange={(e) => setActivityLevel(parseInt(e.target.value, 10))}
            className="w-full accent-teal-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>1 (Sedentary)</span>
            <span>5 (Moderate)</span>
            <span>10 (Very Active)</span>
          </div>
        </div>

        {/* Occupation */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5 flex items-center gap-1.5">
            <Briefcase className="w-4 h-4 text-slate-400" /> Occupation (Optional)
          </label>
          <input
            type="text"
            value={occupation}
            onChange={(e) => setOccupation(e.target.value)}
            placeholder="Software Engineer, Teacher, Retired..."
            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 px-4 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition shadow-lg shadow-teal-600/20 disabled:opacity-60 text-sm"
        >
          <CheckCircle2 className="w-5 h-5" />
          <span>{loading ? 'Saving Profile...' : 'Complete Setup & Enter Dashboard'}</span>
        </button>
      </form>
    </div>
  );
};
