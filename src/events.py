"""Scan customers for birthday / Tết Tây / Tết Âm events on T-0 and T-1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from src.config import today_vn, tomorrow_vn
from src.lunar import tet_solar_date


@dataclass
class Event:
    customer: dict[str, Any]
    event_type: str   # birthday | tet_duong | tet_am
    notify_type: str  # T-0 | T-1
    year: int         # solar year of the event


def _parse_birth_date(s: str) -> date | None:
    """Parse dd/mm/yyyy → date. Returns None on failure."""
    try:
        parts = s.strip().split("/")
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None


def _tet_am_candidates(today: date) -> list[tuple[date, str, int]]:
    """Build list of (solar_date, notify_type, year) to match against today.

    Checks current and next solar year to cover the Dec→Jan boundary.
    """
    candidates: list[tuple[date, str, int]] = []
    for y in (today.year, today.year + 1):
        tet = tet_solar_date(y)
        candidates.append((tet, "T-0", y))
        candidates.append((tet - timedelta(days=1), "T-1", y))
    return candidates


def scan_events(
    customers: list[dict[str, Any]],
    sent_log: set[tuple[str, str, str, str]],
) -> list[Event]:
    """Return events that need notification today and are not already in sent_log."""
    today = today_vn()
    tomorrow = tomorrow_vn()
    events: list[Event] = []

    # Pre-compute Tết Âm candidates once (not per customer)
    tet_am_candidates = _tet_am_candidates(today)

    # Tết Tây: T-0 = 1 Jan, T-1 = 31 Dec (notifying for next year's Tết)
    tet_tay_checks: list[tuple[date, str, int]] = []
    if today == date(today.year, 1, 1):
        tet_tay_checks.append((today, "T-0", today.year))
    if today == date(today.year, 12, 31):
        tet_tay_checks.append((today, "T-1", today.year + 1))

    for customer in customers:
        name = str(customer.get("name", ""))

        # ── Sinh nhật ──────────────────────────────────────────────────────
        birth_str = str(customer.get("birth_date", "")).strip()
        if birth_str:
            bd = _parse_birth_date(birth_str)
            if bd is not None:
                for check_date, notify_type, event_year in [
                    (today, "T-0", today.year),
                    (tomorrow, "T-1", tomorrow.year),
                ]:
                    if bd.day == check_date.day and bd.month == check_date.month:
                        key = (name, "birthday", notify_type, str(event_year))
                        if key not in sent_log:
                            events.append(Event(customer, "birthday", notify_type, event_year))

        # ── Tết Tây ────────────────────────────────────────────────────────
        for _match_date, notify_type, year in tet_tay_checks:
            key = (name, "tet_duong", notify_type, str(year))
            if key not in sent_log:
                events.append(Event(customer, "tet_duong", notify_type, year))

        # ── Tết Âm ─────────────────────────────────────────────────────────
        for tet_date, notify_type, year in tet_am_candidates:
            if today == tet_date:
                key = (name, "tet_am", notify_type, str(year))
                if key not in sent_log:
                    events.append(Event(customer, "tet_am", notify_type, year))

    return events
