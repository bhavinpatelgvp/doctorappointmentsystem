"""
Administrator UI module.
"""
import streamlit as st
import pandas as pd

from audit_service import log_action
from certificate_service import get_certificates_for_hod
from database import get_session
from models import (
    AuditLog,
    Department,
    Doctor,
    DoctorSchedule,
    Hod,
    Notification,
    Programme,
    Specialization,
    Student,
    User,
)
from report_service import (
    appointment_status_stats,
    appointments_df,
    certificate_status_stats,
    department_wise_appointments,
    doctor_wise_appointments,
    get_admin_kpis,
    monthly_appointment_trend,
    to_csv,
    to_excel,
)
from security import hash_password
from utils import empty_state, render_dashboard_card, render_header, section_title


def require_admin():
    from security import require_role
    require_role("admin")


def _all_users(db):
    return db.query(User).all()


def render_admin_dashboard():
    require_admin()
    render_header()
    db = get_session()
    try:
        st.markdown("## Welcome, Administrator 🏛")
        kpis = get_admin_kpis(db)
        col1, col2, col3, col4 = st.columns(4)
        render_dashboard_card("Students", kpis["total_students"], "🎓")
        render_dashboard_card("Doctors", kpis["total_doctors"], "🩺")
        with col3:
            render_dashboard_card("Appointments", kpis["total_appointments"], "📅")
        with col4:
            render_dashboard_card("Certificates", kpis["total_certificates"], "📄")
        col5, col6, col7, col8 = st.columns(4)
        render_dashboard_card("Today", kpis["today_appointments"], "📌")
        with col6:
            render_dashboard_card("Completed", kpis["completed"], "✅")
        with col7:
            render_dashboard_card("Cancelled", kpis["cancelled"], "❌")
        with col8:
            render_dashboard_card("No-show", kpis["no_show"], "⚠")

        st.markdown("---")
        section_title("📊 Analytics")
        tab1, tab2, tab3, tab4 = st.tabs(["Appointment Status", "Trends", "Department-wise", "Doctor-wise"])
        with tab1:
            stat_df = appointment_status_stats(db)
            if not stat_df.empty:
                st.bar_chart(stat_df.set_index("status"))
                st.dataframe(stat_df)
        with tab2:
            trend = monthly_appointment_trend(db)
            if not trend.empty:
                st.line_chart(trend.set_index("month"))
                st.dataframe(trend)
            else:
                empty_state("No trend data yet.")
        with tab3:
            dept_df = department_wise_appointments(db)
            if not dept_df.empty:
                dept_map = {d.id: d.name for d in db.query(Department).all()}
                dept_df["department"] = dept_df["department_id"].map(dept_map)
                st.dataframe(dept_df)
            else:
                empty_state("No department data yet.")
        with tab4:
            doc_df = doctor_wise_appointments(db)
            if not doc_df.empty:
                st.dataframe(doc_df)
            else:
                empty_state("No data yet.")
    finally:
        db.close()


def render_user_management():
    require_admin()
    render_header()
    section_title("👥 User Management")
    db = get_session()
    try:
        users = _all_users(db)
        st.markdown("**All Users**")
        data = [{
            "ID": u.id, "Username": u.username, "Email": u.email,
            "Role": u.role, "Active": u.is_active,
        } for u in users]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.markdown("---")
        st.markdown("**Create User**")
        col1, col2 = st.columns(2)
        username = col1.text_input("Username")
        email = col2.text_input("Email")
        role = st.selectbox("Role", ["student", "doctor", "hod", "admin"])
        password = st.text_input("Password", type="password")
        if st.button("Create User", type="primary"):
            if username and email and password:
                existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
                if existing:
                    st.error("Username or email already exists.")
                else:
                    u = User(username=username, email=email.lower(),
                             password_hash=hash_password(password), role=role)
                    db.add(u)
                    db.commit()
                    log_action("USER_CREATED", "admin", record_id=u.id, details=f"Created {role} user")
                    st.success(f"User {username} created.")
            else:
                st.error("All fields are required.")
    finally:
        db.close()


def render_student_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🎓 Student Management")
        students = db.query(Student).all()
        data = [{
            "ID": s.id, "Name": s.full_name, "Enrollment": s.enrollment_no,
            "Programme": s.programme.name if s.programme else '—',
            "Department": s.department.name if s.department else '—',
        } for s in students]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    finally:
        db.close()


def render_doctor_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🩺 Doctor Management")
        doctors = db.query(Doctor).all()
        data = [{
            "ID": d.id, "Name": d.full_name, "Reg No": d.doctor_reg_no,
            "Specialization": d.specialization.name if d.specialization else '—',
            "Department": d.department.name if d.department else '—',
            "Experience": d.experience_years,
        } for d in doctors]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    finally:
        db.close()


def render_department_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🏛 Department Management")
        st.markdown("**Add Department**")
        name = st.text_input("Department Name")
        desc = st.text_input("Description")
        if st.button("Add Department", type="primary"):
            if name:
                db.add(Department(name=name, description=desc))
                db.commit()
                st.success(f"Department {name} added.")
            else:
                st.error("Name is required.")
        departments = db.query(Department).all()
        st.dataframe(pd.DataFrame([{"ID": d.id, "Name": d.name, "Description": d.description} for d in departments]))
    finally:
        db.close()


def render_programme_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🎓 Programme Management")
        name = st.text_input("Programme Name")
        level = st.text_input("Level")
        if st.button("Add Programme", type="primary"):
            if name:
                db.add(Programme(name=name, level=level))
                db.commit()
                st.success(f"Programme {name} added.")
        programmes = db.query(Programme).all()
        st.dataframe(pd.DataFrame([{"ID": p.id, "Name": p.name, "Level": p.level} for p in programmes]))
    finally:
        db.close()


def render_specialization_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🩺 Specialization Management")
        name = st.text_input("Specialization Name")
        if st.button("Add Specialization", type="primary"):
            if name:
                db.add(Specialization(name=name))
                db.commit()
                st.success(f"Specialization {name} added.")
        specs = db.query(Specialization).all()
        st.dataframe(pd.DataFrame([{"ID": s.id, "Name": s.name} for s in specs]))
    finally:
        db.close()


def render_hod_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("📋 HOD Management")
        hods = db.query(Hod).all()
        data = [{
            "ID": h.id, "Name": h.full_name, "Email": h.email,
            "Department": h.department.name if h.department else '—',
        } for h in hods]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    finally:
        db.close()


def render_appointment_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("📅 Appointment Management")
        today = __import__("utils").today_str()
        appts = db.query(__import__("models").Appointment).all()
        data = [{
            "No": a.appointment_no, "Patient ID": a.patient_id, "Doctor ID": a.doctor_id,
            "Date": a.appointment_date, "Time": a.appointment_time, "Status": a.status,
        } for a in appts]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    finally:
        db.close()


def render_certificate_management():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("📄 Medical Certificate Management")
        certs = db.query(__import__("models").MedicalCertificate).all()
        data = [{
            "No": c.certificate_no, "Student": c.patient.full_name,
            "Doctor": c.doctor.full_name, "Issued": c.issued_date,
            "Rest": f"{c.rest_from} → {c.rest_to}", "Status": c.status,
        } for c in certs]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    finally:
        db.close()


def render_notifications():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("🔔 Email Notifications")
        notifs = db.query(Notification).order_by(Notification.id.desc()).limit(100).all()
        data = [{
            "No": n.notification_no, "Recipient": n.recipient, "Type": n.recipient_type,
            "Email": n.email_address, "Status": n.status, "Subject": (n.subject or "")[:40],
        } for n in notifs]
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            empty_state("No notifications yet.")
    finally:
        db.close()


def render_audit_logs():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("📜 Audit Logs")
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
        data = [{
            "Log": l.log_id, "User": l.user_id, "Role": l.role, "Action": l.action,
            "Module": l.module, "Record": l.record_id, "Timestamp": l.timestamp, "Status": l.status,
        } for l in logs]
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            empty_state("No audit logs yet.")
    finally:
        db.close()


def render_reports():
    require_admin()
    render_header()
    section_title("📊 Reports & Export")
    db = get_session()
    try:
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", value=__import__("datetime").date(2020, 1, 1))
        end_date = col2.date_input("End Date", value=__import__("datetime").date.today())
        df = appointments_df(db, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        st.markdown(f"**{len(df)} appointment records**")
        csv = to_csv(df)
        excel = to_excel(df)
        c1, c2 = st.columns(2)
        c1.download_button("⬇ Download CSV", csv, file_name="appointments_report.csv", mime="text/csv")
        c2.download_button("⬇ Download Excel", excel, file_name="appointments_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(df, use_container_width=True)
    finally:
        db.close()


def render_settings():
    require_admin()
    render_header()
    db = get_session()
    try:
        section_title("⚙️ System Settings")
        st.markdown("**Institution Information**")
        from config import APP_NAME, APP_SUBTITLE, APP_TAGLINE, INSTITUTION_ADDRESS
        st.markdown(f"- **Organization:** {APP_NAME}")
        st.markdown(f"- **Subtitle:** {APP_SUBTITLE}")
        st.markdown(f"- **Tagline:** {APP_TAGLINE}")
        st.markdown(f"- **Address:** {INSTITUTION_ADDRESS}")
        st.info("Email/SMTP settings are configured via the .env file. Requests manually."
                " For security, passwords and secrets are never stored in the database.")
    finally:
        db.close()
