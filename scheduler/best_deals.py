"""Daily Best Deals scheduler running independently from long polling."""

import logging
import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.best_deals import run_daily_scan
from storage import database
from telegram import protection


LOGGER = logging.getLogger(__name__)


def _timezone() -> ZoneInfo:
    name = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        LOGGER.warning("Timezone inválida %s; usando America/Sao_Paulo.", name)
        return ZoneInfo("America/Sao_Paulo")


def _scan_hour() -> int:
    try:
        return min(23, max(0, int(os.getenv("BEST_DEALS_SCAN_HOUR", "12"))))
    except ValueError:
        return 12


def should_scan(now: datetime) -> bool:
    return now.hour >= _scan_hour() and database.last_scan_date() != now.date().isoformat()


def run_if_due(now: datetime | None = None) -> bool:
    now = now or datetime.now(_timezone())
    if not should_scan(now):
        return False
    if not protection.acquire_background_slot():
        LOGGER.info("Best Deals scan aguardando capacidade global.")
        return False
    try:
        run_daily_scan()
    except Exception:
        LOGGER.exception("Best Deals scan não concluído; será tentado novamente mais tarde.")
        return False
    finally:
        protection.release_background_slot()
    database.mark_scan_complete(now.date().isoformat())
    return True


def _loop() -> None:
    while True:
        run_if_due()
        time.sleep(60)


def start() -> threading.Thread:
    thread = threading.Thread(target=_loop, name="best-deals-scheduler", daemon=True)
    thread.start()
    LOGGER.info("Scheduler de Best Deals iniciado.")
    return thread
