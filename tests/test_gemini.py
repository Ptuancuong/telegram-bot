"""Tests for gemini.py — Phase 2 wish generation.

Không gọi mạng thật: `requests.post` được mock. Kiểm:
  - Tắt cờ / thiếu key  -> None (fallback template)
  - Thành công          -> list câu chúc (parse theo ===)
  - HTTP/mạng lỗi       -> None (nuốt exception)
  - Output rỗng/lạ      -> None
  - build_message dùng câu AI khi có, và fallback khi None
  - Prompt chứa xưng hô + tên + dịp đúng
"""

from unittest.mock import MagicMock, patch

import pytest

from src import config, gemini
from src.events import Event
from src.messages import build_message


def _event(name="Lan", event_type="birthday", notify_type="T-0", year=2025,
           gender="Nữ", note=""):
    return Event(
        customer={"name": name, "gender": gender, "birth_date": "15/06/1990", "note": note},
        event_type=event_type,
        notify_type=notify_type,
        year=year,
    )


@pytest.fixture
def ai_on(monkeypatch):
    """Bật AI + key giả cho các test cần gọi Gemini.

    Ghi đè fixture autouse `_disable_ai_by_default` trong conftest.py (pytest chạy
    fixture autouse cùng scope trước fixture được yêu cầu tường minh).
    """
    monkeypatch.setattr(config, "USE_AI", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-3.1-flash-lite")


def _mock_response(text):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    }
    return resp


# ---------------------------------------------------------------------------
# Gate: tắt AI / thiếu key -> None (không gọi mạng)
# ---------------------------------------------------------------------------

def test_returns_none_when_ai_disabled(monkeypatch):
    monkeypatch.setattr(config, "USE_AI", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    with patch("src.gemini.requests.post") as post:
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None
        post.assert_not_called()


def test_returns_none_when_key_missing(monkeypatch):
    monkeypatch.setattr(config, "USE_AI", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with patch("src.gemini.requests.post") as post:
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None
        post.assert_not_called()


# ---------------------------------------------------------------------------
# Thành công: parse theo === , tối đa 3 câu
# ---------------------------------------------------------------------------

def test_parses_three_wishes(ai_on):
    text = "Chúc em Lan sinh nhật vui!\n===\nHappy birthday em Lan 🎂\n===\nMừng sinh nhật em nha 🎉"
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        wishes = gemini.generate_wishes(_event(), ("em", "anh"))
    assert wishes == [
        "Chúc em Lan sinh nhật vui!",
        "Happy birthday em Lan 🎂",
        "Mừng sinh nhật em nha 🎉",
    ]


def test_caps_at_three(ai_on):
    text = "\n===\n".join(f"Câu {i}" for i in range(6))
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        wishes = gemini.generate_wishes(_event(), ("em", "anh"))
    assert len(wishes) == 3


def test_fallback_split_on_blank_lines(ai_on):
    """Nếu model không dùng === thì tách theo dòng trống."""
    text = "Lời chúc một.\n\nLời chúc hai.\n\nLời chúc ba."
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        wishes = gemini.generate_wishes(_event(), ("em", "anh"))
    assert wishes == ["Lời chúc một.", "Lời chúc hai.", "Lời chúc ba."]


def test_strips_numbering_and_bullets(ai_on):
    text = "1. Chúc mừng\n===\n- Vui vẻ nhé\n===\n• Mạnh khoẻ"
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        wishes = gemini.generate_wishes(_event(), ("em", "anh"))
    assert wishes == ["Chúc mừng", "Vui vẻ nhé", "Mạnh khoẻ"]


# ---------------------------------------------------------------------------
# Lỗi -> None (nuốt exception)
# ---------------------------------------------------------------------------

def test_network_error_returns_none(ai_on):
    with patch("src.gemini.requests.post", side_effect=RuntimeError("boom")):
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None


def test_http_error_returns_none(ai_on):
    resp = MagicMock()
    resp.raise_for_status.side_effect = RuntimeError("429 quota")
    with patch("src.gemini.requests.post", return_value=resp):
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None


def test_bad_json_shape_returns_none(ai_on):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"unexpected": "shape"}
    with patch("src.gemini.requests.post", return_value=resp):
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None


def test_empty_output_returns_none(ai_on):
    with patch("src.gemini.requests.post", return_value=_mock_response("   \n  \n")):
        assert gemini.generate_wishes(_event(), ("em", "anh")) is None


# ---------------------------------------------------------------------------
# Prompt nội dung
# ---------------------------------------------------------------------------

def test_prompt_contains_salutation_name_and_occasion(ai_on):
    captured = {}

    def _capture(url, headers=None, json=None, timeout=None):
        captured["prompt"] = json["contents"][0]["parts"][0]["text"]
        return _mock_response("A\n===\nB")

    with patch("src.gemini.requests.post", side_effect=_capture):
        gemini.generate_wishes(_event(name="Hùng"), ("anh", "em"))

    p = captured["prompt"]
    assert "Hùng" in p
    assert '"anh"' in p and '"em"' in p
    assert "sinh nhật" in p


def test_prompt_tet_am_includes_lunar_year(ai_on):
    captured = {}

    def _capture(url, headers=None, json=None, timeout=None):
        captured["prompt"] = json["contents"][0]["parts"][0]["text"]
        return _mock_response("A\n===\nB")

    with patch("src.gemini.requests.post", side_effect=_capture):
        gemini.generate_wishes(_event(event_type="tet_am", year=2025), ("em", "anh"))

    assert "Ất Tỵ" in captured["prompt"]


def test_request_uses_configured_model_and_key(ai_on):
    captured = {}

    def _capture(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return _mock_response("A\n===\nB")

    with patch("src.gemini.requests.post", side_effect=_capture):
        gemini.generate_wishes(_event(), ("em", "anh"))

    assert "gemini-3.1-flash-lite:generateContent" in captured["url"]
    # Key đi qua header, không lọt vào URL (tránh rò rỉ qua chuỗi lỗi HTTP).
    assert captured["headers"] == {"x-goog-api-key": "test-key"}
    assert "test-key" not in captured["url"]


# ---------------------------------------------------------------------------
# build_message tích hợp: dùng AI khi có, fallback khi None
# ---------------------------------------------------------------------------

def test_build_message_uses_ai_wishes(ai_on):
    text = "Chúc em Lan sinh nhật vui 🎂\n===\nHappy birthday em nha 🎉"
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        msg = build_message(_event(name="Lan"), ("em", "anh"))
    assert "Chúc em Lan sinh nhật vui" in msg
    assert "<pre>" in msg
    # Header vẫn có tên + nhãn dịp
    assert "Lan" in msg and "Sinh nhật" in msg


def test_build_message_falls_back_to_template_on_error(ai_on):
    with patch("src.gemini.requests.post", side_effect=RuntimeError("boom")):
        msg = build_message(_event(name="Lan"), ("em", "anh"))
    # Vẫn có 2–3 khối <pre> từ template, không rỗng
    import re
    blocks = re.findall(r"<pre>.*?</pre>", msg, re.DOTALL)
    assert 2 <= len(blocks) <= 3


def test_build_message_escapes_ai_html(ai_on):
    """Câu chúc AI chứa ký tự HTML phải được escape trong <pre>."""
    text = "Chúc <b>em</b> & bạn 🎂\n===\nVui nhé"
    with patch("src.gemini.requests.post", return_value=_mock_response(text)):
        msg = build_message(_event(), ("em", "anh"))
    assert "&lt;b&gt;" in msg and "&amp;" in msg
    assert "<b>em</b> &" not in msg
