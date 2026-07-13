"""Google Sheets auth + data access."""

import json
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from src.config import (
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_CREDENTIALS_JSON,
    SHEET_ID,
)

# 'spreadsheets' alone grants read+write on the target sheet opened by key.
# 'drive' scopes would only be needed to enumerate files (openall), which we
# never do — keep least privilege.
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_client() -> gspread.Client:
    if GOOGLE_CREDENTIALS_JSON:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    elif GOOGLE_CREDENTIALS_FILE:
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=_SCOPES)
    else:
        raise ValueError(
            "No Google credentials configured. "
            "Set GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS_FILE."
        )
    return gspread.authorize(creds)


def load_customers() -> list[dict[str, Any]]:
    """Return active customer rows from the 'customers' tab."""
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet("customers")
    records = ws.get_all_records()
    return [r for r in records if str(r.get("active", "")).upper() == "TRUE"]


def load_sent_log() -> set[tuple[str, str, str, str]]:
    """Return a set of (customer_name, event_type, notify_type, year) strings."""
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet("sent_log")
    records = ws.get_all_records()
    return {
        (
            str(r.get("customer_name", "")),
            str(r.get("event_type", "")),
            str(r.get("notify_type", "")),
            str(r.get("year", "")),
        )
        for r in records
    }


def append_sent_rows(rows: list[dict]) -> None:
    """Append rows to 'sent_log'. Each dict needs keys:
    date_sent, customer_name, event_type, notify_type, year.
    """
    if not rows:
        return
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet("sent_log")
    for row in rows:
        ws.append_row(
            [
                row["date_sent"],
                row["customer_name"],
                row["event_type"],
                row["notify_type"],
                str(row["year"]),
            ],
            value_input_option="USER_ENTERED",
        )
