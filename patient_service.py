"""
Patient/Student service: profile management, medical profile and history.
"""
from audit_service import log_action
from database import get_session
from models import Consultation, MedicalCertificate, Student
from validators import is_valid_email


def get_student_by_user(db, user_id):
    return db.query(Student).filter(Student.user_id == user_id).first()


def get_student(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def update_student_profile(db, student_id, full_name, gender, dob, mobile,
                           address, emergency_contact, blood_group, basic_medical_info):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return False, "Student not found."
    student.full_name = full_name or student.full_name
    student.gender = gender
    student.date_of_birth = dob
    student.mobile = mobile
    student.address = address
    student.emergency_contact = emergency_contact
    student.blood_group = blood_group
    student.basic_medical_info = basic_medical_info
    db.commit()
    log_action("STUDENT_PROFILE_UPDATED", "student", record_id=student.id)
    return True, "Profile updated successfully."


def get_consultations_for_student(db, student_id):
    return (db.query(Consultation)
            .filter(Consultation.patient_id == student_id)
            .order_by(Consultation.consult_date.desc())
            .all())


def get_certificates_for_student(db, student_id):
    return (db.query(MedicalCertificate)
            .filter(MedicalCertificate.patient_id == student_id)
            .order_by(MedicalCertificate.issued_date.desc())
            .all())


def profile_completion_pct(student) -> int:
    fields = [student.full_name, student.gender, student.date_of_birth,
              student.mobile, student.address, student.emergency_contact,
              student.programme_id, student.department_id]
    filled = sum(1 for f in fields if f)
    return int((filled / len(fields)) * 100)
