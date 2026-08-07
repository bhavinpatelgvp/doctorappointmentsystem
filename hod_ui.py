"""
HOD UI module.

HOD has restricted access to medical certificate notifications only.
It does NOT see unrestricted student medical history.
"""
import streamlit as st

from certificate_service import get_certificates_for_hod, verify_certificate
from database import get_session
from models import Hod
from patient_service import get_student
from utils import empty_state, render_dashboard_card, render_header, section_title, status_badge


def require_hod():
    from security import require_role
    require_role("hod")


def _get_hod(db, user_id):
    return db.query(Hod).filter(Hod.user_id == user_id).first()


def render_hod_dashboard():
    require_hod()
    render_header()
    db = get_session()
    try:
        hod = _get_hod(db, st.session_state["user_id"])
        if not hod:
            st.error("HOD profile not found.")
            return
        st.markdown(f"## Welcome, {hod.full_name} 📋")
        st.caption(f"Department: {(hod.department.name if hod.department else '—')}")

        dept_id = hod.department_id
        certs = get_certificates_for_hod(db, dept_id)
        col1, col2 = st.columns(2)
        render_dashboard_card("Medical Certificates", len(certs), "📄")
        with col2:
            render_dashboard_card("Pending Review", sum(1 for c in certs if c.status != "Emailed"), "⏳")

        section_title("🔎 Verify Certificate")
        with st.form("hod_verify"):
            cert_no = st.text_input("Enter Certificate ID to verify")
            submitted = st.form_submit_button("Verify")
            if submitted and cert_no:
                cert = verify_certificate(db, cert_no.strip())
                if cert:
                    st.success("Certificate is VALID.")
                    st.markdown(f"- Student: **{cert.patient.full_name}** ({cert.patient.enrollment_no})")
                    st.markdown(f"- Programme: {cert.patient.programme.name if cert.patient.programme else '—'}")
                    st.markdown(f"- Department: {cert.patient.department.name if cert.patient.department else '—'}")
                    st.markdown(f"- Doctor: Dr. {cert.doctor.full_name}")
                    st.markdown(f"- Certificate Date: {cert.issued_date}")
                    st.markdown(f"- Rest Period: {cert.rest_from} to {cert.rest_to} ({cert.rest_days} days)")
                    st.markdown(f"- Status: {cert.status}")
                else:
                    st.error("Certificate not found or invalid.")
    finally:
        db.close()


def render_certificates():
    require_hod()
    render_header()
    db = get_session()
    try:
        hod = _get_hod(db, st.session_state["user_id"])
        section_title("📄 Medical Certificate Notifications")
        st.caption("You have restricted access to relevant student medical certificates only.")

        dept_id = hod.department_id
        certs = get_certificates_for_hod(db, dept_id)

        # Filters
        col1, col2, col3 = st.columns(3)
        search = col1.text_input("Search by student name / enrollment")
        status_filter = col2.selectbox("Status", ["All", "Issued", "Emailed", "Partially_Emailed", "Failed"])
        date_filter = col3.text_input("Filter by date (YYYY-MM-DD)")

        filtered = certs
        if search:
            filtered = [c for c in filtered
                        if search.lower() in c.patient.full_name.lower()
                        or search.lower() in c.patient.enrollment_no.lower()]
        if status_filter != "All":
            filtered = [c for c in filtered if c.status == status_filter]
        if date_filter:
            filtered = [c for c in filtered if c.issued_date == date_filter]

        if not filtered:
            empty_state("No medical certificate notifications found.")
            return
        for cert in filtered:
            with st.container(border=True):
                colA, colB, colC, colD, colE = st.columns([2, 2, 2, 1, 1])
                colA.markdown(f"**{cert.patient.full_name}**")
                colA.caption(cert.patient.enrollment_no)
                colB.markdown(f"{(cert.patient.programme.name if cert.patient.programme else '—')}")
                colB.caption(f"{(cert.patient.department.name if cert.patient.department else '—')}")
                colC.markdown(f"{cert.rest_from} → {cert.rest_to} ({cert.rest_days} days)")
                colC.caption(f"Dr. {cert.doctor.full_name}")
                colD.markdown(status_badge(cert.status))
                if cert.pdf_path:
                    import os
                    if os.path.exists(cert.pdf_path):
                        with open(cert.pdf_path, "rb") as f:
                            colE.download_button("⬇", f.read(),
                                                 file_name=f"{cert.certificate_no}.pdf",
                                                 mime="application/pdf",
                                                 key=f"hod_dl_{cert.id}")
        if st.button("← Back to Dashboard"):
            st.session_state["current_page"] = "hod_dashboard"
            st.rerun()
    finally:
        db.close()
