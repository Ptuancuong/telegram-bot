"""Verify tet_solar_date() against known Tết dates."""

from datetime import date

import pytest

from src.lunar import tet_solar_date


@pytest.mark.parametrize(
    "year, expected",
    [
        (2020, date(2020, 1, 25)),   # Canh Tý
        (2021, date(2021, 2, 12)),   # Tân Sửu
        (2022, date(2022, 2, 1)),    # Nhâm Dần
        (2023, date(2023, 1, 22)),   # Quý Mão
        (2024, date(2024, 2, 10)),   # Giáp Thìn
        (2025, date(2025, 1, 29)),   # Ất Tỵ
        (2026, date(2026, 2, 17)),   # Bính Ngọ
        (2027, date(2027, 2, 6)),    # Đinh Mùi
    ],
)
def test_tet_solar_date(year: int, expected: date) -> None:
    assert tet_solar_date(year) == expected
