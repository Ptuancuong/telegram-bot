"""Send messages to Telegram via Bot API."""

import requests

from src.config import DRY_RUN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

_SEPARATOR = "─" * 50


def send_message(text: str) -> None:
    """Send an HTML-formatted message to every configured Telegram chat.

    Gửi cùng một tin cho từng chat_id trong TELEGRAM_CHAT_IDS (một hoặc nhiều
    người nhận). In DRY_RUN mode, prints to stdout instead.
    """
    if DRY_RUN:
        recipients = ", ".join(TELEGRAM_CHAT_IDS) or "(chưa cấu hình)"
        print(f"[DRY_RUN] Telegram → {recipients}:\n{text}\n{_SEPARATOR}")
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to send messages."
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
