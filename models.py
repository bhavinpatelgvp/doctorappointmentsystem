"""
ORM models for the Gujarat Vidyapith Doctor Appointment
& Student Medical Management System.

Normalized relational schema covering users, students, doctors, HODs,
departments, programmes, specializations, schedules, appointments,
consultations, medical records, prescriptions, medical certificates,
notifications, audit logs and system settings.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # student | doctor | hod | admin
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    hod = relationship("Hod", back_populates="user", uselist=False)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    doctors = relationship("Doctor", back_populates="department")
    students = relationship("Student", back_populates="department")


class Programme(Base):
    __tablename__ = "programmes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g. B.Sc. Computer Science
    level = Column(String(50), nullable=True)               # e.g. Undergraduate


class Specialization(Base):
    __tablename__ = "specializations"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g. General Medicine


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("enrollment_no", name="uq_student_enrollment"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrollment_no = Column(String(30), nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    programme_id = Column(Integer, ForeignKey("programmes.id"), nullable=True)
    semester = Column(String(20), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    mobile = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    emergency_contact = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    basic_medical_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="student")
    department = relationship("Department", back_populates="students")
    programme = relationship("Programme")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_reg_no = Column(String(30), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    qualification = Column(String(150), nullable=True)
    specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    experience_years = Column(Integer, nullable=True)
    consultation_fee = Column(Integer, nullable=True)
    contact = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="doctor")
    specialization = relationship("Specialization")
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class Hod(Base):
    __tablename__ = "hods"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    contact = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="hod")
    department = relationship("Department")


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    weekday = Column(Integer, nullable=False)          # 0=Monday ... 6=Sunday
    start_time = Column(String(5), nullable=False)     # HH:MM (24h)
    end_time = Column(String(5), nullable=False)
    slot_minutes = Column(Integer, default=15)
    slot_capacity = Column(Integer, default=1)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)
    is_active = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="schedules")

    __table_args__ = (UniqueConstraint("doctor_id", "weekday", name="uq_doctor_weekday"),)


class BlockedDate(Base):
    __tablename__ = "blocked_dates"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    blocked_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    reason = Column(String(255), nullable=True)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    appointment_no = Column(String(30), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    appointment_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    appointment_time = Column(String(5), nullable=False)   # HH:MM
    appointment_type = Column(String(30), default="In-person")
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="Requested")  # Requested|Confirmed|Completed|Cancelled|Rescheduled|No-show
    booking_timestamp = Column(DateTime, default=datetime.utcnow)
    confirmation_timestamp = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Student")
    doctor = relationship("Doctor", back_populates="appointments")
    consultation = relationship("Consultation", back_populates="appointment", uselist=False)

    __table_args__ = (
        UniqueConstraint("doctor_id", "appointment_date", "appointment_time",
                         name="uq_doctor_datetime"),
    )


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True)
    consult_no = Column(String(30), unique=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    consult_date = Column(String(20), nullable=False)
    symptoms = Column(Text, nullable=True)
    observations = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment = Column(Text, nullable=True)
    doctor_advice = Column(Text, nullable=True)
    followup_date = Column(String(20), nullable=True)
    rest_recommended = Column(Boolean, default=False)
    rest_from = Column(String(20), nullable=True)
    rest_to = Column(String(20), nullable=True)
    created_timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Student")
    doctor = relationship("Doctor")
    appointment = relationship("Appointment", back_populates="consultation")
    prescription = relationship("Prescription", back_populates="consultation", uselist=False)
    certificate = relationship("MedicalCertificate", back_populates="consultation", uselist=False)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False)
    medicine_name = Column(String(150), nullable=False)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)

    consultation = relationship("Consultation", back_populates="prescription")


class MedicalCertificate(Base):
    __tablename__ = "medical_certificates"

    id = Column(Integer, primary_key=True)
    certificate_no = Column(String(30), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False)
    issued_date = Column(String(20), nullable=False)
    medical_advice = Column(Text, nullable=True)
    rest_from = Column(String(20), nullable=False)
    rest_to = Column(String(20), nullable=False)
    rest_days = Column(Integer, nullable=False)
    remarks = Column(Text, nullable=True)
    status = Column(String(20), default="Issued")  # Issued|Emailed|Partially_Emailed|Failed
    pdf_path = Column(String(255), nullable=True)
    created_timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Student")
    doctor = relationship("Doctor")
    consultation = relationship("Consultation", back_populates="certificate")
    notifications = relationship("Notification", back_populates="certificate")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    notification_no = Column(String(30), unique=True, nullable=False)
    certificate_id = Column(Integer, ForeignKey("medical_certificates.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    recipient = Column(String(120), nullable=False)
    recipient_type = Column(String(20), nullable=False)  # student|hod|doctor
    subject = Column(String(255), nullable=True)
    email_address = Column(String(120), nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="Pending")  # Pending|Sent|Failed
    failure_reason = Column(Text, nullable=True)
    created_timestamp = Column(DateTime, default=datetime.utcnow)

    certificate = relationship("MedicalCertificate", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    log_id = Column(String(30), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    role = Column(String(20), nullable=True)
    action = Column(String(100), nullable=False)
    module = Column(String(50), nullable=True)
    record_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="OK")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

