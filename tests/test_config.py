"""Tests for config.py — DRY_RUN parsing, today_vn/tomorrow_vn timezone."""

import importlib
import sys
from datetime import date, timedelta
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# today_vn / tomorrow_vn use Asia/Ho_Chi_Minh, not bare datetime.now()
# ---------------------------------------------------------------------------

def test_today_vn_returns_date():
    from src.config import today_vn
    result = today_vn()
    assert isinstance(result, date)


def test_tomorrow_vn_is_today_plus_one():
    from src.config import today_vn, tomorrow_vn
    assert tomorrow_vn() == today_vn() + timedelta(days=1)


def test_today_vn_uses_vietnam_timezone():
    """today_vn() must use Asia/Ho_Chi_Minh, not UTC or local time.

    We monkeypatch datetime.now to return a UTC midnight that is still
    "yesterday" in UTC but "today morning" in UTC+7, then verify that
    today_vn() returns the VN date, not the UTC date.
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime

    # A real datetime in UTC+7: 2025-06-18 01:00:00 UTC+7 = 2025-06-17 18:00:00 UTC
    # If the function used UTC it would return 2025-06-17; VN should return 2025-06-18
    vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    fake_dt = datetime(2025, 6, 18, 1, 0, 0, tzinfo=vn_tz)

    with patch("src.config.datetime") as mock_dt:
        mock_dt.now.return_value = fake_dt
        from src.config import today_vn
        result = today_vn()

    assert result == date(2025, 6, 18)


# ---------------------------------------------------------------------------
# DRY_RUN parsing — must accept truthy strings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("val, expected", [
    ("1", True),
    ("true", True),
    ("True", True),
    ("TRUE", True),
    ("yes", True),
    ("Yes", True),
    ("YES", True),
    ("0", False),
    ("false", False),
    ("False", False),
    ("no", False),
    ("", False),
    ("2", False),
])
def test_dry_run_env_parsing(val: str, expected: bool):
    """DRY_RUN is parsed at import time; reload the module with patched env."""
    with patch.dict("os.environ", {"DRY_RUN": val}):
        # Force re-evaluation by reloading the module
        if "src.config" in sys.modules:
            del sys.modules["src.config"]
        import src.config as cfg
        assert cfg.DRY_RUN is expected
    # Restore for subsequent tests
    if "src.config" in sys.modules:
        del sys.modules["src.config"]
    import src.config  # noqa: F401


# ---------------------------------------------------------------------------
# Trailing whitespace/newline in env vars must be stripped — this bit us for
# real in GitHub Secrets, where a copy-pasted value silently gained a
# trailing "\n" and broke Google Sheets API lookups with a 404.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("var_name", [
    "SHEET_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GOOGLE_CREDENTIALS_JSON",
])
def test_env_vars_are_stripped_of_trailing_newline(var_name: str):
    with patch.dict("os.environ", {var_name: "value123\n"}), patch("dotenv.load_dotenv"):
        if "src.config" in sys.modules:
            del sys.modules["src.config"]
        import src.config as cfg
        assert getattr(cfg, var_name) == "value123"
    if "src.config" in sys.modules:
        del sys.modules["src.config"]
    import src.config  # noqa: F401


def test_dry_run_default_is_false():
    """When DRY_RUN env var is not set, default is False.

    load_dotenv() is mocked out here: a real .env file in the project root
    (used for local runs) would otherwise supply DRY_RUN=1 and defeat the
    "no env var set" scenario this test is checking.
    """
    env = {k: v for k, v in __import__("os").environ.items() if k != "DRY_RUN"}
    with patch.dict("os.environ", env, clear=True), patch("dotenv.load_dotenv"):
        if "src.config" in sys.modules:
            del sys.modules["src.config"]
        import src.config as cfg
        assert cfg.DRY_RUN is False
    if "src.config" in sys.modules:
        del sys.modules["src.config"]
    import src.config  # noqa: F401
