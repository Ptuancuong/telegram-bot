"""Send messages to Telegram via Bot API."""

import requests

from src.config import DRY_RUN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_SEPARATOR = "─" * 50


def send_message(text: str) -> None:
    """Send an HTML-formatted message to the configured Telegram chat.

    In DRY_RUN mode, prints to stdout instead.
    """
    if DRY_RUN:
        print(f"[DRY_RUN] Telegram message:\n{text}\n{_SEPARATOR}")
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to send messages."
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
