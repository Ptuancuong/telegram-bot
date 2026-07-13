"""
Map (tuổi, giới tính) → (cách gọi khách, cách mình xưng).

Quy tắc (theo CLAUDE.md):
  < 35      → gọi "em"          / xưng "anh"
  35 – 60   → gọi "anh"/"chị"   / xưng "em"
  > 60      → gọi "chú"/"cô"    / xưng "cháu"
"""

from __future__ import annotations

from src.config import today_vn

_FEMALE_VALS = frozenset({"Nữ", "nữ", "Nu", "nu", "female", "Female", "f", "F"})


def _parse_birth_year(birth_str: str) -> int | None:
    parts = birth_str.strip().split("/")
    if len(parts) == 3:
        try:
            return int(parts[2])
        except ValueError:
            pass
    return None


def get_salutation(customer: dict) -> tuple[str, str]:
    """Return (cal_khach, xung_minh).

    cal_khach: cách gọi khách (em / anh / chị / chú / cô)
    xung_minh: cách shop xưng  (anh / em / cháu)
    """
    birth_str = str(customer.get("birth_date", "")).strip()
    gender = str(customer.get("gender", "")).strip()
    is_female = gender in _FEMALE_VALS

    birth_year = _parse_birth_year(birth_str) if birth_str else None
    if birth_year is not None:
        age = today_vn().year - birth_year
    else:
        # Không có năm sinh → dùng nhóm trung niên làm mặc định an toàn
        age = 45

    if age < 35:
        return ("em", "anh")
    elif age <= 60:
        return ("chị" if is_female else "anh", "em")
    else:
        return ("cô" if is_female else "chú", "cháu")
