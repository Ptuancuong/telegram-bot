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

# Chỉ còn template cho T-0 (đúng ngày): mỗi khách 1 tin kèm 2–3 lời chúc để
# chạm-copy gửi Zalo. T-1 (báo trước 1 ngày) KHÔNG dùng template ở đây nữa —
# nó chỉ là 1 tin nhắc ngắn (xem `_reminder_message`), không sinh lời chúc.
_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("birthday", "T-0"): [
        "Chúc mừng sinh nhật {cal} {name}! {Xung} kính chúc {cal} một tuổi mới thật nhiều sức khoẻ, bình an và mọi việc hanh thông ạ.",
        "{Xung} xin gửi tới {cal} {name} lời chúc sinh nhật vui vẻ, an lành. Chúc {cal} luôn dồi dào sức khoẻ và gặt hái nhiều thành công trong năm nay nhé.",
        "Happy Birthday {cal} {name}! Chúc {cal} một ngày sinh nhật ấm áp bên gia đình, tuổi mới nhiều niềm vui và may mắn ạ 🎂",
        "Nhân ngày sinh nhật, {xung} chúc {cal} {name} luôn mạnh khoẻ, tinh thần thoải mái và công việc thuận lợi. Chúc {cal} có một ngày thật ý nghĩa nhé.",
    ],
    ("tet_duong", "T-0"): [
        "Chúc mừng năm mới {year}! {Xung} kính chúc {cal} {name} một năm dồi dào sức khoẻ, an khang và mọi việc hanh thông ạ.",
        "Nhân dịp năm mới {year}, {xung} xin gửi tới {cal} {name} lời chúc bình an, may mắn và thành công. Chúc {cal} cùng gia đình một năm thật trọn vẹn nhé.",
        "Happy New Year {cal} {name}! Chúc {cal} bước sang năm {year} với thật nhiều sức khoẻ, niềm vui và tài lộc ạ 🎉",
        "{Xung} kính chúc {cal} {name} năm {year} vạn sự như ý, công việc thuận lợi và gia đình luôn ấm êm, hạnh phúc.",
    ],
    ("tet_am", "T-0"): [
        "Chúc mừng năm mới {lunar_year}! {Xung} kính chúc {cal} {name} một năm an khang, thịnh vượng và vạn sự như ý ạ 🧧",
        "Nhân dịp Tết {lunar_year}, {xung} xin gửi {cal} {name} lời chúc sức khoẻ, bình an và tài lộc. Chúc {cal} cùng gia đình một năm mới thật ấm áp, sung túc nhé.",
        "Năm mới {lunar_year}, {xung} kính chúc {cal} {name} dồi dào sức khoẻ, công việc hanh thông và gia đình sum vầy hạnh phúc ạ.",
        "Chúc {cal} {name} đón Tết {lunar_year} an lành. Chúc {cal} một năm mới nhiều may mắn, thuận lợi trong công việc và vạn sự bình an.",
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

    - **T-1** (báo trước 1 ngày): chỉ 1 tin NHẮC ngắn ("Ngày mai là sinh nhật
      …, nhớ gửi lời chúc"). Không gọi Gemini, không kèm khối lời chúc.
    - **T-0** (đúng ngày): tin đầy đủ kèm 2–3 lời chúc để chạm-copy gửi Zalo.

    Args:
        event:      Event dataclass from events.py
        salutation: (cal_khach, xung_minh) from salutation.py

    Returns:
        HTML string ready for Telegram sendMessage (parse_mode=HTML).
    """
    if event.notify_type == "T-1":
        return _reminder_message(event, salutation)

    wishes = generate_wishes(event, salutation)
    if wishes is None:
        wishes = _template_wishes(event, salutation)

    return _wrap_telegram(event, wishes)


def _reminder_message(event: Event, salutation: tuple[str, str]) -> str:
    """Tin nhắc trước 1 ngày (T-1) — ngắn gọn, không kèm lời chúc.

    - **Sinh nhật**: nhắc RIÊNG từng khách (kèm tên + SĐT) —
      "Ngày mai là sinh nhật anh Nguyễn Văn A. Nhớ chuẩn bị lời chúc nhé!"
    - **Tết dương/âm**: 1 tin nhắc CHUNG cho toàn bộ khách (không kèm tên) —
      "Ngày mai là Tết Dương lịch (2027). Nhớ gửi lời chúc toàn bộ khách hàng nhé!"

    Nội dung được escape HTML một lần (parse_mode=HTML).
    """
    event_label = html.escape(_EVENT_LABELS.get(event.event_type, event.event_type))

    # Sinh nhật: nhắc riêng từng khách.
    if event.event_type == "birthday":
        cal, _ = salutation
        name = str(event.customer.get("name", ""))
        body = f"Ngày mai là sinh nhật {cal} {name}. Nhớ chuẩn bị lời chúc để mai gửi khách nhé!"
        name_safe = html.escape(name)
        phone = _format_phone(str(event.customer.get("phone", "")))
        phone_line = f"\n📱 <code>{html.escape(phone)}</code>" if phone else ""
        header = f"🔔 <b>Nhắc trước 1 ngày</b> · <b>{event_label}</b> · <b>{name_safe}</b>{phone_line}"
        return f"{header}\n\n{html.escape(body)}"

    # Tết dương/âm: 1 tin nhắc chung cho toàn bộ khách.
    if event.event_type == "tet_duong":
        occ = f"Tết Dương lịch ({event.year})"
    elif event.event_type == "tet_am":
        occ = f"Tết {lunar_year_name(event.year)} ({event.year} dương lịch)"
    else:
        occ = _EVENT_LABELS.get(event.event_type, event.event_type)

    body = f"Ngày mai là {occ}. Nhớ gửi lời chúc cho toàn bộ khách hàng nhé!"
    header = f"🔔 <b>Nhắc trước 1 ngày</b> · <b>{event_label}</b>"
    return f"{header}\n\n{html.escape(body)}"


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
    phone = _format_phone(str(event.customer.get("phone", "")))
    phone_line = f"\n📱 <code>{html.escape(phone)}</code>" if phone else ""
    header = (
        f"<b>👤 {name_safe}</b> · <b>{event_label}</b> · {event.notify_type}"
        f"{phone_line}\n\n"
        "Lời chúc gợi ý (copy để gửi Zalo):"
    )

    wish_blocks = "\n\n".join(f"<pre>{html.escape(w)}</pre>" for w in wishes)

    return f"{header}\n\n{wish_blocks}"


def _format_phone(raw: str) -> str:
    """Chuẩn hoá SĐT để hiển thị.

    Google Sheets hay tự cắt số 0 đầu khi ô định dạng kiểu số
    (0917035969 → 917035969). Ca bị cắt cho ra chuỗi 9 số KHÔNG bắt đầu bằng 0,
    nên chỉ khi đó mới thêm lại '0'. Số đã đúng dạng text (còn số 0 đầu, dù chỉ
    9 số như '078489939') thì giữ nguyên — tránh biến thành '0078489939'.
    """
    p = raw.strip()
    if p.isdigit() and len(p) == 9 and not p.startswith("0"):
        p = "0" + p
    return p


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
