"""Tests for the template engine: HTML escaping and brace-injection safety."""

from src.events import Event
from src.messages import build_message


def _event(name: str, event_type="birthday", notify_type="T-0", year=2025) -> Event:
    return Event(
        customer={"name": name, "gender": "Nam", "birth_date": "15/06/1990"},
        event_type=event_type,
        notify_type=notify_type,
        year=year,
    )


def test_html_is_escaped():
    msg = build_message(_event("<b>Hacker</b>"), ("em", "anh"))
    assert "<b>Hacker</b>" not in msg
    assert "&lt;b&gt;Hacker&lt;/b&gt;" in msg


def test_brace_placeholder_in_name_is_not_expanded():
    """A name containing {year} must stay literal, not become '2025'.

    Birthday templates never reference {year}, so the only way '2025' could
    appear is via injection through the name into the wish body.
    """
    msg = build_message(_event("{year}"), ("em", "anh"))
    assert "{year}" in msg
    assert "2025" not in msg


def test_unknown_placeholder_in_name_does_not_crash():
    # Would raise KeyError under str.format(); must render cleanly now.
    msg = build_message(_event("Nguyen {foo} A"), ("em", "anh"))
    assert "Nguyen {foo} A" in msg


def test_name_substituted_into_wish():
    msg = build_message(_event("Lan"), ("em", "anh"))
    assert "Lan" in msg
    assert "<pre>" in msg
