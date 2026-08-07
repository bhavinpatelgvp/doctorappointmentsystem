"""
Input validation helpers.

All validation is strict and provides user-friendly error messages.
No sensitive information is revealed in messages.
"""
import re
from datetime import datetime


def is_required(value) -> bool:
    return value is not None and str(value).strip() != ""


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email.strip()) is not None


def is_valid_mobile(mobile: str) -> bool:
    if not mobile:
        return False
    # Accept 10-15 digit numbers with optional leading +
    pattern = r"^\+?[0-9]{10,15}$"
    return re.match(pattern, mobile.strip()) is not None


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def is_valid_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def is_valid_username(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.]{3,50}$", username or ""))


def date_range_valid(start: str, end: str) -> bool:
    """Return True if start <= end and both are valid dates."""
    if not (is_valid_date(start) and is_valid_date(end)):
        return False
    return start <= end


def compute_days_between(start: str, end: str) -> int:
    if not date_range_valid(start, end):
        return 0
    d1 = datetime.strptime(start, "%Y-%m-%d")
    d2 = datetime.strptime(end, "%Y-%m-%d")
    return (d2 - d1).days + 1


def validate_rest_dates(rest_from: str, rest_to: str) -> tuple[bool, str]:
    if not is_valid_date(rest_from) or not is_valid_date(rest_to):
        return False, "Please provide valid rest dates."
    if rest_to < rest_from:
        return False, "Rest end date cannot be before the rest start date."
    return True, ""
