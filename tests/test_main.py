"""Tests for main.py orchestrator — DRY_RUN does not write sent_log,
flow wires modules correctly (mocked sheets + telegram).

Because gspread and requests are not installed in this environment, all
I/O modules (src.sheets, src.telegram) are replaced with MagicMock stubs
before any src.main import occurs.
"""

import sys
import types
from datetime import date
from unittest.mock import patch, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Install fake third-party modules so src.sheets / src.telegram can import
# ---------------------------------------------------------------------------

def _install_stubs():
    """Install minimal fake modules for requests and gspread if absent."""
    if "requests" not in sys.modules:
        fake_requests = types.ModuleType("requests")
        fake_requests.post = MagicMock()
        sys.modules["requests"] = fake_requests

    if "gspread" not in sys.modules:
        fake_gspread = types.ModuleType("gspread")
        sys.modules["gspread"] = fake_gspread

    for sub in ("google", "google.oauth2", "google.oauth2.service_account"):
        if sub not in sys.modules:
            mod = types.ModuleType(sub)
            sys.modules[sub] = mod

    if "google.oauth2.service_account" in sys.modules:
        creds_mod = sys.modules["google.oauth2.service_account"]
        if not hasattr(creds_mod, "Credentials"):
            creds_mod.Credentials = MagicMock()


def _purge_src():
    """Remove all cached src.* modules to allow a fresh import."""
    for mod in list(sys.modules.keys()):
        if mod.startswith("src."):
            del sys.modules[mod]


def _make_customer(name="Alice", birth_date="18/06/1990", gender="Nữ"):
    return {
        "name": name,
        "gender": gender,
        "birth_date": birth_date,
        "age_group": "",
        "note": "",
        "active": "TRUE",
    }


# ---------------------------------------------------------------------------
# Core helper: run main() with fully mocked I/O
# ---------------------------------------------------------------------------

def _run_main(dry_run: bool, customers, sent_log=None, today=date(2025, 6, 18)):
    if sent_log is None:
        sent_log = set()

    _install_stubs()
    _purge_src()

    env_patch = {
        "DRY_RUN": "1" if dry_run else "0",
        "SHEET_ID": "fake",
        "TELEGRAM_BOT_TOKEN": "fake-token",
        "TELEGRAM_CHAT_ID": "fake-chat",
        "GOOGLE_CREDENTIALS_JSON": "",
        "GOOGLE_CREDENTIALS_FILE": "",
    }

    with patch.dict("os.environ", env_patch):
        import src.main as main_mod

        with patch("src.main.load_customers", return_value=customers), \
             patch("src.main.load_sent_log", return_value=sent_log), \
             patch("src.main.append_sent_rows") as mock_append, \
             patch("src.main.send_message") as mock_send, \
             patch("src.main.today_vn", return_value=today), \
             patch("src.events.today_vn", return_value=today), \
             patch("src.events.tomorrow_vn", return_value=today + __import__("datetime").timedelta(days=1)):

            main_mod.main()
            # Capture results before cleanup
            _mock_send = mock_send
            _mock_append = mock_append

    # Purge re-imported src.* modules to prevent state leaking to later tests
    _purge_src()
    return _mock_send, _mock_append


# ---------------------------------------------------------------------------
# DRY_RUN: send_message called, append_sent_rows NOT called
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write_sent_log():
    """DRY_RUN=1: messages are sent (printed) but log is never written."""
    customer = _make_customer(birth_date="18/06/1990")  # birthday today 2025-06-18
    mock_send, mock_append = _run_main(
        dry_run=True,
        customers=[customer],
        today=date(2025, 6, 18),
    )
    mock_send.assert_called()
    mock_append.assert_not_called()


def test_non_dry_run_writes_sent_log():
    """Without DRY_RUN: both send_message and append_sent_rows are called."""
    customer = _make_customer(birth_date="18/06/1990")
    mock_send, mock_append = _run_main(
        dry_run=False,
        customers=[customer],
        today=date(2025, 6, 18),
    )
    mock_send.assert_called()
    mock_append.assert_called_once()


def test_no_events_nothing_sent():
    """If no events match, send_message and append_sent_rows are not called."""
    customer = _make_customer(birth_date="20/06/1990")  # birthday in 2 days
    mock_send, mock_append = _run_main(
        dry_run=False,
        customers=[customer],
        today=date(2025, 6, 18),
    )
    mock_send.assert_not_called()
    mock_append.assert_not_called()


def test_empty_customer_list_nothing_sent():
    mock_send, mock_append = _run_main(
        dry_run=False,
        customers=[],
        today=date(2025, 6, 18),
    )
    mock_send.assert_not_called()
    mock_append.assert_not_called()


# ---------------------------------------------------------------------------
# send_message called once per event
# ---------------------------------------------------------------------------

def test_one_call_per_event():
    """With 2 customers each having a birthday today, send_message called twice."""
    customers = [
        _make_customer("Alice", "18/06/1990", "Nữ"),
        _make_customer("Bob", "18/06/1990", "Nam"),
    ]
    mock_send, _ = _run_main(
        dry_run=True,
        customers=customers,
        today=date(2025, 6, 18),
    )
    assert mock_send.call_count == 2


# ---------------------------------------------------------------------------
# Dedup: already-sent event not re-sent
# ---------------------------------------------------------------------------

def test_dedup_already_sent_not_resent():
    """Birthday today already in sent_log → no send, no append.

    We patch BOTH src.main.today_vn and src.events.today_vn so that
    scan_events internally sees the same frozen date.
    """
    _install_stubs()
    _purge_src()

    today = date(2025, 6, 18)
    customer = _make_customer("Alice", "18/06/1990", "Nữ")
    sent_log = {("Alice", "birthday", "T-0", "2025")}

    with patch.dict("os.environ", {
        "DRY_RUN": "0",
        "SHEET_ID": "fake",
        "TELEGRAM_BOT_TOKEN": "fake-token",
        "TELEGRAM_CHAT_ID": "fake-chat",
        "GOOGLE_CREDENTIALS_JSON": "",
        "GOOGLE_CREDENTIALS_FILE": "",
    }):
        import src.main as main_mod

        with patch("src.main.load_customers", return_value=[customer]), \
             patch("src.main.load_sent_log", return_value=sent_log), \
             patch("src.main.append_sent_rows") as mock_append, \
             patch("src.main.send_message") as mock_send, \
             patch("src.main.today_vn", return_value=today), \
             patch("src.events.today_vn", return_value=today), \
             patch("src.events.tomorrow_vn", return_value=today + __import__("datetime").timedelta(days=1)):

            main_mod.main()
            mock_send.assert_not_called()
            mock_append.assert_not_called()

    _purge_src()


# ---------------------------------------------------------------------------
# append_sent_rows receives correctly structured rows
# ---------------------------------------------------------------------------

def test_append_sent_rows_row_structure():
    """Each row dict must contain all required keys."""
    customer = _make_customer("Alice", "18/06/1990", "Nữ")
    mock_send, mock_append = _run_main(
        dry_run=False,
        customers=[customer],
        today=date(2025, 6, 18),
    )
    mock_append.assert_called_once()
    rows = mock_append.call_args[0][0]
    assert len(rows) >= 1
    for row in rows:
        assert "date_sent" in row
        assert "customer_name" in row
        assert "event_type" in row
        assert "notify_type" in row
        assert "year" in row


def test_append_sent_rows_date_is_today():
    customer = _make_customer("Alice", "18/06/1990", "Nữ")
    mock_send, mock_append = _run_main(
        dry_run=False,
        customers=[customer],
        today=date(2025, 6, 18),
    )
    rows = mock_append.call_args[0][0]
    for row in rows:
        assert row["date_sent"] == "2025-06-18"
