import React from 'react';
import { Activity, ShieldCheck, Database, LogIn, UserPlus } from 'lucide-react';

export default function Navbar({ onOpenLogin, onOpenRegister, user, onLogout }) {
  return (
    <header className="sticky top-0 z-40 w-full bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-600/20 border border-teal-500/40 flex items-center justify-center text-teal-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <span className="font-semibold tracking-tight text-white text-base sm:text-lg">
              HealthTrace
            </span>
            <span className="hidden sm:inline-block ml-2 text-xs font-normal text-teal-400/80 bg-teal-950/60 border border-teal-800/40 px-2 py-0.5 rounded-md">
              Longitudinal Health
            </span>
          </div>
        </div>

        {/* Right side auth controls */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-300 hidden sm:inline">
                {user.email || 'Connected User'}
              </span>
              <button
                onClick={onLogout}
                className="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 transition"
              >
                Log Out
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={onOpenLogin}
                className="flex items-center gap-1.5 text-xs sm:text-sm font-medium text-slate-200 hover:text-white px-3 sm:px-4 py-2 rounded-xl transition hover:bg-slate-800/70"
              >
                <LogIn className="w-4 h-4 text-slate-400" />
                <span>Sign In</span>
              </button>
              <button
                onClick={onOpenRegister}
                className="flex items-center gap-1.5 text-xs sm:text-sm font-medium text-white bg-teal-600 hover:bg-teal-500 active:bg-teal-700 px-3.5 sm:px-4 py-2 rounded-xl shadow-sm transition"
              >
                <UserPlus className="w-4 h-4" />
                <span>Create Account</span>
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
