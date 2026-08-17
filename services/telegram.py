"""Small, isolated client for Telegram notification delivery."""

import logging
import os
import json
import time
import threading
from collections.abc import Mapping
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"
REQUEST_TIMEOUT_SECONDS = 10
CONNECT_TIMEOUT_SECONDS = 5
_polling_session = requests.Session()
_api_session = requests.Session()
_api_session_lock = threading.Lock()


def _request(method: str, data: dict[str, Any], timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    """Call Telegram without ever logging credentials or message contents."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        LOGGER.error("Telegram request was skipped: TELEGRAM_BOT_TOKEN is not configured.")
        return None
    started_at = time.monotonic()
    LOGGER.info("Telegram %s iniciado.", method)
    try:
        if method == "getUpdates":
            response = _polling_session.post(
                TELEGRAM_API_URL.format(token=token, method=method),
                data=data,
                timeout=(CONNECT_TIMEOUT_SECONDS, timeout),
            )
        else:
            # requests.Session is not thread-safe. Serializing only outgoing API
            # calls lets all handler workers share keep-alive connections while
            # long polling continues independently on its own session.
            with _api_session_lock:
                response = _api_session.post(
                    TELEGRAM_API_URL.format(token=token, method=method),
                    data=data,
                    timeout=(CONNECT_TIMEOUT_SECONDS, timeout),
                )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.Timeout:
        LOGGER.error("Telegram %s timed out after %s seconds.", method, timeout)
    except requests.exceptions.ConnectionError:
        LOGGER.error("Telegram %s failed: unable to connect to the API.", method)
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unknown"
        payload = {}
        if error.response is not None:
            try:
                payload = error.response.json()
            except ValueError:
                pass
        description = payload.get("description", "não informado")
        if method == "editMessageText" and "message is not modified" in description.casefold():
            LOGGER.info("Telegram editMessageText sem alterações; operação ignorada.")
            return {"ok": True}
        LOGGER.error(
            "Telegram %s falhou: HTTP %s, error_code=%s, description=%r.",
            method, status_code, payload.get("error_code", status_code), description,
        )
    except (requests.exceptions.RequestException, ValueError) as error:
        LOGGER.error("Telegram %s failed (%s).", method, type(error).__name__)
    else:
        if payload.get("ok"):
            elapsed = time.monotonic() - started_at
            if method == "getUpdates":
                LOGGER.info("Long polling getUpdates retornou após %.2fs (HTTP %s).", elapsed, response.status_code)
            else:
                LOGGER.info("Telegram %s concluído em %.2fs (HTTP %s).", method, elapsed, response.status_code)
            return payload
        LOGGER.error("Telegram %s was rejected by the API.", method)
    return None


def send_message(message: str, chat_id: int | str | None = None, reply_markup: dict | None = None) -> bool:
    """Send *message* to the configured Telegram chat.

    Failures are logged and reported as ``False`` so notification delivery never
    interrupts the Steam price lookup.
    """
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not chat_id:
        LOGGER.error(
            "Telegram notification was skipped: TELEGRAM_BOT_TOKEN or "
            "TELEGRAM_CHAT_ID is not configured."
        )
        return False

    data: dict[str, Any] = {"chat_id": chat_id, "text": message}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return _request("sendMessage", data) is not None


def edit_message_text(chat_id: int | str, message_id: int, text: str, reply_markup: dict | None = None) -> bool:
    data: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return _request("editMessageText", data) is not None


def answer_callback_query(callback_query_id: str, text: str | None = None) -> bool:
    data: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
    return _request("answerCallbackQuery", data) is not None


def get_updates(offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]] | None:
    data: dict[str, Any] = {"timeout": timeout, "allowed_updates": json.dumps(["message", "callback_query"])}
    if offset is not None:
        data["offset"] = offset
    payload = _request("getUpdates", data, timeout=timeout + 10)
    return payload.get("result", []) if payload else None


def get_me() -> bool:
    """Verify API connectivity using the same outgoing HTTP session as the bot."""
    return _request("getMe", {}) is not None


def send_deal(game: Mapping[str, Any], app_id: int | str) -> bool:
    """Format a Steam game deal and deliver it through Telegram."""
    price = game.get("price_overview", {})
    name = game.get("name", "Jogo não identificado")
    initial_price = price.get("initial_formatted", "Preço original indisponível")
    final_price = price.get("final_formatted", "Preço promocional indisponível")
    discount = price.get("discount_percent", "Desconto indisponível")
    store_url = f"https://store.steampowered.com/app/{app_id}/"

    message = (
        "🔥 Nova promoção encontrada!\n\n"
        f"🎮 {name}\n\n"
        f"💰 De: {initial_price}\n"
        f"🏷️ Por: {final_price}\n"
        f"📉 Desconto: {discount}%\n\n"
        f"🔗 {store_url}"
    )
    return send_message(message)
