"""
Reusable UI helpers and generic utilities.
"""
import uuid
from datetime import datetime

import streamlit as st

from config import APP_SUBTITLE, APP_TAGLINE


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------
def generate_id(prefix: str) -> str:
    """Generate a short human-friendly unique ID with a prefix."""
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def generate_number(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


# ---------------------------------------------------------------------------
# Date/time helpers
# ---------------------------------------------------------------------------
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

WEEKDAY_MAP = {name: idx for idx, name in enumerate(WEEKDAYS)}


def weekday_name(index: int) -> str:
    return WEEKDAYS[((index % 7) + 7) % 7]


def weekday_index(name: str) -> int:
    return WEEKDAY_MAP[name]


def format_time_12h(time_str: str) -> str:
    """Convert 'HH:MM' (24h) to 'h:mm AM/PM'."""
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p")
    except (ValueError, TypeError):
        return time_str


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_hm() -> str:
    return datetime.now().strftime("%H:%M")


# ---------------------------------------------------------------------------
# Status badge styling
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    "Requested": "blue",
    "Confirmed": "green",
    "Completed": "green",
    "Cancelled": "red",
    "Rescheduled": "orange",
    "No-show": "orange",
    "Issued": "green",
    "Emailed": "green",
    "Partially_Emailed": "orange",
    "Pending": "yellow",
    "Sent": "green",
    "Failed": "red",
    "OK": "green",
}


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "gray")
    return f":{color}-background[{status}]"


# ---------------------------------------------------------------------------
# Streamlit UI helpers
# ---------------------------------------------------------------------------
def render_header():
    st.markdown(
        f"""
        <div class="gv-header">
          <div class="gv-header-title">
            <div class="gv-org">Gujarat Vidyapith</div>
            <div class="gv-subtitle">{APP_SUBTITLE}</div>
          </div>
        </div>
        <div class="gv-tagline">⋆ {APP_TAGLINE} ⋆</div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
        <div class="gv-footer">
          © Gujarat Vidyapith · Doctor Appointment & Medical Management System ·
          Confidential · For authorized users only
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_card(label, value, icon="📊", color="gv-brown"):
    st.markdown(
        f"""
        <div class="gv-card {color}">
          <div class="gv-card-icon">{icon}</div>
          <div class="gv-card-value">{value}</div>
          <div class="gv-card-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str):
    st.markdown(f'<div class="gv-section-title">{title}</div>', unsafe_allow_html=True)


def empty_state(message: str, icon: str = "🗂️"):
    st.markdown(
        f'<div class="gv-empty">{icon} {message}</div>',
        unsafe_allow_html=True,
    )

