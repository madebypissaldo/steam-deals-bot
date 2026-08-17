"""Explicit entry point for the local Telegram long-polling bot."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import dotenv

from services.telegram import get_updates
from telegram.handlers import handle_update


LOGGER = logging.getLogger(__name__)
POLL_TIMEOUT_SECONDS = 30
RETRY_DELAY_SECONDS = 5


def run_bot() -> None:
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    offset = None
    LOGGER.info("Steam Deals Bot")
    LOGGER.info("Telegram bot iniciado.")
    LOGGER.info("Long polling ativo. Aguardando mensagens...")
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="telegram-update") as executor:
        try:
            while True:
                updates = get_updates(offset=offset, timeout=POLL_TIMEOUT_SECONDS)
                if updates is None:
                    LOGGER.warning("Falha temporária no polling; tentando novamente em %s segundos.", RETRY_DELAY_SECONDS)
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        offset = update_id + 1
                    LOGGER.info("Update recebido.")
                    executor.submit(_process_update, update)
        except KeyboardInterrupt:
            LOGGER.info("Bot encerrado.")


def _process_update(update: dict) -> None:
    try:
        handle_update(update)
    except Exception:
        LOGGER.exception("Erro ao processar update do Telegram.")


if __name__ == "__main__":
    run_bot()
