"""
Medical certificate service.

Implements the complete Student Medical Leave Workflow:
    Doctor recommends rest → Certificate generated → PDF created →
    Emailed to Student + HOD → Notifications recorded → Status tracked.

If email fails, the certificate is preserved and notifications are marked
FAILED with a retry option.
"""
from audit_service import log_action
from database import get_session
from email_service import send_email
from models import Hod, MedicalCertificate, Notification, Student
from pdf_service import create_medical_certificate_pdf
from utils import generate_number, today_str
from validators import compute_days_between, validate_rest_dates


def get_certificate(db, certificate_id):
    return db.query(MedicalCertificate).filter(MedicalCertificate.id == certificate_id).first()


def get_certificates_for_doctor(db, doctor_id):
    return (db.query(MedicalCertificate)
            .filter(MedicalCertificate.doctor_id == doctor_id)
            .order_by(MedicalCertificate.issued_date.desc())
            .all())


def get_certificates_for_hod(db, hod_department_id=None):
    """Return certificates for an HOD. Filters by the student's department."""
    q = (db.query(MedicalCertificate)
         .join(Student, Student.id == MedicalCertificate.patient_id))
    if hod_department_id:
        q = q.filter(Student.department_id == hod_department_id)
    return q.order_by(MedicalCertificate.issued_date.desc()).all()


def generate_certificate(db, doctor_id, patient_id, consultation_id, medical_advice,
                         rest_from, rest_to, remarks=""):
    """Generate a certificate + PDF + email to student and HOD.

    Returns (success, message, certificate).
    """
    ok, msg = validate_rest_dates(rest_from or "", rest_to or "")
    if not ok:
        return False, msg, None

    # Ensure a certificate is traceable to a valid consultation.
    from models import Consultation
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if consultation is None:
        return False, "Consultation not found.", None
    if consultation.doctor_id != doctor_id:
        return False, "You are not authorized to certify this consultation.", None

    student = db.query(Student).filter(Student.id == patient_id).first()
    if student is None:
        return False, "Student not found.", None

    rest_days = compute_days_between(rest_from, rest_to)
    if rest_days <= 0:
        return False, "Invalid rest period.", None

    certificate = MedicalCertificate(
        certificate_no=generate_number("MC"),
        patient_id=patient_id,
        doctor_id=doctor_id,
        consultation_id=consultation_id,
        issued_date=today_str(),
        medical_advice=medical_advice,
        rest_from=rest_from,
        rest_to=rest_to,
        rest_days=rest_days,
        remarks=remarks,
        status="Issued",
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)

    doctor = consultation.doctor
    pdf_path = create_medical_certificate_pdf(certificate, student, doctor, consultation)
    certificate.pdf_path = pdf_path
    db.commit()

    log_action("CERTIFICATE_CREATED", "certificate", record_id=certificate.id,
               details=f"Certificate {certificate.certificate_no}")

    # Email to student
    student_subject = f"Medical Certificate – {student.full_name} – {certificate.certificate_no}"
    student_body = (
        f"Dear {student.full_name},\n\n"
        f"Your medical certificate has been issued.\n\n"
        f"Certificate ID: {certificate.certificate_no}\n"
        f"Consultation Date: {consultation.consult_date}\n"
        f"Doctor: Dr. {doctor.full_name}\n"
        f"Rest Period: {rest_from} to {rest_to} ({rest_days} day(s))\n\n"
        f"Please find the certificate attached.\n\n"
        f"Regards,\nGujarat Vidyapith Health Centre"
    )
    s_ok, _, _ = send_email(
        student.full_name, "student", student.user.email, student_subject,
        student_body, attachment_path=pdf_path, certificate_id=certificate.id,
    )

    # Email to HOD
    hod_emails = []
    if student.department_id:
        hod_list = db.query(Hod).filter(Hod.department_id == student.department_id).all()
        hod_emails = [(h.full_name, h.user.email) for h in hod_list if h.user]
    if not hod_emails:
        hod_emails.append(("HOD", ""))
    hod_results = []
    for hod_name, hod_email in hod_emails:
        if not hod_email:
            # No HOD mapped; record as failed so it can be retried later.
            from datetime import datetime
            from models import Notification
            from utils import generate_id
            n = Notification(
                notification_no=generate_id("NOT"),
                certificate_id=certificate.id,
                recipient=hod_name,
                recipient_type="hod",
                email_address="",
                subject=f"Medical Certificate – {student.full_name} – {certificate.certificate_no}",
                status="Failed",
                failure_reason="No HOD email mapped for department.",
            )
            db.add(n)
            hod_results.append((False, "No HOD email mapped"))
            continue
        hod_subject = f"Medical Certificate – {student.full_name} – {certificate.certificate_no}"
        hod_body = (
            f"Dear {hod_name},\n\n"
            f"A medical certificate has been issued for your student.\n\n"
            f"Student Name: {student.full_name}\n"
            f"Enrollment No: {student.enrollment_no}\n"
            f"Programme: {(student.programme.name if student.programme else '—')}\n"
            f"Department: {(student.department.name if student.department else '—')}\n"
            f"Doctor: Dr. {doctor.full_name}\n"
            f"Certificate Date: {certificate.issued_date}\n"
            f"Recommended Rest: {rest_from} to {rest_to} ({rest_days} day(s))\n"
            f"Certificate ID: {certificate.certificate_no}\n\n"
            f"Please find the certificate attached for your records.\n\n"
            f"Regards,\nGujarat Vidyapith Health Centre"
        )
        h_ok, _, _ = send_email(
            hod_name, "hod", hod_email, hod_subject, hod_body,
            attachment_path=pdf_path, certificate_id=certificate.id,
        )
        hod_results.append((h_ok, hod_email))
    db.commit()

    # Update certificate status based on both emails
    student_ok = s_ok
    hods_ok = all(r[0] for r in hod_results) if hod_results else False
    if student_ok and hods_ok:
        certificate.status = "Emailed"
    elif student_ok or hods_ok:
        certificate.status = "Partially_Emailed"
    else:
        certificate.status = "Issued"
    db.commit()

    if certificate.status == "Emailed":
        message = "Medical certificate generated and emailed successfully to student and HOD."
    elif certificate.status == "Partially_Emailed":
        message = "Certificate generated, but some emails failed. Please retry."
    else:
        message = "Certificate generated successfully, but email delivery failed. Please retry."
    return True, message, certificate


def retry_failed_notifications(db, certificate):
    """Retry sending failed notifications for a certificate."""
    from models import Notification
    failed = db.query(Notification).filter(
        Notification.certificate_id == certificate.id,
        Notification.status == "Failed",
    ).all()
    results = []
    for notif in failed:
        if not notif.email_address:
            results.append((notif, False, "No recipient email address."))
            continue
        ok, msg, _ = send_email(
            notif.recipient, notif.recipient_type, notif.email_address,
            notif.subject or "Medical Certificate",
            "Please find the attached medical certificate.",
            attachment_path=certificate.pdf_path,
            certificate_id=certificate.id,
        )
        results.append((notif, ok, msg))
    # Re-evaluate status
    still_failed = db.query(Notification).filter(
        Notification.certificate_id == certificate.id,
        Notification.status == "Failed",
    ).count()
    if still_failed == 0:
        certificate.status = "Emailed"
    db.commit()
    log_action("CERTIFICATE_RETRY", "certificate", record_id=certificate.id)
    return results


def verify_certificate(db, certificate_no):
    """Public verification of a certificate by its ID (for attendance/leave office)."""
    return db.query(MedicalCertificate).filter(
        MedicalCertificate.certificate_no == certificate_no).first()
