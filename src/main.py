"""Orchestrator: load → scan → render → send → log."""

from src.config import DRY_RUN, today_vn
from src.events import scan_events
from src.messages import build_message
from src.salutation import get_salutation
from src.sheets import append_sent_rows, load_customers, load_sent_log
from src.telegram import send_message


def main() -> None:
    today = today_vn()
    print(f"[INFO] Starting customer care bot — {today} — DRY_RUN={DRY_RUN}")

    customers = load_customers()
    print(f"[INFO] Active customers: {len(customers)}")

    sent_log = load_sent_log()
    print(f"[INFO] Sent log entries: {len(sent_log)}")

    events = scan_events(customers, sent_log)
    print(f"[INFO] Events to notify: {len(events)}")

    if not events:
        print("[INFO] Nothing to send today.")
        return

    new_log_rows = []

    for event in events:
        sal = get_salutation(event.customer)
        text = build_message(event, sal)
        send_message(text)

        name = str(event.customer.get("name", ""))
        print(f"[INFO] Sent → {name} | {event.event_type} | {event.notify_type} | {event.year}")

        if not DRY_RUN:
            new_log_rows.append(
                {
                    "date_sent": today.isoformat(),
                    "customer_name": name,
                    "event_type": event.event_type,
                    "notify_type": event.notify_type,
                    "year": event.year,
                }
            )

    if new_log_rows:
        append_sent_rows(new_log_rows)
        print(f"[INFO] Logged {len(new_log_rows)} rows to sent_log.")

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
