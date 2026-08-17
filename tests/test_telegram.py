"""Run a direct Telegram delivery test, without querying Steam."""

import logging

import dotenv

from services.telegram import send_message


dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


if __name__ == "__main__":
    sent = send_message("✅ Telegram integrado com sucesso!")
    raise SystemExit(0 if sent else 1)
