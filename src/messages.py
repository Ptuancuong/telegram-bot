"""
Template engine — Phase 1 (fixed templates, no AI).

Public API:
    build_message(event, salutation) -> str   (Telegram HTML string)

Template variables available in each string:
    {cal}        cách gọi khách   (em / anh / chị / chú / cô)
    {name}       tên khách        (HTML-escaped)
    {xung}       mình xưng        (anh / em / cháu)
    {Xung}       mình xưng — viết hoa đầu câu
    {year}       năm dương lịch   (tet_duong)
    {lunar_year} tên năm âm lịch  (tet_am)  e.g. "Ất Tỵ"
"""

from __future__ import annotations

import html
import random

from src.events import Event

# ---------------------------------------------------------------------------
# Vietnamese can-chi year names
# ---------------------------------------------------------------------------

_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
_CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]


def _lunar_year_name(solar_year: int) -> str:
    """Return the can-chi name for the lunar year of Tết in solar_year."""
    return f"{_CAN[(solar_year - 4) % 10]} {_CHI[(solar_year - 4) % 12]}"


# ---------------------------------------------------------------------------
# Message templates
# ---------------------------------------------------------------------------
# 4 variants per (event_type, notify_type) → random.sample picks 2–3

_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("birthday", "T-0"): [
        "Chúc {cal} {name} sinh nhật vui vẻ! Chúc {cal} luôn mạnh khoẻ, bình an và tràn đầy niềm vui. Shop cảm ơn {cal} đã đồng hành cùng mình nhé! 🎂🎉",
        "Happy Birthday {cal} {name}! {Xung} kính chúc {cal} một ngày sinh nhật thật đặc biệt, mọi điều ước đều thành hiện thực ạ 🎉🥳",
        "{Xung} chúc {cal} {name} sinh nhật vui vẻ! Tuổi mới nhiều sức khoẻ, hạnh phúc và thành công trong cuộc sống nhé 🌸",
        "Chúc mừng sinh nhật {cal} {name}! Chúc {cal} ngày sinh nhật thật trọn vẹn, sức khoẻ dồi dào và vạn sự như ý ạ 🎂",
    ],
    ("birthday", "T-1"): [
        "Ngày mai là sinh nhật của {cal} {name} rồi! {Xung} xin gửi lời chúc sớm: chúc {cal} sinh nhật vui vẻ, luôn mạnh khoẻ và hạnh phúc nhé 🎂",
        "Sắp đến sinh nhật {cal} {name} rồi! {Xung} kính chúc {cal} tuổi mới tràn đầy niềm vui, sức khoẻ dồi dào và mọi ước mơ đều thành sự thật ạ 🌸🎉",
        "{Xung} muốn chúc mừng sinh nhật sớm đến {cal} {name}! Chúc {cal} luôn vui vẻ, khoẻ mạnh và thành công trong năm tuổi mới nhé 🥳",
        "Ngày mai {cal} {name} sinh nhật! Chúc {cal} tuổi mới an khang, vạn sự như ý và gia đình hạnh phúc ạ 🎂🎊",
    ],
    ("tet_duong", "T-0"): [
        "Chúc mừng năm mới {year}! {Xung} kính chúc {cal} {name} năm mới an khang thịnh vượng, vạn sự như ý và gia đình hạnh phúc ạ 🎊🎆",
        "Happy New Year {cal} {name}! Chúc {cal} năm {year} tràn đầy sức khoẻ, may mắn và thành công trong mọi việc nhé 🥳🎉",
        "Chúc {cal} {name} năm mới {year} bình an, thịnh vượng! Shop cảm ơn {cal} và kính chúc {cal} một năm mới thật tươi đẹp ạ 🎆🌟",
        "{Xung} kính chúc {cal} {name} năm mới {year} dồi dào sức khoẻ, công việc thuận lợi và gia đình sum vầy hạnh phúc 🎊",
    ],
    ("tet_duong", "T-1"): [
        "Năm mới {year} sắp đến rồi! {Xung} kính gửi lời chúc sớm đến {cal} {name}: chúc {cal} năm mới vạn sự như ý, bình an và thịnh vượng ạ 🎊",
        "Còn một ngày nữa là năm mới {year} rồi {cal} {name} ơi! Chúc {cal} đón năm mới vui vẻ, mọi điều tốt đẹp sẽ đến trong năm mới nhé 🎆🥳",
        "{Xung} chúc {cal} {name} năm mới {year} an khang thịnh vượng! Chúc {cal} và gia đình đón năm mới thật hạnh phúc ạ 🎉🌟",
        "Sắp đón năm mới {year} rồi! {Xung} kính chúc {cal} {name} một năm mới tràn đầy sức khoẻ, may mắn và niềm vui 🎊",
    ],
    ("tet_am", "T-0"): [
        "Chúc mừng năm mới {lunar_year}! {Xung} kính chúc {cal} {name} Tết đến vạn sự như ý, bình an và thịnh vượng ạ 🧧🎊",
        "Tết {lunar_year} đến rồi! Chúc {cal} {name} năm mới tràn đầy sức khoẻ, hạnh phúc và tài lộc. Shop kính chúc {cal} một mùa Tết thật trọn vẹn nhé 🧧🌸",
        "{Xung} kính chúc {cal} {name} năm mới {lunar_year} an khang thịnh vượng, gia đình sum vầy và mọi điều ước đều thành hiện thực ạ 🎉🧧",
        "Chúc {cal} {name} đón Tết {lunar_year} vui vẻ! Năm mới chúc {cal} dồi dào sức khoẻ, công việc thuận lợi và vạn sự hanh thông 🧧🎊",
    ],
    ("tet_am", "T-1"): [
        "Tết {lunar_year} sắp đến rồi! {Xung} kính gửi lời chúc sớm đến {cal} {name}: chúc {cal} đón Tết vui vẻ, bình an và thịnh vượng ạ 🧧",
        "Còn một ngày nữa là Tết {lunar_year} rồi {cal} {name} ơi! Chúc {cal} và gia đình đón Tết thật vui, năm mới nhiều sức khoẻ và hạnh phúc nhé 🌸🧧",
        "{Xung} chúc {cal} {name} chuẩn bị đón Tết {lunar_year} thật vui! Năm mới kính chúc {cal} vạn sự như ý, an khang và thịnh vượng ạ 🎊🧧",
        "Sắp đến Tết {lunar_year} rồi! {Xung} kính chúc {cal} {name} năm mới bình an, tài lộc dồi dào và gia đình hạnh phúc nhé 🧧🎉",
    ],
}

_EVENT_LABELS = {
    "birthday": "Sinh nhật",
    "tet_duong": "Tết Dương lịch",
    "tet_am": "Tết Âm lịch",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_message(event: Event, salutation: tuple[str, str]) -> str:
    """Build a Telegram HTML message for one event.

    Args:
        event:      Event dataclass from events.py
        salutation: (cal_khach, xung_minh) from salutation.py

    Returns:
        HTML string ready for Telegram sendMessage (parse_mode=HTML).
    """
    cal, xung = salutation
    name_safe = html.escape(str(event.customer.get("name", "")))

    lunar_year = _lunar_year_name(event.year)

    vars_: dict[str, str] = {
        "cal": cal,
        "name": name_safe,
        "xung": xung,
        "Xung": xung[0].upper() + xung[1:] if xung else xung,
        "year": str(event.year),
        "lunar_year": lunar_year,
    }

    pool = _TEMPLATES.get((event.event_type, event.notify_type), [])
    n = min(len(pool), random.randint(2, 3))
    chosen = random.sample(pool, n)

    event_label = html.escape(_EVENT_LABELS.get(event.event_type, event.event_type))
    header = (
        f"<b>👤 {name_safe}</b> · <b>{event_label}</b> · {event.notify_type}\n\n"
        "Lời chúc gợi ý (copy để gửi Zalo):"
    )

    wish_blocks = "\n\n".join(
        f"<pre>{_render(t, vars_)}</pre>" for t in chosen
    )

    return f"{header}\n\n{wish_blocks}"


def _render(template: str, vars_: dict[str, str]) -> str:
    """Substitute {key} placeholders without str.format().

    Using plain replacement (not .format) so that customer names containing
    curly braces — e.g. "{year}" or an unknown "{foo}" — cannot inject template
    values or raise KeyError. html.escape does not touch braces, so {name} is
    substituted LAST: any braces inside the name itself are left as literal
    text instead of being re-expanded as placeholders.
    """
    result = template
    for key, val in vars_.items():
        if key == "name":
            continue
        result = result.replace("{" + key + "}", val)
    return result.replace("{name}", vars_["name"])
