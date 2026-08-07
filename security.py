"""
Security helpers: password hashing, role-based access control,
session checks and authorization enforcement.

The rule followed throughout the application is:
    Authentication + Authorization + Ownership + Audit
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from config import MAX_LOGIN_ATTEMPTS, LOCKOUT_MINUTES, SECRET_KEY, SESSION_TIMEOUT_MINUTES

# Duration (in hours) that a persistent login token remains valid.
_PERSISTENT_SESSION_HOURS = 24 * 7  # one week


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
    # Persist login so it survives page refresh.
    store_persistent_session(user_id, username, role)


def do_logout(reason="User logged out"):
    clear_persistent_session()
    st.session_state.clear()
    st.session_state["current_page"] = "login"


# ---------------------------------------------------------------------------
# Constant-time comparison helper
# ---------------------------------------------------------------------------
def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# ---------------------------------------------------------------------------
# Persistent session (survives page refresh)
# ---------------------------------------------------------------------------
# Streamlit's session_state is reset on a full browser refresh because it is
# tied to the websocket connection. To keep users logged in across refreshes,
# we persist a signed token in the URL query parameter "gv_token". The token is
# signed with SECRET_KEY, so it cannot be forged or tampered with.
#
# NOTE: This is a convenience persistence layer. Authorization is still always
# enforced server-side against the database on every protected operation.

_QUERY_TOKEN_KEY = "gv_token"


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(user_id: int, username: str, role: str) -> str:
    """Create a signed, JSON-encoded, base64 token for persistent login."""
    expiry = (datetime.utcnow() + timedelta(hours=_PERSISTENT_SESSION_HOURS)).isoformat()
    payload = json.dumps({
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expiry,
    })
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    signature = _sign(encoded)
    return f"{encoded}.{signature}"


def decode_session_token(token: str) -> dict | None:
    """Validate and decode a signed session token. Returns None if invalid/expired."""
    try:
        encoded, signature = token.rsplit(".", 1)
        if not secure_compare(_sign(encoded), signature):
            return None
        payload = json.loads(
            base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
        )
        exp = datetime.fromisoformat(payload["exp"])
        if exp < datetime.utcnow():
            return None
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def store_persistent_session(user_id: int, username: str, role: str):
    """Persist the logged-in session token into the URL query parameter."""
    token = create_session_token(user_id, username, role)
    st.query_params[_QUERY_TOKEN_KEY] = token


def clear_persistent_session():
    """Remove the persistent session token from the URL."""
    try:
        params = {k: v for k, v in st.query_params.items() if k != _QUERY_TOKEN_KEY}
        st.query_params.clear()
        for k, v in params.items():
            st.query_params[k] = v
    except Exception:  # noqa: BLE001
        pass


def get_persistent_session() -> dict | None:
    """Return the decoded persistent session if a valid token is present."""
    token = st.query_params.get(_QUERY_TOKEN_KEY)
    if not token:
        return None
    return decode_session_token(token)


def restore_session_from_token():
    """Restore the in-memory session from a valid persistent token.

    Used on page load when session_state is empty but a valid login token
    survives in the URL from a previous (pre-refresh) session.
    Returns True if a session was restored.
    """
    if is_authenticated():
        return True
    payload = get_persistent_session()
    if not payload:
        return False
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = payload["user_id"]
    st.session_state["username"] = payload["username"]
    st.session_state["role"] = payload["role"]
    st.session_state["display_name"] = payload["username"]
    st.session_state["last_activity"] = datetime.now().isoformat()
    return True
