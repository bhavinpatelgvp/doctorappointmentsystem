# Gujarat Vidyapith · Doctor Appointment & Student Medical Management System

A secure, role-based, database-driven **Doctor Appointment & Student Medical Management System** built with **Python + Streamlit**.

It digitizes the appointment booking, consultation, medical-history, and medical-certificate workflow for Gujarat Vidyapith students — including an automatic **Student Medical Leave Workflow** that emails medical certificates to the student and the concerned **HOD**.

---

## ✨ Key Features

- **Role-Based Access Control (RBAC)** — Student, Doctor, HOD, Administrator dashboards.
- **Doctor Search & Filtering** — by name, specialization, availability, date, consultation type.
- **Atomic Appointment Booking** — prevents double-booking (same doctor + date + time), unavailable slots, and blocked dates.
- **Doctor Schedule Management** — working days, time slots, slot duration, capacity, break periods, blocked dates.
- **Consultation & Medical History** — symptoms, observations, diagnosis, treatment, prescription, follow-up, rest recommendation.
- **Medical Certificate PDF** — professional, traceable to a valid consultation, with rest period.
- **Student Medical Leave Workflow** — certificate emailed to **Student + HOD**, with tracked status and retry.
- **Email Notification System** — appointment confirmation, certificate issuance, HOD notification, failure logging with retry.
- **Audit Logging** — login, appointments, consultations, certificates, emails, admin changes.
- **Admin Analytics & Reports** — KPI cards, charts (bar/line), status stats, CSV/Excel export.
- **Gujarat Vidyapith-inspired UI** — cream/off-white + earthy brown theme.
- **Security** — password hashing (bcrypt), failed-login lockout, session timeout, role & ownership checks, no secrets in code.

---

## 🧩 Tech Stack

- Python 3.11+
- Streamlit
- SQLAlchemy ORM (SQLite by default; MySQL/Postgres supported)
- Pandas (analytics)
- ReportLab (PDF generation)
- bcrypt (password hashing)
- python-dotenv (env config)
- SMTP (email; configurable via `.env`)

---

## 📁 Project Structure

```
gv_doctor_appointment/
├── app.py                  # Entry point, routing, session
├── config.py               # Configuration / env vars
├── database.py             # SQLAlchemy engine/session
├── models.py               # ORM models (16 tables)
├── auth.py                 # Authentication & registration
├── session_manager.py      # Session state helpers
├── security.py             # Password hashing, RBAC, lockout
├── validators.py           # Input validation
├── utils.py                # UI helpers & badges
├── audit_service.py        # Audit logging
├── email_service.py        # SMTP email + notification records
├── pdf_service.py          # Medical certificate PDF
├── appointment_service.py  # Booking engine (atomic)
├── doctor_service.py       # Schedules, patients, stats
├── patient_service.py      # Student profiles & history
├── consultation_service.py # Consultations & prescriptions
├── certificate_service.py  # Certificate + email workflow
├── report_service.py       # Admin analytics & export
├── admin_ui.py             # Admin dashboard & management
├── doctor_ui.py            # Doctor dashboard
├── student_ui.py           # Student dashboard
├── hod_ui.py               # HOD dashboard
├── theme.py                # Gujarat Vidyapith theme/CSS
├── seed_data.py            # Demo/seed data
├── tests/                  # Test cases
├── requirements.txt
├── .env.example            # Environment template
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment (optional)
```bash
cp .env.example .env
# Edit .env and add SMTP credentials to enable email.
# Without SMTP, emails are recorded as FAILED and can be retried — the app stays fully functional.
```

### 3. Initialize the database & seed demo data
```bash
python seed_data.py
```
This creates `gv_medical.db` and populates demo records.

### 4. Run the application
```bash
streamlit run app.py
```

Open the URL shown in the terminal (default `http://localhost:8501`).

---

## 🔑 Demo Login Credentials

| Role    | Username   | Password    |
|---------|------------|-------------|
| Admin   | `admin`    | `admin123`  |
| Doctor  | `dr.shah`  | `doctor123` |
| HOD     | `hod.cs`   | `hod123`    |
| Student | `student1` | `student123`|

> These are clearly-marked **demo records** — do not use in production.

---

## 📧 Email Configuration

The email system uses **SMTP** credentials from `.env`. Example:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM=your-email@gmail.com
```

> For Gmail, use an **App Password** (enable 2-Step Verification first). Never commit real credentials.

When issuing a medical certificate, the system emails:
1. The **student** (certificate PDF attached).
2. The **concerned HOD** (certificate forwarded for records).

If delivery fails, the certificate is preserved, notifications are logged as **FAILED**, and the doctor can **retry** from the Certificates page.

---

## 🔐 Security Notes

- Passwords are hashed with **bcrypt** (never stored in plaintext).
- **Role-based access control** enforced in the UI *and* backend services.
- **Ownership checks** on all record operations (e.g., a student can only cancel their own appointments).
- **Failed-login lockout** after `MAX_LOGIN_ATTEMPTS` (default 5).
- **Session timeout** after `SESSION_TIMEOUT_MINUTES` (default 30).
- **Audit logging** of important activities.
- No passwords, SMTP credentials, or secrets in source code — all from `.env`.
- No raw SQL; parameterized ORM queries throughout.

---

## 🧪 Testing

```bash
pip install pytest
pytest tests/ -v
```

The test suite covers authentication, authorization, booking, double-booking prevention, cancellation, schedule management, consultation, certificate generation, and validation.

---

## 📊 Reporting

Administrators can view:
- KPI cards (students, doctors, appointments, certificates)
- Appointment status distribution
- Monthly appointment trends
- Department-wise & doctor-wise statistics
- Export appointment reports as **CSV** or **Excel**

---

## 📄 License & Institutional Use

This is a demonstration implementation. For production deployment at Gujarat Vidyapith, integrate with the institution's official student, faculty, department, email, and attendance systems, and obtain an approved logo asset and authorization for any official seal/signature.

---

© Gujarat Vidyapith · Doctor Appointment & Medical Management System
