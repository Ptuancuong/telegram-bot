"""Tests for salutation.py — age boundary, gender variants, missing birth_date.

NOTE: We import get_salutation lazily (inside _sal()) rather than at module
level. This ensures the patch("src.salutation.today_vn") always targets the
same module object that get_salutation is bound to, even when other tests
purge src.* from sys.modules.
"""

import pytest
from unittest.mock import patch
from datetime import date


def _customer(birth_date: str, gender: str) -> dict:
    return {"name": "Test", "birth_date": birth_date, "gender": gender}


def _sal(birth_date: str, gender: str, today: date) -> tuple:
    """Call get_salutation with a frozen today date."""
    # Import lazily so we always get the live module after any purges
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=today):
        return sal_mod.get_salutation(_customer(birth_date, gender))


# ---------------------------------------------------------------------------
# Age group < 35: call "em", shop says "anh"
# ---------------------------------------------------------------------------

def test_young_male():
    # age = 2025 - 2000 = 25
    assert _sal("01/01/2000", "Nam", date(2025, 6, 1)) == ("em", "anh")


def test_young_female():
    # age = 34 — still < 35
    assert _sal("01/06/1991", "Nữ", date(2025, 6, 1)) == ("em", "anh")


# ---------------------------------------------------------------------------
# Boundary age = 35: belongs to the middle group (35–60)
# ---------------------------------------------------------------------------

def test_boundary_35_male():
    # born 1990, today 2025 → age exactly 35
    assert _sal("01/01/1990", "Nam", date(2025, 6, 1)) == ("anh", "em")


def test_boundary_35_female():
    assert _sal("01/01/1990", "Nữ", date(2025, 6, 1)) == ("chị", "em")


# ---------------------------------------------------------------------------
# Middle group 35–60: call "anh"/"chị", shop says "em"
# ---------------------------------------------------------------------------

def test_middle_male():
    # age = 50
    assert _sal("01/01/1975", "Nam", date(2025, 6, 1)) == ("anh", "em")


def test_middle_female():
    assert _sal("01/01/1975", "Nữ", date(2025, 6, 1)) == ("chị", "em")


# ---------------------------------------------------------------------------
# Boundary age = 60: still middle group (age <= 60)
# ---------------------------------------------------------------------------

def test_boundary_60_male():
    # born 1965, today 2025 → age exactly 60
    assert _sal("01/01/1965", "Nam", date(2025, 6, 1)) == ("anh", "em")


def test_boundary_60_female():
    assert _sal("01/01/1965", "Nữ", date(2025, 6, 1)) == ("chị", "em")


# ---------------------------------------------------------------------------
# Boundary age = 61: senior group (> 60)
# ---------------------------------------------------------------------------

def test_boundary_61_male():
    # born 1964, today 2025 → age 61
    assert _sal("01/01/1964", "Nam", date(2025, 6, 1)) == ("chú", "cháu")


def test_boundary_61_female():
    assert _sal("01/01/1964", "Nữ", date(2025, 6, 1)) == ("cô", "cháu")


# ---------------------------------------------------------------------------
# Senior group > 60
# ---------------------------------------------------------------------------

def test_senior_male():
    assert _sal("01/01/1950", "Nam", date(2025, 6, 1)) == ("chú", "cháu")


def test_senior_female():
    assert _sal("01/01/1950", "Nữ", date(2025, 6, 1)) == ("cô", "cháu")


# ---------------------------------------------------------------------------
# Gender variants for female detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("gender", ["Nữ", "nữ", "Nu", "nu", "female", "Female", "f", "F"])
def test_female_variants_middle_group(gender: str):
    # age = 50, female — should use "chị"
    cal, _ = _sal("01/01/1975", gender, date(2025, 6, 1))
    assert cal == "chị"


@pytest.mark.parametrize("gender", ["Nữ", "nữ", "Nu", "nu", "female", "Female", "f", "F"])
def test_female_variants_senior(gender: str):
    # age = 70, female — should use "cô"
    cal, _ = _sal("01/01/1955", gender, date(2025, 6, 1))
    assert cal == "cô"


@pytest.mark.parametrize("gender", ["Nam", "nam", "m", "M", "Male", "other", ""])
def test_non_female_middle_group(gender: str):
    # Non-female values in middle group → "anh"
    cal, _ = _sal("01/01/1975", gender, date(2025, 6, 1))
    assert cal == "anh"


# ---------------------------------------------------------------------------
# Missing / malformed birth_date → falls back to age 45 (middle group)
# ---------------------------------------------------------------------------

def test_missing_birth_date_defaults_middle():
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=date(2025, 6, 1)):
        result = sal_mod.get_salutation({"name": "X", "birth_date": "", "gender": "Nam"})
    assert result == ("anh", "em")


def test_none_birth_date_defaults_middle():
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=date(2025, 6, 1)):
        result = sal_mod.get_salutation({"name": "X", "birth_date": None, "gender": "Nữ"})
    assert result == ("chị", "em")


def test_malformed_birth_date_defaults_middle():
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=date(2025, 6, 1)):
        result = sal_mod.get_salutation({"name": "X", "birth_date": "not-a-date", "gender": "Nam"})
    assert result == ("anh", "em")


def test_partial_birth_date_defaults_middle():
    # Only day/month — no year part
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=date(2025, 6, 1)):
        result = sal_mod.get_salutation({"name": "X", "birth_date": "15/06", "gender": "Nam"})
    assert result == ("anh", "em")


def test_missing_birth_date_key_defaults_middle():
    # customer dict has no birth_date key at all
    import src.salutation as sal_mod
    with patch.object(sal_mod, "today_vn", return_value=date(2025, 6, 1)):
        result = sal_mod.get_salutation({"name": "X", "gender": "Nam"})
    assert result == ("anh", "em")
