"""Additional tests for messages.py — variant count, headers, lunar year names,
all event_type × notify_type combinations, Xung capitalisation."""

import re

import pytest

from src.events import Event
from src.lunar import lunar_year_name
from src.messages import build_message


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _event(name: str = "Lan", event_type: str = "birthday",
           notify_type: str = "T-0", year: int = 2025) -> Event:
    return Event(
        customer={"name": name, "gender": "Nam", "birth_date": "15/06/1990"},
        event_type=event_type,
        notify_type=notify_type,
        year=year,
    )


# ---------------------------------------------------------------------------
# _lunar_year_name: can-chi cycle
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("solar_year, expected", [
    (2023, "Quý Mão"),
    (2024, "Giáp Thìn"),
    (2026, "Bính Ngọ"),
    (2027, "Đinh Mùi"),
    (2030, "Canh Tuất"),
    (2034, "Giáp Dần"),   # 10-cycle wrap for Can
])
def test_lunar_year_name(solar_year: int, expected: str):
    assert lunar_year_name(solar_year) == expected


def test_lunar_year_name_snake_year():
    """Regression for BUG-001: Snake chi must be 'Tỵ' (U+1EF5), not 'Tị'.

    Affects all Snake years (2025 Ất Tỵ, 2013 Quý Tỵ, ...).
    """
    assert lunar_year_name(2025) == "Ất Tỵ"
    assert lunar_year_name(2013) == "Quý Tỵ"


# ---------------------------------------------------------------------------
# build_message: 2–3 <pre> blocks always produced
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event_type", ["birthday", "tet_duong", "tet_am"])
def test_variant_count_2_or_3(event_type: str):
    """T-0 (đúng ngày) phải sinh đúng 2–3 khối <pre>…</pre> lời chúc."""
    # Run several times because of randomness
    for _ in range(20):
        msg = build_message(_event(event_type=event_type, notify_type="T-0"), ("em", "anh"))
        blocks = re.findall(r"<pre>.*?</pre>", msg, re.DOTALL)
        assert 2 <= len(blocks) <= 3, (
            f"{event_type}/T-0: expected 2–3 blocks, got {len(blocks)}"
        )


# ---------------------------------------------------------------------------
# T-1 (báo trước 1 ngày): tin nhắc ngắn, KHÔNG kèm khối lời chúc <pre>
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event_type", ["birthday", "tet_duong", "tet_am"])
def test_t1_is_short_reminder_without_wish_blocks(event_type: str):
    """T-1 chỉ là tin nhắc, không có <pre> và không có mục 'Lời chúc gợi ý'."""
    msg = build_message(_event(event_type=event_type, notify_type="T-1"), ("em", "anh"))
    assert "<pre>" not in msg
    assert "Lời chúc gợi ý" not in msg
    assert "Ngày mai" in msg
    assert "Nhắc trước" in msg


def test_t1_reminder_contains_name_and_occasion():
    msg = build_message(
        _event(name="Nguyễn Văn A", event_type="birthday", notify_type="T-1"), ("anh", "em")
    )
    assert "Nguyễn Văn A" in msg
    assert "sinh nhật" in msg


def test_t1_reminder_skips_gemini(monkeypatch):
    """T-1 không được gọi Gemini (tin nhắc là text cố định)."""
    import src.messages as messages

    def _boom(*args, **kwargs):
        raise AssertionError("generate_wishes không được gọi cho T-1")

    monkeypatch.setattr(messages, "generate_wishes", _boom)
    # Không raise ⇒ đã bỏ qua Gemini
    build_message(_event(notify_type="T-1"), ("em", "anh"))


# ---------------------------------------------------------------------------
# build_message: header structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event_type,notify_type,label", [
    ("birthday", "T-0", "Sinh nhật"),
    ("birthday", "T-1", "Sinh nhật"),
    ("tet_duong", "T-0", "Tết Dương lịch"),
    ("tet_duong", "T-1", "Tết Dương lịch"),
    ("tet_am", "T-0", "Tết Âm lịch"),
    ("tet_am", "T-1", "Tết Âm lịch"),
])
def test_header_contains_label(event_type, notify_type, label):
    """Cả T-0 lẫn T-1 đều có nhãn dịp trong tiêu đề."""
    msg = build_message(_event(event_type=event_type, notify_type=notify_type), ("em", "anh"))
    assert label in msg


def test_header_contains_bold_name():
    msg = build_message(_event(name="TestName"), ("em", "anh"))
    assert "<b>" in msg
    assert "TestName" in msg


def test_header_shows_phone_when_present():
    """Có cột phone → hiện số trong tiêu đề, bọc <code> để chạm-copy."""
    ev = Event(
        customer={"name": "Lan", "gender": "Nữ", "birth_date": "15/06/1990",
                  "phone": "0901234567"},
        event_type="birthday", notify_type="T-0", year=2025,
    )
    msg = build_message(ev, ("em", "anh"))
    assert "📱" in msg
    assert "<code>0901234567</code>" in msg
    # Số nằm ở phần tiêu đề, trước các khối lời chúc
    assert msg.index("0901234567") < msg.index("<pre>")


def test_phone_restores_dropped_leading_zero():
    """SĐT bị Google Sheets cắt số 0 (9 chữ số) → tự thêm lại '0' khi hiển thị."""
    ev = Event(
        customer={"name": "Lan", "birth_date": "15/06/1990", "phone": "917035969"},
        event_type="birthday", notify_type="T-0", year=2025,
    )
    msg = build_message(ev, ("em", "anh"))
    assert "<code>0917035969</code>" in msg


def test_phone_9digits_with_leading_zero_not_double_prefixed():
    """Số 9 chữ số nhưng ĐÃ có 0 đầu (vd 078489939) → giữ nguyên, không thêm 0."""
    ev = Event(
        customer={"name": "Lan", "birth_date": "15/06/1990", "phone": "078489939"},
        event_type="birthday", notify_type="T-0", year=2025,
    )
    msg = build_message(ev, ("em", "anh"))
    assert "<code>078489939</code>" in msg
    assert "0078489939" not in msg


def test_phone_kept_when_already_has_zero():
    """SĐT lưu đúng dạng text (10 số, có 0 đầu) → giữ nguyên, không thêm nữa."""
    ev = Event(
        customer={"name": "Lan", "birth_date": "15/06/1990", "phone": "0917035969"},
        event_type="birthday", notify_type="T-0", year=2025,
    )
    msg = build_message(ev, ("em", "anh"))
    assert "<code>0917035969</code>" in msg
    assert "00917035969" not in msg


def test_header_no_phone_line_when_absent():
    """Không có phone (hoặc rỗng) → không có dòng 📱, tiêu đề như cũ."""
    msg = build_message(_event(name="Lan"), ("em", "anh"))
    assert "📱" not in msg
    ev_empty = Event(
        customer={"name": "Lan", "birth_date": "15/06/1990", "phone": "   "},
        event_type="birthday", notify_type="T-0", year=2025,
    )
    assert "📱" not in build_message(ev_empty, ("em", "anh"))


# ---------------------------------------------------------------------------
# Salutation substitution in wish bodies
# ---------------------------------------------------------------------------

def test_salutation_cal_substituted():
    """All {cal} placeholders replaced with the given salutation."""
    msg = build_message(_event(), ("chị", "em"))
    # {cal} must not remain literally in wish blocks
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{cal}" not in block
        assert "chị" in block  # at least one occurrence across blocks or in at least one


def test_salutation_xung_substituted():
    msg = build_message(_event(), ("em", "anh"))
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{xung}" not in block
        assert "{Xung}" not in block


def test_xung_capitalised_at_sentence_start():
    """When {Xung} is used, its first letter should be uppercase."""
    # Run many times to hit templates that use {Xung}
    found_capitalised = False
    for _ in range(50):
        msg = build_message(_event(), ("em", "anh"))
        # Look for capitalised xung values in wish blocks
        if re.search(r"<pre>Anh", msg) or re.search(r"<pre>Em", msg) or re.search(r"<pre>Cháu", msg):
            found_capitalised = True
            break
    assert found_capitalised, "No capitalised Xung found in 50 attempts"


# ---------------------------------------------------------------------------
# {year} substitution in tet_duong templates
# ---------------------------------------------------------------------------

def test_year_substituted_tet_duong():
    msg = build_message(_event(event_type="tet_duong", notify_type="T-0", year=2026), ("anh", "em"))
    assert "2026" in msg
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{year}" not in block


# ---------------------------------------------------------------------------
# {lunar_year} substitution in tet_am templates
# ---------------------------------------------------------------------------

def test_lunar_year_substituted_tet_am():
    # 2024 = Giáp Thìn (not a snake year — avoids BUG-001)
    msg = build_message(_event(event_type="tet_am", notify_type="T-0", year=2024), ("em", "anh"))
    assert "Giáp Thìn" in msg
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{lunar_year}" not in block


# ---------------------------------------------------------------------------
# HTML escape in header — name with HTML special chars
# ---------------------------------------------------------------------------

def test_html_escape_in_header_name():
    msg = build_message(_event(name="<script>"), ("em", "anh"))
    assert "<script>" not in msg.split("\n")[0]  # header line is first
    assert "&lt;script&gt;" in msg


def test_ampersand_escaped():
    msg = build_message(_event(name="Tom & Jerry"), ("em", "anh"))
    assert "Tom & Jerry" not in msg
    assert "Tom &amp; Jerry" in msg


# ---------------------------------------------------------------------------
# Name with curly braces: brace injection prevention already tested
# but also check that {name} is NOT literal in output
# ---------------------------------------------------------------------------

def test_name_placeholder_not_literal_in_output():
    msg = build_message(_event(name="Alice"), ("em", "anh"))
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{name}" not in block


# ---------------------------------------------------------------------------
# Wish text for birthday does NOT contain {year} literal
# ---------------------------------------------------------------------------

def test_birthday_no_year_placeholder_leaked():
    msg = build_message(_event(event_type="birthday", notify_type="T-0"), ("em", "anh"))
    for block in re.findall(r"<pre>(.*?)</pre>", msg, re.DOTALL):
        assert "{year}" not in block
