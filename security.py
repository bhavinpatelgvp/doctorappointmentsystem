"""
Security helpers: password hashing, role-based access control,
session checks and authorization enforcement.

The rule followed throughout the application is:
    Authentication + Authorization + Ownership + Audit
"""
import hmac
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from config import MAX_LOGIN_ATTEMPTS, LOCKOUT_MINUTES, SESSION_TIMEOUT_MINUTES


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Login lockout helpers
# ---------------------------------------------------------------------------
def is_locked(user) -> bool:
    if user.locked_until and user.locked_until > datetime.utcnow():
        return True
    return False


def register_failed_attempt(db, user) -> bool:
    """Increment failed attempts; lock account if threshold reached.

    Returns True if the account was locked.
    """
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        user.failed_login_attempts = 0
        db.commit()
        return True
    db.commit()
    return False


def reset_failed_attempts(db, user):
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def get_current_user_id() -> int | None:
    return st.session_state.get("user_id")


def get_current_role() -> str | None:
    return st.session_state.get("role")


def require_login():
    """Redirect to login if the user is not authenticated."""
    if not is_authenticated():
        st.session_state["current_page"] = "login"
        st.warning("Please log in to continue.")
        st.stop()


def require_role(*allowed_roles):
    """Stop the app if the current user's role is not allowed."""
    require_login()
    role = get_current_role()
    if role not in allowed_roles:
        st.error("You are not authorized to access this page.")
        st.stop()


def check_session_timeout():
    """Expire the session if it has been idle too long."""
    if not is_authenticated():
        return
    last_active = st.session_state.get("last_activity")
    if last_active:
        try:
            last = datetime.fromisoformat(last_active)
            if datetime.now() - last > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                do_logout("Session expired due to inactivity.")
                st.warning("Your session has expired. Please log in again.")
                st.stop()
        except (ValueError, TypeError):
            pass
    st.session_state["last_activity"] = datetime.now().isoformat()


def do_login(user_id, username, role, display_name=""):
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username
    st.session_state["role"] = role
    st.session_state["display_name"] = display_name
    st.session_state["last_activity"] = datetime.now().isoformat()


def do_logout(reason="User logged out"):
    st.session_state.clear()
    st.session_state["current_page"] = "login"


# ---------------------------------------------------------------------------
# Constant-time comparison helper
# ---------------------------------------------------------------------------
def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
