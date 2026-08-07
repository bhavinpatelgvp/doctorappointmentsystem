"""
Appointment service: doctor search, slot generation, atomic booking,
rescheduling and cancellation.

Booking is atomic to prevent double-booking of the same doctor/date/time.
"""
from datetime import datetime, timedelta

from sqlalchemy import func

from audit_service import log_action
from database import get_session
from email_service import send_appointment_confirmation
from models import (
    Appointment,
    BlockedDate,
    Doctor,
    DoctorSchedule,
    Specialization,
    Student,
)
from utils import generate_number, today_str, weekday_index
from validators import is_valid_date


# ---------------------------------------------------------------------------
# Doctor search
# ---------------------------------------------------------------------------
def search_doctors(db, name="", specialization_id=None, department_id=None):
    q = db.query(Doctor)
    if name:
        q = q.filter(Doctor.full_name.ilike(f"%{name}%"))
    if specialization_id:
        q = q.filter(Doctor.specialization_id == specialization_id)
    if department_id:
        q = q.filter(Doctor.department_id == department_id)
    return q.all()


def get_specializations(db):
    return db.query(Specialization).all()


def get_departments(db):
    return list(db.query(Doctor).with_entities(Doctor.department_id).distinct())


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------
def _parse_hm(hhmm: str) -> datetime:
    return datetime.strptime(hhmm, "%H:%M")


def generate_slots(schedule: DoctorSchedule, date_str: str):
    """Generate (time, remaining_capacity) slots for a doctor on a date."""
    start = _parse_hm(schedule.start_time)
    end = _parse_hm(schedule.end_time)
    slot = timedelta(minutes=schedule.slot_minutes or 15)
    break_start = _parse_hm(schedule.break_start) if schedule.break_start else None
    break_end = _parse_hm(schedule.break_end) if schedule.break_end else None

    slots = []
    cur = start
    while cur < end:
        time_str = cur.strftime("%H:%M")
        if break_start and break_end and break_start <= cur < break_end:
            cur += slot
            continue
        slots.append(time_str)
        cur += slot
    return slots


def get_available_slots(db, doctor_id, date_str):
    """Return list of (time_str, remaining) available on a date for a doctor."""
    if not is_valid_date(date_str):
        return []

    try:
        weekday_idx = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    except ValueError:
        return []

    schedule = (
        db.query(DoctorSchedule)
        .filter(DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.weekday == weekday_idx,
                DoctorSchedule.is_active.is_(True))
        .first()
    )
    if schedule is None:
        return []

    blocked = (
        db.query(BlockedDate)
        .filter(BlockedDate.doctor_id == doctor_id,
                BlockedDate.blocked_date == date_str)
        .first()
    )
    if blocked:
        return []

    slots = generate_slots(schedule, date_str)

    # Count existing appointments per slot (non-cancelled count toward capacity)
    rows = (
        db.query(Appointment.appointment_time, func.count(Appointment.id))
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == date_str,
            Appointment.status.in_(["Requested", "Confirmed", "Rescheduled"]),
        )
        .group_by(Appointment.appointment_time)
        .all()
    )
    booked_count = {t: c for t, c in rows}
    capacity = schedule.slot_capacity or 1

    available = []
    for slot in slots:
        used = booked_count.get(slot, 0)
        remaining = capacity - used
        if remaining > 0:
            available.append((slot, remaining))
    return available


# ---------------------------------------------------------------------------
# Booking (atomic)
# ---------------------------------------------------------------------------
def book_appointment(db, student_id, doctor_id, appointment_date, appointment_time,
                     appointment_type="In-person", reason="", created_by=None):
    """Atomically book an appointment. Returns (success, message, appointment)."""
    if not is_valid_date(appointment_date):
        return False, "Please select a valid appointment date.", None

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if appointment_date < today_str():
        return False, "Cannot book an appointment in the past.", None

    # Lock the doctor row to serialize concurrent bookings for this doctor.
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).with_for_update().first()
    if doctor is None:
        return False, "Doctor not found.", None

    available = {t: c for t, c in get_available_slots(db, doctor_id, appointment_date)}
    info = available.get(appointment_time)
    if info is None:
        return False, "This appointment slot has already been booked. Please select another time.", None
    if info <= 0:
        return False, "This appointment slot has already been booked. Please select another time.", None

    # Double-booking prevention (same doctor + date + time)
    exists = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_(["Requested", "Confirmed", "Rescheduled"]),
        )
        .first()
    )
    if exists:
        return False, "This appointment slot has already been booked. Please select another time.", None

    # Prevent a student double-booking the same doctor/time
    dup = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == student_id,
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_(["Requested", "Confirmed", "Rescheduled"]),
        )
        .first()
    )
    if dup:
        return False, "You already have an appointment for this slot.", None

    appointment = Appointment(
        appointment_no=generate_number("APT"),
        patient_id=student_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        appointment_type=appointment_type,
        reason=reason or None,
        status="Requested",
        created_by=created_by,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    log_action("APPOINTMENT_BOOKED", "appointment", record_id=appointment.id,
               details=f"Appt {appointment.appointment_no} booked")
    return True, f"Appointment successfully booked. ID: {appointment.appointment_no}", appointment


def confirm_appointment(db, appointment_id, doctor_id):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.doctor_id != doctor_id:
        return False, "Appointment not found."
    if appointment.status not in ("Requested", "Rescheduled"):
        return False, "Only requested or rescheduled appointments can be confirmed."
    appointment.status = "Confirmed"
    appointment.confirmation_timestamp = datetime.utcnow()
    db.commit()
    log_action("APPOINTMENT_CONFIRMED", "appointment", record_id=appointment.id)
    # Notify student
    student = db.query(Student).filter(Student.id == appointment.patient_id).first()
    send_appointment_confirmation(student, appointment.doctor, appointment)
    return True, "Appointment confirmed."


def cancel_appointment_by_student(db, appointment_id, student_id, reason=""):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.patient_id != student_id:
        return False, "Appointment not found."
    if appointment.status in ("Completed", "Cancelled"):
        return False, "This appointment cannot be cancelled."
    appointment.status = "Cancelled"
    appointment.cancellation_reason = reason or "Cancelled by student"
    db.commit()
    log_action("APPOINTMENT_CANCELLED", "appointment", record_id=appointment.id,
               details="Cancelled by student")
    return True, "Appointment cancelled."


def cancel_appointment_by_doctor(db, appointment_id, doctor_id, reason=""):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.doctor_id != doctor_id:
        return False, "Appointment not found."
    if appointment.status in ("Completed", "Cancelled"):
        return False, "This appointment cannot be cancelled."
    appointment.status = "Cancelled"
    appointment.cancellation_reason = reason or "Cancelled by doctor"
    db.commit()
    log_action("APPOINTMENT_CANCELLED", "appointment", record_id=appointment.id,
               details="Cancelled by doctor")
    return True, "Appointment cancelled."


def reschedule_appointment(db, appointment_id, student_id, new_date, new_time):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.patient_id != student_id:
        return False, "Appointment not found."
    if appointment.status in ("Completed", "Cancelled"):
        return False, "This appointment cannot be rescheduled."

    available = {t: c for t, c in get_available_slots(db, appointment.doctor_id, new_date)}
    if new_time not in available:
        return False, "Selected slot is unavailable. Please choose another time."

    clash = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == new_date,
            Appointment.appointment_time == new_time,
            Appointment.status.in_(["Requested", "Confirmed", "Rescheduled"]),
            Appointment.id != appointment.id,
        )
        .first()
    )
    if clash:
        return False, "This slot has already been booked. Please choose another time."

    appointment.appointment_date = new_date
    appointment.appointment_time = new_time
    appointment.status = "Rescheduled"
    db.commit()
    log_action("APPOINTMENT_RESCHEDULED", "appointment", record_id=appointment.id)
    return True, "Appointment rescheduled successfully."


def mark_status(db, appointment_id, doctor_id, new_status):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.doctor_id != doctor_id:
        return False, "Appointment not found."
    if new_status not in ("Confirmed", "Completed", "Cancelled", "No-show"):
        return False, "Invalid status."
    appointment.status = new_status
    if new_status == "Confirmed":
        appointment.confirmation_timestamp = datetime.utcnow()
    db.commit()
    log_action("APPOINTMENT_STATUS", "appointment", record_id=appointment.id,
               details=f"Status -> {new_status}")
    return True, f"Appointment marked as {new_status}."


def get_appointments_for_student(db, student_id, status=None, upcoming_only=False):
    q = db.query(Appointment).filter(Appointment.patient_id == student_id)
    if status:
        q = q.filter(Appointment.status == status)
    if upcoming_only:
        q = q.filter(Appointment.status.in_(["Requested", "Confirmed", "Rescheduled"]),
                     Appointment.appointment_date >= today_str())
    return q.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()


def get_appointments_for_doctor(db, doctor_id, status=None, date_str=None):
    q = db.query(Appointment).filter(Appointment.doctor_id == doctor_id)
    if status:
        q = q.filter(Appointment.status == status)
    if date_str:
        q = q.filter(Appointment.appointment_date == date_str)
    return q.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
