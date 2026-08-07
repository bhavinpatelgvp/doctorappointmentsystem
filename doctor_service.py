"""
Doctor service: profile management, schedule management, blocked dates,
patient lookup and statistics.
"""
from audit_service import log_action
from database import get_session
from models import BlockedDate, Doctor, DoctorSchedule, Student, User
from utils import weekday_index
from validators import is_valid_date, is_valid_time


def get_doctor_by_user(db, user_id):
    return db.query(Doctor).filter(Doctor.user_id == user_id).first()


def get_doctor(db, doctor_id):
    return db.query(Doctor).filter(Doctor.id == doctor_id).first()


def update_profile(db, doctor_id, full_name, qualification, experience_years,
                   consultation_fee, contact, bio):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return False, "Doctor not found."
    doctor.full_name = full_name or doctor.full_name
    doctor.qualification = qualification
    doctor.experience_years = experience_years
    doctor.consultation_fee = consultation_fee
    doctor.contact = contact
    doctor.bio = bio
    db.commit()
    log_action("DOCTOR_PROFILE_UPDATED", "doctor", record_id=doctor.id)
    return True, "Profile updated successfully."


def get_schedules(db, doctor_id):
    return (db.query(DoctorSchedule)
            .filter(DoctorSchedule.doctor_id == doctor_id)
            .order_by(DoctorSchedule.weekday)
            .all())


def upsert_schedule(db, doctor_id, weekday_name, start_time, end_time, slot_minutes,
                    slot_capacity, break_start, break_end, is_active):
    if not is_valid_time(start_time) or not is_valid_time(end_time):
        return False, "Invalid time. Use HH:MM (24-hour format)."
    if end_time <= start_time:
        return False, "End time must be after start time."
    if break_start and break_end and break_start >= break_end:
        return False, "Break start must be before break end."

    weekday_idx = weekday_index(weekday_name)
    schedule = (db.query(DoctorSchedule)
                .filter(DoctorSchedule.doctor_id == doctor_id,
                        DoctorSchedule.weekday == weekday_idx)
                .first())
    if not schedule:
        schedule = DoctorSchedule(doctor_id=doctor_id, weekday=weekday_idx)
        db.add(schedule)
    schedule.start_time = start_time
    schedule.end_time = end_time
    schedule.slot_minutes = slot_minutes
    schedule.slot_capacity = slot_capacity
    schedule.break_start = break_start or None
    schedule.break_end = break_end or None
    schedule.is_active = is_active
    db.commit()
    log_action("SCHEDULE_UPSERTED", "doctor", record_id=doctor_id,
               details=f"Schedule for {weekday_name}")
    return True, f"Schedule for {weekday_name} saved."


def delete_schedule(db, schedule_id, doctor_id):
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.id == schedule_id, DoctorSchedule.doctor_id == doctor_id).first()
    if not schedule:
        return False, "Schedule not found."
    db.delete(schedule)
    db.commit()
    log_action("SCHEDULE_DELETED", "doctor", record_id=schedule_id)
    return True, "Schedule removed."


def get_blocked_dates(db, doctor_id):
    return (db.query(BlockedDate)
            .filter(BlockedDate.doctor_id == doctor_id)
            .order_by(BlockedDate.blocked_date.desc())
            .all())


def add_blocked_date(db, doctor_id, blocked_date, reason=""):
    if not is_valid_date(blocked_date):
        return False, "Invalid date format."
    exists = (db.query(BlockedDate)
              .filter(BlockedDate.doctor_id == doctor_id,
                      BlockedDate.blocked_date == blocked_date)
              .first())
    if exists:
        return False, "This date is already blocked."
    db.add(BlockedDate(doctor_id=doctor_id, blocked_date=blocked_date, reason=reason))
    db.commit()
    log_action("DATE_BLOCKED", "doctor", record_id=doctor_id, details=blocked_date)
    return True, f"{blocked_date} blocked."


def remove_blocked_date(db, blocked_id, doctor_id):
    item = db.query(BlockedDate).filter(
        BlockedDate.id == blocked_id, BlockedDate.doctor_id == doctor_id).first()
    if not item:
        return False, "Blocked date not found."
    db.delete(item)
    db.commit()
    log_action("DATE_UNBLOCKED", "doctor", record_id=blocked_id)
    return True, "Date unblocked."


def search_students(db, query=""):
    q = db.query(Student)
    if query:
        q = q.filter((Student.full_name.ilike(f"%{query}%")) |
                     (Student.enrollment_no.ilike(f"%{query}%")))
    return q.all()


def count_patients(db, doctor_id):
    from models import Consultation
    return (db.query(Consultation.patient_id)
            .filter(Consultation.doctor_id == doctor_id)
            .distinct().count())


def get_doctor_stats(db, doctor_id):
    from models import Appointment
    all_appts = db.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()
    today = __import__("utils").today_str()
    stats = {
        "total": len(all_appts),
        "today": sum(1 for a in all_appts if a.appointment_date == today),
        "upcoming": sum(1 for a in all_appts if a.appointment_date >= today and a.status in ("Requested", "Confirmed", "Rescheduled")),
        "completed": sum(1 for a in all_appts if a.status == "Completed"),
        "cancelled": sum(1 for a in all_appts if a.status == "Cancelled"),
        "no_show": sum(1 for a in all_appts if a.status == "No-show"),
    }
    return stats
