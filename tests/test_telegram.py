"""Tests for telegram.py — DRY_RUN suppresses requests, missing token raises."""

import sys
import types
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers: install a fake 'requests' module before importing src.telegram,
# because requests is not installed in this environment.
# ---------------------------------------------------------------------------

def _make_fake_requests():
    """Create a minimal fake requests module with a post() stub."""
    fake = types.ModuleType("requests")
    fake.post = MagicMock()
    return fake


def _install_fake_requests():
    fake = _make_fake_requests()
    sys.modules["requests"] = fake
    return fake


def _reload_telegram(dry_run: bool, token: str = "", chat_id: str = ""):
    """Force-reload src.telegram with specific config values and fake requests."""
    # Ensure fake requests is in sys.modules
    fake_requests = _install_fake_requests()

    # Remove cached src modules so fresh import picks up patched env
    for mod in list(sys.modules.keys()):
        if mod in ("src.telegram", "src.config"):
            del sys.modules[mod]

    with patch.dict("os.environ", {
        "DRY_RUN": "1" if dry_run else "0",
        "TELEGRAM_BOT_TOKEN": token,
        "TELEGRAM_CHAT_ID": chat_id,
    }):
        import src.config  # noqa: F401
        import src.telegram as tg
        # Bind the fake requests into the loaded module's namespace
        tg.requests = fake_requests
        return tg, fake_requests


def _cleanup():
    for mod in list(sys.modules.keys()):
        if mod in ("src.telegram", "src.config"):
            del sys.modules[mod]
    # Leave fake requests in sys.modules — harmless, avoids re-install overhead


# ---------------------------------------------------------------------------
# DRY_RUN=True: requests.post must NOT be called
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_requests_post(capsys):
    tg, fake_req = _reload_telegram(dry_run=True, token="", chat_id="")
    try:
        tg.send_message("Hello dry run")
        fake_req.post.assert_not_called()
    finally:
        _cleanup()


def test_dry_run_prints_to_stdout(capsys):
    tg, _ = _reload_telegram(dry_run=True, token="", chat_id="")
    try:
        tg.send_message("My test message")
        captured = capsys.readouterr()
        assert "My test message" in captured.out
        assert "[DRY_RUN]" in captured.out
    finally:
        _cleanup()


def test_dry_run_does_not_raise_with_empty_token():
    """In DRY_RUN mode, missing token/chat_id must NOT raise ValueError."""
    tg, _ = _reload_telegram(dry_run=True, token="", chat_id="")
    try:
        tg.send_message("test")  # must not raise
    finally:
        _cleanup()


# ---------------------------------------------------------------------------
# Non-DRY_RUN + missing credentials: must raise ValueError
# ---------------------------------------------------------------------------

def test_missing_token_raises_value_error():
    tg, _ = _reload_telegram(dry_run=False, token="", chat_id="")
    try:
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            tg.send_message("test")
    finally:
        _cleanup()


def test_missing_chat_id_raises_value_error():
    tg, _ = _reload_telegram(dry_run=False, token="fake-token", chat_id="")
    try:
        with pytest.raises(ValueError):
            tg.send_message("test")
    finally:
        _cleanup()


# ---------------------------------------------------------------------------
# Non-DRY_RUN + valid credentials: requests.post IS called with correct args
# ---------------------------------------------------------------------------

def test_send_calls_requests_post_with_correct_url():
    tg, fake_req = _reload_telegram(dry_run=False, token="mytoken", chat_id="mychat")
    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        fake_req.post.return_value = mock_resp
        tg.send_message("<b>Hello</b>")
        fake_req.post.assert_called_once()
        call_args = fake_req.post.call_args
        url = call_args[0][0]
        assert "mytoken" in url
        assert "sendMessage" in url
    finally:
        _cleanup()


def test_send_uses_html_parse_mode():
    tg, fake_req = _reload_telegram(dry_run=False, token="mytoken", chat_id="mychat")
    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        fake_req.post.return_value = mock_resp
        tg.send_message("test")
        payload = fake_req.post.call_args[1]["json"]
        assert payload.get("parse_mode") == "HTML"
    finally:
        _cleanup()


def test_send_sets_correct_chat_id():
    tg, fake_req = _reload_telegram(dry_run=False, token="mytoken", chat_id="chat123")
    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        fake_req.post.return_value = mock_resp
        tg.send_message("test")
        payload = fake_req.post.call_args[1]["json"]
        assert payload.get("chat_id") == "chat123"
    finally:
        _cleanup()


def test_send_passes_text():
    tg, fake_req = _reload_telegram(dry_run=False, token="mytoken", chat_id="mychat")
    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        fake_req.post.return_value = mock_resp
        tg.send_message("<b>actual content</b>")
        payload = fake_req.post.call_args[1]["json"]
        assert payload.get("text") == "<b>actual content</b>"
    finally:
        _cleanup()


def test_raise_for_status_called():
    """HTTP error from Telegram must propagate (raise_for_status called)."""
    tg, fake_req = _reload_telegram(dry_run=False, token="mytoken", chat_id="mychat")
    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 400")
        fake_req.post.return_value = mock_resp
        with pytest.raises(Exception, match="HTTP 400"):
            tg.send_message("test")
    finally:
        _cleanup()
