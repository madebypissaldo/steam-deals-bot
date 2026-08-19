"""Best Deal classification, deduplication and alert broadcasting."""

import logging
import os
import time
from typing import Callable

from services import steam
from services.telegram import send_message
from storage import database


LOGGER = logging.getLogger(__name__)
BROADCAST_DELAY_SECONDS = 0.05


def _int_setting(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        LOGGER.warning("Configuração inválida para %s; usando %s.", name, default)
        return default


def is_best_deal(deal: dict) -> bool:
    """Identify temporarily free paid products or exceptionally cheap sales."""
    final_cents = deal.get("final_cents")
    initial_cents = deal.get("initial_cents")
    discount = deal.get("discount_percent", 0)
    if not isinstance(final_cents, int) or not isinstance(discount, int):
        return False
    # A positive original price prevents permanently free products from qualifying.
    if (discount == 100 or final_cents == 0) and isinstance(initial_cents, int) and initial_cents > 0:
        return True
    if final_cents == 0:
        return False
    return discount >= _int_setting("BEST_DEALS_MIN_DISCOUNT", 90) and final_cents <= _int_setting("BEST_DEALS_MAX_PRICE", 10) * 100


def find_best_deals(deals: list[dict]) -> list[dict]:
    maximum = _int_setting("BEST_DEALS_MAX_NOTIFICATIONS", 10)
    candidates = [deal for deal in deals if is_best_deal(deal) and not database.was_notified(deal)]
    return _sort_and_limit(candidates, maximum)


def find_current_best_deals(deals: list[dict]) -> list[dict]:
    """Return current qualifying deals, including ones notified to older subscribers."""
    return _sort_and_limit([deal for deal in deals if is_best_deal(deal)], _int_setting("BEST_DEALS_MAX_NOTIFICATIONS", 10))


def _sort_and_limit(candidates: list[dict], maximum: int) -> list[dict]:
    candidates.sort(key=lambda deal: (deal["final_cents"] != 0, -deal["discount_percent"], deal["final_cents"]))
    return candidates[:maximum]


def format_best_deal(deal: dict) -> str:
    if deal["final_cents"] == 0:
        price = f"🎁 GRÁTIS\n📉 {deal['discount_percent']}% de desconto\n\n🏷️ Preço normal: {deal['initial_formatted']}"
    else:
        price = f"🏷️ {deal['initial_formatted']} → {deal['final_formatted']}\n📉 {deal['discount_percent']}% de desconto"
    return f"🔥 BEST DEAL\n\n🎮 {deal['name']}\n\n{price}"


def run_daily_scan(send: Callable[..., bool] = send_message) -> int:
    """Fetch once, notify opted-in users, and persist successful scan completion."""
    started_at = time.monotonic()
    LOGGER.info("Best Deals scan iniciado.")
    try:
        deals = steam.search_deals(limit=50, refresh=True)
        best_deals = find_best_deals(deals)
    except steam.SteamServiceError:
        LOGGER.exception("Best Deals scan falhou ao consultar Steam.")
        raise

    subscribers = database.active_subscribers()
    LOGGER.info("Promoções carregadas: %s. Best Deals novas: %s. Assinantes ativos: %s.", len(deals), len(best_deals), len(subscribers))
    sent = failures = 0
    for deal in best_deals:
        for subscriber in subscribers:
            if send(format_best_deal(deal), subscriber["chat_id"], {"inline_keyboard": [[{"text": "🎮 Abrir na Steam", "url": deal["url"]}]]}):
                sent += 1
            else:
                failures += 1
            # Keep broadcasts below Telegram's usual per-bot message rate.
            time.sleep(BROADCAST_DELAY_SECONDS)
        database.mark_notified(deal)
    LOGGER.info("Notificações enviadas: %s. Falhas de envio: %s. Best Deals scan concluído em %.2fs.", sent, failures, time.monotonic() - started_at)
    return len(best_deals)


def send_current_best_deals(chat_id: int | str, send: Callable[..., bool] = send_message) -> int:
    """Send today's qualifying deals once to a user who just opted in."""
    deals = steam.search_deals(limit=50)
    current_deals = find_current_best_deals(deals)
    for deal in current_deals:
        send(format_best_deal(deal), chat_id, {"inline_keyboard": [[{"text": "🎮 Abrir na Steam", "url": deal["url"]}]]})
        time.sleep(BROADCAST_DELAY_SECONDS)
    LOGGER.info("Best Deals atuais enviados ao chat_id=%s: %s.", chat_id, len(current_deals))
    return len(current_deals)
