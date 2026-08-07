"""
Session state management helpers.

Centralizes access to Streamlit session_state keys so that the rest of the
application uses a consistent, well-defined session contract.
"""
import streamlit as st


def init_session():
    """Initialize default session state keys."""
    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "role": None,
        "display_name": None,
        "current_page": "login",
        "last_activity": None,
        "selected_doctor_id": None,
        "selected_appointment_id": None,
        "selected_certificate_id": None,
        "form_data": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set(key: str, value):
    st.session_state[key] = value


def get(key: str, default=None):
    return st.session_state.get(key, default)


def navigate(page: str):
    st.session_state["current_page"] = page


def current_page() -> str:
    return st.session_state.get("current_page", "login")
