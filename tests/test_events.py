"""Tests for event scanning: T-0/T-1, edge cases, dedup."""

from datetime import date
from unittest.mock import patch

import pytest

from src.events import scan_events

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_C_A = {
    "name": "Nguyen Van A",
    "gender": "Nam",
    "birth_date": "15/06/1990",
    "age_group": "",
    "note": "",
    "active": "TRUE",
}
_C_B = {
    "name": "Tran Thi B",
    "gender": "Nữ",
    "birth_date": "01/01/1985",  # birthday on Jan 1
    "age_group": "",
    "note": "",
    "active": "TRUE",
}

_CUSTOMERS = [_C_A, _C_B]


def _scan(today: date, tomorrow: date, customers=None, sent_log=None):
    if customers is None:
        customers = _CUSTOMERS
    if sent_log is None:
        sent_log = set()
    with patch("src.events.today_vn", return_value=today), patch(
        "src.events.tomorrow_vn", return_value=tomorrow
    ):
        return scan_events(customers, sent_log)


# ---------------------------------------------------------------------------
# Birthday
# ---------------------------------------------------------------------------

def test_birthday_t0():
    events = _scan(date(2025, 6, 15), date(2025, 6, 16))
    matched = [e for e in events if e.customer["name"] == "Nguyen Van A"
               and e.event_type == "birthday" and e.notify_type == "T-0"]
    assert len(matched) == 1
    assert matched[0].year == 2025


def test_birthday_t1():
    events = _scan(date(2025, 6, 14), date(2025, 6, 15))
    matched = [e for e in events if e.customer["name"] == "Nguyen Van A"
               and e.event_type == "birthday" and e.notify_type == "T-1"]
    assert len(matched) == 1
    assert matched[0].year == 2025


def test_birthday_not_today():
    events = _scan(date(2025, 6, 20), date(2025, 6, 21))
    bday = [e for e in events if e.event_type == "birthday"]
    assert len(bday) == 0


def test_birthday_edge_jan1():
    """T-1 is Dec 31 2024; birthday is Jan 1 2025 → year should be 2025."""
    events = _scan(date(2024, 12, 31), date(2025, 1, 1))
    matched = [e for e in events if e.customer["name"] == "Tran Thi B"
               and e.event_type == "birthday" and e.notify_type == "T-1"]
    assert len(matched) == 1
    assert matched[0].year == 2025


def test_birthday_dedup():
    sent_log = {("Nguyen Van A", "birthday", "T-0", "2025")}
    events = _scan(date(2025, 6, 15), date(2025, 6, 16), sent_log=sent_log)
    matched = [e for e in events if e.customer["name"] == "Nguyen Van A"
               and e.event_type == "birthday" and e.notify_type == "T-0"]
    assert len(matched) == 0


# ---------------------------------------------------------------------------
# Tết Tây
# ---------------------------------------------------------------------------

def test_tet_tay_t0():
    events = _scan(date(2025, 1, 1), date(2025, 1, 2))
    tet = [e for e in events if e.event_type == "tet_duong" and e.notify_type == "T-0"]
    assert len(tet) == 2  # both customers
    assert all(e.year == 2025 for e in tet)


def test_tet_tay_t1():
    events = _scan(date(2024, 12, 31), date(2025, 1, 1))
    tet = [e for e in events if e.event_type == "tet_duong" and e.notify_type == "T-1"]
    assert len(tet) == 2
    assert all(e.year == 2025 for e in tet)


def test_tet_tay_dedup():
    sent_log = {
        ("Nguyen Van A", "tet_duong", "T-0", "2025"),
        ("Tran Thi B", "tet_duong", "T-0", "2025"),
    }
    events = _scan(date(2025, 1, 1), date(2025, 1, 2), sent_log=sent_log)
    tet = [e for e in events if e.event_type == "tet_duong" and e.notify_type == "T-0"]
    assert len(tet) == 0


# ---------------------------------------------------------------------------
# Tết Âm
# ---------------------------------------------------------------------------

def test_tet_am_t0_2025():
    """Tết Ất Tỵ: Jan 29 2025."""
    events = _scan(date(2025, 1, 29), date(2025, 1, 30))
    tet = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-0"]
    assert len(tet) == 2
    assert all(e.year == 2025 for e in tet)


def test_tet_am_t1_2025():
    """T-1 for Tết Ất Tỵ: Jan 28 2025."""
    events = _scan(date(2025, 1, 28), date(2025, 1, 29))
    tet = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-1"]
    assert len(tet) == 2
    assert all(e.year == 2025 for e in tet)


def test_tet_am_not_today():
    events = _scan(date(2025, 2, 5), date(2025, 2, 6))
    tet = [e for e in events if e.event_type == "tet_am"]
    assert len(tet) == 0


def test_tet_am_dedup():
    sent_log = {
        ("Nguyen Van A", "tet_am", "T-0", "2025"),
        ("Tran Thi B", "tet_am", "T-0", "2025"),
    }
    events = _scan(date(2025, 1, 29), date(2025, 1, 30), sent_log=sent_log)
    tet = [e for e in events if e.event_type == "tet_am" and e.notify_type == "T-0"]
    assert len(tet) == 0
