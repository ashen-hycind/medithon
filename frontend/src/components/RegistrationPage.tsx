import React, { useState } from 'react';
import { 
  signInWithPopup, 
  createUserWithEmailAndPassword, 
  updateProfile,
  setPersistence, 
  browserLocalPersistence 
} from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { ArrowLeft, ShieldCheck, Eye, EyeOff, Check, ArrowRight } from 'lucide-react';

interface RegistrationPageProps {
  onBack: () => void;
  onNavigateLogin: () => void;
  onSuccess: () => void;
}

export const RegistrationPage: React.FC<RegistrationPageProps> = ({ 
  onBack, 
  onNavigateLogin, 
  onSuccess 
}) => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreed, setAgreed] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogleSignUp = async () => {
    try {
      setLoading(true);
      setError(null);
      await setPersistence(auth, browserLocalPersistence);
      await signInWithPopup(auth, googleProvider);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to sign up with Google');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (!agreed) {
      setError('Please agree to the Terms of Service & Privacy Policy.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await setPersistence(auth, browserLocalPersistence);
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      // Save display name to Firebase Auth user
      if (userCredential.user) {
        await updateProfile(userCredential.user, { displayName: fullName });
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to create account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col font-sans selection:bg-[#e7f8fa] selection:text-[#1b5879]">
      {/* Top Header */}
      <header className="w-full border-b border-[#edf2f4] py-4 px-6 sm:px-12 bg-white">
        <div className="max-w-[1180px] mx-auto flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[13px] font-semibold text-slate-600 hover:text-[#1b5879] transition"
          >
            <ArrowLeft className="w-4 h-4 text-slate-500" />
            <span>Back to MediBridge</span>
          </button>

          <div className="flex items-center gap-2 text-[12px] text-slate-500">
            <span>Protected by</span>
            <div className="flex items-center gap-1.5 font-bold text-[#1b5879] bg-[#e7f8fa] px-2.5 py-1 rounded-md border border-[#c4edf2]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#1b5879]" />
              <span>FHIR R4 Security</span>
            </div>
          </div>
        </div>
      </header>

      {/* Center Form Container */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-[460px] bg-white rounded-[20px] p-8 sm:p-10 shadow-[0_4px_30px_rgba(0,0,0,0.06)] border border-[#edf2f4]">
          
          {/* MediBridge Cross Badge */}
          <div className="flex justify-center mb-6">
            <div className="w-12 h-12 rounded-[14px] bg-[#1b5879] flex items-center justify-center text-white text-2xl font-bold shadow-sm">
              <span className="leading-none pb-0.5">+</span>
            </div>
          </div>

          <div className="text-center mb-8">
            <h1 className="font-serif text-[28px] font-bold text-[#1b5879] tracking-tight">
              Create your account
            </h1>
            <p className="text-[13px] text-slate-500 mt-1.5 font-sans leading-relaxed">
              Sign up to start tracking chronic vitals with evidence-linked OCR.
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3.5 bg-rose-50 border border-rose-200 text-rose-700 text-[12px] rounded-[10px] leading-relaxed">
              {error}
            </div>
          )}

          {/* Google Button */}
          <button
            type="button"
            onClick={handleGoogleSignUp}
            disabled={loading}
            className="w-full py-3 px-4 flex items-center justify-center gap-3 bg-white border border-[#e2e8f0] hover:bg-slate-50 text-slate-700 text-[13px] font-semibold rounded-[10px] transition shadow-sm mb-6 disabled:opacity-60"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

          {/* Divider */}
          <div className="relative flex py-2 items-center mb-6">
            <div className="flex-grow border-t border-[#edf2f4]"></div>
            <span className="flex-shrink mx-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              OR CONTINUE WITH EMAIL
            </span>
            <div className="flex-grow border-t border-[#edf2f4]"></div>
          </div>

          <form onSubmit={handleEmailSignUp} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wide mb-1.5">
                FULL NAME
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Madhav Sharma"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white transition"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wide mb-1.5">
                EMAIL
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="madhav.sharma@medibridge.health"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white transition"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wide mb-1.5">
                PASSWORD
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-[#e2e8f0] rounded-[10px] text-[13px] text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1b5879] focus:bg-white transition pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <div className="flex items-center gap-1 text-[11px] text-[#6b855d] mt-1.5 font-medium">
                <span>✓</span>
                <span>Must be at least 6 characters with secure salt</span>
              </div>
            </div>

            {/* Terms Checkbox */}
            <div className="pt-1">
              <label className="flex items-start gap-2.5 cursor-pointer select-none text-[11px] text-slate-600 leading-normal">
                <input
                  type="checkbox"
                  required
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  className="w-4 h-4 mt-0.5 text-[#1b5879] rounded border-slate-300 focus:ring-[#1b5879]"
                />
                <span>
                  I agree to the <span className="font-semibold text-slate-700">Terms of Service</span>, <span className="font-semibold text-slate-700">Privacy Policy</span>, and <span className="font-semibold text-slate-700">HIPAA-compliant health data encryption agreement</span>.
                </span>
              </label>
            </div>

            {/* Create Account Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-3 py-3 px-4 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] flex items-center justify-center gap-2 transition shadow-md disabled:opacity-60"
            >
              <span>{loading ? 'Creating Account...' : 'Create Account & Setup Profile →'}</span>
            </button>
          </form>

          {/* Next Step Calibration Pill */}
          <div className="mt-6 p-3 bg-[#f3fbfc] border border-[#e2f1f4] rounded-[12px] flex items-center gap-3 text-left">
            <span className="w-7 h-7 rounded-full bg-[#1b5879] text-white text-[12px] font-bold flex items-center justify-center flex-shrink-0">
              1
            </span>
            <div>
              <div className="text-[11px] font-bold text-[#1b5879]">
                Next Step: Baseline Health Calibration
              </div>
              <div className="text-[10px] text-slate-500">
                3 quick clinical steps to calibrate your vital ranges.
              </div>
            </div>
          </div>

          {/* Switch to Sign In */}
          <div className="mt-6 text-center text-[12px] text-slate-500">
            <span>Already have a MediBridge account? </span>
            <button
              type="button"
              onClick={onNavigateLogin}
              className="font-bold text-[#1b5879] hover:underline"
            >
              Sign In
            </button>
          </div>

        </div>
      </main>
    </div>
  );
};
