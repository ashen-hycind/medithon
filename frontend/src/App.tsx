import React, { useEffect, useState } from 'react';
import { onAuthStateChanged, signOut, User } from 'firebase/auth';
import { auth } from './firebase';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { RegistrationPage } from './components/RegistrationPage';
import { OnboardingFlow } from './components/OnboardingFlow';
import { DesktopDashboard } from './components/DesktopDashboard';
import { UserProfile, BloodPressureMeasurement, BloodGlucoseMeasurement } from './types';
import { Activity, Scale } from 'lucide-react';
import { ScanModal } from './components/ScanModal';
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
  const [bpMeasurements, setBpMeasurements] = useState<BloodPressureMeasurement[]>([]);
  const [glucoseMeasurements, setGlucoseMeasurements] = useState<BloodGlucoseMeasurement[]>([]);
  const [measurementsLoading, setMeasurementsLoading] = useState(false);
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanDefaultDevice, setScanDefaultDevice] = useState<'blood_pressure' | 'blood_glucose'>('blood_pressure');
  const [refreshDashboardTrigger, setRefreshDashboardTrigger] = useState(0);

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

  // Fully Onboarded User Dashboard View (Figma desktop_dashboard 1 replica)
  return (
    <>
      <DesktopDashboard
        user={user}
        profile={profile}
        token={token || ''}
        onSignOut={handleSignOut}
        onOpenScan={(deviceType) => {
          setScanDefaultDevice(deviceType || 'blood_pressure');
          setShowScanModal(true);
        }}
        onOpenWeightModal={() => setShowWeightModal(true)}
        refreshTrigger={refreshDashboardTrigger}
      />

      {/* Quick Weight Update Modal */}
      {showWeightModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
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
                  placeholder={profile.weight_kg ? profile.weight_kg.toString() : '70'}
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
            } else {
              setGlucoseMeasurements(prev => [m as BloodGlucoseMeasurement, ...prev]);
            }
            setRefreshDashboardTrigger(prev => prev + 1);
          }}
        />
      )}
    </>
  );
}
