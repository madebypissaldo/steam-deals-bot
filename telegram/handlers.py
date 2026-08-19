"""Routing for Telegram commands, text and inline-button callbacks."""

import logging
import math
import time
from typing import Any

from services import best_deals, steam
from services.telegram import answer_callback_query, edit_message_text, send_message
from telegram import keyboards, protection, states
from storage import database


LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 5
MAX_DEALS_PAGES = 5
MAX_DEALS_RESULTS = PAGE_SIZE * MAX_DEALS_PAGES
MENU_TEXT = "🎮 Steam Deals Bot\n\nO que deseja fazer?"


def _best_deals_text(enabled: bool) -> str:
    status = "✅ Ativos" if enabled else "❌ Desativados"
    return f"🔥 Best Deals\n\nReceba automaticamente promoções excepcionais encontradas pela pesquisa diária.\n\nAlertas: {status}"


def is_private_chat(chat: dict[str, Any]) -> bool:
    return chat.get("type") == "private"


def _user_id(payload: dict[str, Any], fallback: int | str) -> int | str:
    sender = payload.get("from")
    return sender.get("id", fallback) if isinstance(sender, dict) else fallback


def _rate_limit_message(reason: str) -> str:
    if reason == "active":
        return "🔎 Já existe uma pesquisa em andamento. Aguarde ela terminar."
    if reason == "global":
        return "⏳ O bot está atendendo muitas pesquisas. Aguarde alguns segundos e tente novamente."
    return "⏳ Muitas solicitações em pouco tempo. Aguarde alguns segundos e tente novamente."


def format_game(game: dict[str, Any]) -> str:
    return (
        f"🎮 {game['name']}\n\n"
        f"💰 Preço atual: {game['final_formatted']}\n"
        f"🏷️ Preço original: {game['initial_formatted']}\n"
        f"📉 Desconto: {game['discount_percent']}%\n\n"
        "🔗 Ver na Steam"
    )


def format_deals(title: str, games: list[dict[str, Any]], page: int) -> str:
    selected = games[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if not selected:
        return f"{title}\n\nNenhuma promoção encontrada agora."
    entries = [
        f"🎮 {game['name']}\n💰 {game['initial_formatted']} → {game['final_formatted']}\n📉 {game['discount_percent']}%"
        for game in selected
    ]
    return f"{title}\n\n" + "\n\n".join(entries)


def _edit_menu(chat_id: int | str, message_id: int) -> None:
    states.clear_state(chat_id)
    edit_message_text(chat_id, message_id, MENU_TEXT, keyboards.main_menu())


def _show_results(chat_id: int | str, message_id: int, title: str, kind: str, page: int = 0) -> None:
    state = states.get_state(chat_id) or {}
    games = state.get("results", [])
    total_pages = max(1, math.ceil(len(games) / PAGE_SIZE))
    states.set_state(chat_id, "results", results=games, title=title, kind=kind, page=page)
    edit_message_text(chat_id, message_id, format_deals(title, games, page), keyboards.results_keyboard(kind, page, total_pages))


def _search_deals(user_id: int | str, chat_id: int | str, message_id: int, title: str, kind: str, **filters: Any) -> None:
    started_at = time.monotonic()
    reason = protection.start_search(user_id)
    if reason:
        LOGGER.warning("Pesquisa recusada user_id=%s action=%s reason=%s.", user_id, kind, reason)
        edit_message_text(chat_id, message_id, _rate_limit_message(reason), keyboards.menu_button())
        return
    try:
        edit_message_text(chat_id, message_id, "🔎 Buscando promoções...")
        LOGGER.info("Pesquisa iniciada user_id=%s action=%s.", user_id, kind)
        games = steam.search_deals(limit=MAX_DEALS_RESULTS, **filters)
        states.set_state(chat_id, "results", results=games, title=title, kind=kind, page=0)
        _show_results(chat_id, message_id, title, kind)
        LOGGER.info("Pesquisa concluída user_id=%s action=%s results=%s duration=%.2fs.", user_id, kind, len(games), time.monotonic() - started_at)
    except (steam.SteamServiceError, KeyError, TypeError, ValueError):
        LOGGER.exception("Erro na pesquisa user_id=%s action=%s.", user_id, kind)
        edit_message_text(chat_id, message_id, "⚠️ Não foi possível concluir a solicitação agora. Tente novamente em alguns instantes.", keyboards.menu_button())
    finally:
        protection.finish_search(user_id)


def handle_message(message: dict[str, Any]) -> None:
    if not isinstance(message, dict):
        return
    started_at = time.monotonic()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    raw_text = message.get("text")
    if chat_id is None:
        return
    if not is_private_chat(chat):
        LOGGER.info("Mensagem ignorada de chat não privado chat_id=%s.", chat_id)
        return
    user_id = _user_id(message, chat_id)
    if not isinstance(raw_text, str):
        send_message("Use os botões do menu ou envie o nome de um jogo quando solicitado.", chat_id, keyboards.menu_button())
        return
    text = raw_text.strip()
    if text in {"/start", "/menu"}:
        states.clear_state(chat_id)
        send_message(MENU_TEXT, chat_id, keyboards.main_menu())
        return
    if text == "/help":
        send_message("Use /start e escolha uma opção do menu.", chat_id, keyboards.main_menu())
        return
    if (states.get_state(chat_id) or {}).get("state") != states.WAITING_GAME_SEARCH:
        send_message("Use /start para abrir o menu.", chat_id, keyboards.main_menu())
        return
    if not text:
        send_message("Informe o nome de um jogo para pesquisar.", chat_id, keyboards.menu_button())
        return
    if len(text) > 100:
        send_message("⚠️ O nome informado é muito longo.", chat_id, keyboards.menu_button())
        return
    reason = protection.start_search(user_id)
    if reason:
        LOGGER.warning("Pesquisa recusada user_id=%s action=name reason=%s.", user_id, reason)
        send_message(_rate_limit_message(reason), chat_id, keyboards.menu_button())
        return
    states.clear_state(chat_id)
    send_message(f'🔎 Procurando "{text}"...', chat_id)
    try:
        LOGGER.info("Pesquisa iniciada user_id=%s action=name.", user_id)
        game = steam.search_game(text)
        if not game:
            send_message("Jogo não encontrado. Tente outro nome.", chat_id, keyboards.search_menu())
            return
        send_message(format_game(game), chat_id, keyboards.deal_keyboard(game))
        LOGGER.info("Pesquisa concluída user_id=%s action=name duration=%.2fs.", user_id, time.monotonic() - started_at)
    except (steam.SteamServiceError, KeyError, TypeError, ValueError):
        LOGGER.exception("Erro na pesquisa user_id=%s action=name.", user_id)
        send_message("⚠️ Não foi possível concluir a solicitação agora. Tente novamente em alguns instantes.", chat_id, keyboards.menu_button())
    finally:
        protection.finish_search(user_id)


def handle_callback(callback: dict[str, Any]) -> None:
    if not isinstance(callback, dict):
        return
    started_at = time.monotonic()
    callback_id = callback.get("id")
    message = callback.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat") or {}
    if not isinstance(chat, dict):
        return
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    data = callback.get("data", "")
    if chat_id is None or message_id is None:
        return
    if not is_private_chat(chat):
        LOGGER.info("Callback ignorado de chat não privado chat_id=%s.", chat_id)
        return
    user_id = _user_id(callback, chat_id)
    if callback_id:
        answer_callback_query(callback_id)
    if not isinstance(data, str):
        LOGGER.warning("Callback inválido user_id=%s.", user_id)
        return
    action, _, value = data.partition(":")
    if action == "menu":
        if value == "search":
            edit_message_text(chat_id, message_id, "🔎 Como deseja pesquisar?", keyboards.search_menu())
        elif value == "deals":
            _search_deals(user_id, chat_id, message_id, "🔥 Maiores descontos", "deals")
        elif value == "under20":
            _search_deals(user_id, chat_id, message_id, "💸 Jogos até R$ 20", "under20", max_price=20)
        elif value == "discount80":
            _search_deals(user_id, chat_id, message_id, "📉 Desconto de 80% ou mais", "discount80", min_discount=80)
        elif value == "watchlist":
            edit_message_text(chat_id, message_id, "⭐ Watchlist\n\nEssa funcionalidade ainda está em desenvolvimento.", keyboards.menu_button())
        return
    if action == "bestdeals":
        if value == "menu":
            enabled = database.is_subscribed(user_id)
            edit_message_text(chat_id, message_id, _best_deals_text(enabled), keyboards.best_deals_menu(enabled))
        elif value == "subscribe":
            database.set_subscription(user_id, chat_id, True)
            edit_message_text(chat_id, message_id, "✅ Alertas de Best Deals ativados.\n\nVocê receberá uma mensagem quando encontrarmos uma oferta excepcional.", keyboards.best_deals_menu(True))
            reason = protection.start_search(user_id)
            if reason:
                LOGGER.info("Envio inicial de Best Deals adiado user_id=%s reason=%s.", user_id, reason)
                return
            try:
                best_deals.send_current_best_deals(chat_id)
            except steam.SteamServiceError:
                LOGGER.exception("Falha ao enviar Best Deals atuais user_id=%s.", user_id)
            finally:
                protection.finish_search(user_id)
        elif value == "unsubscribe":
            database.set_subscription(user_id, chat_id, False)
            edit_message_text(chat_id, message_id, "🔕 Alertas de Best Deals desativados.", keyboards.best_deals_menu(False))
        return
    if action == "search" and value == "name":
        states.set_state(chat_id, states.WAITING_GAME_SEARCH)
        edit_message_text(chat_id, message_id, "🔎 Digite o nome do jogo que deseja pesquisar:", keyboards.menu_button())
        return
    if action == "category" and value in steam.CATEGORY_GENRES:
        _search_deals(user_id, chat_id, message_id, f"🔎 Promoções: {steam.CATEGORY_GENRES[value]}", f"category-{value}", category=value)
        return
    if action == "category" and value in steam.UNSUPPORTED_CATEGORIES:
        edit_message_text(chat_id, message_id, "🚧 Essa categoria ainda não está disponível.", keyboards.unavailable_category_menu())
        return
    if action == "nav" and value == "main":
        _edit_menu(chat_id, message_id)
        return
    if action == "nav" and value == "categories":
        edit_message_text(chat_id, message_id, "🔎 Como deseja pesquisar?", keyboards.search_menu())
        return
    if action == "nav" and value == "noop":
        return
    if action == "page":
        _, _, page_text = value.partition(":")
        state = states.get_state(chat_id) or {}
        requested_page = int(page_text) if page_text.isdigit() else -1
        games = state.get("results", [])
        total_pages = max(1, math.ceil(len(games) / PAGE_SIZE))
        if state.get("kind") == value.split(":", 1)[0] and 0 <= requested_page < total_pages:
            if state.get("page") != requested_page:
                _show_results(chat_id, message_id, str(state["title"]), str(state["kind"]), requested_page)
        return
    if action == "watchlist":
        edit_message_text(chat_id, message_id, "⭐ Watchlist\n\nEssa funcionalidade ainda está em desenvolvimento.", keyboards.menu_button())
        return
    LOGGER.warning("Callback desconhecido user_id=%s.", user_id)
    LOGGER.info("Callback processado em: %.2fs.", time.monotonic() - started_at)


def handle_update(update: dict[str, Any]) -> None:
    if not isinstance(update, dict):
        return
    if isinstance(update.get("message"), dict):
        handle_message(update["message"])
    elif isinstance(update.get("callback_query"), dict):
        handle_callback(update["callback_query"])
