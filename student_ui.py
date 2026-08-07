"""
Student/Patient UI module.
"""
import streamlit as st

from appointment_service import (
    book_appointment,
    cancel_appointment_by_student,
    get_appointments_for_student,
    get_available_slots,
    get_departments,
    get_specializations,
    reschedule_appointment,
    search_doctors,
)
from database import get_session
from patient_service import (
    get_certificates_for_student,
    get_consultations_for_student,
    get_student_by_user,
    profile_completion_pct,
    update_student_profile,
)
from utils import (
    empty_state,
    format_time_12h,
    render_dashboard_card,
    render_header,
    section_title,
    status_badge,
    today_str,
)
from validators import is_valid_date


def require_student():
    from security import require_role
    require_role("student")


def render_student_dashboard():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        if not student:
            st.error("Student profile not found.")
            return
        st.markdown(f"## Welcome, {student.full_name} 📘")
        st.caption(f"Enrollment No: {student.enrollment_no}")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            render_dashboard_card("Profile", f"{profile_completion_pct(student)}%", "👤")
        with col2:
            upcoming = get_appointments_for_student(db, student.id, upcoming_only=True)
            render_dashboard_card("Upcoming Appointments", len(upcoming), "📅")
        with col3:
            certs = get_certificates_for_student(db, student.id)
            render_dashboard_card("Medical Certificates", len(certs), "📄")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📅 Book Appointment", use_container_width=True):
                st.session_state["current_page"] = "student_book"
                st.rerun()
        with c2:
            if st.button("🔍 Find Doctor", use_container_width=True):
                st.session_state["current_page"] = "student_book"
                st.rerun()

        section_title("Upcoming Appointment")
        upcoming = get_appointments_for_student(db, student.id, upcoming_only=True)
        if not upcoming:
            empty_state("No upcoming appointments. Book one to get started.")
        else:
            for apt in upcoming[:5]:
                doc = apt.doctor
                with st.container(border=True):
                    colA, colB, colC = st.columns([3, 2, 1])
                    colA.markdown(f"**Dr. {doc.full_name}**")
                    colA.caption(f"{apt.appointment_date} · {format_time_12h(apt.appointment_time)}")
                    colB.markdown(status_badge(apt.status))
                    colC.markdown(f"`{apt.appointment_no}`")
        st.markdown("---")
        section_title("Quick Links")
        q1, q2, q3 = st.columns(3)
        if q1.button("My Appointments", use_container_width=True):
            st.session_state["current_page"] = "student_appointments"
            st.rerun()
        if q2.button("Medical History", use_container_width=True):
            st.session_state["current_page"] = "student_history"
            st.rerun()
        if q3.button("Medical Certificates", use_container_width=True):
            st.session_state["current_page"] = "student_certificates"
            st.rerun()
    finally:
        db.close()


def render_book_appointment():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("🔍 Find a Doctor")
        specs = get_specializations(db)
        spec_opts = {("All Specializations" if not s else s.name): s.id for s in specs}
        spec_choice = st.selectbox("Specialization", list(spec_opts.keys()))
        name_query = st.text_input("Search by name")

        doctors = search_doctors(
            db,
            name=name_query,
            specialization_id=None if "All" in spec_choice else spec_opts[spec_choice],
        )
        if not doctors:
            empty_state("No doctors found. Try adjusting your search.")
            return

        st.markdown("**Select a Doctor**")
        for doc in doctors:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.markdown(f"**Dr. {doc.full_name}**")
                col1.caption(f"{doc.qualification or '—'} · Specialization: {(doc.specialization.name if doc.specialization else '—')}")
                col2.caption(f"Experience: {doc.experience_years or 0} yrs" if doc.experience_years else "")
                if col3.button("Book", key=f"book_{doc.id}"):
                    st.session_state["selected_doctor_id"] = doc.id
                    st.session_state["current_page"] = "student_slot"
                    st.rerun()

        st.markdown("---")
        if st.button("← Back to Dashboard"):
            st.session_state["current_page"] = "student_dashboard"
            st.rerun()
    finally:
        db.close()


def render_slot_selection():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        doctor_id = st.session_state.get("selected_doctor_id")
        from appointment_service import get_doctor as _gd
        from doctor_service import get_doctor
        doctor = get_doctor(db, doctor_id)
        if not doctor:
            st.error("Please select a doctor first.")
            st.session_state["current_page"] = "student_book"
            st.rerun()
            return

        st.markdown(f"## Book with Dr. {doctor.full_name}")
        st.caption(f"{doctor.qualification or '—'} · {(doctor.specialization.name if doctor.specialization else '—')}")

        selected_date = st.date_input("Select Date", value=__import__("datetime").date.today())
        date_str = selected_date.strftime("%Y-%m-%d")
        if date_str < today_str():
            st.warning("Please select today or a future date.")
            return

        slots = get_available_slots(db, doctor_id, date_str)
        if not slots:
            empty_state("No available slots for this date. Please choose another date.")
            return

        slot_opts = {f"{format_time_12h(t)} ({c} left)": t for t, c in slots}
        st.markdown("**Available Time Slots**")
        chosen = st.radio("Time", list(slot_opts.keys()), horizontal=True)
        chosen_time = slot_opts[chosen]

        apt_type = st.selectbox("Consultation Type", ["In-person", "Teleconsultation"])
        reason = st.text_area("Reason for visit (optional)")

        if st.button("✅ Confirm Appointment", type="primary"):
            ok, msg, apt = book_appointment(
                db, student.id, doctor_id, date_str, chosen_time,
                appointment_type=apt_type, reason=reason,
                created_by=st.session_state["user_id"],
            )
            if ok:
                st.success(msg)
                st.info(f"**Appointment ID:** {apt.appointment_no}\n\n"
                        f"**Doctor:** Dr. {doctor.full_name}\n"
                        f"**Date:** {apt.appointment_date}\n"
                        f"**Time:** {format_time_12h(apt.appointment_time)}\n"
                        f"**Status:** {apt.status}\n"
                        f"**Department/Specialization:** {(doctor.specialization.name if doctor.specialization else '—')}")
            else:
                st.error(msg)

        if st.button("← Back"):
            st.session_state["current_page"] = "student_book"
            st.rerun()
    finally:
        db.close()


def render_appointments():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("📅 My Appointments")
        statuses = ["All", "Requested", "Confirmed", "Completed", "Cancelled", "Rescheduled", "No-show"]
        chosen = st.selectbox("Filter by status", statuses)
        appts = get_appointments_for_student(
            db, student.id, status=None if chosen == "All" else chosen)
        if not appts:
            empty_state("No appointments found.")
            return

        for apt in appts:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
                col1.markdown(f"**Dr. {apt.doctor.full_name}**")
                col1.caption(f"{apt.appointment_date} · {format_time_12h(apt.appointment_time)}")
                col2.markdown(status_badge(apt.status))
                col3.markdown(f"`{apt.appointment_no}`")
                if apt.status in ("Requested", "Confirmed", "Rescheduled"):
                    with col4:
                        if st.button("Cancel", key=f"cancel_{apt.id}"):
                            ok, msg = cancel_appointment_by_student(db, apt.id, student.id, "Cancelled by student")
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
        st.markdown("---")
        if st.button("Reschedule an Appointment"):
            st.session_state["current_page"] = "student_reschedule"
            st.rerun()
        if st.button("← Back"):
            st.session_state["current_page"] = "student_dashboard"
            st.rerun()
    finally:
        db.close()


def render_reschedule():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("🔄 Reschedule Appointment")
        appts = get_appointments_for_student(db, student.id)
        rescheduable = [a for a in appts if a.status in ("Requested", "Confirmed", "Rescheduled")]
        if not rescheduable:
            empty_state("No appointments available to reschedule.")
            return
        options = {f"{a.appointment_no} · {a.appointment_date} {a.appointment_time}": a for a in rescheduable}
        choice = st.selectbox("Select appointment", list(options.keys()))
        apt = options[choice]
        new_date = st.date_input("New Date", value=__import__("datetime").date.today())
        date_str = new_date.strftime("%Y-%m-%d")
        slots = get_available_slots(db, apt.doctor_id, date_str)
        if slots:
            slot_opts = {format_time_12h(t): t for t, _ in slots}
            new_time = st.selectbox("New Time", list(slot_opts.keys()))
            if st.button("Reschedule"):
                ok, msg = reschedule_appointment(db, apt.id, student.id, date_str, slot_opts[new_time])
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.warning("No slots available for the selected date.")
        if st.button("← Back"):
            st.session_state["current_page"] = "student_appointments"
            st.rerun()
    finally:
        db.close()


def render_history():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("🩺 Medical History")
        consults = get_consultations_for_student(db, student.id)
        if not consults:
            empty_state("No medical history yet.")
            return
        for c in consults:
            with st.expander(f"Consultation on {c.consult_date} · Dr. {c.doctor.full_name}"):
                st.markdown(f"**Symptoms:** {c.symptoms or '—'}")
                st.markdown(f"**Diagnosis:** {c.diagnosis or '—'}")
                st.markdown(f"**Treatment:** {c.treatment or '—'}")
                st.markdown(f"**Advice:** {c.doctor_advice or '—'}")
                if c.rest_recommended:
                    st.warning(f"Rest recommended: {c.rest_from} to {c.rest_to}")
                if c.followup_date:
                    st.info(f"Follow-up: {c.followup_date}")
                pres = c.prescription
                if pres and pres.medicine_name:
                    st.markdown("**Prescription:**")
                    st.markdown(f"- {pres.medicine_name} ({pres.dosage or ''} · {pres.frequency or ''} · {pres.duration or ''})")
        if st.button("← Back"):
            st.session_state["current_page"] = "student_dashboard"
            st.rerun()
    finally:
        db.close()


def render_certificates():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("📄 My Medical Certificates")
        certs = get_certificates_for_student(db, student.id)
        if not certs:
            empty_state("No medical certificates issued yet.")
            return
        for cert in certs:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 2])
                col1.markdown(f"**Dr. {cert.doctor.full_name}**")
                col1.caption(f"Issued: {cert.issued_date} · Rest: {cert.rest_from} to {cert.rest_to} ({cert.rest_days} days)")
                col2.markdown(status_badge(cert.status))
                col3.markdown(f"`{cert.certificate_no}`")
                if cert.pdf_path:
                    import os
                    if os.path.exists(cert.pdf_path):
                        with open(cert.pdf_path, "rb") as f:
                            col3.download_button("Download PDF", f.read(),
                                                 file_name=f"{cert.certificate_no}.pdf",
                                                 mime="application/pdf",
                                                 key=f"dl_{cert.id}")
        if st.button("← Back"):
            st.session_state["current_page"] = "student_dashboard"
            st.rerun()
    finally:
        db.close()


def render_profile():
    require_student()
    render_header()
    db = get_session()
    try:
        student = get_student_by_user(db, st.session_state["user_id"])
        section_title("👤 My Profile")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=student.full_name)
            gender = st.selectbox("Gender", ["", "Male", "Female", "Other"],
                                  index=["", "Male", "Female", "Other"].index(student.gender or ""))
            dob = st.date_input("Date of Birth", value=__import__("datetime").date.today())
            mobile = st.text_input("Mobile", value=student.mobile or "")
            blood = st.selectbox("Blood Group (optional)", ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                                 index=["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].index(student.blood_group or ""))
        with col2:
            address = st.text_area("Address", value=student.address or "")
            emergency = st.text_input("Emergency Contact", value=student.emergency_contact or "")
            basic_info = st.text_area("Basic Medical Information (optional)", value=student.basic_medical_info or "")
        if st.button("💾 Save Profile", type="primary"):
            ok, msg = update_student_profile(
                db, student.id, full_name, gender, dob.strftime("%Y-%m-%d"),
                mobile, address, emergency, blood, basic_info)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
        if st.button("← Back"):
            st.session_state["current_page"] = "student_dashboard"
            st.rerun()
    finally:
        db.close()
