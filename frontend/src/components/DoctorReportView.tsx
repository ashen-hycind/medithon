import React, { useState } from 'react';
import {
  FileText,
  Download,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Activity,
  Heart,
  Droplet,
  Scale,
  ShieldCheck,
  ArrowLeft
} from 'lucide-react';
import { UserProfile } from '../types';
import { generateDoctorReportPdf } from '../services/measurementService';

interface DoctorReportViewProps {
  token: string | null;
  profile: UserProfile;
  bpCount: number;
  spo2Count: number;
  gluCount: number;
  weightCount: number;
  onBackToDashboard: () => void;
}

export const DoctorReportView: React.FC<DoctorReportViewProps> = ({
  token,
  profile,
  bpCount,
  spo2Count,
  gluCount,
  weightCount,
  onBackToDashboard
}) => {
  const [generating, setGenerating] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateReport = async () => {
    if (!token) {
      setError('You must be logged in to generate a report.');
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const blob = await generateDoctorReportPdf(token);
      // Revoke previous URL if any
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
      }
      const newUrl = URL.createObjectURL(blob);
      setPdfBlobUrl(newUrl);
      setReportGeneratedAt(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (err: any) {
      console.error('Failed to generate Doctor Report PDF:', err);
      setError(err?.message || 'Failed to generate Doctor Health Report. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!pdfBlobUrl) return;
    const a = document.createElement('a');
    a.href = pdfBlobUrl;
    const dateStr = new Date().toISOString().slice(0, 10);
    a.download = `MediBridge_Doctor_Health_Report_${profile.name.replace(/\s+/g, '_')}_${dateStr}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleOpenNewTab = () => {
    if (!pdfBlobUrl) return;
    window.open(pdfBlobUrl, '_blank');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Breadcrumb Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToDashboard}
            className="flex items-center gap-1 text-[12.5px] font-bold text-[#1b5879] hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Dashboard</span>
          </button>
          <span className="text-slate-300">/</span>
          <span className="text-[12.5px] font-medium text-[#536b78]">Clinical Documents</span>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-[#536b78] bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
          <ShieldCheck className="w-3.5 h-3.5 text-[#1b5879]" />
          <span>Clinician-Facing PDF Audit Document</span>
        </div>
      </div>

      {/* Main Action Banner */}
      <div className="bg-white border border-[#e2e8f0] rounded-[24px] p-6 sm:p-8 shadow-[0_4px_24px_rgba(27,88,121,0.04)] space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-[12px] bg-[#c3edf2] text-[#1b5879] flex items-center justify-center font-bold text-lg flex-shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-serif text-xl sm:text-2xl font-bold text-[#142833] tracking-tight">
                  Doctor Health Report
                </h2>
                <p className="text-[12px] sm:text-[13px] text-[#536b78]">
                  Longitudinal Telemetry Audit &amp; Clinician Consultation Summary
                </p>
              </div>
            </div>
            <p className="text-[12px] sm:text-[12.5px] text-[#536b78] leading-relaxed pt-1">
              Generates a comprehensive, publication-grade clinical PDF report directly from the patient’s current stored health records. Every time you click generate, the backend pulls the latest dataset, computes strict statistical baselines, renders high-resolution charts, and provides MedGemma clinical reasoning.
            </p>
          </div>

          {/* Action Button */}
          <div className="flex flex-col gap-2.5 flex-shrink-0">
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className="px-6 py-3.5 bg-[#1b5879] hover:bg-[#14425b] text-white text-[13.5px] font-bold rounded-[14px] shadow-sm hover:shadow transition flex items-center justify-center gap-2.5 disabled:opacity-60 disabled:cursor-not-allowed group"
            >
              <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
              <span>{generating ? 'Generating Latest Report...' : pdfBlobUrl ? 'Regenerate Fresh Report' : 'Generate Doctor Report'}</span>
            </button>
            <span className="text-[10.5px] text-center text-slate-400 font-medium">
              Always freshly computed from latest data
            </span>
          </div>
        </div>

        {/* Live Ingestion Telemetry Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-[14px] flex items-center gap-3">
            <div className="w-8 h-8 rounded-[10px] bg-rose-100 text-rose-700 flex items-center justify-center shrink-0">
              <Heart className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[10.5px] text-[#536b78] truncate font-medium">Blood Pressure</div>
              <div className="text-[13px] font-bold text-[#142833]">{bpCount} reading{bpCount !== 1 ? 's' : ''}</div>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-[14px] flex items-center gap-3">
            <div className="w-8 h-8 rounded-[10px] bg-sky-100 text-sky-700 flex items-center justify-center shrink-0">
              <Activity className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[10.5px] text-[#536b78] truncate font-medium">Pulse Oximeter</div>
              <div className="text-[13px] font-bold text-[#142833]">{spo2Count} reading{spo2Count !== 1 ? 's' : ''}</div>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-[14px] flex items-center gap-3">
            <div className="w-8 h-8 rounded-[10px] bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <Droplet className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[10.5px] text-[#536b78] truncate font-medium">Blood Glucose</div>
              <div className="text-[13px] font-bold text-[#142833]">{gluCount} reading{gluCount !== 1 ? 's' : ''}</div>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-[14px] flex items-center gap-3">
            <div className="w-8 h-8 rounded-[10px] bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
              <Scale className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[10.5px] text-[#536b78] truncate font-medium">Weight Scale</div>
              <div className="text-[13px] font-bold text-[#142833]">{weightCount} reading{weightCount !== 1 ? 's' : ''}</div>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-[14px] flex items-start gap-2.5 text-rose-800 text-[12px]">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Failed to generate Doctor Report</p>
              <p className="text-rose-700 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Generating Progress State */}
        {generating && (
          <div className="p-6 bg-slate-50 border border-slate-200 rounded-[18px] text-center space-y-3">
            <RefreshCw className="w-7 h-7 text-[#1b5879] animate-spin mx-auto" />
            <div className="space-y-1">
              <p className="font-serif text-[15px] font-bold text-[#142833]">
                Generating Dynamic Doctor Report...
              </p>
              <p className="text-[11.5px] text-[#536b78] max-w-md mx-auto">
                Ingesting current health records, calculating deterministic statistical baselines, plotting vector charts with Matplotlib, and assembling ReportLab PDF document.
              </p>
            </div>
          </div>
        )}

        {/* Success Toolbar and Controls */}
        {pdfBlobUrl && !generating && (
          <div className="space-y-4 pt-2">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-[16px] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <div>
                  <span className="font-bold text-[13px] text-emerald-900">
                    Report Generated Successfully
                  </span>
                  <span className="text-[11px] text-emerald-700 block">
                    Generated at {reportGeneratedAt} • Complete multi-page clinical document
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2.5 flex-wrap">
                <button
                  onClick={handleOpenNewTab}
                  className="px-4 py-2 bg-white text-[#1b5879] border border-[#1b5879]/30 hover:border-[#1b5879] text-[12px] font-bold rounded-[10px] shadow-2xs hover:shadow-xs transition flex items-center gap-1.5"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open PDF</span>
                </button>

                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-[#1b5879] hover:bg-[#14425b] text-white text-[12px] font-bold rounded-[10px] shadow-xs hover:shadow transition flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF</span>
                </button>
              </div>
            </div>

            {/* Embedded Live PDF Viewer */}
            <div className="rounded-[20px] overflow-hidden border border-slate-200 shadow-sm bg-slate-800">
              <div className="px-4 py-2.5 bg-slate-900 text-slate-300 text-[11px] flex items-center justify-between">
                <span>Embedded PDF Viewer</span>
                <span>Use controls below or click Open PDF to view full screen</span>
              </div>
              <iframe
                src={pdfBlobUrl}
                title="Doctor Health Report Preview"
                className="w-full h-[700px] border-none bg-white"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
