import React from 'react';
import { 
  ArrowRight, 
  Layers, 
  CheckCircle2, 
  Smartphone, 
  Sparkles,
  TrendingUp,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  ArrowDown
} from 'lucide-react';

export default function ProblemMissionHero({ onOpenRegister, onOpenLogin }) {
  return (
    <main className="relative overflow-hidden pt-12 pb-24 lg:pt-20 lg:pb-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Core Motto & Mission Statement */}
        <div className="text-center max-w-3xl mx-auto mb-16 lg:mb-24">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200/80 text-teal-800 text-xs font-semibold uppercase tracking-wider mb-6">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            Device-Agnostic Health Continuity
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.15]">
            Turn fragmented health readings into <span className="text-teal-700">one trusted record</span>.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 leading-relaxed font-normal">
            For chronic conditions, isolated measurements tell only half the story. We bridge your blood pressure cuffs, glucometers, scales, and test strips into a standardized longitudinal health dataset patients and doctors can understand.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3.5">
            <button
              onClick={onOpenRegister}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-teal-800 hover:bg-teal-900 active:bg-teal-950 text-white font-medium text-sm sm:text-base shadow-md transition"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={onOpenLogin}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-medium text-sm sm:text-base border border-slate-200 shadow-sm transition"
            >
              <span>Sign In to Existing Record</span>
            </button>
          </div>
        </div>

        {/* The Problem We Are Solving */}
        <section aria-labelledby="problem-heading" className="mt-8 lg:mt-16">
          <div className="bg-slate-900 rounded-3xl p-8 sm:p-12 lg:p-16 text-slate-100 shadow-xl ring-1 ring-slate-800">
            <div className="max-w-2xl">
              <h2 id="problem-heading" className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                The Problem: Your vital health data is scattered and stranded.
              </h2>
              <p className="mt-3 text-slate-400 text-sm sm:text-base leading-relaxed">
                Every device generates valuable longitudinal data, but locks it inside siloed ecosystems, proprietary apps, or paper slips:
              </p>
            </div>

            {/* Split comparison: Fragmented Reality vs Unified Truth */}
            <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
              
              {/* Fragmented Reality */}
              <div className="rounded-2xl bg-slate-950/60 border border-slate-800 p-6 sm:p-7 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold uppercase tracking-wider mb-4">
                    <AlertTriangle className="w-4 h-4" />
                    Today’s Fragmented Reality
                  </div>
                  <ul className="space-y-3.5 text-sm text-slate-300">
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0 mt-2" />
                      <span><strong>Incompatible Devices:</strong> Blood pressure monitor from one vendor, glucometer from another, paper test strips from a clinic.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0 mt-2" />
                      <span><strong>Disconnected Records:</strong> Screenshots, handwritten notebooks, and forgotten app passwords with no single timeline.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0 mt-2" />
                      <span><strong>Doctor Appointments:</strong> Doctors only see sporadic single-point measurements instead of true multi-week clinical patterns.</span>
                    </li>
                  </ul>
                </div>
                <div className="mt-6 pt-5 border-t border-slate-800/80 text-xs text-slate-500 font-mono">
                  Status: Fragmented • Context loss high
                </div>
              </div>

              {/* Unified Solution */}
              <div className="rounded-2xl bg-teal-950/40 border border-teal-500/30 p-6 sm:p-7 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-teal-400 text-xs font-semibold uppercase tracking-wider mb-4">
                    <CheckCircle2 className="w-4 h-4 text-teal-400" />
                    Our Unified Solution
                  </div>
                  <ul className="space-y-3.5 text-sm text-slate-200">
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0 mt-2" />
                      <span><strong>Zero Vendor Lock-In:</strong> Works with any hardware via camera OCR, direct photo capture, or manual verification.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0 mt-2" />
                      <span><strong>Standardized Longitudinal Datasets:</strong> Systolic/diastolic, glucose, SpO₂, weight, and urinalysis on one calibrated axis.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0 mt-2" />
                      <span><strong>Clinician-Ready Insights:</strong> Export structured, concise trend summaries designed for doctor reviews in seconds.</span>
                    </li>
                  </ul>
                </div>
                <div className="mt-6 pt-5 border-t border-teal-900/60 text-xs text-teal-300 font-mono flex items-center justify-between">
                  <span>Status: Unified Continuous Record</span>
                  <span className="text-teal-400 font-semibold">Ready</span>
                </div>
              </div>

            </div>

            {/* Bottom Call to Action banner inside Problem Block */}
            <div className="mt-10 pt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <span className="text-sm text-slate-400">
                Take control of your home health history in minutes.
              </span>
              <button
                onClick={onOpenRegister}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs sm:text-sm font-semibold transition"
              >
                Create Free Account
              </button>
            </div>

          </div>
        </section>

      </div>
    </main>
  );
}
