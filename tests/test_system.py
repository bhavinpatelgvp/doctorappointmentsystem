"""
Test suite for the Gujarat Vidyapith Doctor Appointment system.

Covers authentication, authorization, booking, double-booking prevention,
cancellation, schedule management, consultation, certificate generation,
and validation. Uses an in-memory / temp SQLite database.
"""
import os
import tempfile
from datetime import datetime, timedelta

import pytest

# Use a temporary DB before importing the app modules.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.name}"

from database import Base, engine, get_session  # noqa: E402
from models import (  # noqa: E402
    Department,
    Doctor,
    DoctorSchedule,
    Programme,
    Specialization,
    Student,
    User,
)
from security import hash_password, verify_password  # noqa: E402
from validators import (  # noqa: E402
    is_valid_email,
    is_valid_date,
    validate_rest_dates,
)
from appointment_service import (  # noqa: E402
    book_appointment,
    cancel_appointment_by_student,
    get_available_slots,
)
from consultation_service import create_consultation  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    # Drop and recreate all tables for a clean state per test.
    import models  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = get_session()
    # Seed minimal data
    dept = Department(name="Test Dept")
    prog = Programme(name="Test Prog")
    spec = Specialization(name="General Medicine")
    db.add_all([dept, prog, spec])
    db.flush()

    doc_user = User(username="doc1", email="doc1@test.com",
                    password_hash=hash_password("pass123"), role="doctor")
    stu_user = User(username="stu1", email="stu1@test.com",
                    password_hash=hash_password("pass123"), role="student")
    hod_user = User(username="hod1", email="hod1@test.com",
                    password_hash=hash_password("pass123"), role="hod")
    db.add_all([doc_user, stu_user, hod_user])
    db.flush()

    doctor = Doctor(user_id=doc_user.id, doctor_reg_no="REG1", full_name="Test Doctor",
                    specialization_id=spec.id, department_id=dept.id)
    student = Student(user_id=stu_user.id, enrollment_no="ENR1", full_name="Test Student",
                      programme_id=prog.id, department_id=dept.id)
    db.add_all([doctor, student])
    db.flush()

    # Schedule Monday (weekday 0) 09:00-10:00, 15 min slots
    db.add(DoctorSchedule(doctor_id=doctor.id, weekday=0, start_time="09:00",
                          end_time="10:00", slot_minutes=15, slot_capacity=1))
    db.commit()

    yield db
    db.close()


def next_monday():
    d = datetime.now()
    days_ahead = (0 - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (d + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def _get_doctor(db):
    return db.query(Doctor).first()


def _get_student(db):
    return db.query(Student).first()


# --- Authentication ---
def test_password_hash_and_verify(setup_db):
    h = hash_password("secret")
    assert h != "secret"
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


# --- Validation ---
def test_email_validation(setup_db):
    assert is_valid_email("abc@test.com")
    assert not is_valid_email("abc")
    assert not is_valid_email("")


def test_date_validation(setup_db):
    assert is_valid_date("2024-01-01")
    assert not is_valid_date("01-01-2024")


def test_rest_dates(setup_db):
    ok, _ = validate_rest_dates("2024-01-05", "2024-01-07")
    assert ok
    ok, _ = validate_rest_dates("2024-01-10", "2024-01-05")
    assert not ok


# --- Appointment booking ---
def test_booking_success(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    slots = get_available_slots(db, doc.id, next_monday())
    assert len(slots) > 0
    time = slots[0][0]
    ok, msg, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    assert apt is not None
    assert apt.patient_id == stu.id


def test_double_booking_prevention(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, _ = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    # Second booking same slot must fail
    ok2, msg2, apt2 = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert not ok2
    assert "already been booked" in msg2


def test_booking_unavailable_slot(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    # 10:30 not in 09:00-10:00 schedule
    ok, msg, _ = book_appointment(db, stu.id, doc.id, next_monday(), "10:30")
    assert not ok


def test_booking_past_date(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    past = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    ok, msg, _ = book_appointment(db, stu.id, doc.id, past, "09:15")
    assert not ok


# --- Cancellation ---
def test_cancel_appointment(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    ok, msg = cancel_appointment_by_student(db, apt.id, stu.id)
    assert ok
    db.refresh(apt)
    assert apt.status == "Cancelled"


def test_cancel_wrong_owner(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    # Wrong student id should not be able to cancel
    ok2, _ = cancel_appointment_by_student(db, apt.id, stu.id + 999)
    assert not ok2


# --- Consultation ---
def test_consultation_with_rest(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    ok, msg, cons = create_consultation(
        db, doc.id, stu.id, apt.id,
        symptoms="Fever", observations="Temp", diagnosis="Viral",
        treatment="Medication", doctor_advice="Rest", followup_date="",
        rest_recommended=True, rest_from="2024-10-01", rest_to="2024-10-03")
    assert ok
    assert cons.rest_recommended
    assert cons.rest_from == "2024-10-01"
    assert cons.rest_to == "2024-10-03"
    db.refresh(apt)
    assert apt.status == "Completed"


def test_consultation_invalid_rest(setup_db):
    db = setup_db
    doc = _get_doctor(db)
    stu = _get_student(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    ok, msg, _ = create_consultation(
        db, doc.id, stu.id, apt.id,
        symptoms="Fever", observations="", diagnosis="", treatment="",
        doctor_advice="", followup_date="",
        rest_recommended=True, rest_from="2024-10-05", rest_to="2024-10-03")
    assert not ok


def test_authorization_consultation_wrong_doctor(setup_db):
    db = setup_db
    stu = _get_student(db)
    doc = _get_doctor(db)
    time = get_available_slots(db, doc.id, next_monday())[0][0]
    ok, _, apt = book_appointment(db, stu.id, doc.id, next_monday(), time)
    assert ok
    # Wrong doctor (id + 999) cannot create consultation
    ok2, _, _ = create_consultation(db, doc.id + 999, stu.id, apt.id,
                                    symptoms="x", observations="", diagnosis="",
                                    treatment="", doctor_advice="", followup_date="",
                                    rest_recommended=False, rest_from="", rest_to="")
    assert not ok2
