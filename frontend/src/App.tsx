import React, { useEffect, useState } from 'react';
import { onAuthStateChanged, signOut, User } from 'firebase/auth';
import { auth } from './firebase';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { RegistrationPage } from './components/RegistrationPage';
import { OnboardingFlow } from './components/OnboardingFlow';
import { UserProfile, BloodPressureMeasurement, BloodGlucoseMeasurement } from './types';
import { Activity, LogOut, PlusCircle, FileText, Camera, Upload, Scale, Sparkles, TrendingUp, Heart, Droplet, RefreshCw } from 'lucide-react';
import { ScanModal } from './components/ScanModal';
import { BloodPressureTimeline } from './components/BloodPressureTimeline';
import { BloodGlucoseTimeline } from './components/BloodGlucoseTimeline';
import { getBloodPressureMeasurements, getBloodGlucoseMeasurements } from './services/measurementService';

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Navigation State
  const [currentRoute, setCurrentRoute] = useState<'landing' | 'login' | 'register'>('landing');
  const [showWeightModal, setShowWeightModal] = useState(false);
  const [newWeight, setNewWeight] = useState('');
  const [weightLoading, setWeightLoading] = useState(false);

  // Vitals & Measurements State
  const [activeTab, setActiveTab] = useState<'blood_pressure' | 'blood_glucose'>('blood_pressure');
  const [bpMeasurements, setBpMeasurements] = useState<BloodPressureMeasurement[]>([]);
  const [glucoseMeasurements, setGlucoseMeasurements] = useState<BloodGlucoseMeasurement[]>([]);
  const [measurementsLoading, setMeasurementsLoading] = useState(false);
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanDefaultDevice, setScanDefaultDevice] = useState<'blood_pressure' | 'blood_glucose'>('blood_pressure');

  const loadMeasurements = async (authToken: string) => {
    setMeasurementsLoading(true);
    try {
      const [bpRes, gluRes] = await Promise.allSettled([
        getBloodPressureMeasurements(authToken),
        getBloodGlucoseMeasurements(authToken)
      ]);
      if (bpRes.status === 'fulfilled') setBpMeasurements(bpRes.value);
      if (gluRes.status === 'fulfilled') setGlucoseMeasurements(gluRes.value);
    } catch (err) {
      console.error('Failed to load measurements:', err);
    } finally {
      setMeasurementsLoading(false);
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        try {
          const idToken = await currentUser.getIdToken();
          setToken(idToken);
          const res = await fetch('/api/users/profile', {
            headers: { 'Authorization': 'Bearer ' + idToken }
          });
          if (res.ok) {
            const data = await res.json();
            setProfile(data);
            loadMeasurements(idToken);
          } else {
            setProfile(null);
          }
        } catch (err) {
          console.error('Error fetching user profile:', err);
        }
      } else {
        setToken(null);
        setProfile(null);
        setBpMeasurements([]);
        setGlucoseMeasurements([]);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const handleSignOut = () => {
    signOut(auth);
    setCurrentRoute('landing');
  };

  const handleWeightUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newWeight) return;
    try {
      setWeightLoading(true);
      const res = await fetch('/api/users/weight', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ weight_kg: parseFloat(newWeight) })
      });
      if (res.ok) {
        setProfile(prev => prev ? { ...prev, weight_kg: parseFloat(newWeight) } : null);
        setShowWeightModal(false);
        setNewWeight('');
      }
    } catch (err) {
      console.error('Failed to update weight:', err);
    } finally {
      setWeightLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Activity className="w-8 h-8 animate-spin text-[#1b5879]" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans">
            Loading MediBridge...
          </p>
        </div>
      </div>
    );
  }

  // Not signed in -> Route to Landing, Login, or Register
  if (!user) {
    if (currentRoute === 'login') {
      return (
        <LoginPage 
          onBack={() => setCurrentRoute('landing')}
          onNavigateRegister={() => setCurrentRoute('register')}
          onSuccess={() => setCurrentRoute('landing')}
        />
      );
    }

    if (currentRoute === 'register') {
      return (
        <RegistrationPage
          onBack={() => setCurrentRoute('landing')}
          onNavigateLogin={() => setCurrentRoute('login')}
          onSuccess={() => setCurrentRoute('landing')}
        />
      );
    }

    return (
      <LandingPage 
        onOpenAuth={(mode) => setCurrentRoute(mode === 'register' ? 'register' : 'login')} 
      />
    );
  }

  // Signed in but hasn't completed onboarding profile yet -> Show Stepwise Onboarding Flow
  if (!profile) {
    return (
      <OnboardingFlow
        token={token || ''}
        initialName={user.displayName || 'Madhav Sharma'}
        onBackToRegister={handleSignOut}
        onComplete={(savedProfile) => setProfile(savedProfile)}
      />
    );
  }

  // Fully Onboarded User Dashboard View
  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* Top Navigation */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#1b5879] text-white rounded-xl flex items-center justify-center shadow-inner font-bold text-xl">
              +
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-[#1b5879] leading-tight">MediBridge</h1>
              <span className="text-[10px] font-bold text-teal-800 bg-[#c7edf3] px-2 py-0.5 rounded">
                CLINICAL EHR
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowWeightModal(true)}
              className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-1.5 transition"
            >
              <Scale className="w-3.5 h-3.5 text-slate-500" />
              <span>Log Weight ({profile.weight_kg} kg)</span>
            </button>

            <div className="h-6 w-px bg-slate-200" />

            <div className="text-right hidden sm:block">
              <div className="text-sm font-semibold text-slate-800">{profile.name}</div>
              <div className="text-xs text-slate-400">{profile.blood_group} • {profile.sex}</div>
            </div>

            <button
              onClick={handleSignOut}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
              title="Sign Out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <h2 className="font-serif text-2xl font-bold text-[#1b5879]">Hello, {profile.name} 👋</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Ready to capture readings from your BP monitor, glucometer, pulse oximeter, or scale.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => {
                  setScanDefaultDevice(activeTab);
                  setShowScanModal(true);
                }}
                className="px-4 py-2.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-sm font-semibold rounded-xl flex items-center gap-2 shadow-sm transition"
              >
                <Camera className="w-4 h-4" />
                <span>Snap Device Photo</span>
              </button>
              <button 
                onClick={() => {
                  setScanDefaultDevice(activeTab);
                  setShowScanModal(true);
                }}
                className="px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-xl flex items-center gap-2 shadow-sm transition"
              >
                <Upload className="w-4 h-4" />
                <span>Upload Screenshot</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3 mt-4 text-xs">
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block font-medium">Height</span>
              <span className="text-sm font-bold text-slate-700">{profile.height_cm} cm</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block font-medium">Current Weight</span>
              <span className="text-sm font-bold text-slate-700">{profile.weight_kg} kg</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block font-medium">Blood Group</span>
              <span className="text-sm font-bold text-[#1b5879]">{profile.blood_group}</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block font-medium">Activity Level</span>
              <span className="text-sm font-bold text-slate-700">{profile.activity_level} / 10</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 block font-medium">Age</span>
              <span className="text-sm font-bold text-slate-700">{new Date().getFullYear() - new Date(profile.dob).getFullYear()} yrs</span>
            </div>
            {profile.pregnancy_status && (
              <div className="p-2.5 bg-[#e4f3f6] rounded-xl border border-[#c7edf3]">
                <span className="text-teal-700 block font-medium">Gestational Age</span>
                <span className="text-sm font-bold text-teal-900">{profile.gestational_age_weeks || '—'} wks</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {/* Vitals Tab Switcher */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab('blood_pressure')}
                  className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 transition ${
                    activeTab === 'blood_pressure'
                      ? 'bg-[#1b5879] text-white shadow-sm'
                      : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                  }`}
                >
                  <Heart className={`w-4 h-4 ${activeTab === 'blood_pressure' ? 'text-white' : 'text-rose-500'}`} />
                  <span>Blood Pressure</span>
                  <span className={`text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-bold ${
                    activeTab === 'blood_pressure' ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {bpMeasurements.length}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('blood_glucose')}
                  className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 transition ${
                    activeTab === 'blood_glucose'
                      ? 'bg-[#1b5879] text-white shadow-sm'
                      : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                  }`}
                >
                  <Droplet className={`w-4 h-4 ${activeTab === 'blood_glucose' ? 'text-white' : 'text-teal-600'}`} />
                  <span>Blood Glucose</span>
                  <span className={`text-[10px] sm:text-xs px-2 py-0.5 rounded-full font-bold ${
                    activeTab === 'blood_glucose' ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {glucoseMeasurements.length}
                  </span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => token && loadMeasurements(token)}
                  disabled={measurementsLoading}
                  className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
                  title="Refresh Timeline"
                >
                  <RefreshCw className={`w-4 h-4 ${measurementsLoading ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={() => {
                    setScanDefaultDevice(activeTab);
                    setShowScanModal(true);
                  }}
                  className="px-3 py-1.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition shadow-sm"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Add Reading</span>
                  <span className="sm:hidden">Add</span>
                </button>
              </div>
            </div>

            {/* Active Tab Timeline Display */}
            {measurementsLoading && bpMeasurements.length === 0 && glucoseMeasurements.length === 0 ? (
              <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center gap-3">
                <Activity className="w-8 h-8 animate-spin text-[#1b5879]" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Loading clinical vitals...
                </p>
              </div>
            ) : activeTab === 'blood_pressure' ? (
              <BloodPressureTimeline
                measurements={bpMeasurements}
                onAddNew={() => {
                  setScanDefaultDevice('blood_pressure');
                  setShowScanModal(true);
                }}
              />
            ) : (
              <BloodGlucoseTimeline
                measurements={glucoseMeasurements}
                onAddNew={() => {
                  setScanDefaultDevice('blood_glucose');
                  setShowScanModal(true);
                }}
              />
            )}
          </div>

          <div className="space-y-6">
            <div className="bg-[#1b5879] text-white rounded-2xl p-6 shadow-md">
              <div className="flex items-center gap-2 text-teal-300 text-xs font-bold uppercase tracking-wider mb-2">
                <Sparkles className="w-4 h-4" /> Grounded AI Insights
              </div>
              <h4 className="text-sm font-semibold mb-2">Deterministic Trend Engine</h4>
              <p className="text-xs text-slate-200 leading-relaxed">
                As soon as you log readings, our deterministic engine calculates rolling averages and flags trends, which the AI explains without making unauthorized medical diagnoses.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-5 h-5 text-[#1b5879]" />
                <h4 className="text-sm font-bold text-slate-800">Clinician Health Report</h4>
              </div>
              <p className="text-xs text-slate-500 mb-4 leading-relaxed">
                Generates a clean 1-page summary of your blood pressure, glucose, and weight for your doctor.
              </p>
              <button disabled className="w-full py-2.5 px-3 bg-slate-100 text-slate-400 text-xs font-semibold rounded-xl border border-slate-200 cursor-not-allowed">
                Report will activate after first reading
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Quick Weight Update Modal */}
      {showWeightModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl border border-slate-100">
            <h3 className="text-base font-bold text-slate-800 mb-1 flex items-center gap-2">
              <Scale className="w-5 h-5 text-[#1b5879]" /> Update Current Weight
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Regular weight updates allow tracking fluid retention and metabolic correlations.
            </p>
            <form onSubmit={handleWeightUpdate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Weight (kg)</label>
                <input
                  type="number"
                  step="0.1"
                  min="15"
                  max="400"
                  required
                  autoFocus
                  value={newWeight}
                  onChange={(e) => setNewWeight(e.target.value)}
                  placeholder={profile.weight_kg.toString()}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowWeightModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={weightLoading}
                  className="px-4 py-2 bg-[#1b5879] hover:bg-[#14425b] text-white text-xs font-semibold rounded-xl transition"
                >
                  {weightLoading ? 'Saving...' : 'Save Weight'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Multimodal Clinical Scan Modal (BP & Glucometer) */}
      {token && (
        <ScanModal
          isOpen={showScanModal}
          onClose={() => setShowScanModal(false)}
          token={token}
          defaultDeviceType={scanDefaultDevice}
          onMeasurementSaved={(m) => {
            if ('systolic' in m.values) {
              setBpMeasurements(prev => [m as BloodPressureMeasurement, ...prev]);
              setActiveTab('blood_pressure');
            } else {
              setGlucoseMeasurements(prev => [m as BloodGlucoseMeasurement, ...prev]);
              setActiveTab('blood_glucose');
            }
          }}
        />
      )}
    </div>
  );
}
