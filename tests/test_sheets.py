"""Tests for sheets.load_sent_log — header validation & dedup key parsing.

Không gọi Google API: _get_client được mock để trả worksheet giả.
"""

from unittest.mock import MagicMock, patch

import pytest

from src import sheets

HEADER = ["date_sent", "customer_name", "event_type", "notify_type", "year"]


def _fake_ws(values, records):
    ws = MagicMock()
    ws.get_all_values.return_value = values
    ws.get_all_records.return_value = records
    client = MagicMock()
    client.open_by_key.return_value.worksheet.return_value = ws
    return client


# Dùng patch.object trên chính object module `sheets` (không dùng chuỗi
# "src.sheets._get_client") để không bị lệ thuộc trạng thái sys.modules mà
# test_main.py thao túng (purge/re-import) — nếu không sẽ gọi mạng thật.


def test_load_sent_log_parses_keys():
    values = [HEADER, ["2026-07-14", "Lan", "birthday", "T-0", "2026"]]
    records = [{"date_sent": "2026-07-14", "customer_name": "Lan",
                "event_type": "birthday", "notify_type": "T-0", "year": "2026"}]
    with patch.object(sheets, "_get_client", return_value=_fake_ws(values, records)):
        result = sheets.load_sent_log()
    assert result == {("Lan", "birthday", "T-0", "2026")}


def test_load_sent_log_empty_sheet_returns_empty_set():
    with patch.object(sheets, "_get_client", return_value=_fake_ws([], [])):
        assert sheets.load_sent_log() == set()


def test_load_sent_log_raises_when_header_missing():
    """Header bị xoá → dòng dữ liệu đầu bị hiểu nhầm là header → phải BÁO LỖI,
    không được lặng lẽ trả rỗng (sẽ gây gửi lặp)."""
    # Không có dòng header; dòng đầu là dữ liệu thật.
    values = [["2026-07-14", "Lan", "birthday", "T-0", "2026"],
              ["2026-07-14", "Hoa", "birthday", "T-0", "2026"]]
    with patch.object(sheets, "_get_client", return_value=_fake_ws(values, [])):
        with pytest.raises(ValueError, match="sent_log"):
            sheets.load_sent_log()


def test_load_sent_log_tolerates_header_whitespace_and_extra_cols():
    values = [["date_sent", " customer_name ", "event_type", "notify_type", "year", "note"]]
    records = []
    with patch.object(sheets, "_get_client", return_value=_fake_ws(values, records)):
        assert sheets.load_sent_log() == set()
