import React from 'react';
import { ShieldCheck, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white py-12 text-slate-500 text-xs sm:text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <ShieldCheck className="w-4 h-4 text-teal-700" />
          <span>HealthTrace — Device-Agnostic Medical Recording</span>
        </div>

        <p className="text-center sm:text-right text-slate-500">
          Personal data remains private, standardized, and patient-owned.
        </p>
      </div>
    </footer>
  );
}
