"""
Message builder — Phase 1 template + Phase 2 Gemini.

`build_message` ưu tiên gọi Gemini (`gemini.generate_wishes`); nếu AI bị tắt,
thiếu key hoặc lỗi thì rơi về template cố định của Phase 1. Cả hai nguồn dùng
chung lớp trình bày Telegram (`_wrap_telegram`).

Public API:
    build_message(event, salutation) -> str   (Telegram HTML string)

Template variables available in each string:
    {cal}        cách gọi khách   (em / anh / chị / chú / cô)
    {name}       tên khách        (thay CUỐI cùng; escape ở bước đóng khung)
    {xung}       mình xưng        (anh / em / cháu)
    {Xung}       mình xưng — viết hoa đầu câu
    {year}       năm dương lịch   (tet_duong)
    {lunar_year} tên năm âm lịch  (tet_am)  e.g. "Ất Tỵ"
"""

from __future__ import annotations

import html
import random

from src.events import Event
from src.gemini import generate_wishes
from src.lunar import lunar_year_name

# ---------------------------------------------------------------------------
# Message templates
# ---------------------------------------------------------------------------
# 4 variants per (event_type, notify_type) → random.sample picks 2–3

_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("birthday", "T-0"): [
        "Chúc mừng sinh nhật {cal} {name}! {Xung} kính chúc {cal} một tuổi mới thật nhiều sức khoẻ, bình an và mọi việc hanh thông ạ.",
        "{Xung} xin gửi tới {cal} {name} lời chúc sinh nhật vui vẻ, an lành. Chúc {cal} luôn dồi dào sức khoẻ và gặt hái nhiều thành công trong năm nay nhé.",
        "Happy Birthday {cal} {name}! Chúc {cal} một ngày sinh nhật ấm áp bên gia đình, tuổi mới nhiều niềm vui và may mắn ạ 🎂",
        "Nhân ngày sinh nhật, {xung} chúc {cal} {name} luôn mạnh khoẻ, tinh thần thoải mái và công việc thuận lợi. Chúc {cal} có một ngày thật ý nghĩa nhé.",
    ],
    ("birthday", "T-1"): [
        "Ngày mai là sinh nhật {cal} {name} rồi! {Xung} xin gửi lời chúc sớm: chúc {cal} tuổi mới nhiều sức khoẻ, bình an và mọi điều tốt lành ạ.",
        "{Xung} chúc mừng sinh nhật {cal} {name} trước một ngày. Chúc {cal} luôn mạnh khoẻ, vui vẻ và thành công trong công việc cũng như cuộc sống nhé.",
        "Sắp tới sinh nhật {cal} {name} rồi. {Xung} kính chúc {cal} một tuổi mới an khang, thuận lợi và thật nhiều niềm vui ạ 🎂",
        "Ngày mai {cal} {name} thêm một tuổi mới. Chúc {cal} luôn giữ được sức khoẻ, sự bình an và gặt hái nhiều điều như ý trong năm nay nhé.",
    ],
    ("tet_duong", "T-0"): [
        "Chúc mừng năm mới {year}! {Xung} kính chúc {cal} {name} một năm dồi dào sức khoẻ, an khang và mọi việc hanh thông ạ.",
        "Nhân dịp năm mới {year}, {xung} xin gửi tới {cal} {name} lời chúc bình an, may mắn và thành công. Chúc {cal} cùng gia đình một năm thật trọn vẹn nhé.",
        "Happy New Year {cal} {name}! Chúc {cal} bước sang năm {year} với thật nhiều sức khoẻ, niềm vui và tài lộc ạ 🎉",
        "{Xung} kính chúc {cal} {name} năm {year} vạn sự như ý, công việc thuận lợi và gia đình luôn ấm êm, hạnh phúc.",
    ],
    ("tet_duong", "T-1"): [
        "Năm mới {year} sắp đến rồi! {Xung} xin gửi {cal} {name} lời chúc sớm: một năm mới an khang, thịnh vượng và nhiều may mắn ạ.",
        "Chỉ còn một ngày nữa là sang năm {year}. {Xung} chúc {cal} {name} đón năm mới bình an, sức khoẻ dồi dào và mọi việc hanh thông nhé.",
        "Sắp chào năm mới {year} rồi {cal} {name} ơi. Chúc {cal} một năm tràn đầy năng lượng, công việc thuận lợi và gia đình hạnh phúc ạ 🎉",
        "{Xung} kính chúc {cal} {name} đón năm mới {year} thật vui, khởi đầu thuận lợi và gặt hái nhiều thành công trong năm nay.",
    ],
    ("tet_am", "T-0"): [
        "Chúc mừng năm mới {lunar_year}! {Xung} kính chúc {cal} {name} một năm an khang, thịnh vượng và vạn sự như ý ạ 🧧",
        "Nhân dịp Tết {lunar_year}, {xung} xin gửi {cal} {name} lời chúc sức khoẻ, bình an và tài lộc. Chúc {cal} cùng gia đình một năm mới thật ấm áp, sung túc nhé.",
        "Năm mới {lunar_year}, {xung} kính chúc {cal} {name} dồi dào sức khoẻ, công việc hanh thông và gia đình sum vầy hạnh phúc ạ.",
        "Chúc {cal} {name} đón Tết {lunar_year} an lành. Chúc {cal} một năm mới nhiều may mắn, thuận lợi trong công việc và vạn sự bình an.",
    ],
    ("tet_am", "T-1"): [
        "Tết {lunar_year} sắp đến rồi! {Xung} xin gửi {cal} {name} lời chúc sớm: một năm mới an khang, thịnh vượng và bình an ạ 🧧",
        "Chỉ còn một ngày nữa là Tết {lunar_year}. {Xung} chúc {cal} {name} cùng gia đình đón năm mới thật ấm áp, sức khoẻ dồi dào và nhiều tài lộc nhé.",
        "Sắp đón Tết {lunar_year} rồi {cal} {name} ơi. {Xung} kính chúc {cal} một năm mới vạn sự như ý, công việc thuận lợi và an khang ạ.",
        "{Xung} kính chúc {cal} {name} đón Tết {lunar_year} bình an, khởi đầu năm mới thuận lợi và gia đình luôn hạnh phúc, sung túc.",
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

    Ưu tiên lời chúc do Gemini sinh (Phase 2); nếu AI không dùng được thì rơi
    về template cố định (Phase 1). Cả hai đóng khung Telegram giống nhau.

    Args:
        event:      Event dataclass from events.py
        salutation: (cal_khach, xung_minh) from salutation.py

    Returns:
        HTML string ready for Telegram sendMessage (parse_mode=HTML).
    """
    wishes = generate_wishes(event, salutation)
    if wishes is None:
        wishes = _template_wishes(event, salutation)

    return _wrap_telegram(event, wishes)


def _template_wishes(event: Event, salutation: tuple[str, str]) -> list[str]:
    """Chọn ngẫu nhiên 2–3 câu chúc template và thay biến (Phase 1)."""
    cal, xung = salutation
    vars_: dict[str, str] = {
        "cal": cal,
        "name": str(event.customer.get("name", "")),
        "xung": xung,
        "Xung": xung[0].upper() + xung[1:] if xung else xung,
        "year": str(event.year),
        "lunar_year": lunar_year_name(event.year),
    }

    pool = _TEMPLATES.get((event.event_type, event.notify_type), [])
    n = min(len(pool), random.randint(2, 3))
    chosen = random.sample(pool, n)
    return [_render(t, vars_) for t in chosen]


def _wrap_telegram(event: Event, wishes: list[str]) -> str:
    """Đóng khung danh sách câu chúc (plain text) thành 1 tin Telegram HTML.

    Escape ở đây một lần cho toàn bộ nội dung — bất kể nguồn là template hay AI —
    nên tên khách hoặc câu chúc chứa `<`, `>`, `&` đều an toàn với parse_mode=HTML.
    """
    name_safe = html.escape(str(event.customer.get("name", "")))
    event_label = html.escape(_EVENT_LABELS.get(event.event_type, event.event_type))
    # Số điện thoại (cột 'phone' trong Sheet, nếu có) — để nhân viên tra nhanh.
    # Bọc <code> để Telegram cho chạm-copy số.
    phone = str(event.customer.get("phone", "")).strip()
    phone_line = f"\n📱 <code>{html.escape(phone)}</code>" if phone else ""
    header = (
        f"<b>👤 {name_safe}</b> · <b>{event_label}</b> · {event.notify_type}"
        f"{phone_line}\n\n"
        "Lời chúc gợi ý (copy để gửi Zalo):"
    )

    wish_blocks = "\n\n".join(f"<pre>{html.escape(w)}</pre>" for w in wishes)

    return f"{header}\n\n{wish_blocks}"


def _render(template: str, vars_: dict[str, str]) -> str:
    """Substitute {key} placeholders without str.format().

    Using plain replacement (not .format) so that customer names containing
    curly braces — e.g. "{year}" or an unknown "{foo}" — cannot inject template
    values or raise KeyError. {name} is substituted LAST so any braces inside
    the name itself are left as literal text instead of being re-expanded as
    placeholders. HTML-escaping happens later in `_wrap_telegram`.
    """
    result = template
    for key, val in vars_.items():
        if key == "name":
            continue
        result = result.replace("{" + key + "}", val)
    return result.replace("{name}", vars_["name"])
