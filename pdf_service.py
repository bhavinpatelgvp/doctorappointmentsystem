"""
PDF generation service for medical certificates.

Uses ReportLab to produce a professional Gujarat Vidyapith-themed certificate.
No official seal/signature is simulated unless explicitly permitted.
"""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import APP_NAME, APP_SUBTITLE, CERTIFICATE_DIR, INSTITUTION_ADDRESS
from utils import format_time_12h

# Fonts: try to register DejaVu (supports broader glyphs). Fallback to Helvetica.
_FONT_REGISTERED = None


def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    candidates = {
        "DejaVuSans": "C:/Windows/Fonts/DejaVuSans.ttf",
        "DejaVuSans-Bold": "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
    }
    for name, path in candidates.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_REGISTERED = name
            except Exception:  # noqa: BLE001
                continue
    if _FONT_REGISTERED is None:
        _FONT_REGISTERED = "Helvetica"


def _font(base="normal"):
    if _FONT_REGISTERED is None:
        _register_fonts()
    if _FONT_REGISTERED == "Helvetica":
        return "Helvetica" if base == "normal" else "Helvetica-Bold"
    return _FONT_REGISTERED if base == "normal" else f"{_FONT_REGISTERED}-Bold"


CREATE_BROWN = colors.HexColor("#5C3A21")
DUSTY_BROWN = colors.HexColor("#8A6D4F")
CREAM = colors.HexColor("#F7F1E3")


def create_medical_certificate_pdf(certificate, student, doctor, consultation) -> str:
    """Generate a PDF medical certificate and return the file path."""
    filename = f"MedicalCertificate_{certificate.certificate_no}.pdf"
    filepath = CERTIFICATE_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    # --- Custom styles using earthy brown + cream theme ---
    org_style = ParagraphStyle(
        "org", parent=styles["Title"], fontName=_font("bold"), fontSize=22,
        textColor=CREATE_BROWN, alignment=TA_CENTER, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"], fontName=_font(), fontSize=12,
        textColor=DUSTY_BROWN, alignment=TA_CENTER, spaceAfter=2,
    )
    cert_title = ParagraphStyle(
        "cert", parent=styles["Title"], fontName=_font("bold"), fontSize=18,
        textColor=CREATE_BROWN, alignment=TA_CENTER, spaceAfter=2,
    )
    meta_style = ParagraphStyle(
        "meta", parent=styles["Normal"], fontName=_font(), fontSize=11,
        textColor=colors.black, alignment=TA_CENTER,
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"], fontName=_font(), fontSize=11,
        leading=16, textColor=colors.black,
    )
    strong = ParagraphStyle(
        "strong", parent=body, fontName=_font("bold"),
    )
    right = ParagraphStyle(
        "right", parent=body, alignment=TA_RIGHT,
    )

    story = []
    story.append(Paragraph(APP_NAME, org_style))
    story.append(Paragraph(APP_SUBTITLE, sub_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=CREATE_BROWN))
    story.append(Spacer(1, 14))
    story.append(Paragraph("MEDICAL CERTIFICATE", cert_title))
    story.append(Paragraph(f"Certificate No: {certificate.certificate_no}", meta_style))
    story.append(Paragraph(f"Date of Issue: {certificate.issued_date}", meta_style))
    story.append(Spacer(1, 16))

    # Student / Doctor details table
    details = Table(
        [
            [Paragraph("Student Information", strong), Paragraph("Doctor Information", strong)],
            [Paragraph(f"Name: {student.full_name}", body),
             Paragraph(f"Name: {doctor.full_name}", body)],
            [Paragraph(f"Enrollment No: {student.enrollment_no}", body),
             Paragraph(f"Qualification: {doctor.qualification or '—'}", body)],
            [Paragraph(f"Programme: {(student.programme.name if student.programme else '—')}", body),
             Paragraph(f"Specialization: {(doctor.specialization.name if doctor.specialization else '—')}", body)],
            [Paragraph(f"Department: {(student.department.name if student.department else '—')}", body),
             Paragraph(f"Reg. No: {doctor.doctor_reg_no}", body)],
        ],
        colWidths=[3.3 * inch, 3.3 * inch],
    )
    details.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CREAM),
        ("BOX", (0, 0), (-1, -1), 0.75, DUSTY_BROWN),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0D3BF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(details)
    story.append(Spacer(1, 16))

    if consultation and consultation.symptoms:
        story.append(Paragraph(f"Reported Symptoms: {consultation.symptoms}", body))
        story.append(Spacer(1, 6))
    if consultation and consultation.diagnosis:
        story.append(Paragraph(f"Diagnosis: {consultation.diagnosis}", body))
        story.append(Spacer(1, 6))

    if consultation and consultation.doctor_advice:
        story.append(Paragraph(f"Medical Advice / Doctor's Instructions: {consultation.doctor_advice}", body))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    rest_table = Table(
        [
            [Paragraph("Recommended Rest Period", strong)],
            [Paragraph(
                f"From: <b>{certificate.rest_from}</b>   &nbsp;&nbsp; To: "
                f"<b>{certificate.rest_to}</b>   &nbsp;&nbsp; Total: "
                f"<b>{certificate.rest_days} day(s)</b>",
                body,
            )],
        ],
        colWidths=[6.6 * inch],
    )
    rest_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CREAM),
        ("BOX", (0, 0), (-1, -1), 1, CREATE_BROWN),
        ("GRID", (0, 0), (-1, -1), 0.5, DUSTY_BROWN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rest_table)
    story.append(Spacer(1, 8))

    if certificate.remarks:
        story.append(Paragraph(f"Remarks: {certificate.remarks}", body))
        story.append(Spacer(1, 8))

    story.append(Paragraph(f"Consultation Date: {consultation.consult_date if consultation else '—'}", body))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Consultation No: {consultation.consult_no if consultation else '—'}", body))
    story.append(Spacer(1, 40))

    # Signature area
    sig_table = Table(
        [
            [Paragraph("", body), Paragraph("_________________________", right)],
            [Paragraph("Institution Authorized Signatory", body),
             Paragraph(f"Dr. {doctor.full_name}", right)],
        ],
        colWidths=[3.3 * inch, 3.3 * inch],
    )
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(f"{APP_NAME} · {INSTITUTION_ADDRESS}", meta_style))
    story.append(Paragraph("This certificate is issued on the recommendation of the consulted physician.", meta_style))

    doc.build(story)
    return str(filepath)
