"""
Doctor UI module.
"""
import streamlit as st

from appointment_service import (
    cancel_appointment_by_doctor,
    confirm_appointment,
    get_appointments_for_doctor,
    mark_status,
)
from certificate_service import (
    generate_certificate,
    get_certificates_for_doctor,
    retry_failed_notifications,
    verify_certificate,
)
from consultation_service import (
    create_consultation,
    get_consultations_for_doctor,
    get_prescriptions,
    save_prescription,
)
from database import get_session
from doctor_service import (
    add_blocked_date,
    count_patients,
    delete_schedule,
    get_blocked_dates,
    get_doctor_by_user,
    get_doctor_stats,
    get_schedules,
    remove_blocked_date,
    search_students,
    update_profile,
    upsert_schedule,
)
from patient_service import get_student, get_consultations_for_student
from utils import (
    WEEKDAYS,
    empty_state,
    format_time_12h,
    render_dashboard_card,
    render_header,
    section_title,
    status_badge,
    today_str,
)
from validators import is_valid_date


def require_doctor():
    from security import require_role
    require_role("doctor")


def render_doctor_dashboard():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        if not doctor:
            st.error("Doctor profile not found.")
            return
        st.markdown(f"## Welcome, Dr. {doctor.full_name} 🩺")
        st.caption(f"{doctor.qualification or '—'} · {(doctor.specialization.name if doctor.specialization else '—')}")

        stats = get_doctor_stats(db, doctor.id)
        col1, col2, col3, col4 = st.columns(4)
        render_dashboard_card("Today's Appointments", stats["today"], "📌", color="")
        render_dashboard_card("Upcoming", stats["upcoming"], "📅", color="")
        with col3:
            render_dashboard_card("Completed", stats["completed"], "✅", color="")
        with col4:
            render_dashboard_card("Patients", count_patients(db, doctor.id), "👥", color="")

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🗓 Manage Schedule", use_container_width=True):
            st.session_state["current_page"] = "doctor_schedule"
            st.rerun()
        if c2.button("👥 View Patients", use_container_width=True):
            st.session_state["current_page"] = "doctor_patients"
            st.rerun()
        if c3.button("🩺 Consultation", use_container_width=True):
            st.session_state["current_page"] = "doctor_consult"
            st.rerun()
        if c4.button("📄 Certificates", use_container_width=True):
            st.session_state["current_page"] = "doctor_certificates"
            st.rerun()

        section_title("Today's Appointments")
        today_appts = get_appointments_for_doctor(db, doctor.id, date_str=today_str())
        if not today_appts:
            empty_state("No appointments scheduled for today.")
        else:
            for apt in today_appts:
                with st.container(border=True):
                    colA, colB, colC, colD = st.columns([3, 2, 1, 2])
                    colA.markdown(f"**{apt.patient.full_name}**")
                    colA.caption(f"{apt.appointment_time} · {apt.appointment_type}")
                    colB.markdown(status_badge(apt.status))
                    colC.markdown(f"`{apt.appointment_no}`")
                    if apt.status in ("Requested", "Rescheduled"):
                        if colD.button("Confirm", key=f"cf_{apt.id}"):
                            ok, msg = confirm_appointment(db, apt.id, doctor.id)
                            st.success(msg) if ok else st.error(msg)
                    elif apt.status == "Confirmed":
                        if colD.button("Consult", key=f"cs_{apt.id}"):
                            st.session_state["selected_appointment_id"] = apt.id
                            st.session_state["current_page"] = "doctor_consult"
                            st.rerun()
    finally:
        db.close()


def render_schedule():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        section_title("🗓 Schedule Management")
        tab1, tab2 = st.tabs(["Working Schedule", "Blocked Dates"])

        with tab1:
            st.markdown("**Add / Update Schedule**")
            weekday = st.selectbox("Weekday", WEEKDAYS)
            col1, col2 = st.columns(2)
            start_time = col1.text_input("Start Time (HH:MM)", value="09:00")
            end_time = col2.text_input("End Time (HH:MM)", value="13:00")
            col3, col4 = st.columns(2)
            slot_min = col3.number_input("Slot Duration (min)", value=15, min_value=5, step=5)
            capacity = col4.number_input("Max per Slot", value=1, min_value=1, step=1)
            col5, col6 = st.columns(2)
            break_start = col5.text_input("Break Start (HH:MM, optional)", value="")
            break_end = col6.text_input("Break End (HH:MM, optional)", value="")
            is_active = st.checkbox("Active", value=True)
            if st.button("Save Schedule", type="primary"):
                ok, msg = upsert_schedule(db, doctor.id, weekday, start_time, end_time,
                                          int(slot_min), int(capacity), break_start, break_end, is_active)
                st.success(msg) if ok else st.error(msg)

            st.markdown("**Current Schedules**")
            schedules = get_schedules(db, doctor.id)
            if not schedules:
                empty_state("No schedules configured yet.")
            for sch in schedules:
                with st.container(border=True):
                    colA, colB = st.columns([4, 1])
                    colA.markdown(f"**{WEEKDAYS[sch.weekday]}** · {format_time_12h(sch.start_time)} – {format_time_12h(sch.end_time)}"
                                  f" · {sch.slot_minutes} min slots · cap {sch.slot_capacity}"
                                  f" {'· Break ' + format_time_12h(sch.break_start) + '-' + format_time_12h(sch.break_end) if sch.break_start else ''}")
                    if colB.button("Delete", key=f"delsch_{sch.id}"):
                        delete_schedule(db, sch.id, doctor.id)
                        st.rerun()

        with tab2:
            st.markdown("**Block a Date (unavailable)**")
            b_date = st.date_input("Select date to block")
            b_reason = st.text_input("Reason (optional)")
            if st.button("Block Date", type="primary"):
                ok, msg = add_blocked_date(db, doctor.id, b_date.strftime("%Y-%m-%d"), b_reason)
                st.success(msg) if ok else st.error(msg)
            st.markdown("**Blocked Dates**")
            for blk in get_blocked_dates(db, doctor.id):
                colA, colB = st.columns([4, 1])
                colA.markdown(f"**{blk.blocked_date}** — {blk.reason or 'No reason'}")
                if colB.button("Unblock", key=f"unblk_{blk.id}"):
                    remove_blocked_date(db, blk.id, doctor.id)
                    st.rerun()
        if st.button("← Back to Dashboard"):
            st.session_state["current_page"] = "doctor_dashboard"
            st.rerun()
    finally:
        db.close()


def render_patients():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        section_title("👥 Patient Search")
        query = st.text_input("Search by name or enrollment number")
        students = search_students(db, query)
        if not students:
            empty_state("No students found.")
            return
        for student in students[:50]:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.markdown(f"**{student.full_name}**")
                col1.caption(f"{student.enrollment_no} · {(student.programme.name if student.programme else '—')}")
                col2.caption(f"{(student.department.name if student.department else '—')}")
                if col3.button("View", key=f"pt_{student.id}"):
                    st.session_state["selected_doctor_patient_id"] = student.id
                    st.session_state["current_page"] = "doctor_patient_detail"
                    st.rerun()
        if st.button("← Back"):
            st.session_state["current_page"] = "doctor_dashboard"
            st.rerun()
    finally:
        db.close()


def render_patient_detail():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        student_id = st.session_state.get("selected_doctor_patient_id")
        student = get_student(db, student_id)
        if not student:
            st.error("Student not found.")
            return
        st.markdown(f"## {student.full_name}")
        st.caption(f"Enrollment: {student.enrollment_no} · {(student.department.name if student.department else '—')}")
        st.markdown(f"**Blood Group:** {student.blood_group or '—'} · **Emergency Contact:** {student.emergency_contact or '—'}")
        section_title("Medical History")
        consults = get_consultations_for_student(db, student.id)
        if not consults:
            empty_state("No medical history for this student.")
        for c in consults:
            with st.expander(f"{c.consult_date} · Dr. {c.doctor.full_name}"):
                st.markdown(f"**Symptoms:** {c.symptoms or '—'}")
                st.markdown(f"**Diagnosis:** {c.diagnosis or '—'}")
                st.markdown(f"**Treatment:** {c.treatment or '—'}")
                st.markdown(f"**Advice:** {c.doctor_advice or '—'}")
        if st.button("← Back to Patients"):
            st.session_state["current_page"] = "doctor_patients"
            st.rerun()
    finally:
        db.close()


def render_consult():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        section_title("🩺 Conduct Consultation")
        appts = get_appointments_for_doctor(db, doctor.id)
        consultable = [a for a in appts if a.status in ("Confirmed", "Requested", "Rescheduled")]
        default_idx = 0
        if st.session_state.get("selected_appointment_id"):
            for i, a in enumerate(consultable):
                if a.id == st.session_state["selected_appointment_id"]:
                    default_idx = i
                    break
        if not consultable:
            empty_state("No confirmed appointments pending consultation.")
            return
        options = {f"{a.patient.full_name} · {a.appointment_date} {a.appointment_time} · {a.appointment_no}": a for a in consultable}
        choice = st.selectbox("Select appointment", list(options.keys()), index=default_idx)
        apt = options[choice]
        st.markdown(f"**Patient:** {apt.patient.full_name} · **Reason:** {apt.reason or '—'}")

        symptoms = st.text_area("Symptoms")
        observations = st.text_area("Clinical Observations")
        diagnosis = st.text_area("Diagnosis")
        treatment = st.text_area("Treatment")
        advice = st.text_area("Doctor Advice")
        followup = st.date_input("Follow-up Date (optional)", value=None)
        rest_rec = st.checkbox("Recommend Rest (generate Medical Certificate)")
        rest_from = None
        rest_to = None
        if rest_rec:
            col1, col2 = st.columns(2)
            rf = col1.date_input("Rest From")
            rt = col2.date_input("Rest To")
            rest_from = rf.strftime("%Y-%m-%d")
            rest_to = rt.strftime("%Y-%m-%d")

        if st.button("💾 Save Consultation", type="primary"):
            ok, msg, consultation = create_consultation(
                db, doctor.id, apt.patient_id, apt.id, symptoms, observations,
                diagnosis, treatment, advice,
                followup.strftime("%Y-%m-%d") if followup else "",
                rest_rec, rest_from, rest_to)
            if ok:
                st.success(msg)
                st.session_state["selected_consultation_id"] = consultation.id
                st.rerun()
            else:
                st.error(msg)

        # Prescription entry for a selected consultation
        consult_id = st.session_state.get("selected_consultation_id")
        if consult_id:
            st.markdown("---")
            section_title("💊 Prescription")
            med = st.text_input("Medicine Name")
            dos, freq, dur = st.columns(3)
            dosage = dos.text_input("Dosage")
            frequency = freq.text_input("Frequency")
            duration = dur.text_input("Duration")
            if st.button("Save Prescription"):
                ok, msg = save_prescription(db, consult_id, [{
                    "medicine_name": med, "dosage": dosage, "frequency": frequency,
                    "duration": duration,
                }])
                st.success(msg) if ok else st.error(msg)
                if ok and rest_rec and rest_from and rest_to:
                    st.session_state["current_page"] = "doctor_certificate_create"
                    st.session_state["rest_from"] = rest_from
                    st.session_state["rest_to"] = rest_to
                    st.rerun()
        if st.button("← Back"):
            st.session_state["current_page"] = "doctor_dashboard"
            st.rerun()
    finally:
        db.close()


def render_certificates():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        section_title("📄 Medical Certificates")
        col1, col2 = st.columns(2)
        if col1.button("➕ Generate Certificate", use_container_width=True):
            st.session_state["current_page"] = "doctor_certificate_create"
            st.rerun()
        if col2.button("🔎 Verify Certificate", use_container_width=True):
            st.session_state["current_page"] = "doctor_certificate_verify"
            st.rerun()

        certs = get_certificates_for_doctor(db, doctor.id)
        if not certs:
            empty_state("No certificates issued yet.")
            return
        for cert in certs:
            with st.container(border=True):
                colA, colB, colC, colD = st.columns([3, 2, 2, 2])
                colA.markdown(f"**{cert.patient.full_name}**")
                colA.caption(f"{cert.issued_date} · Rest: {cert.rest_from} → {cert.rest_to} ({cert.rest_days} days)")
                colB.markdown(status_badge(cert.status))
                colC.markdown(f"`{cert.certificate_no}`")
                if colD.button("Retry Emails", key=f"retry_{cert.id}"):
                    results = retry_failed_notifications(db, cert)
                    failed = [r for r in results if not r[1]]
                    if failed:
                        st.warning("Some emails still failed.")
                    else:
                        st.success("All failed emails sent successfully.")
        if st.button("← Back"):
            st.session_state["current_page"] = "doctor_dashboard"
            st.rerun()
    finally:
        db.close()


def render_certificate_create():
    require_doctor()
    render_header()
    db = get_session()
    try:
        doctor = get_doctor_by_user(db, st.session_state["user_id"])
        section_title("➕ Generate Medical Certificate")
        st.info("Select a completed consultation to certify.")
        consultable = get_consultations_for_doctor(db, doctor.id)
        if not consultable:
            empty_state("No completed consultations available for certification.")
            return
        options = {f"{c.patient.full_name} · {c.consult_date} · {c.consult_no}": c for c in consultable}
        choice = st.selectbox("Consultation", list(options.keys()))
        consultation = options[choice]
        student = consultation.patient

        st.markdown(f"**Student:** {student.full_name} ({student.enrollment_no})")
        st.markdown(f"**Programme:** {(student.programme.name if student.programme else '—')} · "
                    f"**Department:** {(student.department.name if student.department else '—')}")

        advice = st.text_area("Medical Advice", value=consultation.doctor_advice or "")
        col1, col2 = st.columns(2)
        rf = col1.date_input("Rest From")
        rt = col2.date_input("Rest To")
        remarks = st.text_area("Certificate Remarks")
        if st.button("Generate & Email Certificate", type="primary"):
            ok, msg, cert = generate_certificate(
                db, doctor.id, student.id, consultation.id, advice,
                rf.strftime("%Y-%m-%d"), rt.strftime("%Y-%m-%d"), remarks)
            if ok:
                st.success(msg)
                st.info(f"Certificate ID: {cert.certificate_no}")
            else:
                st.error(msg)
        if st.button("← Back"):
            st.session_state["current_page"] = "doctor_certificates"
            st.rerun()
    finally:
        db.close()


def render_certificate_verify():
    require_doctor()
    render_header()
    db = get_session()
    try:
        section_title("🔎 Verify Medical Certificate")
        cert_no = st.text_input("Enter Certificate ID")
        if st.button("Verify"):
            cert = verify_certificate(db, cert_no.strip())
            if cert:
                st.success("Certificate is VALID.")
                st.markdown(f"- **Certificate No:** {cert.certificate_no}")
                st.markdown(f"- **Student:** {cert.patient.full_name} ({cert.patient.enrollment_no})")
                st.markdown(f"- **Doctor:** Dr. {cert.doctor.full_name}")
                st.markdown(f"- **Issued:** {cert.issued_date}")
                st.markdown(f"- **Rest Period:** {cert.rest_from} to {cert.rest_to} ({cert.rest_days} days)")
                st.markdown(f"- **Status:** {cert.status}")
            else:
                st.error("Certificate not found or invalid.")
        if st.button("← Back"):
            st.session_state["current_page"] = "doctor_certificates"
            st.rerun()
    finally:
        db.close()
