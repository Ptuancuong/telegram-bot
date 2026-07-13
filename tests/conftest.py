"""Cấu hình chung cho test.

Mặc định TẮT Gemini trong mọi test để:
  1. Các test template (Phase 1) vẫn xác định (deterministic), không phụ thuộc
     mạng — kể cả khi máy dev có GEMINI_API_KEY thật trong .env.
  2. Không có test nào vô tình gọi API thật.

Test nào cần bật AI (test_gemini) tự monkeypatch lại `config.USE_AI` /
`config.GEMINI_API_KEY`.
"""

import pytest

from src import config


@pytest.fixture(autouse=True)
def _disable_ai_by_default(monkeypatch):
    # Patch config attributes (cho module config đã import sẵn) ...
    monkeypatch.setattr(config, "USE_AI", False, raising=False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "", raising=False)
    # ... và cả env var, phòng test nào xoá/nạp lại src.config (vd test_main)
    # đọc lại từ môi trường — nếu .env có key thật thì vẫn không gọi mạng.
    monkeypatch.setenv("USE_AI", "0")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
