import React, { useState } from 'react';
import { 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  setPersistence, 
  browserLocalPersistence 
} from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { ArrowLeft, ShieldCheck, Eye, EyeOff, Check, Zap } from 'lucide-react';

interface LoginPageProps {
  onBack: () => void;
  onNavigateRegister: () => void;
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onBack, onNavigateRegister, onSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogleSignIn = async () => {
    try {
      setLoading(true);
      setError(null);
      await setPersistence(auth, browserLocalPersistence);
      await signInWithPopup(auth, googleProvider);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to sign in with Google');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in both email and password.');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      await setPersistence(auth, browserLocalPersistence);
      await signInWithEmailAndPassword(auth, email, password);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillQuickDemo = () => {
    setEmail('demo@user.com');
    setPassword('abc123');
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
              Welcome back
            </h1>
            <p className="text-[13px] text-slate-500 mt-1.5 font-sans leading-relaxed">
              Sign in to continue to your MediBridge health dashboard.
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
            onClick={handleGoogleSignIn}
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

          <form onSubmit={handleEmailSignIn} className="space-y-4">
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
            </div>

            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between pt-1 text-[12px]">
              <label className="flex items-center gap-2 cursor-pointer select-none text-slate-600">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 text-[#1b5879] rounded border-slate-300 focus:ring-[#1b5879]"
                />
                <span>Remember me</span>
              </label>
              <a href="#forgot" className="text-[#1b5879] font-semibold hover:underline">
                Forgot password?
              </a>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] flex items-center justify-center gap-2 transition shadow-md disabled:opacity-60"
            >
              <span>{loading ? 'Signing in...' : 'Sign In to MediBridge →'}</span>
            </button>
          </form>

          {/* Quick Demo Access Card */}
          <div 
            onClick={fillQuickDemo}
            className="mt-6 p-3.5 bg-[#f0f9fa] border border-[#d2f0f4] hover:border-[#b4e6ec] rounded-[12px] cursor-pointer transition text-left"
          >
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[12px] font-bold text-[#1b5879] flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                <span>⚡ Quick Demo Access</span>
              </span>
              <span className="text-[10px] font-bold text-teal-700 bg-teal-100/70 px-1.5 py-0.5 rounded">DEMO</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight">
              Auto-fills verified clinical demo credentials
            </p>
            <span className="text-[10px] text-[#1b5879] font-semibold mt-1 block">
              Click to test instant live EHR environment
            </span>
          </div>

          {/* Switch to Register */}
          <div className="mt-7 text-center text-[12px] text-slate-500">
            <span>Don't have an account? </span>
            <button
              type="button"
              onClick={onNavigateRegister}
              className="font-bold text-[#1b5879] hover:underline"
            >
              Create an account
            </button>
          </div>

        </div>
      </main>
    </div>
  );
};
