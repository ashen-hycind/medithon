import React from 'react';

/**
 * SubtleEdgeDecorations
 *
 * Distinct, elegant hand-drawn medical equipment line-art & subtle scribble decorations
 * placed around the outer edges, gaps, and margins of the MediBridge clinical dashboard.
 *
 * Doctor Equipments included (hand-drawn SaaS line-art):
 * 1. Stethoscope (Binaural headset, looping rubber tube, acoustic diaphragm & soundwaves)
 * 2. Electrocardiogram (ECG / Cardiac Rhythm wave trace with P-Q-R-S-T peaks)
 * 3. Clinical Glass Thermometer (Calibrated scale ticks, mercury bulb & reservoir)
 * 4. Sphygmomanometer (Blood pressure gauge dial, needle, tubing & inflation bulb)
 * 5. Reflex Hammer & Otoscope head contours
 * 6. Minimalist Medical Cross & Floating Rx Capsule accents
 *
 * Contrast & Visibility:
 * - Opacities increased to 0.35 - 0.55 for clear visibility around & behind cards
 * - Deep MediBridge Navy (#1b5879), Cyan Accent (#c3edf2), Sky Blue (#0284c7)
 * - Stroke width 1.35px - 1.8px for crisp, professional line quality
 * - Kept strictly behind cards (z-0, pointer-events-none select-none)
 */
export const SubtleEdgeDecorations: React.FC = () => {
  return (
    <div
      className="absolute inset-0 pointer-events-none overflow-hidden z-0 select-none"
      aria-hidden="true"
    >
      {/* ========================================================================= */}
      {/* 1. TOP-RIGHT CORNER & RIGHT EDGE: ELEGANT HAND-DRAWN STETHOSCOPE         */}
      {/* ========================================================================= */}
      <svg
        className="absolute right-0 top-2 sm:top-6 w-[360px] sm:w-[460px] lg:w-[540px] h-[480px] lg:h-[560px] text-[#1b5879] overflow-visible"
        viewBox="0 0 540 560"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* --- STETHOSCOPE HEADSET --- */}
        {/* Left Eartip */}
        <ellipse cx="380" cy="36" rx="4.5" ry="3" fill="#1b5879" className="opacity-60" transform="rotate(-15 380 36)" />
        {/* Right Eartip */}
        <ellipse cx="440" cy="30" rx="4.5" ry="3" fill="#1b5879" className="opacity-60" transform="rotate(15 440 30)" />

        {/* Left Binaural Tube */}
        <path
          d="M 380 38 C 382 68, 400 95, 412 115"
          stroke="#1b5879"
          strokeWidth="1.75"
          strokeLinecap="round"
          className="opacity-55"
        />
        {/* Right Binaural Tube */}
        <path
          d="M 440 32 C 438 65, 424 95, 412 115"
          stroke="#1b5879"
          strokeWidth="1.75"
          strokeLinecap="round"
          className="opacity-55"
        />

        {/* Binaural Tension Spring Bridge */}
        <path
          d="M 388 68 Q 410 74, 432 64"
          stroke="#0284c7"
          strokeWidth="1.3"
          strokeLinecap="round"
          className="opacity-50"
        />

        {/* Y-Connector Stem */}
        <path
          d="M 412 115 L 412 135"
          stroke="#1b5879"
          strokeWidth="2.2"
          strokeLinecap="round"
          className="opacity-60"
        />

        {/* --- STETHOSCOPE FLEXIBLE TUBING --- */}
        {/* Looping down, curving outward into the visible margin, and wrapping behind the cards */}
        <path
          d="M 412 135 C 410 180, 485 190, 475 250 C 465 305, 385 280, 415 350 C 440 405, 510 390, 500 460 C 492 510, 430 520, 390 535"
          stroke="#1b5879"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-50"
        />

        {/* Parallel highlight stroke on rubber tubing */}
        <path
          d="M 414 140 C 413 182, 482 192, 472 250 C 462 302, 388 282, 417 350 C 441 402, 507 392, 497 458"
          stroke="#c3edf2"
          strokeWidth="0.9"
          strokeLinecap="round"
          className="opacity-60"
        />

        {/* --- STETHOSCOPE CHESTPIECE (Diaphragm & Bell) --- */}
        <g transform="translate(365, 505) rotate(-20)">
          {/* Stem connector */}
          <rect x="22" y="0" width="6" height="14" rx="2" fill="#1b5879" className="opacity-55" />
          {/* Bell housing */}
          <path d="M 12 14 C 18 10, 32 10, 38 14 L 44 22 L 6 22 Z" fill="#c3edf2" stroke="#1b5879" strokeWidth="1.5" className="opacity-55" />
          {/* Main Diaphragm outer ring */}
          <circle cx="25" cy="38" r="22" stroke="#1b5879" strokeWidth="1.8" fill="#ffffff" className="opacity-60" />
          {/* Inner acoustic membrane */}
          <circle cx="25" cy="38" r="16" stroke="#0284c7" strokeWidth="1.2" strokeDasharray="3 2" fill="#c3edf2" className="opacity-50 fill-opacity-40" />
          {/* Center diaphragm pip */}
          <circle cx="25" cy="38" r="4.5" fill="#1b5879" className="opacity-55" />

          {/* Soundwave radiation ripples peeking out */}
          <path d="M 52 28 C 58 34, 58 42, 52 48" stroke="#0284c7" strokeWidth="1.3" strokeLinecap="round" className="opacity-55" />
          <path d="M 58 22 C 67 32, 67 44, 58 54" stroke="#0284c7" strokeWidth="1.1" strokeLinecap="round" className="opacity-45" />
        </g>

        {/* --- CLINICAL THERMOMETER (Angled in the upper right margin) --- */}
        <g transform="translate(460, 90) rotate(28)">
          {/* Glass Stem */}
          <rect x="0" y="0" width="10" height="75" rx="5" stroke="#1b5879" strokeWidth="1.4" fill="#ffffff" className="opacity-55" />
          {/* Mercury Reservoir Bulb */}
          <circle cx="5" cy="80" r="8" stroke="#1b5879" strokeWidth="1.4" fill="#c3edf2" className="opacity-60" />
          {/* Mercury Liquid Column */}
          <path d="M 5 80 L 5 28" stroke="#0284c7" strokeWidth="2.2" strokeLinecap="round" className="opacity-60" />
          {/* Graduated Measurement Ticks */}
          <line x1="7" y1="35" x2="11" y2="35" stroke="#1b5879" strokeWidth="1" className="opacity-55" />
          <line x1="7" y1="42" x2="13" y2="42" stroke="#1b5879" strokeWidth="1.2" className="opacity-60" />
          <line x1="7" y1="49" x2="11" y2="49" stroke="#1b5879" strokeWidth="1" className="opacity-55" />
          <line x1="7" y1="56" x2="13" y2="56" stroke="#1b5879" strokeWidth="1.2" className="opacity-60" />
          <line x1="7" y1="63" x2="11" y2="63" stroke="#1b5879" strokeWidth="1" className="opacity-55" />
          {/* Digital Temp readout indicator scribble */}
          <text x="14" y="24" fontSize="9" fontWeight="bold" fill="#1b5879" className="opacity-55 font-mono">37.0°C</text>
        </g>

        {/* Floating abstract scribble accents */}
        <path
          d="M 280 60 C 315 35, 360 45, 375 75 C 388 100, 365 125, 340 120 C 315 115, 310 85, 335 75"
          stroke="#1b5879"
          strokeWidth="1.3"
          strokeLinecap="round"
          className="opacity-45"
        />
        <path
          d="M 440 230 Q 470 215, 495 240 T 520 275"
          stroke="#0284c7"
          strokeWidth="1.2"
          strokeDasharray="4 3"
          strokeLinecap="round"
          className="opacity-45"
        />

        {/* Stipples & Sparkles */}
        <circle cx="340" cy="45" r="2" fill="#1b5879" className="opacity-50" />
        <circle cx="490" cy="180" r="2.5" fill="#0284c7" className="opacity-50" />
        <path d="M 430 185 Q 430 193, 438 193 Q 430 193, 430 201 Q 430 193, 422 193 Q 430 193, 430 185" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />
      </svg>

      {/* ========================================================================= */}
      {/* 2. MIDDLE GAP & LEFT MARGIN: CARDIAC ECG WAVE & REFLEX HAMMER             */}
      {/* ========================================================================= */}
      <svg
        className="absolute left-0 top-[200px] sm:top-[220px] w-full max-w-[1440px] h-[160px] text-[#1b5879] overflow-visible"
        viewBox="0 0 1440 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Continuous ECG Rhythm Wave running through the horizontal gap behind cards */}
        <path
          d="M 0 80 H 70 C 78 72, 86 72, 94 80 H 120 L 128 88 L 138 20 L 148 120 L 158 80 H 180 C 190 70, 204 70, 214 80 H 340 C 348 72, 356 72, 364 80 H 388 L 396 88 L 406 25 L 416 115 L 426 80 H 450 C 460 70, 474 70, 484 80 H 680 C 688 72, 696 72, 704 80 H 728 L 736 88 L 746 18 L 756 122 L 766 80 H 790 C 800 70, 814 70, 824 80 H 1020 C 1028 72, 1036 72, 1044 80 H 1068 L 1076 88 L 1086 24 L 1096 118 L 1106 80 H 1130 C 1140 70, 1154 70, 1164 80 H 1440"
          stroke="#1b5879"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-45"
        />

        {/* Faint Cyan Echo Line above ECG Wave */}
        <path
          d="M 30 68 H 110 L 138 12 L 148 108 L 158 68 H 220"
          stroke="#0284c7"
          strokeWidth="1"
          strokeDasharray="4 3"
          strokeLinecap="round"
          className="opacity-40"
        />
        <path
          d="M 700 68 H 720 L 746 10 L 756 110 L 766 68 H 830"
          stroke="#0284c7"
          strokeWidth="1"
          strokeDasharray="4 3"
          strokeLinecap="round"
          className="opacity-40"
        />

        {/* Cardiac telemetry pulse nodes */}
        <circle cx="138" cy="20" r="3" fill="#1b5879" className="opacity-60" />
        <circle cx="406" cy="25" r="3" fill="#1b5879" className="opacity-60" />
        <circle cx="746" cy="18" r="3" fill="#1b5879" className="opacity-60" />
        <circle cx="1086" cy="24" r="3" fill="#1b5879" className="opacity-60" />

        {/* --- CLINICAL REFLEX HAMMER (Taylor Tomahawk) on the left margin --- */}
        <g transform="translate(18, 15) rotate(22)">
          {/* Triangular Rubber Head */}
          <polygon points="25,5 45,28 5,28" stroke="#1b5879" strokeWidth="1.6" fill="#c3edf2" className="opacity-55" />
          <polygon points="25,9 41,26 9,26" fill="#1b5879" className="opacity-30" />
          {/* Metal ferrule collar */}
          <rect x="22" y="28" width="6" height="5" fill="#1b5879" className="opacity-60" />
          {/* Long Chrome Handle */}
          <path d="M 25 33 L 25 110 C 25 116, 22 122, 25 125 C 28 122, 25 116, 25 110" stroke="#1b5879" strokeWidth="2.2" strokeLinecap="round" className="opacity-55" />
          {/* Handle grip rings */}
          <line x1="22" y1="80" x2="28" y2="80" stroke="#0284c7" strokeWidth="1.2" className="opacity-50" />
          <line x1="22" y1="86" x2="28" y2="86" stroke="#0284c7" strokeWidth="1.2" className="opacity-50" />
          <line x1="22" y1="92" x2="28" y2="92" stroke="#0284c7" strokeWidth="1.2" className="opacity-50" />
        </g>
      </svg>

      {/* ========================================================================= */}
      {/* 3. BOTTOM-RIGHT PERIPHERY: SPHYGMOMANOMETER (BP DIAL & INFLATION BULB)    */}
      {/* ========================================================================= */}
      <svg
        className="absolute right-0 bottom-0 w-[380px] sm:w-[460px] lg:w-[520px] h-[340px] lg:h-[400px] text-[#1b5879] overflow-visible"
        viewBox="0 0 520 400"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* --- SPHYGMOMANOMETER PRESSURE GAUGE DIAL --- */}
        <g transform="translate(310, 140)">
          {/* Mounting Stem */}
          <rect x="36" y="78" width="8" height="18" rx="2" fill="#1b5879" className="opacity-55" />
          {/* Gauge Outer Chrome Bezel */}
          <circle cx="40" cy="40" r="38" stroke="#1b5879" strokeWidth="2" fill="#ffffff" className="opacity-60" />
          {/* Inner Calibration Ring */}
          <circle cx="40" cy="40" r="32" stroke="#0284c7" strokeWidth="1.2" strokeDasharray="3 2" fill="#c3edf2" className="opacity-45 fill-opacity-25" />

          {/* Scale graduation tick marks */}
          <line x1="40" y1="12" x2="40" y2="17" stroke="#1b5879" strokeWidth="1.5" className="opacity-60" />
          <line x1="60" y1="20" x2="56" y2="24" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />
          <line x1="68" y1="40" x2="63" y2="40" stroke="#1b5879" strokeWidth="1.5" className="opacity-60" />
          <line x1="60" y1="60" x2="56" y2="56" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />
          <line x1="40" y1="68" x2="40" y2="63" stroke="#1b5879" strokeWidth="1.5" className="opacity-60" />
          <line x1="20" y1="60" x2="24" y2="56" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />
          <line x1="12" y1="40" x2="17" y2="40" stroke="#1b5879" strokeWidth="1.5" className="opacity-60" />
          <line x1="20" y1="20" x2="24" y2="24" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />

          {/* Manometer Dial Needle pointing at ~120 mmHg target */}
          <line x1="40" y1="40" x2="40" y2="18" stroke="#1b5879" strokeWidth="2" strokeLinecap="round" className="opacity-65" />
          {/* Center Hub */}
          <circle cx="40" cy="40" r="4.5" fill="#1b5879" className="opacity-65" />
          <circle cx="40" cy="40" r="2" fill="#ffffff" className="opacity-80" />

          {/* Text notation: mmHg */}
          <text x="32" y="53" fontSize="7.5" fontWeight="bold" fill="#1b5879" className="opacity-55 font-sans">mmHg</text>
        </g>

        {/* --- CONNECTING PRESSURE TUBING --- */}
        <path
          d="M 350 236 C 350 290, 420 270, 435 320 C 445 355, 410 375, 450 395"
          stroke="#1b5879"
          strokeWidth="2"
          strokeLinecap="round"
          className="opacity-50"
        />

        {/* --- INFLATION BULB WITH AIR VALVE --- */}
        <g transform="translate(425, 275) rotate(-15)">
          {/* Air Release Thumbscrew Valve */}
          <rect x="14" y="0" width="8" height="12" rx="2" stroke="#1b5879" strokeWidth="1.2" fill="#c3edf2" className="opacity-55" />
          <line x1="12" y1="6" x2="24" y2="6" stroke="#1b5879" strokeWidth="1.4" className="opacity-60" />
          {/* Rubber Bulb Body (Contoured pear shape) */}
          <path
            d="M 18 12 C 32 18, 38 45, 32 68 C 26 88, 10 88, 4 68 C -2 45, 4 18, 18 12 Z"
            stroke="#1b5879"
            strokeWidth="1.8"
            fill="#ffffff"
            className="opacity-60"
          />
          {/* Rubber Ribbed Texture Lines */}
          <path d="M 6 38 Q 18 42, 30 38" stroke="#0284c7" strokeWidth="1.2" strokeLinecap="round" className="opacity-45" />
          <path d="M 6 48 Q 18 52, 30 48" stroke="#0284c7" strokeWidth="1.2" strokeLinecap="round" className="opacity-45" />
          <path d="M 8 58 Q 18 62, 28 58" stroke="#0284c7" strokeWidth="1.2" strokeLinecap="round" className="opacity-45" />
        </g>

        {/* Multi-tier organic scribble flourish in the bottom corner */}
        <path
          d="M 40 310 C 110 265, 165 330, 235 285 C 290 250, 310 180, 370 215 C 410 240, 400 310, 350 330 C 300 350, 240 315, 275 375"
          stroke="#1b5879"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-40"
        />

        {/* Faint accent dashes */}
        <path
          d="M 120 230 C 175 190, 225 230, 280 195 C 335 160, 375 200, 430 170"
          stroke="#0284c7"
          strokeWidth="1.1"
          strokeDasharray="5 3"
          strokeLinecap="round"
          className="opacity-35"
        />
      </svg>

      {/* ========================================================================= */}
      {/* 4. BOTTOM-LEFT & LOWER GUTTER: CLINICAL CROSS, OTOSCOPE & CAPSULES        */}
      {/* ========================================================================= */}
      <svg
        className="absolute left-0 bottom-0 w-[360px] sm:w-[440px] lg:w-[480px] h-[320px] lg:h-[360px] text-[#1b5879] overflow-visible"
        viewBox="0 0 480 360"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* --- ELEGANT CLINICAL MEDICAL CROSS --- */}
        <g transform="translate(65, 140)">
          {/* Outer soft glow offset cross */}
          <path
            d="M 22 4 H 38 V 22 H 56 V 38 H 38 V 56 H 22 V 38 H 4 V 22 H 22 Z"
            stroke="#0284c7"
            strokeWidth="1"
            strokeDasharray="3 3"
            className="opacity-45"
          />
          {/* Main Hand-drawn Medical Cross */}
          <path
            d="M 20 0 H 40 V 20 H 60 V 40 H 40 V 60 H 20 V 40 H 0 V 20 H 20 Z"
            stroke="#1b5879"
            strokeWidth="1.8"
            strokeLinejoin="round"
            fill="#c3edf2"
            className="opacity-60 fill-opacity-40"
          />
          {/* Center inner heart emblem in cross */}
          <path
            d="M 30 25 C 30 22, 26 20, 24 22 C 22 24, 22 27, 30 33 C 38 27, 38 24, 36 22 C 34 20, 30 22, 30 25 Z"
            fill="#1b5879"
            className="opacity-50"
          />
        </g>

        {/* --- FLOATING MEDICINE CAPSULE WITH CELLULAR STIPPLES --- */}
        <g transform="translate(180, 220) rotate(35)">
          {/* Capsule Shell */}
          <rect x="0" y="0" width="16" height="42" rx="8" stroke="#1b5879" strokeWidth="1.6" fill="#ffffff" className="opacity-60" />
          {/* Top Half Fill */}
          <path d="M 0 8 C 0 3.5, 3.5 0, 8 0 C 12.5 0, 16 3.5, 16 8 L 16 21 L 0 21 Z" fill="#c3edf2" className="opacity-55" />
          {/* Midline Joint */}
          <line x1="0" y1="21" x2="16" y2="21" stroke="#1b5879" strokeWidth="1.4" className="opacity-60" />
          {/* Micro active ingredient microbeads */}
          <circle cx="5" cy="28" r="1.2" fill="#0284c7" className="opacity-55" />
          <circle cx="11" cy="30" r="1.2" fill="#1b5879" className="opacity-55" />
          <circle cx="8" cy="35" r="1.2" fill="#0284c7" className="opacity-55" />
        </g>

        {/* Secondary Capsule Accent */}
        <g transform="translate(240, 280) rotate(-25)">
          <rect x="0" y="0" width="12" height="30" rx="6" stroke="#0284c7" strokeWidth="1.3" strokeDasharray="3 2" fill="#c3edf2" className="opacity-45 fill-opacity-20" />
          <line x1="0" y1="15" x2="12" y2="15" stroke="#0284c7" strokeWidth="1.2" className="opacity-50" />
        </g>

        {/* Undulating bottom wave scribble */}
        <path
          d="M -20 220 C 50 240, 100 185, 160 210 C 220 235, 250 295, 310 270 C 360 250, 390 185, 450 215"
          stroke="#1b5879"
          strokeWidth="1.4"
          strokeLinecap="round"
          className="opacity-40"
        />

        {/* Flowing dashed echo trace */}
        <path
          d="M 10 250 C 65 265, 110 212, 170 232 C 225 252, 260 310, 320 286 C 365 270, 405 218, 455 242"
          stroke="#0284c7"
          strokeWidth="1.1"
          strokeDasharray="4 4"
          strokeLinecap="round"
          className="opacity-35"
        />

        {/* Sparkle starburst accents */}
        <path d="M 140 100 Q 140 109, 149 109 Q 140 109, 140 118 Q 140 109, 131 109 Q 140 109, 140 100" stroke="#1b5879" strokeWidth="1.2" className="opacity-55" />
        <circle cx="105" cy="85" r="2" fill="#0284c7" className="opacity-50" />
        <circle cx="210" cy="180" r="2" fill="#1b5879" className="opacity-50" />
      </svg>
    </div>
  );
};

export default SubtleEdgeDecorations;
