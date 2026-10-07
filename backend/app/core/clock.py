"""Shared calendar clock for user-facing daily features."""

from datetime import date, datetime, timedelta, timezone


INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


def india_today() -> date:
    """Return today's date in the application's user-facing timezone."""
    return datetime.now(INDIA_TIMEZONE).date()
