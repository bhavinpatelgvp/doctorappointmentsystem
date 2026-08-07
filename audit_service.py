"""
Audit logging service.

Records important activities (login, logout, appointment creation,
consultation, certificate creation, etc.) into the audit_logs table.
No sensitive information is logged.
"""
import logging
from datetime import datetime

import streamlit as st

from database import get_session
from models import AuditLog
from utils import generate_id

logger = logging.getLogger(__name__)


def log_action(
    action: str,
    module: str = "",
    record_id: int | None = None,
    details: str = "",
    status: str = "OK",
    user_id: int | None = None,
    role: str | None = None,
) -> AuditLog:
    """Insert an audit log entry. Never raises to the caller."""
    db = get_session()
    try:
        entry = AuditLog(
            log_id=generate_id("LOG"),
            user_id=user_id if user_id is not None else st.session_state.get("user_id"),
            role=role if role is not None else st.session_state.get("role"),
            action=action,
            module=module,
            record_id=record_id,
            details=details[:500],
            timestamp=datetime.utcnow(),
            status=status,
        )
        db.add(entry)
        db.commit()
        return entry
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("Audit logging failed: %s", exc)
        return None
    finally:
        db.close()
