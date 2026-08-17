"""Measure Telegram HTTP latency without involving Steam."""

import logging
import time

import dotenv

from services.telegram import get_me, send_message


def measure(label: str, operation) -> bool:
    started_at = time.monotonic()
    result = operation()
    print(f"{label}: {time.monotonic() - started_at:.2f}s ({'ok' if result else 'failed'})")
    return result


if __name__ == "__main__":
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    get_me_ok = measure("getMe", get_me)
    message_ok = measure("sendMessage", lambda: send_message("✅ Diagnóstico de latência Telegram"))
    raise SystemExit(0 if get_me_ok and message_ok else 1)
