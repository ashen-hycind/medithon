import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  RefreshCw,
  AlertTriangle,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldCheck,
  Heart,
  Droplet,
  Info,
  Clock,
  Flame,
  CheckCircle2
} from 'lucide-react';
import { HealthAnalysisResponse, CorrelationItem, CorrelationCategory } from '../types';
import { getHealthCorrelations, triggerFreshAnalysis } from '../services/measurementService';

interface AIInsightsCardProps {
  token: string | null;
  refreshTrigger?: number; // increments when a new measurement is logged
}

export function AIInsightsCard({ token, refreshTrigger = 0 }: AIInsightsCardProps) {
  const [analysis, setAnalysis] = useState<HealthAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = async (force: boolean = false) => {
    if (!token) return;
    if (force) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = force
        ? await triggerFreshAnalysis(token)
        : await getHealthCorrelations(token);
      setAnalysis(data);
    } catch (err: any) {
      console.error('Failed to load health correlation analysis:', err);
      setError(err.message || 'Unable to generate clinical correlations.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchAnalysis(false);
    } else {
      setAnalysis(null);
    }
  }, [token, refreshTrigger]);

  // Category badge helper
  const getCategoryMeta = (category: CorrelationCategory) => {
    switch (category) {
      case 'lifestyle_trigger':
        return {
          label: 'Lifestyle Trigger',
          bg: 'bg-amber-50',
          text: 'text-amber-700',
          border: 'border-amber-200'
        };
      case 'metabolic_cardiovascular':
        return {
          label: 'Metabolic & Cardio',
          bg: 'bg-purple-50',
          text: 'text-purple-700',
          border: 'border-purple-200'
        };
      case 'symptom_spike':
        return {
          label: 'Symptom Co-occurrence',
          bg: 'bg-rose-50',
          text: 'text-rose-700',
          border: 'border-rose-200'
        };
      case 'longitudinal_trend':
        return {
          label: 'Longitudinal Trajectory',
          bg: 'bg-sky-50',
          text: 'text-sky-700',
          border: 'border-sky-200'
        };
      case 'fluid_weight_shift':
        return {
          label: 'Fluid & Weight Shift',
          bg: 'bg-cyan-50',
          text: 'text-cyan-700',
          border: 'border-cyan-200'
        };
      default:
        return {
          label: 'Clinical Observation',
          bg: 'bg-slate-50',
          text: 'text-slate-700',
          border: 'border-slate-200'
        };
    }
  };

  // Confidence badge helper
  const getConfidenceBadge = (confidence: string) => {
    if (confidence === 'high') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-2.5 h-2.5" /> High Confidence
        </span>
      );
    }
    if (confidence === 'moderate') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
          Moderate
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
        Emerging
      </span>
    );
  };

  // Trend slope helper
  const renderTrendIndicator = () => {
    if (!analysis?.patterns?.bp_trend) return null;
    const trend = analysis.patterns.bp_trend;
    const slope = trend.ols_slope_mmhg_per_reading;
    const label = trend.trend_label || 'stable';

    let icon = <Minus className="w-3.5 h-3.5 text-slate-500" />;
    let badgeColor = 'bg-slate-100 text-slate-700';

    if (label.includes('rising')) {
      icon = <TrendingUp className="w-3.5 h-3.5 text-rose-500" />;
      badgeColor = 'bg-rose-50 text-rose-700 border border-rose-200';
    } else if (label.includes('falling')) {
      icon = <TrendingDown className="w-3.5 h-3.5 text-emerald-500" />;
      badgeColor = 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    }

    return (
      <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-100 text-xs">
        <span className="text-slate-500 font-medium flex items-center gap-1.5">
          {icon} Systolic Trajectory
        </span>
        <span className={`px-2 py-0.5 rounded-md font-bold uppercase text-[10px] tracking-wider ${badgeColor}`}>
          {label} {slope !== null && slope !== undefined ? `(${slope > 0 ? '+' : ''}${slope} mmHg/rdg)` : ''}
        </span>
      </div>
    );
  };

  if (loading && !analysis) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 bg-slate-200 rounded w-1/3"></div>
          <div className="h-4 bg-slate-200 rounded w-16"></div>
        </div>
        <div className="h-20 bg-slate-100 rounded-xl"></div>
        <div className="h-24 bg-slate-100 rounded-xl"></div>
      </div>
    );
  }

  const hasReadings =
    analysis &&
    (analysis.stats.total_bp_readings > 0 || analysis.stats.total_glucose_readings > 0);

  return (
    <div className="space-y-4">
      {/* Header Bar */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-teal-50 rounded-lg text-teal-600">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 leading-none">
                Grounded AI Insights
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">
                Deterministic Cross-Stream Evaluation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {analysis?.rote_memory?.session_resumed && (
              <span
                className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#1b5879]/10 text-[#1b5879] border border-[#1b5879]/20"
                title={`Checkpoint v${analysis.rote_memory.checkpoint_version}`}
              >
                <Clock className="w-2.5 h-2.5" /> v{analysis.rote_memory.checkpoint_version}
              </span>
            )}
            <button
              onClick={() => fetchAnalysis(true)}
              disabled={refreshing}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
              title="Force Fresh Recomputation"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#1b5879]' : ''}`} />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 mb-3 bg-rose-50 text-rose-700 text-xs rounded-xl border border-rose-200 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Urgent Alerts Banner */}
        {analysis?.urgent_alerts && analysis.urgent_alerts.length > 0 && (
          <div className="mb-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl space-y-1.5">
            <div className="flex items-center gap-1.5 text-rose-800 text-xs font-bold uppercase tracking-wider">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              <span>Priority Safety Warning</span>
            </div>
            {analysis.urgent_alerts.map((alert, idx) => (
              <p key={idx} className="text-xs text-rose-700 leading-relaxed font-medium">
                • {alert}
              </p>
            ))}
          </div>
        )}

        {/* Doctor Summary Banner */}
        {hasReadings && analysis?.doctor_summary && (
          <div className="bg-gradient-to-br from-slate-900 via-[#1b5879] to-[#14425b] text-white rounded-xl p-4 shadow-sm relative overflow-hidden mb-4">
            <div className="flex items-center gap-1.5 text-teal-300 text-[10px] font-bold uppercase tracking-wider mb-2">
              <Activity className="w-3 h-3" /> Clinical Evaluation Note
            </div>
            <p className="text-xs text-slate-100 leading-relaxed font-normal">
              {analysis.doctor_summary}
            </p>

            {analysis.rote_memory?.trajectory_shift_summary && (
              <div className="mt-2.5 pt-2 border-t border-white/15 text-[11px] text-teal-200 flex items-start gap-1.5">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{analysis.rote_memory.trajectory_shift_summary}</span>
              </div>
            )}
          </div>
        )}

        {/* Quick Pattern Diagnostic Grid */}
        {hasReadings && (
          <div className="space-y-2 mb-4">
            {renderTrendIndicator()}

            {analysis?.patterns?.consecutive_elevated_streak?.current_streak !== undefined && (
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-100 text-xs">
                <span className="text-slate-500 font-medium flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5 text-amber-500" /> Stage 1+ Run Streak
                </span>
                <span className="font-bold text-slate-700">
                  {analysis.patterns.consecutive_elevated_streak.current_streak} consecutive (max {analysis.patterns.consecutive_elevated_streak.longest_streak})
                </span>
              </div>
            )}

            {analysis?.stats?.morning_avg_bp && analysis?.stats?.evening_avg_bp && (
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-100 text-xs">
                <span className="text-slate-500 font-medium flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-500" /> Diurnal Vitals
                </span>
                <span className="font-semibold text-slate-700">
                  AM: {analysis.stats.morning_avg_bp.systolic}/{analysis.stats.morning_avg_bp.diastolic} | PM: {analysis.stats.evening_avg_bp.systolic}/{analysis.stats.evening_avg_bp.diastolic}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Active Correlation Findings List */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Discovered Correlations
            </h4>
            <span className="text-[10px] font-semibold text-slate-400">
              {analysis?.correlations?.length || 0} findings
            </span>
          </div>

          {!hasReadings ? (
            <div className="py-6 text-center text-slate-400 space-y-2">
              <Sparkles className="w-6 h-6 mx-auto text-slate-300" />
              <p className="text-xs font-medium">No biometric records yet.</p>
              <p className="text-[11px] text-slate-400">
                Log your first blood pressure or glucose reading to activate longitudinal pattern recognition.
              </p>
            </div>
          ) : analysis?.correlations && analysis.correlations.length > 0 ? (
            <div className="space-y-2.5">
              {analysis.correlations.map((item: CorrelationItem, idx: number) => {
                const meta = getCategoryMeta(item.category);
                return (
                  <div
                    key={idx}
                    className="p-3 bg-white rounded-xl border border-slate-200 hover:border-slate-300 transition shadow-2xs space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${meta.bg} ${meta.text} ${meta.border}`}>
                        {meta.label}
                      </span>
                      {getConfidenceBadge(item.confidence)}
                    </div>

                    <h5 className="text-xs font-bold text-slate-800 leading-snug">
                      {item.headline}
                    </h5>

                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      {item.explanation}
                    </p>

                    {item.clinical_suggestion && (
                      <div className="p-2 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-1.5 text-[11px] text-slate-700">
                        <ShieldCheck className="w-3.5 h-3.5 text-[#1b5879] shrink-0 mt-0.5" />
                        <span className="leading-snug">{item.clinical_suggestion}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-4 text-center text-slate-400 text-xs">
              <CheckCircle2 className="w-5 h-5 mx-auto text-emerald-500 mb-1" />
              <p className="font-medium text-slate-600">Stable Baseline Profile</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                No acute confounders or cross-stream anomalies detected.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
