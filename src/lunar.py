"""
Vietnamese lunar calendar — Hồ Ngọc Đức algorithm (UTC+7).
Reference: http://www.informatik.uni-leipzig.de/~duc/amlich/
Public API: tet_solar_date(year) -> date ; lunar_year_name(solar_year) -> str
"""

import math
from datetime import date

_TZ = 7  # UTC+7

# Can-chi (thiên can / địa chi) để đặt tên năm âm lịch.
_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
_CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]


# ---------------------------------------------------------------------------
# Core astronomical helpers
# ---------------------------------------------------------------------------

def _jd_from_date(dd: int, mm: int, yyyy: int) -> int:
    """Gregorian date → Julian Day Number."""
    a = (14 - mm) // 12
    y = yyyy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if jd < 2299161:
        jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083
    return jd


def _jd_to_date(jd: int) -> tuple[int, int, int]:
    """Julian Day Number → (day, month, year) Gregorian."""
    if jd > 2299160:
        a = jd + 32044
        b = (4 * a + 3) // 146097
        c = a - (b * 146097) // 4
    else:
        b = 0
        c = jd + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = b * 100 + d - 4800 + m // 10
    return day, month, year


def _new_moon(k: int) -> float:
    """Approximate JD of the k-th new moon (k=0 ≈ Jan 6.0, 1900 UTC)."""
    T = k / 1236.85
    T2 = T * T
    T3 = T2 * T
    dr = math.pi / 180

    Jd1 = (
        2415020.75933
        + 29.53058868 * k
        + 0.0001178 * T2
        - 0.000000155 * T3
        + 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    )
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3

    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr)
    C1 += 0.0021 * math.sin(2 * dr * M)
    C1 -= 0.4068 * math.sin(Mpr * dr)
    C1 += 0.0161 * math.sin(dr * 2 * Mpr)
    C1 -= 0.0004 * math.sin(dr * 3 * Mpr)
    C1 += 0.0104 * math.sin(dr * 2 * F)
    C1 -= 0.0051 * math.sin(dr * (M + Mpr))
    C1 -= 0.0074 * math.sin(dr * (M - Mpr))
    C1 += 0.0004 * math.sin(dr * (2 * F + M))
    C1 -= 0.0004 * math.sin(dr * (2 * F - M))
    C1 -= 0.0006 * math.sin(dr * (2 * F + Mpr))
    C1 += 0.0010 * math.sin(dr * (2 * F - Mpr))
    C1 += 0.0005 * math.sin(dr * (M + 2 * Mpr))

    if T < -11:
        deltat = (
            0.001
            + 0.000839 * T
            + 0.0002261 * T2
            - 0.00000845 * T3
            - 0.000000081 * T * T3
        )
    else:
        deltat = -0.000278 + 0.000265 * T + 0.000262 * T2

    return Jd1 + C1 - deltat


def _sun_longitude(jdn: float) -> float:
    """Sun's ecliptic longitude in radians for a given JD."""
    T = (jdn - 2451545.0) / 36525
    T2 = T * T
    dr = math.pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.9146 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M)
    DL += 0.00029 * math.sin(dr * 3 * M)
    L = (L0 + DL) * dr
    L -= math.pi * 2 * int(L / (math.pi * 2))
    return L


def _get_sun_longitude(day_number: int, tz: int) -> float:
    return _sun_longitude(day_number - 0.5 - tz / 24)


def _get_new_moon_day(k: int, tz: int) -> int:
    """Day number (JD) of the k-th new moon in timezone tz."""
    return int(_new_moon(k) + 0.5 + tz / 24)


def _get_lunar_month11(yy: int, tz: int) -> int:
    """JD of the first day of the 11th lunar month of solar year yy."""
    off = _jd_from_date(31, 12, yy) - 2415021.076998695
    k = int(off / 29.530588853)
    nm = _get_new_moon_day(k, tz)
    if _get_sun_longitude(nm, tz) >= 9 * math.pi / 6:
        nm = _get_new_moon_day(k - 1, tz)
    return nm


def _get_leap_month_offset(a11: int, tz: int) -> int:
    """Offset of the leap month within the lunar year starting at a11."""
    k = int(0.5 + (a11 - 2415021.076998695) / 29.530588853)
    i = 1
    arc = _get_sun_longitude(_get_new_moon_day(k + i, tz), tz)
    while True:
        last = arc
        i += 1
        arc = _get_sun_longitude(_get_new_moon_day(k + i, tz), tz)
        if arc < last or i >= 14:
            break
    return i - 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tet_solar_date(year: int) -> date:
    """Return the solar date of Mùng 1 Tết (1st day of 1st lunar month).

    Examples:
        tet_solar_date(2023) == date(2023, 1, 22)   # Quý Mão
        tet_solar_date(2024) == date(2024, 2, 10)   # Giáp Thìn
        tet_solar_date(2025) == date(2025, 1, 29)   # Ất Tỵ
    """
    a11 = _get_lunar_month11(year - 1, _TZ)
    b11 = _get_lunar_month11(year, _TZ)
    k = int(0.5 + (a11 - 2415021.076998695) / 29.530588853)

    if b11 - a11 > 365:
        leap_off = _get_leap_month_offset(a11, _TZ)
        leap_month = leap_off - 1
        if leap_month < 0:
            leap_month = 11
    else:
        leap_month = -1

    # Month 11 is offset 0; month 12 is +1; month 1 (Tết) is +2.
    # If month 11 is the leap month, Tết shifts to +3.
    months_after_11 = 3 if leap_month == 11 else 2

    tet_jd = _get_new_moon_day(k + months_after_11, _TZ)
    dd, mm, yyyy = _jd_to_date(tet_jd)
    return date(yyyy, mm, dd)


def lunar_year_name(solar_year: int) -> str:
    """Tên can-chi của năm âm lịch mà Tết rơi vào solar_year, e.g. 'Ất Tỵ'."""
    return f"{_CAN[(solar_year - 4) % 10]} {_CHI[(solar_year - 4) % 12]}"
