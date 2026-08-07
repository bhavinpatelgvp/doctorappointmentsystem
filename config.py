"""
Configuration module for the Gujarat Vidyapith Doctor Appointment
& Student Medical Management System.

Loads environment variables from a .env file and provides application-level
configuration constants. No secrets are hard-coded here.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CERTIFICATE_DIR = BASE_DIR / "certificates"
CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "Gujarat Vidyapith"
APP_SUBTITLE = "Doctor Appointment & Medical Management System"
APP_TAGLINE = "Digital Healthcare Support for Student Well-being"
APP_ICON = "🏥"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Use SQLite by default. Override with DATABASE_URL for MySQL/Postgres.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'gv_medical.db'}",
)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# In production always set a strong SECRET_KEY in the environment.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-change-me")
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))

# ---------------------------------------------------------------------------
# SMTP / Email
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@gujaratvidyapith.example")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", APP_NAME)

# Whether email sending is enabled. If not configured, notifications are
# recorded as FAILED and can be retried later.
EMAIL_ENABLED = bool(SMTP_HOST and SMTP_USER)

# ---------------------------------------------------------------------------
# Institution contact / footer
# ---------------------------------------------------------------------------
INSTITUTION_ADDRESS = os.getenv(
    "INSTITUTION_ADDRESS",
    "Ashram Road, Ahmedabad, Gujarat, India",
)
