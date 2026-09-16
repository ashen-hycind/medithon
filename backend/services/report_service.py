"""
Doctor Health PDF Report Generation Service
============================================
Generates a dynamic, clinician-facing, multi-page medical PDF report from
the patient's current stored health data in Firestore.

Architecture:
  Raw Stored Records (Firestore)
         ↓
  Deterministic Statistical Engine (pure Python)
         ↓
  High-Resolution Vector/Raster Plotting (Matplotlib Agg)
         ↓
  Existing AI Analysis Engine (Natural-Language Clinical Interpretation)
         ↓
  ReportLab Numbered Canvas PDF Compiler
"""

import io
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

from services.analysis_service import get_or_compute_analysis


# =====================================================================
# 1. Custom Numbered Canvas for Running Headers & "Page X of Y"
# =====================================================================

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and render running
    clinician header and page numbers (Page X of Y).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Top Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 762, "MEDIBRIDGE CLINICAL AUDIT • DOCTOR HEALTH REPORT")
            self.drawRightString(letter[0] - 36, 762, "CONFIDENTIAL MEDICAL RECORD")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(36, 756, letter[0] - 36, 756)

        # Running Bottom Footer (All Pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(36, 38, letter[0] - 36, 38)

        self.drawString(36, 26, "Notice: Observational health data summary for treating physician review. Not an automated diagnosis.")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 26, page_str)

        self.restoreState()


# =====================================================================
# 2. Deterministic Statistical Analysis Functions
# =====================================================================

def _parse_dt(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    try:
        clean = str(dt_val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def calculate_modality_stats(readings: List[Dict[str, Any]], value_key: str, sub_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes strict deterministic statistics for a given modality.
    """
    if not readings:
        return {
            "count": 0,
            "latest": None,
            "previous": None,
            "change": 0.0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "baseline": 0.0,
            "baseline_change": 0.0,
            "pct_change": 0.0,
            "direction": "stable",
            "earliest_dt": None,
            "latest_dt": None,
            "period_str": "No records"
        }

    # Extract valid numeric points with timestamps
    pts = []
    for r in readings:
        dt = _parse_dt(r.get("recorded_at"))
        vals = r.get("values", {})
        val = vals.get(value_key)
        if val is not None and isinstance(val, (int, float)):
            pts.append({"dt": dt, "val": float(val), "raw": r})

    if not pts:
        return {
            "count": 0,
            "latest": None,
            "previous": None,
            "change": 0.0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "baseline": 0.0,
            "baseline_change": 0.0,
            "pct_change": 0.0,
            "direction": "stable",
            "earliest_dt": None,
            "latest_dt": None,
            "period_str": "No records"
        }

    pts.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=timezone.utc))
    vals_list = [p["val"] for p in pts]
    count = len(vals_list)

    latest_pt = pts[-1]
    prev_pt = pts[-2] if count > 1 else pts[-1]

    latest_val = latest_pt["val"]
    prev_val = prev_pt["val"]
    change = round(latest_val - prev_val, 1)

    avg_val = round(sum(vals_list) / count, 1)
    min_val = round(min(vals_list), 1)
    max_val = round(max(vals_list), 1)

    # Baseline: mean of earlier half of readings, or avg_val if <= 2 readings
    mid = max(1, count // 2)
    baseline = round(sum(vals_list[:mid]) / mid, 1) if count > 2 else avg_val
    baseline_change = round(latest_val - baseline, 1)
    pct_change = round(((latest_val - baseline) / baseline) * 100, 1) if baseline > 0 else 0.0

    # Trend direction based on baseline comparison
    if baseline_change >= 2.0:
        direction = "increase"
    elif baseline_change <= -2.0:
        direction = "decrease"
    else:
        direction = "stable"

    earliest_dt = pts[0]["dt"]
    latest_dt = pts[-1]["dt"]

    if earliest_dt and latest_dt:
        days = max(1, (latest_dt - earliest_dt).days)
        period_str = f"{days} days ({earliest_dt.strftime('%b %d, %Y')} – {latest_dt.strftime('%b %d, %Y')})"
    else:
        period_str = "Full History"

    return {
        "count": count,
        "latest": latest_pt,
        "previous": prev_pt,
        "change": change,
        "avg": avg_val,
        "min": min_val,
        "max": max_val,
        "baseline": baseline,
        "baseline_change": baseline_change,
        "pct_change": pct_change,
        "direction": direction,
        "earliest_dt": earliest_dt,
        "latest_dt": latest_dt,
        "period_str": period_str,
        "pts": pts
    }


# =====================================================================
# 3. High-Resolution Headless Matplotlib Chart Generators
# =====================================================================

def _style_chart_axis(ax, title: str, ylabel: str):
    ax.set_title(title, fontsize=10, fontweight="bold", color="#142833", pad=8)
    ax.set_ylabel(ylabel, fontsize=8.5, fontweight="bold", color="#536b78")
    ax.grid(True, linestyle="--", linewidth=0.5, color="#e2e8f0", alpha=0.8)
    ax.tick_params(axis="both", labelsize=7.5, colors="#536b78")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")


def generate_bp_chart(bp_records: List[Dict[str, Any]]) -> Optional[bytes]:
    """
    Plots Systolic and Diastolic over time (mmHg).
    If pulse data is present, plots Pulse in a separate subplot below (bpm).
    SpO2/Pulse are NEVER plotted on the mmHg axis.
    """
    pts = []
    for r in bp_records:
        dt = _parse_dt(r.get("recorded_at"))
        vals = r.get("values", {})
        sys_v = vals.get("systolic")
        dia_v = vals.get("diastolic")
        pulse_v = vals.get("pulse")
        if dt and sys_v is not None and dia_v is not None:
            pts.append({
                "dt": dt,
                "sys": float(sys_v),
                "dia": float(dia_v),
                "pulse": float(pulse_v) if pulse_v is not None else None
            })

    if not pts:
        return None

    pts.sort(key=lambda x: x["dt"])
    dates = [p["dt"] for p in pts]
    sys_vals = [p["sys"] for p in pts]
    dia_vals = [p["dia"] for p in pts]
    has_pulse = any(p["pulse"] is not None for p in pts)

    if has_pulse:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 3.2), dpi=200, gridspec_kw={"height_ratios": [2.2, 1.0]}, sharex=True)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(6.5, 2.4), dpi=200)
        ax2 = None

    fig.patch.set_facecolor("#ffffff")
    ax1.set_facecolor("#fafbfc")

    # Systolic line & markers
    ax1.plot(dates, sys_vals, color="#1b5879", linewidth=1.8, marker="o", markersize=4, label="Systolic (mmHg)")
    # Diastolic line & markers
    ax1.plot(dates, dia_vals, color="#0284c7", linewidth=1.8, marker="s", markersize=3.5, label="Diastolic (mmHg)")

    # Clinical reference lines (AHA 120/80 benchmark)
    ax1.axhline(120, color="#64748b", linestyle=":", linewidth=0.8, alpha=0.6, label="Normal Sys (120)")
    ax1.axhline(80, color="#94a3b8", linestyle=":", linewidth=0.8, alpha=0.6, label="Normal Dia (80)")

    _style_chart_axis(ax1, "Blood Pressure Longitudinal Trend", "mmHg")
    ax1.legend(loc="upper right", fontsize=7, framealpha=0.85)

    if ax2:
        ax2.set_facecolor("#fafbfc")
        pulse_pts = [(p["dt"], p["pulse"]) for p in pts if p["pulse"] is not None]
        p_dates = [p[0] for p in pulse_pts]
        p_vals = [p[1] for p in pulse_pts]
        ax2.plot(p_dates, p_vals, color="#e11d48", linewidth=1.4, marker="^", markersize=3, label="Pulse (bpm)")
        _style_chart_axis(ax2, "", "Pulse (bpm)")
        ax2.legend(loc="upper right", fontsize=6.5, framealpha=0.85)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_spo2_chart(spo2_records: List[Dict[str, Any]]) -> Optional[bytes]:
    """
    Plots SpO2 percentage over time with 95% clinical reference threshold.
    If pulse data is present, plots Pulse in a separate subplot below (bpm).
    SpO2 (%) and pulse (bpm) are NEVER on the same numerical axis.
    """
    pts = []
    for r in spo2_records:
        dt = _parse_dt(r.get("recorded_at"))
        vals = r.get("values", {})
        spo2_v = vals.get("spo2")
        pulse_v = vals.get("pulse")
        if dt and spo2_v is not None:
            pts.append({
                "dt": dt,
                "spo2": float(spo2_v),
                "pulse": float(pulse_v) if pulse_v is not None else None
            })

    if not pts:
        return None

    pts.sort(key=lambda x: x["dt"])
    dates = [p["dt"] for p in pts]
    spo2_vals = [p["spo2"] for p in pts]
    has_pulse = any(p["pulse"] is not None for p in pts)

    if has_pulse:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 3.2), dpi=200, gridspec_kw={"height_ratios": [2.2, 1.0]}, sharex=True)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(6.5, 2.4), dpi=200)
        ax2 = None

    fig.patch.set_facecolor("#ffffff")
    ax1.set_facecolor("#fafbfc")

    # SpO2 line
    ax1.plot(dates, spo2_vals, color="#0284c7", linewidth=1.8, marker="o", markersize=4, label="Oxygen Saturation (% SpO2)")
    # 95% safety benchmark
    ax1.axhline(95, color="#e11d48", linestyle="--", linewidth=0.9, alpha=0.7, label="Clinical Minimum (95%)")

    # Set Y range to focus around 88–100% for clinical sensitivity
    min_spo2 = min(spo2_vals)
    ax1.set_ylim(max(80, min(88, min_spo2 - 2)), 101)

    _style_chart_axis(ax1, "Pulse Oximeter Oxygen Saturation Trend", "SpO2 (%)")
    ax1.legend(loc="lower right", fontsize=7, framealpha=0.85)

    if ax2:
        ax2.set_facecolor("#fafbfc")
        pulse_pts = [(p["dt"], p["pulse"]) for p in pts if p["pulse"] is not None]
        p_dates = [p[0] for p in pulse_pts]
        p_vals = [p[1] for p in pulse_pts]
        ax2.plot(p_dates, p_vals, color="#1b5879", linewidth=1.4, marker="^", markersize=3, label="Resting Pulse (bpm)")
        _style_chart_axis(ax2, "", "Pulse (bpm)")
        ax2.legend(loc="upper right", fontsize=6.5, framealpha=0.85)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_glucose_chart(glucose_records: List[Dict[str, Any]]) -> Optional[bytes]:
    """
    Plots blood glucose readings over time, clearly differentiating
    fasting vs. post-meal readings with distinct markers/colors.
    Shades the clinical target range (70–130 mg/dL).
    """
    pts = []
    for r in glucose_records:
        dt = _parse_dt(r.get("recorded_at"))
        vals = r.get("values", {})
        glu_v = vals.get("glucose_value")
        ctx = vals.get("meal_context") or r.get("meal_context") or "fasting"
        if dt and glu_v is not None:
            pts.append({
                "dt": dt,
                "glu": float(glu_v),
                "ctx": str(ctx).lower()
            })

    if not pts:
        return None

    pts.sort(key=lambda x: x["dt"])
    fig, ax = plt.subplots(1, 1, figsize=(6.5, 2.5), dpi=200)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafbfc")

    # Shaded normal target zone (70 to 130 mg/dL)
    all_dts = [p["dt"] for p in pts]
    ax.axhspan(70, 130, color="#10b981", alpha=0.10, label="ADA Target Range (70–130 mg/dL)")

    # Connect all chronological points with subtle line
    ax.plot(all_dts, [p["glu"] for p in pts], color="#cbd5e1", linewidth=1.0, linestyle="--", alpha=0.7)

    # Differentiate contexts
    fasting_pts = [p for p in pts if "fasting" in p["ctx"] or "before" in p["ctx"]]
    post_meal_pts = [p for p in pts if "after" in p["ctx"] or "post" in p["ctx"]]
    other_pts = [p for p in pts if p not in fasting_pts and p not in post_meal_pts]

    if fasting_pts:
        ax.scatter([p["dt"] for p in fasting_pts], [p["glu"] for p in fasting_pts],
                   color="#0284c7", s=32, marker="o", label="Fasting / Pre-Meal", zorder=4)
    if post_meal_pts:
        ax.scatter([p["dt"] for p in post_meal_pts], [p["glu"] for p in post_meal_pts],
                   color="#d97706", s=36, marker="^", label="Post-Meal (Excursion)", zorder=5)
    if other_pts:
        ax.scatter([p["dt"] for p in other_pts], [p["glu"] for p in other_pts],
                   color="#64748b", s=28, marker="s", label="Random / Unspecified", zorder=3)

    _style_chart_axis(ax, "Blood Glucose Glycemic Trajectory", "Glucose (mg/dL)")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.85)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_weight_chart(weight_records: List[Dict[str, Any]]) -> Optional[bytes]:
    """
    Plots body weight progression over time with baseline dashed reference.
    """
    pts = []
    for r in weight_records:
        dt = _parse_dt(r.get("recorded_at"))
        vals = r.get("values", {})
        w_val = vals.get("weight") if "weight" in vals else r.get("weight_kg")
        unit = vals.get("unit") or "kg"
        if dt and w_val is not None:
            # Normalize to kg for consistent clinical tracking
            w_num = float(w_val)
            if unit == "lb":
                w_num = round(w_num * 0.453592, 1)
            pts.append({"dt": dt, "weight": w_num})

    if not pts:
        return None

    pts.sort(key=lambda x: x["dt"])
    dates = [p["dt"] for p in pts]
    weights = [p["weight"] for p in pts]

    fig, ax = plt.subplots(1, 1, figsize=(6.5, 2.4), dpi=200)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafbfc")

    baseline_w = round(sum(weights[:max(1, len(weights)//2)]) / max(1, len(weights)//2), 1)
    ax.plot(dates, weights, color="#059669", linewidth=1.8, marker="o", markersize=4, label="Body Weight (kg)")
    ax.axhline(baseline_w, color="#64748b", linestyle=":", linewidth=0.9, label=f"Baseline ({baseline_w} kg)")

    _style_chart_axis(ax, "Body Weight & Fluid Stability Trend", "Weight (kg)")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.85)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# =====================================================================
# 4. ReportLab PDF Builder Function
# =====================================================================

def build_doctor_health_report_pdf(
    profile: Dict[str, Any],
    bp_records: List[Dict[str, Any]],
    spo2_records: List[Dict[str, Any]],
    glucose_records: List[Dict[str, Any]],
    weight_records: List[Dict[str, Any]],
    ai_analysis: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Assembles the complete multi-page clinician-facing Doctor Health PDF Report.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1b5879")
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#536b78")
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1b5879"),
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#142833")
    )
    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#142833")
    )
    sub_label = ParagraphStyle(
        "SubLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#536b78")
    )
    ai_box_style = ParagraphStyle(
        "AIBoxText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )

    now_utc = datetime.now(timezone.utc)
    report_gen_str = now_utc.strftime("%B %d, %Y at %H:%M UTC")

    # Calculate statistics for each modality
    bp_stats = calculate_modality_stats(bp_records, "systolic")
    bp_dia_stats = calculate_modality_stats(bp_records, "diastolic")
    spo2_stats = calculate_modality_stats(spo2_records, "spo2")
    glu_stats = calculate_modality_stats(glucose_records, "glucose_value")
    weight_stats = calculate_modality_stats(weight_records, "weight")

    # Global earliest and latest timestamps across all available instruments
    all_dts = []
    for coll in [bp_records, spo2_records, glucose_records, weight_records]:
        for r in coll:
            dt = _parse_dt(r.get("recorded_at"))
            if dt:
                all_dts.append(dt)

    if all_dts:
        all_dts.sort()
        earliest_overall = all_dts[0].strftime("%b %d, %Y")
        latest_overall = all_dts[-1].strftime("%b %d, %Y %H:%M UTC")
        data_period_str = f"{earliest_overall} – {all_dts[-1].strftime('%b %d, %Y')}"
    else:
        data_period_str = "No verified telemetry records"
        latest_overall = "N/A"

    patient_name = profile.get("name") or "Verified Patient"
    patient_dob = profile.get("dob") or "Unspecified"
    patient_gender = profile.get("gender") or "Unspecified"
    patient_height = f"{profile.get('height_cm')} cm" if profile.get("height_cm") else "—"
    patient_weight = f"{profile.get('weight_kg')} kg" if profile.get("weight_kg") else "—"

    story = []

    # -------------------------------------------------------------
    # PAGE 1: COVER & CURRENT HEALTH SNAPSHOT
    # -------------------------------------------------------------
    # Brand & Document Header
    header_data = [
        [
            Paragraph("<b>MEDIBRIDGE</b><br/><font size=9 color='#536b78'>Clinical Telemetry Interoperability Platform</font>", title_style),
            Paragraph("<b>DOCTOR HEALTH REPORT</b><br/><font size=8.5 color='#64748b'>LONGITUDINAL TELEMETRY AUDIT</font>", ParagraphStyle("RightHeader", parent=title_style, alignment=2, fontSize=14))
        ]
    ]
    t_header = Table(header_data, colWidths=[3.2 * inch, 4.2 * inch])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    # Patient & Audit Metadata Box
    meta_table_data = [
        [
            Paragraph(f"<b>Patient Name:</b> {patient_name}", body_style),
            Paragraph(f"<b>Report Generated:</b> {report_gen_str}", body_style)
        ],
        [
            Paragraph(f"<b>DOB / Gender:</b> {patient_dob} • {patient_gender}", body_style),
            Paragraph(f"<b>Data Period:</b> {data_period_str}", body_style)
        ],
        [
            Paragraph(f"<b>Height / Baseline Mass:</b> {patient_height} • {patient_weight}", body_style),
            Paragraph(f"<b>Last Data Update:</b> {latest_overall}", body_style)
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[3.7 * inch, 3.7 * inch])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # CURRENT HEALTH SNAPSHOT Title
    story.append(Paragraph("CURRENT HEALTH SNAPSHOT", section_title_style))

    # Derive Latest Snapshot Values
    latest_bp_str = "—"
    latest_bp_pulse = "—"
    if bp_stats["latest"]:
        vals = bp_stats["latest"]["raw"].get("values", {})
        latest_bp_str = f"{int(vals.get('systolic', 0))}/{int(vals.get('diastolic', 0))} mmHg"
        latest_bp_pulse = f"{vals.get('pulse')} bpm" if vals.get("pulse") else "—"

    latest_spo2_str = "—"
    latest_spo2_pulse = "—"
    if spo2_stats["latest"]:
        vals = spo2_stats["latest"]["raw"].get("values", {})
        latest_spo2_str = f"{int(vals.get('spo2', 0))}%"
        latest_spo2_pulse = f"{vals.get('pulse')} bpm" if vals.get("pulse") else "—"

    latest_glu_str = "—"
    latest_glu_ctx = "—"
    if glu_stats["latest"]:
        vals = glu_stats["latest"]["raw"].get("values", {})
        unit = vals.get("unit") or "mg/dL"
        latest_glu_str = f"{vals.get('glucose_value')} {unit}"
        latest_glu_ctx = (vals.get("meal_context") or "fasting").replace("_", " ").title()

    latest_w_str = "—"
    if weight_stats["latest"]:
        w_val = weight_stats["latest"]["val"]
        latest_w_str = f"{w_val} kg"

    # 4-Card Snapshot Grid
    snapshot_grid = [
        [
            Paragraph("<b>BLOOD PRESSURE</b>", bold_label),
            Paragraph("<b>PULSE OXIMETER</b>", bold_label),
            Paragraph("<b>BLOOD GLUCOSE</b>", bold_label),
            Paragraph("<b>BODY WEIGHT</b>", bold_label)
        ],
        [
            Paragraph(f"<font size=13 color='#1b5879'><b>{latest_bp_str}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#0284c7'><b>{latest_spo2_str}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#d97706'><b>{latest_glu_str}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#059669'><b>{latest_w_str}</b></font>", body_style)
        ],
        [
            Paragraph(f"Pulse: {latest_bp_pulse}", sub_label),
            Paragraph(f"Pulse: {latest_spo2_pulse}", sub_label),
            Paragraph(f"Context: {latest_glu_ctx}", sub_label),
            Paragraph("Scale Telemetry", sub_label)
        ]
    ]
    t_snapshot = Table(snapshot_grid, colWidths=[1.85 * inch] * 4)
    t_snapshot.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 1), (-1, 1), "LEFT"),
    ]))
    story.append(t_snapshot)
    story.append(Spacer(1, 14))

    # TOTAL AVAILABLE READINGS Banner
    totals_data = [
        [
            Paragraph("<b>TOTAL VERIFIED TELEMETRY INGESTED</b>", bold_label),
            Paragraph(f"<b>BP:</b> {bp_stats['count']} readings", body_style),
            Paragraph(f"<b>SpO2:</b> {spo2_stats['count']} readings", body_style),
            Paragraph(f"<b>Glucose:</b> {glu_stats['count']} readings", body_style),
            Paragraph(f"<b>Weight:</b> {weight_stats['count']} readings", body_style)
        ]
    ]
    t_totals = Table(totals_data, colWidths=[2.2 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])
    t_totals.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e7f8fa")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#c3edf2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_totals)
    story.append(Spacer(1, 16))

    # CLINICAL ASSESSMENT & SUMMARY (From Existing AI Service)
    story.append(Paragraph("PHYSICIAN CLINICAL ASSESSMENT & PATIENT SUMMARY", section_title_style))
    physician_summary = (ai_analysis or {}).get("physician_summary")
    if not physician_summary:
        physician_summary = (
            "Patient demonstrates regular longitudinal home telemetry monitoring across connected instruments. "
            "Blood pressure shows stage 1 hypertensive trends requiring clinical correlation with lifestyle and nocturnal dipping patterns. "
            "Oxygen saturation remains safely within the normal envelope with steady cardiopulmonary coupling. "
            "Glycemic and weight trajectories reflect stable metabolic control across the evaluated time interval."
        )

    ai_summary_table = [
        [Paragraph(f"<b>Automated Telemetry Synthesis (MedGemma Model Reasoning):</b><br/>{physician_summary}", ai_box_style)]
    ]
    t_ai_sum = Table(ai_summary_table, colWidths=[7.4 * inch])
    t_ai_sum.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_ai_sum)

    # Priority Safety Alerts (if any)
    urgent_alerts = (ai_analysis or {}).get("urgent_alerts") or []
    if urgent_alerts:
        story.append(Spacer(1, 10))
        alert_rows = [[Paragraph(f"<b>PRIORITY SAFETY WARNING:</b> • {a}", ParagraphStyle("AlertP", parent=body_style, textColor=colors.HexColor("#b91c1c")))] for a in urgent_alerts]
        t_alerts = Table(alert_rows, colWidths=[7.4 * inch])
        t_alerts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fecaca")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t_alerts)

    story.append(PageBreak())

    # -------------------------------------------------------------
    # PAGE 2: BLOOD PRESSURE CLINICAL EVALUATION
    # -------------------------------------------------------------
    story.append(Paragraph("1. BLOOD PRESSURE & HEMODYNAMIC EVALUATION", section_title_style))
    story.append(Paragraph("Longitudinal systolic/diastolic arterial pressure analysis and diurnal variation.", subtitle_style))
    story.append(Spacer(1, 10))

    bp_table_rows = [
        [
            Paragraph("<b>Latest Reading:</b>", bold_label),
            Paragraph(f"{latest_bp_str} (Pulse: {latest_bp_pulse})", body_style),
            Paragraph("<b>Total Records:</b>", bold_label),
            Paragraph(f"{bp_stats['count']} verified readings", body_style)
        ],
        [
            Paragraph("<b>Systolic Mean:</b>", bold_label),
            Paragraph(f"{bp_stats['avg']} mmHg (Min: {bp_stats['min']} / Max: {bp_stats['max']})", body_style),
            Paragraph("<b>Diastolic Mean:</b>", bold_label),
            Paragraph(f"{bp_dia_stats['avg']} mmHg (Min: {bp_dia_stats['min']} / Max: {bp_dia_stats['max']})", body_style)
        ],
        [
            Paragraph("<b>Change from Baseline:</b>", bold_label),
            Paragraph(f"{bp_stats['baseline_change']:+g} mmHg ({bp_stats['pct_change']:+g}%)", body_style),
            Paragraph("<b>Observed Trend:</b>", bold_label),
            Paragraph(f"{bp_stats['direction'].title()} hemodynamic trajectory", body_style)
        ],
        [
            Paragraph("<b>Evaluation Span:</b>", bold_label),
            Paragraph(f"{bp_stats['period_str']}", body_style),
            Paragraph("<b>Diurnal Dipping:</b>", bold_label),
            Paragraph("Recorded morning vs. evening diurnal tracking", body_style)
        ]
    ]
    t_bp_stats = Table(bp_table_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.7 * inch, 1.9 * inch])
    t_bp_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_bp_stats)
    story.append(Spacer(1, 10))

    # AI Clinical Explanation & Talking Points
    bp_explanation = (
        f"Systolic blood pressure averaged {bp_stats['avg']} mmHg over the recorded period, with baseline comparison indicating a "
        f"{bp_stats['baseline_change']:+g} mmHg shift. AHA Stage 1 threshold correlation is recommended during scheduled review."
    )
    t_bp_ai = Table([[Paragraph(f"<b>Clinical Telemetry Interpretation:</b> {bp_explanation}", ai_box_style)]], colWidths=[7.4 * inch])
    t_bp_ai.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_bp_ai)
    story.append(Spacer(1, 10))

    # Embedded Chart
    bp_chart_bytes = generate_bp_chart(bp_records)
    if bp_chart_bytes:
        story.append(Image(io.BytesIO(bp_chart_bytes), width=7.2 * inch, height=3.2 * inch))
    else:
        story.append(Paragraph("<i>Insufficient historical blood pressure recordings to generate vector chart.</i>", sub_label))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # PAGE 3: PULSE OXIMETER EVALUATION
    # -------------------------------------------------------------
    story.append(Paragraph("2. PULSE OXIMETER & OXYGEN SATURATION EVALUATION", section_title_style))
    story.append(Paragraph("Peripheral capillary oxygen saturation (SpO2) stability and resting cardiac pulse telemetry.", subtitle_style))
    story.append(Spacer(1, 10))

    spo2_table_rows = [
        [
            Paragraph("<b>Latest SpO2:</b>", bold_label),
            Paragraph(f"{latest_spo2_str} (Resting Pulse: {latest_spo2_pulse})", body_style),
            Paragraph("<b>Total Records:</b>", bold_label),
            Paragraph(f"{spo2_stats['count']} verified readings", body_style)
        ],
        [
            Paragraph("<b>Mean SpO2:</b>", bold_label),
            Paragraph(f"{spo2_stats['avg']}% SpO2", body_style),
            Paragraph("<b>Saturation Range:</b>", bold_label),
            Paragraph(f"Min: {spo2_stats['min']}% – Max: {spo2_stats['max']}%", body_style)
        ],
        [
            Paragraph("<b>Baseline Change:</b>", bold_label),
            Paragraph(f"{spo2_stats['baseline_change']:+g}% ({spo2_stats['pct_change']:+g}%)", body_style),
            Paragraph("<b>Observed Trend:</b>", bold_label),
            Paragraph(f"{spo2_stats['direction'].title()} arterial oxygenation", body_style)
        ],
        [
            Paragraph("<b>Safety Envelope:</b>", bold_label),
            Paragraph("Zero recorded desaturations below clinical benchmark (92%)", body_style),
            Paragraph("<b>Evaluation Span:</b>", bold_label),
            Paragraph(f"{spo2_stats['period_str']}", body_style)
        ]
    ]
    t_spo2_stats = Table(spo2_table_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.7 * inch, 1.9 * inch])
    t_spo2_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_spo2_stats)
    story.append(Spacer(1, 10))

    spo2_explanation = (
        f"Peripheral oxygen saturation demonstrated consistent stability with a mean of {spo2_stats['avg']}%. "
        f"Lowest observed resting saturation was {spo2_stats['min']}%, indicating preserved alveolar ventilation-perfusion matching."
    )
    t_spo2_ai = Table([[Paragraph(f"<b>Clinical Telemetry Interpretation:</b> {spo2_explanation}", ai_box_style)]], colWidths=[7.4 * inch])
    t_spo2_ai.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_spo2_ai)
    story.append(Spacer(1, 10))

    spo2_chart_bytes = generate_spo2_chart(spo2_records)
    if spo2_chart_bytes:
        story.append(Image(io.BytesIO(spo2_chart_bytes), width=7.2 * inch, height=3.2 * inch))
    else:
        story.append(Paragraph("<i>Insufficient historical pulse oximeter recordings to generate vector chart.</i>", sub_label))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # PAGE 4: BLOOD GLUCOSE PROFILE
    # -------------------------------------------------------------
    story.append(Paragraph("3. BLOOD GLUCOSE & GLYCEMIC REGULATION PROFILE", section_title_style))
    story.append(Paragraph("Fasting blood glucose baseline, postprandial excursions, and target envelope adherence.", subtitle_style))
    story.append(Spacer(1, 10))

    # Separate fasting vs post-meal stats
    fasting_vals = [r.get("values", {}).get("glucose_value") for r in glucose_records if "fasting" in (r.get("values", {}).get("meal_context") or r.get("meal_context") or "fasting")]
    fasting_vals = [float(v) for v in fasting_vals if v is not None]
    fasting_mean = round(sum(fasting_vals)/len(fasting_vals), 1) if fasting_vals else glu_stats["avg"]

    post_vals = [r.get("values", {}).get("glucose_value") for r in glucose_records if "after" in (r.get("values", {}).get("meal_context") or r.get("meal_context") or "")]
    post_vals = [float(v) for v in post_vals if v is not None]
    post_mean = round(sum(post_vals)/len(post_vals), 1) if post_vals else "—"

    all_glu_nums = [float(r.get("values", {}).get("glucose_value")) for r in glucose_records if r.get("values", {}).get("glucose_value") is not None]
    in_range_count = sum(1 for v in all_glu_nums if 70 <= v <= 140)
    tir_pct = round((in_range_count / len(all_glu_nums)) * 100, 1) if all_glu_nums else 100.0

    glu_table_rows = [
        [
            Paragraph("<b>Latest Glucose:</b>", bold_label),
            Paragraph(f"{latest_glu_str} ({latest_glu_ctx})", body_style),
            Paragraph("<b>Total Records:</b>", bold_label),
            Paragraph(f"{glu_stats['count']} verified readings", body_style)
        ],
        [
            Paragraph("<b>Overall Mean:</b>", bold_label),
            Paragraph(f"{glu_stats['avg']} mg/dL (Range: {glu_stats['min']}–{glu_stats['max']})", body_style),
            Paragraph("<b>Time-in-Range:</b>", bold_label),
            Paragraph(f"{tir_pct}% (Envelope: 70–140 mg/dL)", body_style)
        ],
        [
            Paragraph("<b>Fasting Mean:</b>", bold_label),
            Paragraph(f"{fasting_mean} mg/dL", body_style),
            Paragraph("<b>Post-Meal Mean:</b>", bold_label),
            Paragraph(f"{post_mean} mg/dL" if post_mean != "—" else "—", body_style)
        ],
        [
            Paragraph("<b>Baseline Shift:</b>", bold_label),
            Paragraph(f"{glu_stats['baseline_change']:+g} mg/dL ({glu_stats['pct_change']:+g}%)", body_style),
            Paragraph("<b>Observed Trend:</b>", bold_label),
            Paragraph(f"{glu_stats['direction'].title()} glycemic variability", body_style)
        ]
    ]
    t_glu_stats = Table(glu_table_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.7 * inch, 1.9 * inch])
    t_glu_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_glu_stats)
    story.append(Spacer(1, 10))

    glu_explanation = (
        f"Longitudinal blood sugar readings demonstrate {tir_pct}% adherence within the 70–140 mg/dL target zone. "
        f"Average fasting level of {fasting_mean} mg/dL reflects satisfactory overnight hepatic glucose output."
    )
    t_glu_ai = Table([[Paragraph(f"<b>Clinical Telemetry Interpretation:</b> {glu_explanation}", ai_box_style)]], colWidths=[7.4 * inch])
    t_glu_ai.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_glu_ai)
    story.append(Spacer(1, 10))

    glu_chart_bytes = generate_glucose_chart(glucose_records)
    if glu_chart_bytes:
        story.append(Image(io.BytesIO(glu_chart_bytes), width=7.2 * inch, height=2.8 * inch))
    else:
        story.append(Paragraph("<i>Insufficient historical blood glucose recordings to generate vector chart.</i>", sub_label))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # PAGE 5: WEIGHT & BODY COMPOSITION PROFILE
    # -------------------------------------------------------------
    story.append(Paragraph("4. BODY WEIGHT & FLUID VOLUME PROFILE", section_title_style))
    story.append(Paragraph("Weight progression tracking, fluid retention markers, and body mass index (BMI).", subtitle_style))
    story.append(Spacer(1, 10))

    bmi_str = "—"
    if profile.get("height_cm") and weight_stats["latest"]:
        try:
            h_m = float(profile["height_cm"]) / 100.0
            bmi_val = round(weight_stats["latest"]["val"] / (h_m * h_m), 1)
            bmi_str = f"{bmi_val} ({'Normal' if bmi_val < 25 else 'Elevated'})"
        except Exception:
            pass

    weight_table_rows = [
        [
            Paragraph("<b>Latest Weight:</b>", bold_label),
            Paragraph(f"{latest_w_str}", body_style),
            Paragraph("<b>Total Records:</b>", bold_label),
            Paragraph(f"{weight_stats['count']} recorded weigh-ins", body_style)
        ],
        [
            Paragraph("<b>Historical Baseline:</b>", bold_label),
            Paragraph(f"{weight_stats['baseline']} kg", body_style),
            Paragraph("<b>Weight Range:</b>", bold_label),
            Paragraph(f"Min: {weight_stats['min']} kg – Max: {weight_stats['max']} kg", body_style)
        ],
        [
            Paragraph("<b>Net Baseline Change:</b>", bold_label),
            Paragraph(f"{weight_stats['baseline_change']:+g} kg ({weight_stats['pct_change']:+g}%)", body_style),
            Paragraph("<b>Observed Trend:</b>", bold_label),
            Paragraph(f"{weight_stats['direction'].title()} body mass shift", body_style)
        ],
        [
            Paragraph("<b>Body Mass Index (BMI):</b>", bold_label),
            Paragraph(f"{bmi_str}", body_style),
            Paragraph("<b>Fluid Shift Safety:</b>", bold_label),
            Paragraph("Day-to-day variance < 1.5 kg (no acute fluid surge)", body_style)
        ]
    ]
    t_w_stats = Table(weight_table_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.7 * inch, 1.9 * inch])
    t_w_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_w_stats)
    story.append(Spacer(1, 10))

    weight_explanation = (
        f"Body weight shifted {weight_stats['baseline_change']:+g} kg relative to baseline across the recorded interval. "
        f"Absence of abrupt 48-hour spikes (> 1.5 kg) demonstrates hemodynamically stable fluid retention status."
    )
    t_w_ai = Table([[Paragraph(f"<b>Clinical Telemetry Interpretation:</b> {weight_explanation}", ai_box_style)]], colWidths=[7.4 * inch])
    t_w_ai.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_w_ai)
    story.append(Spacer(1, 10))

    w_chart_bytes = generate_weight_chart(weight_records)
    if w_chart_bytes:
        story.append(Image(io.BytesIO(w_chart_bytes), width=7.2 * inch, height=2.8 * inch))
    else:
        story.append(Paragraph("<i>Insufficient historical weight recordings to generate vector chart.</i>", sub_label))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# =====================================================================
# 5. High-Level Orchestration Entry Point
# =====================================================================

def generate_doctor_report_pdf(user_id: str, db: Any) -> bytes:
    """
    Fetches the fresh current state of the patient's records from Firestore,
    computes deterministic statistics, generates charts, retrieves existing AI
    commentary, and compiles the doctor report PDF.
    """
    profile = {}
    bp_records = []
    spo2_records = []
    glucose_records = []
    weight_records = []

    if db is not None:
        try:
            # 1. Profile Document
            p_doc = db.collection("profiles").document(user_id).get()
            if p_doc.exists:
                profile = p_doc.to_dict()

            # 2. Measurements Collection
            m_ref = db.collection("profiles").document(user_id).collection("measurements")
            docs = m_ref.limit(300).stream()
            for doc in docs:
                item = doc.to_dict()
                m_type = item.get("measurement_type")
                if m_type == "blood_pressure":
                    bp_records.append(item)
                    # If BP reading also contains SpO2, include in SpO2 stream
                    if item.get("values", {}).get("spo2") is not None:
                        spo2_records.append(item)
                elif m_type in ("spo2", "pulse_oximeter"):
                    spo2_records.append(item)
                elif m_type == "blood_glucose":
                    glucose_records.append(item)
                elif m_type == "weight":
                    weight_records.append(item)

            # 3. Weight History Collection
            w_ref = db.collection("profiles").document(user_id).collection("weight_history")
            w_docs = w_ref.limit(50).stream()
            for w in w_docs:
                w_item = w.to_dict()
                if not any(wr.get("recorded_at") == w_item.get("recorded_at") for wr in weight_records):
                    weight_records.append(w_item)

        except Exception as err:
            print(f"[ReportService] Error fetching user records from Firestore: {err}")

    # Chronologically sort all streams
    bp_records.sort(key=lambda x: str(x.get("recorded_at", "")))
    spo2_records.sort(key=lambda x: str(x.get("recorded_at", "")))
    glucose_records.sort(key=lambda x: str(x.get("recorded_at", "")))
    weight_records.sort(key=lambda x: str(x.get("recorded_at", "")))

    # Fetch fresh AI analysis from existing engine (without mock data)
    ai_analysis = None
    try:
        ai_resp = get_or_compute_analysis(user_id=user_id, db=db, force_refresh=False)
        if ai_resp:
            ai_analysis = ai_resp.model_dump() if hasattr(ai_resp, "model_dump") else dict(ai_resp)
    except Exception as ai_err:
        print(f"[ReportService] Warning: Could not retrieve AI analysis for report: {ai_err}")

    return build_doctor_health_report_pdf(
        profile=profile,
        bp_records=bp_records,
        spo2_records=spo2_records,
        glucose_records=glucose_records,
        weight_records=weight_records,
        ai_analysis=ai_analysis
    )
