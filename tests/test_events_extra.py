"""Additional event-scanning tests: malformed birth_date, active filter,
Tết Âm Dec boundary, multiple events same customer, no events day."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.events import scan_events, Event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan(today: date, customers, sent_log=None):
    tomorrow = today + timedelta(days=1)
    if sent_log is None:
        sent_log = set()
    with patch("src.events.today_vn", return_value=today), \
         patch("src.events.tomorrow_vn", return_value=tomorrow):
        return scan_events(customers, sent_log)


def _make(name: str, birth_date: str, active="TRUE", gender="Nam") -> dict:
    return {
        "name": name,
        "gender": gender,
        "birth_date": birth_date,
        "age_group": "",
        "note": "",
        "active": active,
    }


# ---------------------------------------------------------------------------
# Malformed / empty birth_date: must not crash, must not produce birthday event
# ---------------------------------------------------------------------------

def test_empty_birth_date_no_birthday():
    c = _make("Alice", "")
    events = _scan(date(2025, 6, 15), [c])
    assert all(e.event_type != "birthday" for e in events)


def test_malformed_birth_date_no_crash():
    """'not-a-date' must not raise an exception."""
    c = _make("Bob", "not-a-date")
    events = _scan(date(2025, 6, 15), [c])  # should not raise
    assert all(e.event_type != "birthday" for e in events)


def test_partial_birth_date_no_crash():
    """'15/06' (missing year) must not crash."""
    c = _make("Carol", "15/06")
    events = _scan(date(2025, 6, 15), [c])
    assert all(e.event_type != "birthday" for e in events)


def test_month_only_birth_date_no_crash():
    c = _make("Dave", "06")
    events = _scan(date(2025, 6, 15), [c])
    assert all(e.event_type != "birthday" for e in events)


def test_invalid_day_in_birth_date_no_crash():
    """32/13/2000 is an out-of-range date; must not crash."""
    c = _make("Eve", "32/13/2000")
    events = _scan(date(2025, 6, 15), [c])
    assert all(e.event_type != "birthday" for e in events)


# ---------------------------------------------------------------------------
# scan_events receives a pre-filtered list: does NOT re-check active flag
# (load_customers filters; scan_events trusts the list it receives)
# ---------------------------------------------------------------------------

def test_inactive_customer_in_list_still_processed():
    """scan_events does not re-filter by active; that is load_customers' job.
    If an inactive customer is mistakenly passed, the event IS produced.
    This documents the contract: filtering must happen before scan_events."""
    c = _make("Frank", "15/06/1990", active="FALSE")
    events = _scan(date(2025, 6, 15), [c])
    # scan_events has no active-check, so birthday IS triggered
    birthday_events = [e for e in events if e.event_type == "birthday"]
    assert len(birthday_events) == 1


# ---------------------------------------------------------------------------
# Customer with birthday on Tết Tây (Jan 1): gets both events in same run
# ---------------------------------------------------------------------------

def test_birthday_and_tet_tay_same_day():
    """Customer born Jan 1: both birthday T-0 and tet_duong T-0 on Jan 1."""
    c = _make("G", "01/01/1990")
    events = _scan(date(2025, 1, 1), [c])
    types = {e.event_type for e in events if e.customer["name"] == "G"}
    assert "birthday" in types
    assert "tet_duong" in types


# ---------------------------------------------------------------------------
# Tết Âm Dec→Jan boundary: today = Dec 31, next year's Tết is Jan 29 → T-1
# is Jan 28, not today, so no tet_am event; but if Tết is on Jan 1, T-1
# would be Dec 31. Test that the year-+1 branch is exercised.
# ---------------------------------------------------------------------------

def test_tet_am_dec31_boundary_no_false_positive():
    """Dec 31 is not typically T-1 for Tết Âm (which is late Jan/Feb).
    Verify no spurious tet_am event is created on an ordinary Dec 31."""
    c = _make("H", "")
    # Use a year where Tết is NOT on Jan 1 so T-1 is not Dec 31
    # Tết 2026 = Feb 17; T-1 = Feb 16 → Dec 31 2025 should have no tet_am
    events = _scan(date(2025, 12, 31), [c])
    tet_am = [e for e in events if e.event_type == "tet_am"]
    assert len(tet_am) == 0


def test_tet_am_year_next_year_candidate_fires():
    """When today matches next-year's Tết T-0 via the +1 branch, it fires.
    Tết 2026 = Feb 17 2026; test with today=Feb 17 2026."""
    c = _make("I", "")
    events = _scan(date(2026, 2, 17), [c])
    tet_am = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-0"]
    assert len(tet_am) == 1
    assert tet_am[0].year == 2026


def test_tet_am_t1_next_year_fires():
    """T-1 for Tết 2026 (Feb 17) is Feb 16 2026."""
    c = _make("J", "")
    events = _scan(date(2026, 2, 16), [c])
    tet_am = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-1"]
    assert len(tet_am) == 1
    assert tet_am[0].year == 2026


# ---------------------------------------------------------------------------
# Empty customer list
# ---------------------------------------------------------------------------

def test_empty_customer_list():
    events = _scan(date(2025, 6, 15), [])
    assert events == []


# ---------------------------------------------------------------------------
# Sent log key format: year must be string in the tuple
# ---------------------------------------------------------------------------

def test_dedup_key_uses_string_year():
    """sent_log stores year as str; confirm integer year in key would NOT dedup."""
    c = _make("K", "15/06/1990")
    # This key uses integer 2025 — should NOT match (key is str "2025")
    sent_log_int_year = {("K", "birthday", "T-0", 2025)}  # int year
    events = _scan(date(2025, 6, 15), [c], sent_log=sent_log_int_year)
    matched = [e for e in events if e.event_type == "birthday" and e.notify_type == "T-0"]
    # Integer year key does NOT match the str "2025" check → event still fires
    assert len(matched) == 1


def test_dedup_key_uses_string_year_correctly():
    """Correct string-year key deduplicates."""
    c = _make("K", "15/06/1990")
    sent_log_str_year = {("K", "birthday", "T-0", "2025")}
    events = _scan(date(2025, 6, 15), [c], sent_log=sent_log_str_year)
    matched = [e for e in events if e.event_type == "birthday" and e.notify_type == "T-0"]
    assert len(matched) == 0


# ---------------------------------------------------------------------------
# Multiple customers: only matching birthday fires, others silent
# ---------------------------------------------------------------------------

def test_only_matching_birthday_fires():
    """Match has birthday today (T-0). NoMatch has birthday tomorrow (T-1).
    Neither should appear in the other's slot."""
    customers = [
        _make("Match", "15/06/1990"),
        _make("NoMatch", "17/06/1990"),  # birthday in 2 days — neither T-0 nor T-1
    ]
    events = _scan(date(2025, 6, 15), customers)
    bd = [e for e in events if e.event_type == "birthday"]
    names = {e.customer["name"] for e in bd}
    assert "Match" in names
    assert "NoMatch" not in names


# ---------------------------------------------------------------------------
# Event dataclass fields are correct
# ---------------------------------------------------------------------------

def test_event_fields_birthday():
    c = _make("L", "15/06/1990")
    events = _scan(date(2025, 6, 15), [c])
    bd = [e for e in events if e.event_type == "birthday" and e.notify_type == "T-0"]
    assert len(bd) == 1
    e = bd[0]
    assert e.customer is c
    assert e.event_type == "birthday"
    assert e.notify_type == "T-0"
    assert e.year == 2025


def test_event_fields_tet_am():
    c = _make("M", "")
    # Tết 2025 = Jan 29
    events = _scan(date(2025, 1, 29), [c])
    tet = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-0"]
    assert len(tet) == 1
    e = tet[0]
    assert e.year == 2025
    assert e.event_type == "tet_am"
