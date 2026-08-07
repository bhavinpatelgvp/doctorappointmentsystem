"""
Consultation service: conduct consultations, record medical history,
rest recommendation and preserve the consultation lifecycle.
"""
from audit_service import log_action
from database import get_session
from models import Appointment, Consultation, MedicalCertificate, Prescription
from utils import generate_number, today_str
from validators import compute_days_between, is_valid_date, validate_rest_dates


def get_consultation(db, consultation_id):
    return db.query(Consultation).filter(Consultation.id == consultation_id).first()


def get_consultations_for_doctor(db, doctor_id):
    return (db.query(Consultation)
            .filter(Consultation.doctor_id == doctor_id)
            .order_by(Consultation.consult_date.desc())
            .all())


def create_consultation(db, doctor_id, patient_id, appointment_id, symptoms,
                        observations, diagnosis, treatment, doctor_advice,
                        followup_date, rest_recommended, rest_from, rest_to):
    """Create a consultation record. Returns (success, message, consultation)."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None or appointment.doctor_id != doctor_id:
        return False, "Appointment not found.", None

    if is_valid_date(followup_date) and followup_date and followup_date < today_str():
        return False, "Follow-up date cannot be in the past.", None

    if rest_recommended:
        ok, msg = validate_rest_dates(rest_from or "", rest_to or "")
        if not ok:
            return False, msg, None

    consultation = Consultation(
        consult_no=generate_number("CON"),
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        consult_date=today_str(),
        symptoms=symptoms,
        observations=observations,
        diagnosis=diagnosis,
        treatment=treatment,
        doctor_advice=doctor_advice,
        followup_date=followup_date or None,
        rest_recommended=bool(rest_recommended),
        rest_from=rest_from if rest_recommended else None,
        rest_to=rest_to if rest_recommended else None,
    )
    db.add(consultation)
    db.flush()

    appointment.status = "Completed"
    db.commit()
    db.refresh(consultation)

    log_action("CONSULTATION_CREATED", "consultation", record_id=consultation.id,
               details=f"Consultation for patient {patient_id}")
    return True, "Consultation saved successfully.", consultation


def save_prescription(db, consultation_id, items):
    """Replace prescriptions for a consultation. items = list of dicts."""
    existing = db.query(Prescription).filter(
        Prescription.consultation_id == consultation_id).all()
    for p in existing:
        db.delete(p)
    for item in items:
        if item.get("medicine_name"):
            db.add(Prescription(
                consultation_id=consultation_id,
                medicine_name=item["medicine_name"],
                dosage=item.get("dosage"),
                frequency=item.get("frequency"),
                duration=item.get("duration"),
                instructions=item.get("instructions"),
            ))
    db.commit()
    log_action("PRESCRIPTION_SAVED", "consultation", record_id=consultation_id)
    return True, "Prescription saved."


def get_prescriptions(db, consultation_id):
    return (db.query(Prescription)
            .filter(Prescription.consultation_id == consultation_id)
            .all())


def get_consultation_with_certificate(db, consultation_id):
    return db.query(MedicalCertificate).filter(
        MedicalCertificate.consultation_id == consultation_id).first()
