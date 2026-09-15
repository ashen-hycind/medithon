import React from 'react';

interface LandingPageProps {
  onOpenAuth: (mode: 'signin' | 'register') => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  return (
    <div className="min-h-screen bg-white text-slate-800 flex flex-col font-sans selection:bg-[#e7f8fa] selection:text-[#1b5879]">
      {/* Top Header Navbar */}
      <header className="w-full bg-white border-b border-[#edf2f4] py-4 px-6 sm:px-10 sticky top-0 z-30">
        <div className="max-w-[1180px] mx-auto flex items-center justify-between">
          
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-[34px] h-[34px] rounded-[10px] bg-[#1b5879] flex items-center justify-center text-white text-lg font-bold shadow-sm">
              <span className="leading-none pb-0.5">+</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[20px] font-bold text-[#1b5879] tracking-tight font-sans">MediBridge</span>
              <span className="text-[9px] font-extrabold tracking-wider text-teal-800 bg-[#c4edf2] px-1.5 py-0.5 rounded-[3px] uppercase font-sans">
                CLINICAL EHR
              </span>
            </div>
          </div>

          {/* Navigation Items */}
          <div className="flex items-center gap-7">
            <nav className="hidden md:flex items-center gap-6 text-[13px] font-semibold text-slate-600 font-sans">
              <a href="#chronic-conditions" className="hover:text-[#1b5879] transition">Chronic Conditions</a>
              <a href="#device-support" className="hover:text-[#1b5879] transition">Device Support</a>
            </nav>

            <div className="flex items-center gap-2.5 font-sans">
              <button
                onClick={() => onOpenAuth('signin')}
                className="px-4 py-2 text-[13px] font-semibold text-[#1b5879] bg-[#e7f8fa] hover:bg-[#d9f2f5] rounded-[8px] transition"
              >
                Sign In
              </button>
              <button
                onClick={() => onOpenAuth('register')}
                className="px-4 py-2 text-[13px] font-semibold text-white bg-[#6b855d] hover:bg-[#5c744f] rounded-[8px] transition shadow-sm"
              >
                Register +
              </button>
            </div>
          </div>

        </div>
      </header>

      {/* Hero Section */}
      <section className="w-full pt-12 pb-16 px-6 sm:px-10">
        <div className="max-w-[1180px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          
          {/* Left Hero Column */}
          <div className="lg:col-span-7 space-y-6">
            <h1 className="font-serif text-[42px] sm:text-[50px] lg:text-[54px] font-bold text-[#1b5879] tracking-tight leading-[1.12]">
              From scattered device displays to a unified clinical health record.
            </h1>

            <p className="text-[13px] sm:text-[14px] text-slate-500 max-w-lg leading-relaxed font-normal font-sans">
              Capture readings from your blood pressure monitor, pulse oximeter, digital scale, or glucometer using your phone camera. MediBridge deterministically validates digits, tracks longitudinal diurnal trends, and provides evidence-linked AI summaries.
            </p>

            {/* CTA Button */}
            <div className="flex flex-wrap items-center gap-3.5 pt-1 font-sans">
              <button
                onClick={() => onOpenAuth('register')}
                className="px-5 py-3 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13px] font-bold rounded-[10px] shadow transition flex items-center gap-2"
              >
                <span>Create Health Passport (Register)</span>
                <span>+</span>
              </button>
            </div>

            {/* 3 Stats Row */}
            <div className="grid grid-cols-3 gap-6 pt-8 border-t border-slate-100 max-w-md font-sans">
              <div>
                <div className="font-serif text-[26px] font-bold text-[#1b5879]">4 Vitals</div>
                <div className="text-[11px] text-slate-400 font-medium mt-0.5">BP, SpO2, Weight, Sugar</div>
              </div>
              <div>
                <div className="font-serif text-[26px] font-bold text-[#6b855d]">98.4%</div>
                <div className="text-[11px] text-slate-400 font-medium mt-0.5">Verified OCR Confidence</div>
              </div>
              <div>
                <div className="font-serif text-[26px] font-bold text-[#1b5879]">FHIR R4</div>
                <div className="text-[11px] text-slate-400 font-medium mt-0.5">Hospital Interoperable</div>
              </div>
            </div>

          </div>

          {/* Right Hero Column: Direct Vector Art Extracted from Figma */}
          <div className="lg:col-span-5 flex justify-center items-center">
            <div className="relative w-full max-w-[440px]">
              <img 
                src="/doctor_illustration.svg" 
                alt="MediBridge Doctor & Vitals Vector" 
                className="w-full h-auto object-contain select-none pointer-events-none drop-shadow-sm" 
              />
            </div>
          </div>

        </div>
      </section>

      {/* Middle Section: Engineered for the Devices Chronic Patients Actually Use */}
      <section id="device-support" className="w-full bg-[#f3fbfc] py-16 px-6 sm:px-10 border-y border-[#e2f1f4]">
        <div className="max-w-[1180px] mx-auto">
          
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="font-serif text-[28px] sm:text-[32px] font-bold text-[#1b5879] tracking-tight">
              Engineered for the Devices Chronic Patients Actually Use
            </h2>
            <p className="text-[13px] text-slate-500 mt-1 font-sans">
              No expensive Bluetooth hubs required. Simply photograph the physical LCD screen.
            </p>
          </div>

          {/* 4 Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            
            {/* 1. Hypertension */}
            <div className="bg-white rounded-[14px] p-6 shadow-sm border border-slate-100 hover:shadow transition">
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 rounded-full bg-[#d5eff3] flex items-center justify-center">
                  <span className="w-3 h-3 rounded-full bg-[#1b5879]"></span>
                </span>
                <h3 className="font-serif text-[17px] font-bold text-[#1b5879]">Hypertension</h3>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed font-sans">
                Extracts Systolic, Diastolic, and Pulse from Omron and digital BP monitors.
              </p>
            </div>

            {/* 2. Pulse Oximeter */}
            <div className="bg-white rounded-[14px] p-6 shadow-sm border border-slate-100 hover:shadow transition">
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 rounded-full bg-[#dbe8da] flex items-center justify-center">
                  <span className="w-3 h-3 rounded-full bg-[#6b855d]"></span>
                </span>
                <h3 className="font-serif text-[17px] font-bold text-slate-800">Pulse Oximeter</h3>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed font-sans">
                Reads bright LED/OLED numbers on dark clips. Tracks SpO2 & pulse rate.
              </p>
            </div>

            {/* 3. Weighing Scale */}
            <div className="bg-white rounded-[14px] p-6 shadow-sm border border-slate-100 hover:shadow transition">
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 rounded-full bg-[#d5eff3] flex items-center justify-center">
                  <span className="w-3 h-3 rounded-full bg-[#1b5879]"></span>
                </span>
                <h3 className="font-serif text-[17px] font-bold text-[#1b5879]">Weighing Scale</h3>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed font-sans">
                Handles reflective glass scale displays. Monitors weight drift and fluid retention.
              </p>
            </div>

            {/* 4. Glucometer */}
            <div className="bg-white rounded-[14px] p-6 shadow-sm border border-slate-100 hover:shadow transition">
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 rounded-full bg-[#d5eff3] flex items-center justify-center">
                  <span className="w-3 h-3 rounded-full bg-[#1b5879]"></span>
                </span>
                <h3 className="font-serif text-[17px] font-bold text-slate-800">Glucometer</h3>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed font-sans">
                Captures blood glucose in mg/dL. Fasting vs post-meal time-in-range.
              </p>
            </div>

          </div>

        </div>
      </section>

      {/* Bottom Section: We Never Let Raw AI Silently Enter the Medical Record */}
      <section className="w-full py-14 px-6 sm:px-10 bg-white">
        <div className="max-w-[1180px] mx-auto">
          
          <div className="bg-[#1b5879] rounded-[22px] p-8 sm:p-10 text-white shadow-xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Left Column in Navy Container */}
            <div className="lg:col-span-6 space-y-4 pr-0 lg:pr-4">
              <h3 className="font-serif text-[28px] sm:text-[32px] font-bold tracking-tight leading-tight">
                We Never Let Raw AI Silently Enter the Medical Record.
              </h3>
              <p className="text-[13px] text-slate-200 leading-relaxed max-w-md font-sans">
                Vision extraction and medical reasoning are separated. Readings pass deterministic physiological checks, are verified side-by-side by the patient, and link to source photos.
              </p>
              <div className="pt-2 font-sans">
                <button
                  onClick={() => onOpenAuth('register')}
                  className="px-5 py-2.5 bg-white text-[#1b5879] hover:bg-slate-50 text-[12px] font-bold rounded-[10px] shadow transition"
                >
                  Inspect Live Verification Pipeline +
                </button>
              </div>
            </div>

            {/* Right Column in Navy Container: 4 Steps List */}
            <div className="lg:col-span-6 space-y-2.5 font-sans">
              
              <div className="bg-white/10 hover:bg-white/15 transition rounded-[10px] p-3 px-4 flex items-center gap-3.5 border border-white/10">
                <span className="w-5 h-5 rounded-full bg-[#6b855d] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">
                  1
                </span>
                <span className="text-[12px] font-bold tracking-wide text-white">
                  Camera Ingestion & Gemini Multimodal OCR
                </span>
              </div>

              <div className="bg-white/10 hover:bg-white/15 transition rounded-[10px] p-3 px-4 flex items-center gap-3.5 border border-white/10">
                <span className="w-5 h-5 rounded-full bg-[#6b855d] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">
                  2
                </span>
                <span className="text-[12px] font-bold tracking-wide text-white">
                  Deterministic Range & Unit Validation
                </span>
              </div>

              <div className="bg-white/10 hover:bg-white/15 transition rounded-[10px] p-3 px-4 flex items-center gap-3.5 border border-white/10">
                <span className="w-5 h-5 rounded-full bg-[#6b855d] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">
                  3
                </span>
                <span className="text-[12px] font-bold tracking-wide text-white">
                  Side-by-Side Human Verification
                </span>
              </div>

              <div className="bg-white/10 hover:bg-white/15 transition rounded-[10px] p-3 px-4 flex items-center gap-3.5 border border-white/10">
                <span className="w-5 h-5 rounded-full bg-[#6b855d] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">
                  4
                </span>
                <span className="text-[12px] font-bold tracking-wide text-white">
                  Evidence-Linked AI Insights & HL7 FHIR Export
                </span>
              </div>

            </div>

          </div>

        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-slate-100 py-6 px-6 sm:px-10 bg-white mt-auto font-sans">
        <div className="max-w-[1180px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-slate-400">
          <div>
            <span className="font-bold text-[#1b5879]">MediBridge</span>
            <span> - Chronic Care Health Bridge - Compliant with HL7 FHIR R4</span>
          </div>
          <div className="flex items-center gap-2 font-semibold">
            <button onClick={() => onOpenAuth('signin')} className="text-slate-600 hover:text-[#1b5879]">
              Sign In
            </button>
            <span>•</span>
            <button onClick={() => onOpenAuth('register')} className="text-slate-600 hover:text-[#1b5879]">
              Register
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
