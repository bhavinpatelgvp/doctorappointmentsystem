"""
Gujarat Vidyapith Doctor Appointment & Student Medical Management System.

Entry point: session init, authentication, routing and role-based navigation.
"""
import streamlit as st

from auth import authenticate, logout, register_student
from database import get_session, init_db
from models import Department, Programme
from security import (
    check_session_timeout,
    is_authenticated,
    require_login,
    restore_session_from_token,
)
from theme import inject_theme, set_page_config

import admin_ui
import doctor_ui
import hod_ui
import student_ui
import session_manager as sm
from utils import render_footer, render_header


def render_login():
    render_header()
    st.markdown("## 🔐 Login")
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if authenticate(username, password):
                st.session_state["current_page"] = {
                    "student": "student_dashboard",
                    "doctor": "doctor_dashboard",
                    "hod": "hod_dashboard",
                    "admin": "admin_dashboard",
                }.get(st.session_state["role"], "login")
                st.rerun()
            else:
                st.error(st.session_state.get("login_error", "Invalid username or password."))
    with col2:
        st.markdown("### New Student?")
        st.markdown("Register to book appointments and access medical services.")
        if st.button("Student Registration", use_container_width=True):
            st.session_state["current_page"] = "register"
            st.rerun()
    st.markdown("---")
    st.caption("Demo accounts are available in the README. Use the credentials to explore each role.")


def render_register():
    render_header()
    st.markdown("## 📝 Student Registration")
    db = get_session()
    try:
        programmes = {p.name: p.id for p in db.query(Programme).all()}
        departments = {d.name: d.id for d in db.query(Department).all()}
        col1, col2 = st.columns(2)
        full_name = col1.text_input("Full Name")
        enrollment_no = col2.text_input("Enrollment Number")
        username = col1.text_input("Username")
        email = col2.text_input("Email")
        programme = col1.selectbox("Programme", list(programmes.keys()))
        semester = col2.selectbox("Semester", [1, 2, 3, 4, 5, 6, 7, 8])
        department = col1.selectbox("Department", list(departments.keys()))
        mobile = col2.text_input("Mobile")
        password = col1.text_input("Password", type="password")
        confirm = col2.text_input("Confirm Password", type="password")
        if st.button("Register", type="primary"):
            ok, msg = register_student(
                username, email, password, confirm, full_name, enrollment_no,
                programmes[programme], semester, departments[department], mobile)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    finally:
        db.close()
    if st.button("← Back to Login"):
        st.session_state["current_page"] = "login"
        st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("### Gujarat Vidyapith")
        st.markdown("Health & Medical Services")
        st.markdown("---")
        role = st.session_state.get("role")
        if role == "student":
            nav = {
                "student_dashboard": "🏠 Dashboard",
                "student_book": "🔍 Find Doctor / Book",
                "student_appointments": "📅 My Appointments",
                "student_history": "🩺 Medical History",
                "student_certificates": "📄 Certificates",
                "student_profile": "👤 Profile",
            }
        elif role == "doctor":
            nav = {
                "doctor_dashboard": "🏠 Dashboard",
                "doctor_schedule": "🗓 Schedule",
                "doctor_patients": "👥 Patients",
                "doctor_consult": "🩺 Consultation",
                "doctor_certificates": "📄 Certificates",
                "doctor_certificate_create": "➕ New Certificate",
            }
        elif role == "hod":
            nav = {
                "hod_dashboard": "🏠 Dashboard",
                "hod_certificates": "📄 Certificates",
            }
        elif role == "admin":
            nav = {
                "admin_dashboard": "🏠 Dashboard",
                "admin_users": "👥 Users",
                "admin_students": "🎓 Students",
                "admin_doctors": "🩺 Doctors",
                "admin_hods": "📋 HODs",
                "admin_departments": "🏛 Departments",
                "admin_programmes": "🎓 Programmes",
                "admin_specializations": "🩺 Specializations",
                "admin_appointments": "📅 Appointments",
                "admin_certificates": "📄 Certificates",
                "admin_notifications": "🔔 Notifications",
                "admin_reports": "📊 Reports",
                "admin_audit": "📜 Audit Logs",
                "admin_settings": "⚙️ Settings",
            }
        else:
            nav = {}
        for key, label in nav.items():
            if st.button(label, use_container_width=True, key=f"nav_{key}"):
                st.session_state["current_page"] = key
                st.rerun()
        st.markdown("---")
        if is_authenticated():
            st.markdown(f"👤 **{st.session_state.get('display_name', '')}**")
            st.caption(f"Role: {st.session_state.get('role', '').title()}")
            if st.button("🚪 Logout", use_container_width=True):
                logout()
                st.session_state["current_page"] = "login"
                st.rerun()


@st.cache_resource
def _init_app():
    init_db()
    return True


def main():
    set_page_config()
    inject_theme()
    _init_app()
    sm.init_session()
    # Restore login from the persistent token if a page refresh reset session_state.
    restore_session_from_token()
    check_session_timeout()

    current_page = st.session_state.get("current_page", "login")

    # If authenticated via a restored persistent token but still on the login
    # page, redirect to the appropriate role dashboard.
    if is_authenticated() and current_page == "login":
        st.session_state["current_page"] = {
            "student": "student_dashboard",
            "doctor": "doctor_dashboard",
            "hod": "hod_dashboard",
            "admin": "admin_dashboard",
        }.get(st.session_state.get("role"), "login")
        st.rerun()

    # Public pages
    if current_page == "login":
        render_login()
    elif current_page == "register":
        render_register()
    elif is_authenticated():
        render_sidebar()
        role = st.session_state.get("role")
        handlers = {
            ("student", "student_dashboard"): student_ui.render_student_dashboard,
            ("student", "student_book"): student_ui.render_book_appointment,
            ("student", "student_slot"): student_ui.render_slot_selection,
            ("student", "student_appointments"): student_ui.render_appointments,
            ("student", "student_reschedule"): student_ui.render_reschedule,
            ("student", "student_history"): student_ui.render_history,
            ("student", "student_certificates"): student_ui.render_certificates,
            ("student", "student_profile"): student_ui.render_profile,
            ("doctor", "doctor_dashboard"): doctor_ui.render_doctor_dashboard,
            ("doctor", "doctor_schedule"): doctor_ui.render_schedule,
            ("doctor", "doctor_patients"): doctor_ui.render_patients,
            ("doctor", "doctor_patient_detail"): doctor_ui.render_patient_detail,
            ("doctor", "doctor_consult"): doctor_ui.render_consult,
            ("doctor", "doctor_certificates"): doctor_ui.render_certificates,
            ("doctor", "doctor_certificate_create"): doctor_ui.render_certificate_create,
            ("doctor", "doctor_certificate_verify"): doctor_ui.render_certificate_verify,
            ("hod", "hod_dashboard"): hod_ui.render_hod_dashboard,
            ("hod", "hod_certificates"): hod_ui.render_certificates,
            ("admin", "admin_dashboard"): admin_ui.render_admin_dashboard,
            ("admin", "admin_users"): admin_ui.render_user_management,
            ("admin", "admin_students"): admin_ui.render_student_management,
            ("admin", "admin_doctors"): admin_ui.render_doctor_management,
            ("admin", "admin_hods"): admin_ui.render_hod_management,
            ("admin", "admin_departments"): admin_ui.render_department_management,
            ("admin", "admin_programmes"): admin_ui.render_programme_management,
            ("admin", "admin_specializations"): admin_ui.render_specialization_management,
            ("admin", "admin_appointments"): admin_ui.render_appointment_management,
            ("admin", "admin_certificates"): admin_ui.render_certificate_management,
            ("admin", "admin_notifications"): admin_ui.render_notifications,
            ("admin", "admin_reports"): admin_ui.render_reports,
            ("admin", "admin_audit"): admin_ui.render_audit_logs,
            ("admin", "admin_settings"): admin_ui.render_settings,
        }
        handler = handlers.get((role, current_page))
        if handler:
            handler()
            render_footer()
        else:
            # Fall back to role dashboard
            st.session_state["current_page"] = {
                "student": "student_dashboard",
                "doctor": "doctor_dashboard",
                "hod": "hod_dashboard",
                "admin": "admin_dashboard",
            }.get(role, "login")
            st.rerun()
    else:
        st.session_state["current_page"] = "login"
        st.rerun()


if __name__ == "__main__":
    main()
