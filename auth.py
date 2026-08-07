"""
Authentication module: registration, login, logout and role helpers.
"""
import streamlit as st

from audit_service import log_action
from database import get_session
from models import Doctor, Hod, Student, User
from security import do_login, do_logout, is_locked, register_failed_attempt, hash_password, verify_password, reset_failed_attempts
from validators import is_valid_email, is_valid_username


def authenticate(username: str, password: str) -> bool:
    """Authenticate a user by username and password.

    Enforces failed-login protection and lockout. Returns True on success.
    """
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username.strip()).first()
        if user is None:
            log_action("FAILED_LOGIN", "auth", details=f"Unknown username: {username}")
            return False

        if is_locked(user):
            log_action("LOGIN_BLOCKED", "auth", user_id=user.id, role=user.role)
            st.session_state["login_error"] = (
                "Account temporarily locked due to multiple failed attempts. "
                "Please try again later."
            )
            return False

        if not verify_password(password, user.password_hash):
            locked = register_failed_attempt(db, user)
            log_action("FAILED_LOGIN", "auth", user_id=user.id, role=user.role)
            if locked:
                st.session_state["login_error"] = (
                    "Too many failed attempts. Account locked for a few minutes."
                )
            else:
                st.session_state["login_error"] = "Invalid username or password."
            return False

        if not user.is_active:
            log_action("LOGIN_DISABLED", "auth", user_id=user.id, role=user.role)
            st.session_state["login_error"] = "Your account is disabled. Contact administrator."
            return False

        reset_failed_attempts(db, user)
        display_name = _resolve_display_name(user, db)
        do_login(user.id, user.username, user.role, display_name)
        log_action("LOGIN", "auth", user_id=user.id, role=user.role,
                   details=f"Login: {user.username}")
        return True
    finally:
        db.close()


def _resolve_display_name(user: User, db) -> str:
    if user.role == "student":
        s = db.query(Student).filter(Student.user_id == user.id).first()
        return s.full_name if s else user.username
    if user.role == "doctor":
        d = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        return f"Dr. {d.full_name}" if d else user.username
    if user.role == "hod":
        h = db.query(Hod).filter(Hod.user_id == user.id).first()
        return h.full_name if h else user.username
    return "Administrator"


def register_student(username, email, password, confirm_password, full_name,
                     enrollment_no, programme_id, semester, department_id,
                     mobile, gender=None, dob=None):
    """Register a new student account with validation.

    Returns (success: bool, message: str).
    """
    if not is_valid_username(username):
        return False, "Username must be 3-50 characters (letters, numbers, _ or .)."
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirm_password:
        return False, "Passwords do not match."
    if not full_name.strip():
        return False, "Full name is required."
    if not enrollment_no.strip():
        return False, "Enrollment number is required."

    db = get_session()
    try:
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            return False, "Username already exists."
        existing_email = db.query(User).filter(User.email == email.lower()).first()
        if existing_email:
            return False, "Email is already registered."
        existing_enr = db.query(Student).filter(Student.enrollment_no == enrollment_no).first()
        if existing_enr:
            return False, "Enrollment number already registered."

        user = User(
            username=username,
            email=email.lower(),
            password_hash=hash_password(password),
            role="student",
        )
        db.add(user)
        db.flush()

        student = Student(
            user_id=user.id,
            enrollment_no=enrollment_no,
            full_name=full_name.strip(),
            gender=gender,
            date_of_birth=dob,
            programme_id=programme_id,
            semester=semester,
            department_id=department_id,
            mobile=mobile,
        )
        db.add(student)
        db.commit()
        log_action("STUDENT_REGISTER", "auth", user_id=user.id, role="student",
                   details=f"Registered student: {username}")
        return True, "Registration successful. You may now log in."
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return False, "Unable to register. Please try again or contact administrator."
    finally:
        db.close()


def logout():
    log_action("LOGOUT", "auth", details="User logout")
    do_logout()
