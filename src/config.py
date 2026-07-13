import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def today_vn() -> date:
    return datetime.now(_VN_TZ).date()


def tomorrow_vn() -> date:
    return today_vn() + timedelta(days=1)


DRY_RUN: bool = os.getenv("DRY_RUN", "0").strip().lower() in ("1", "true", "yes")

# .strip() guards against trailing newline/whitespace commonly introduced when
# copy-pasting values into GitHub Secrets or .env files (e.g. SHEET_ID becoming
# "...Vo\n" instead of "...Vo", which silently breaks Google API lookups).
SHEET_ID: str = os.getenv("SHEET_ID", "").strip()
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "").strip()
