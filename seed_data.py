"""
Seed data generator for demonstration.

Creates clearly-marked demo records: departments, programmes, specializations,
doctors, students, HODs, schedules, and a sample appointment + consultation.

DEMO DATA ONLY — never mix with production data.
"""
from datetime import datetime, timedelta

from database import get_session, init_db
from models import (
    Appointment,
    Consultation,
    Department,
    Doctor,
    DoctorSchedule,
    Hod,
    Programme,
    Specialization,
    Student,
    User,
)
from security import hash_password
from utils import generate_number


def seed():
    init_db()
    db = get_session()
    try:
        if db.query(User).count() > 0:
            print("Database already has data. Skipping seed.")
            return

        # Departments
        dept_cs = Department(name="Computer Science", description="Department of Computer Science")
        dept_maths = Department(name="Mathematics", description="Department of Mathematics")
        dept_life = Department(name="Life Sciences", description="Department of Life Sciences")
        db.add_all([dept_cs, dept_maths, dept_life])
        db.flush()

        # Programmes
        prog_bsc_cs = Programme(name="B.Sc. Computer Science", level="Undergraduate")
        prog_bsc_maths = Programme(name="B.Sc. Mathematics", level="Undergraduate")
        prog_ma = Programme(name="M.A. Gujarati", level="Postgraduate")
        db.add_all([prog_bsc_cs, prog_bsc_maths, prog_ma])
        db.flush()

        # Specializations
        spec_general = Specialization(name="General Medicine")
        spec_derm = Specialization(name="Dermatology")
        spec_ortho = Specialization(name="Orthopedics")
        db.add_all([spec_general, spec_derm, spec_ortho])
        db.flush()

        # --- Admin ---
        admin_user = User(username="admin", email="admin@gv.edu.in",
                          password_hash=hash_password("admin123"), role="admin")
        db.add(admin_user)

        # --- Doctors ---
        doc1_user = User(username="dr.shah", email="dr.shah@gv.edu.in",
                         password_hash=hash_password("doctor123"), role="doctor")
        doc2_user = User(username="dr.patel", email="dr.patel@gv.edu.in",
                         password_hash=hash_password("doctor123"), role="doctor")
        doc3_user = User(username="dr.joshi", email="dr.joshi@gv.edu.in",
                         password_hash=hash_password("doctor123"), role="doctor")
        db.add_all([doc1_user, doc2_user, doc3_user])
        db.flush()

        doc1 = Doctor(user_id=doc1_user.id, doctor_reg_no="GMC1001", full_name="Amit Shah",
                      qualification="MBBS, MD (General Medicine)", specialization_id=spec_general.id,
                      department_id=dept_cs.id, experience_years=12, consultation_fee=300,
                      contact="9876500001", bio="General physician with 12 years of experience.")
        doc2 = Doctor(user_id=doc2_user.id, doctor_reg_no="GMC1002", full_name="Priya Patel",
                      qualification="MBBS, MD (Dermatology)", specialization_id=spec_derm.id,
                      department_id=dept_maths.id, experience_years=8, consultation_fee=400,
                      contact="9876500002", bio="Dermatologist.")
        doc3 = Doctor(user_id=doc3_user.id, doctor_reg_no="GMC1003", full_name="Ramesh Joshi",
                      qualification="MBBS, MS (Orthopedics)", specialization_id=spec_ortho.id,
                      department_id=dept_life.id, experience_years=15, consultation_fee=500,
                      contact="9876500003", bio="Orthopedic surgeon.")
        db.add_all([doc1, doc2, doc3])
        db.flush()

        # --- HODs ---
        hod1_user = User(username="hod.cs", email="hod.cs@gv.edu.in",
                         password_hash=hash_password("hod123"), role="hod")
        hod2_user = User(username="hod.maths", email="hod.maths@gv.edu.in",
                         password_hash=hash_password("hod123"), role="hod")
        db.add_all([hod1_user, hod2_user])
        db.flush()
        hod1 = Hod(user_id=hod1_user.id, full_name="Dr. Kavita Mehta", email="hod.cs@gv.edu.in",
                   department_id=dept_cs.id, contact="9876500011")
        hod2 = Hod(user_id=hod2_user.id, full_name="Dr. Sunil Desai", email="hod.maths@gv.edu.in",
                   department_id=dept_maths.id, contact="9876500012")
        db.add_all([hod1, hod2])

        # --- Students ---
        stu1_user = User(username="student1", email="student1@gv.edu.in",
                         password_hash=hash_password("student123"), role="student")
        stu2_user = User(username="student2", email="student2@gv.edu.in",
                         password_hash=hash_password("student123"), role="student")
        stu3_user = User(username="student3", email="student3@gv.edu.in",
                         password_hash=hash_password("student123"), role="student")
        db.add_all([stu1_user, stu2_user, stu3_user])
        db.flush()

        stu1 = Student(user_id=stu1_user.id, enrollment_no="GV2024001", full_name="Rohan Mehta",
                       gender="Male", date_of_birth="2004-05-12", programme_id=prog_bsc_cs.id,
                       semester=3, department_id=dept_cs.id, mobile="9876510001",
                       emergency_contact="9876510099", blood_group="B+")
        stu2 = Student(user_id=stu2_user.id, enrollment_no="GV2024002", full_name="Sneha Iyer",
                       gender="Female", date_of_birth="2005-01-20", programme_id=prog_bsc_maths.id,
                       semester=2, department_id=dept_maths.id, mobile="9876510002",
                       emergency_contact="9876510098", blood_group="O+")
        stu3 = Student(user_id=stu3_user.id, enrollment_no="GV2024003", full_name="Arjun Rao",
                       gender="Male", date_of_birth="2003-08-30", programme_id=prog_ma.id,
                       semester=5, department_id=dept_life.id, mobile="9876510003",
                       emergency_contact="9876510097", blood_group="A+")
        db.add_all([stu1, stu2, stu3])
        db.flush()

        # --- Doctor schedules ---
        # doc1: Mon-Fri 09:00-13:00, 15 min slots
        for wd in range(5):
            db.add(DoctorSchedule(doctor_id=doc1.id, weekday=wd, start_time="09:00",
                                  end_time="13:00", slot_minutes=15, slot_capacity=1,
                                  break_start="11:00", break_end="11:15"))
        # doc2: Mon/Wed/Fri 10:00-14:00
        for wd in [0, 2, 4]:
            db.add(DoctorSchedule(doctor_id=doc2.id, weekday=wd, start_time="10:00",
                                  end_time="14:00", slot_minutes=20, slot_capacity=1))
        # doc3: Tue/Thu 09:30-12:30
        for wd in [1, 3]:
            db.add(DoctorSchedule(doctor_id=doc3.id, weekday=wd, start_time="09:30",
                                  end_time="12:30", slot_minutes=15, slot_capacity=1))

        # --- Sample appointment (tomorrow) + consultation for stu1 ---
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        apt = Appointment(
            appointment_no=generate_number("APT"),
            patient_id=stu1.id, doctor_id=doc1.id,
            appointment_date=tomorrow, appointment_time="09:15",
            appointment_type="In-person", reason="Fever and headache",
            status="Confirmed", booking_timestamp=datetime.utcnow(),
            confirmation_timestamp=datetime.utcnow(), created_by=stu1_user.id,
        )
        db.add(apt)
        db.flush()

        today = datetime.now().strftime("%Y-%m-%d")
        consultation = Consultation(
            consult_no=generate_number("CON"),
            patient_id=stu1.id, doctor_id=doc1.id, appointment_id=apt.id,
            consult_date=today, symptoms="Fever, headache, fatigue",
            observations="Mild temperature, otherwise stable",
            diagnosis="Viral infection",
            treatment="Prescribed rest and medication",
            doctor_advice="Drink fluids and take rest.",
            rest_recommended=False,
        )
        db.add(consultation)

        db.commit()
        print("=" * 60)
        print("Sample data seeded successfully.")
        print("=" * 60)
        print("Demo login credentials:")
        print("  Admin  : admin / admin123")
        print("  Doctor : dr.shah / doctor123")
        print("  HOD    : hod.cs / hod123")
        print("  Student: student1 / student123")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
