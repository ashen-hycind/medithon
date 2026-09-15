import React, { useState, useRef, useEffect } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, ChevronDown, Check } from 'lucide-react';

interface ModernCalendarPickerProps {
  value: string; // YYYY-MM-DD
  onChange: (dateStr: string) => void;
  minYear?: number;
  maxYear?: number;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const SHORT_MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

const DAYS_OF_WEEK = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

export const ModernCalendarPicker: React.FC<ModernCalendarPickerProps> = ({
  value,
  onChange,
  minYear = 1920,
  maxYear = new Date().getFullYear()
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Parse initial date
  const parseDate = (str: string) => {
    if (!str) return new Date(2000, 0, 1);
    const [y, m, d] = str.split('-').map(Number);
    if (!y || !m || !d) return new Date(2000, 0, 1);
    return new Date(y, m - 1, d);
  };

  const selectedDate = parseDate(value);

  // View state: 'days' | 'months' | 'years'
  const [viewMode, setViewMode] = useState<'days' | 'months' | 'years'>('days');
  const [viewYear, setViewYear] = useState(selectedDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(selectedDate.getMonth());

  // Year decade page for years view
  const [decadeStart, setDecadeStart] = useState(Math.floor(selectedDate.getFullYear() / 12) * 12);

  // Synchronize when value changes externally
  useEffect(() => {
    const d = parseDate(value);
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
    setDecadeStart(Math.floor(d.getFullYear() / 12) * 12);
  }, [value]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setViewMode('days');
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Days in month calculation
  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month, 1).getDay();
  };

  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((prev) => prev - 1);
    } else {
      setViewMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    const today = new Date();
    if (viewYear === today.getFullYear() && viewMonth >= today.getMonth()) {
      return; // Cannot go to future months for DOB
    }
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((prev) => prev + 1);
    } else {
      setViewMonth((prev) => prev + 1);
    }
  };

  const handleSelectDay = (day: number) => {
    const m = String(viewMonth + 1).padStart(2, '0');
    const d = String(day).padStart(2, '0');
    const newStr = `${viewYear}-${m}-${d}`;
    onChange(newStr);
    setIsOpen(false);
    setViewMode('days');
  };

  const formatDisplayDate = (str: string) => {
    try {
      const d = parseDate(str);
      const day = d.getDate();
      const month = MONTH_NAMES[d.getMonth()];
      const year = d.getFullYear();
      const weekday = d.toLocaleDateString('en-US', { weekday: 'short' });
      return { day, month, year, weekday, formatted: `${day} ${month} ${year}` };
    } catch {
      return { day: 1, month: 'January', year: 2000, weekday: 'Sat', formatted: str };
    }
  };

  const dateInfo = formatDisplayDate(value);

  // Render Day Cells
  const totalDays = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth);
  const prevMonthDays = getDaysInMonth(viewYear, viewMonth - 1);

  const today = new Date();
  const isCurrentMonthFuture =
    viewYear > today.getFullYear() ||
    (viewYear === today.getFullYear() && viewMonth > today.getMonth());

  // Decade years array
  const decadeYears = Array.from({ length: 12 }, (_, i) => decadeStart + i).filter(
    (y) => y >= minYear && y <= maxYear
  );

  return (
    <div className="relative w-full" ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 hover:bg-slate-100/80 border rounded-[12px] text-left transition shadow-xs group ${
          isOpen
            ? 'border-[#1b5879] ring-2 ring-[#1b5879]/15 bg-white'
            : 'border-[#e2e8f0] hover:border-slate-300'
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[8px] bg-[#e7f8fa] text-[#1b5879] flex items-center justify-center transition group-hover:scale-105">
            <CalendarIcon className="w-4 h-4 text-[#1b5879]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif text-[15px] font-bold text-[#1b5879]">
                {dateInfo.formatted}
              </span>
              <span className="text-[11px] font-medium text-slate-400">
                • {dateInfo.weekday}
              </span>
            </div>
            <span className="text-[10px] text-slate-400 block -mt-0.5">
              Click to browse calendar
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-[#6b855d] bg-[#f0f6ee] px-2 py-0.5 rounded-[6px]">
            Change
          </span>
          <ChevronDown
            className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
              isOpen ? 'rotate-180 text-[#1b5879]' : ''
            }`}
          />
        </div>
      </button>

      {/* Popover Calendar Modal */}
      {isOpen && (
        <div className="absolute left-0 top-[calc(100%+8px)] z-50 w-full sm:w-[340px] bg-white rounded-[20px] p-5 shadow-[0_16px_48px_rgba(27,88,121,0.14)] border border-[#c4edf2]/60 animate-in fade-in zoom-in-95 duration-150">
          {/* Header Navigation */}
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#edf2f4]">
            {viewMode === 'days' && (
              <>
                <button
                  type="button"
                  onClick={() => setViewMode('months')}
                  className="px-2.5 py-1 rounded-[8px] hover:bg-[#f0f9fa] text-[13px] font-bold text-[#1b5879] flex items-center gap-1 transition"
                >
                  <span>{MONTH_NAMES[viewMonth]}</span>
                  <ChevronDown className="w-3 h-3 text-[#1b5879]" />
                </button>

                <button
                  type="button"
                  onClick={() => setViewMode('years')}
                  className="px-2.5 py-1 rounded-[8px] hover:bg-[#f0f9fa] text-[13px] font-serif font-bold text-[#1b5879] flex items-center gap-1 transition"
                >
                  <span>{viewYear}</span>
                  <ChevronDown className="w-3 h-3 text-[#1b5879]" />
                </button>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handlePrevMonth}
                    className="w-7 h-7 rounded-[7px] flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition"
                    title="Previous month"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={handleNextMonth}
                    disabled={
                      viewYear >= today.getFullYear() && viewMonth >= today.getMonth()
                    }
                    className="w-7 h-7 rounded-[7px] flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition disabled:opacity-30 disabled:hover:bg-transparent"
                    title="Next month"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </>
            )}

            {viewMode === 'months' && (
              <div className="flex items-center justify-between w-full">
                <span className="text-[13px] font-bold text-[#1b5879]">
                  Select Month ({viewYear})
                </span>
                <button
                  type="button"
                  onClick={() => setViewMode('days')}
                  className="text-[11px] font-bold text-slate-500 hover:text-[#1b5879]"
                >
                  Back to Days
                </button>
              </div>
            )}

            {viewMode === 'years' && (
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setDecadeStart((p) => Math.max(minYear, p - 12))}
                    className="w-7 h-7 rounded-[7px] flex items-center justify-center text-slate-500 hover:bg-slate-100"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-[13px] font-serif font-bold text-[#1b5879]">
                    {decadeStart} – {Math.min(maxYear, decadeStart + 11)}
                  </span>
                  <button
                    type="button"
                    onClick={() => setDecadeStart((p) => Math.min(maxYear - 11, p + 12))}
                    className="w-7 h-7 rounded-[7px] flex items-center justify-center text-slate-500 hover:bg-slate-100"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setViewMode('days')}
                  className="text-[11px] font-bold text-slate-500 hover:text-[#1b5879]"
                >
                  Back
                </button>
              </div>
            )}
          </div>

          {/* VIEW: DAYS GRID */}
          {viewMode === 'days' && (
            <div>
              {/* Day names */}
              <div className="grid grid-cols-7 gap-1 text-center mb-1">
                {DAYS_OF_WEEK.map((d) => (
                  <span
                    key={d}
                    className="text-[10px] font-bold text-slate-400 uppercase tracking-wider py-1"
                  >
                    {d}
                  </span>
                ))}
              </div>

              {/* Day cells */}
              <div className="grid grid-cols-7 gap-1 text-center">
                {/* Previous month filler days */}
                {Array.from({ length: firstDay }, (_, i) => {
                  const dayNum = prevMonthDays - firstDay + i + 1;
                  return (
                    <div
                      key={`prev-${i}`}
                      className="h-8 flex items-center justify-center text-[12px] text-slate-300 pointer-events-none"
                    >
                      {dayNum}
                    </div>
                  );
                })}

                {/* Current month days */}
                {Array.from({ length: totalDays }, (_, i) => {
                  const dayNum = i + 1;
                  const isSelected =
                    selectedDate.getFullYear() === viewYear &&
                    selectedDate.getMonth() === viewMonth &&
                    selectedDate.getDate() === dayNum;

                  const isFuture =
                    viewYear > today.getFullYear() ||
                    (viewYear === today.getFullYear() && viewMonth > today.getMonth()) ||
                    (viewYear === today.getFullYear() &&
                      viewMonth === today.getMonth() &&
                      dayNum > today.getDate());

                  return (
                    <button
                      key={dayNum}
                      type="button"
                      disabled={isFuture}
                      onClick={() => handleSelectDay(dayNum)}
                      className={`h-8 w-8 mx-auto rounded-[8px] text-[12px] font-medium transition flex items-center justify-center relative ${
                        isSelected
                          ? 'bg-[#1b5879] text-white font-bold shadow-sm'
                          : isFuture
                          ? 'text-slate-200 cursor-not-allowed'
                          : 'text-slate-700 hover:bg-[#e7f8fa] hover:text-[#1b5879]'
                      }`}
                    >
                      {dayNum}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* VIEW: MONTHS GRID */}
          {viewMode === 'months' && (
            <div className="grid grid-cols-3 gap-2 py-2">
              {SHORT_MONTHS.map((mName, idx) => {
                const isSelected =
                  selectedDate.getMonth() === idx && selectedDate.getFullYear() === viewYear;
                const isFutureMonth =
                  viewYear === today.getFullYear() && idx > today.getMonth();

                return (
                  <button
                    key={mName}
                    type="button"
                    disabled={isFutureMonth}
                    onClick={() => {
                      setViewMonth(idx);
                      setViewMode('days');
                    }}
                    className={`py-2.5 rounded-[10px] text-[12px] font-semibold transition ${
                      isSelected
                        ? 'bg-[#1b5879] text-white font-bold shadow-xs'
                        : isFutureMonth
                        ? 'text-slate-300 cursor-not-allowed'
                        : 'text-slate-700 bg-slate-50 hover:bg-[#e7f8fa] hover:text-[#1b5879]'
                    }`}
                  >
                    {mName}
                  </button>
                );
              })}
            </div>
          )}

          {/* VIEW: YEARS GRID */}
          {viewMode === 'years' && (
            <div className="grid grid-cols-3 gap-2 py-2">
              {decadeYears.map((yr) => {
                const isSelected = selectedDate.getFullYear() === yr;
                const isFuture = yr > today.getFullYear();

                return (
                  <button
                    key={yr}
                    type="button"
                    disabled={isFuture}
                    onClick={() => {
                      setViewYear(yr);
                      setViewMode('months');
                    }}
                    className={`py-2.5 rounded-[10px] font-serif text-[13px] font-bold transition ${
                      isSelected
                        ? 'bg-[#1b5879] text-white shadow-xs'
                        : isFuture
                        ? 'text-slate-300 cursor-not-allowed'
                        : 'text-slate-700 bg-slate-50 hover:bg-[#e7f8fa] hover:text-[#1b5879]'
                    }`}
                  >
                    {yr}
                  </button>
                );
              })}
            </div>
          )}

          {/* Quick Year Fast-Jump Anchors */}
          <div className="mt-4 pt-3 border-t border-[#edf2f4] flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium">Quick Year:</span>
            <div className="flex gap-1.5">
              {[2007, 2000, 1995, 1990, 1985].map((quickYear) => (
                <button
                  key={quickYear}
                  type="button"
                  onClick={() => {
                    setViewYear(quickYear);
                    setViewMode('days');
                  }}
                  className={`px-1.5 py-0.5 rounded-[5px] text-[10px] font-bold transition ${
                    viewYear === quickYear
                      ? 'bg-[#1b5879] text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-[#e7f8fa] hover:text-[#1b5879]'
                  }`}
                >
                  {quickYear}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
