"""
Reporting & analytics service for administrators.

Provides KPI summaries, chart-ready aggregations and CSV export.
Aggregate reports do not expose personally identifiable medical information.
"""
import io

import pandas as pd
from sqlalchemy import func

from database import get_session
from models import (
    Appointment,
    Doctor,
    MedicalCertificate,
    Student,
    User,
)


def get_admin_kpis(db):
    total_students = db.query(Student).count()
    total_doctors = db.query(Doctor).count()
    total_appointments = db.query(Appointment).count()
    total_certificates = db.query(MedicalCertificate).count()
    today = __import__("utils").today_str()
    today_appts = db.query(Appointment).filter(Appointment.appointment_date == today).count()
    completed = db.query(Appointment).filter(Appointment.status == "Completed").count()
    cancelled = db.query(Appointment).filter(Appointment.status == "Cancelled").count()
    no_show = db.query(Appointment).filter(Appointment.status == "No-show").count()
    admins = db.query(User).filter(User.role == "admin").count()
    return {
        "total_students": total_students,
        "total_doctors": total_doctors,
        "total_appointments": total_appointments,
        "total_certificates": total_certificates,
        "today_appointments": today_appts,
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "admins": admins,
    }


def appointment_status_stats(db):
    rows = (db.query(Appointment.status, func.count(Appointment.id))
            .group_by(Appointment.status).all())
    return pd.DataFrame(rows, columns=["status", "count"])


def department_wise_appointments(db):
    rows = (
        db.query(Doctor.department_id, func.count(Appointment.id))
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(Doctor.department_id)
        .all()
    )
    return pd.DataFrame(rows, columns=["department_id", "count"])


def doctor_wise_appointments(db):
    rows = (
        db.query(Doctor.full_name, func.count(Appointment.id))
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(Doctor.full_name)
        .all()
    )
    return pd.DataFrame(rows, columns=["doctor", "count"])


def monthly_appointment_trend(db):
    rows = (
        db.query(Appointment.appointment_date, func.count(Appointment.id))
        .group_by(Appointment.appointment_date)
        .all()
    )
    df = pd.DataFrame(rows, columns=["date", "count"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df.groupby("month")["count"].sum().reset_index()


def certificate_status_stats(db):
    rows = (db.query(MedicalCertificate.status, func.count(MedicalCertificate.id))
            .group_by(MedicalCertificate.status).all())
    return pd.DataFrame(rows, columns=["status", "count"])


def appointments_df(db, start_date=None, end_date=None):
    q = db.query(Appointment)
    if start_date:
        q = q.filter(Appointment.appointment_date >= start_date)
    if end_date:
        q = q.filter(Appointment.appointment_date <= end_date)
    rows = q.all()
    return pd.DataFrame([{
        "appointment_no": a.appointment_no,
        "patient_id": a.patient_id,
        "doctor_id": a.doctor_id,
        "date": a.appointment_date,
        "time": a.appointment_time,
        "status": a.status,
    } for a in rows])


def to_csv(df) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def to_excel(df) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return buf.getvalue()
