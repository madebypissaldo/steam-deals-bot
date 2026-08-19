"""Steam Store API access, independent from any user interface."""

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 15
FEATURED_DEALS_CACHE_TTL_SECONDS = 300
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "games_appid.json"
CATEGORY_GENRES = {
    "action": "Ação", "rpg": "RPG", "racing": "Corrida",
    "strategy": "Estratégia", "indie": "Indie",
}
UNSUPPORTED_CATEGORIES = {"fps", "survival", "horror"}
_thread_local = threading.local()
_cache_lock = threading.Lock()
_featured_deals_cache: dict[str, Any] = {"games": None, "timestamp": 0.0}


class SteamServiceError(RuntimeError):
    """A recoverable Steam Store API error."""


def _session() -> requests.Session:
    """Keep HTTP connections alive within each worker thread."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session


def _request_json(url: str, **params: Any) -> dict[str, Any]:
    started_at = time.monotonic()
    try:
        response = _session().get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        LOGGER.info("Consulta Steam concluída em %.2fs.", time.monotonic() - started_at)
        return payload
    except (requests.exceptions.RequestException, ValueError) as error:
        LOGGER.error("Erro ao consultar Steam (%s).", type(error).__name__)
        raise SteamServiceError("Steam indisponível no momento.") from error


def _games_index() -> list[dict[str, Any]]:
    with DATA_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def find_game_id(name: str) -> int | None:
    """Find an exact game title first, then a single partial match."""
    query = name.strip().casefold()
    if not query:
        return None
    games = _games_index()
    for game in games:
        if game["name"].casefold() == query:
            return game["appid"]
    for game in games:
        if query in game["name"].casefold():
            return game["appid"]
    return None


def get_game_details(app_id: int | str) -> dict[str, Any] | None:
    payload = _request_json(
        "https://store.steampowered.com/api/appdetails",
        appids=app_id, cc="br", l="portuguese", key=os.getenv("STEAM_API_KEY", ""),
    )
    return payload.get(str(app_id), {}).get("data")


def search_game(name: str) -> dict[str, Any] | None:
    LOGGER.info("Consulta Steam iniciada: pesquisa por nome.")
    app_id = find_game_id(name)
    return game_from_details(app_id, get_game_details(app_id)) if app_id else None


def game_from_details(app_id: int | str, data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    price = data.get("price_overview") or {}
    return {
        "app_id": app_id,
        "name": data.get("name", "Jogo não identificado"),
        "initial_formatted": price.get("initial_formatted", "Indisponível"),
        "initial_cents": price.get("initial"),
        "final_formatted": price.get("final_formatted", "Indisponível"),
        "final_cents": price.get("final"),
        "discount_percent": price.get("discount_percent", 0),
        "short_description": data.get("short_description", "Description not found"),
        "genres": {genre.get("description", "").casefold() for genre in data.get("genres", [])},
        "url": f"https://store.steampowered.com/app/{app_id}/",
    }


def search_deals(
    min_discount: int | None = None,
    max_price: float | None = None,
    category: str | None = None,
    limit: int = 10,
    refresh: bool = False,
) -> list[dict[str, Any]]:
    """Return filtered games from Steam's real featured-specials feed."""
    started_at = time.monotonic()
    games = _get_featured_deals(refresh=refresh)
    filtered = []
    expected_genre = CATEGORY_GENRES.get(category, "").casefold() if category else None
    for game in games:
        if min_discount is not None and game["discount_percent"] < min_discount:
            continue
        if max_price is not None and (game["final_cents"] is None or game["final_cents"] > max_price * 100):
            continue
        if expected_genre and expected_genre not in game["genres"]:
            continue
        filtered.append(game)
    filtered.sort(key=lambda game: game["discount_percent"], reverse=True)
    LOGGER.info("Consulta de promoções concluída em %.2fs.", time.monotonic() - started_at)
    return filtered[:limit]


def _get_featured_deals(refresh: bool = False) -> list[dict[str, Any]]:
    now = time.monotonic()
    with _cache_lock:
        cached_games = _featured_deals_cache["games"]
        if not refresh and cached_games is not None and now - _featured_deals_cache["timestamp"] < FEATURED_DEALS_CACHE_TTL_SECONDS:
            LOGGER.info("Cache de promoções utilizado.")
            return cached_games

    LOGGER.info("Consulta Steam iniciada: promoções em destaque.")
    payload = _request_json("https://store.steampowered.com/api/featuredcategories", cc="br", l="portuguese")
    items = payload.get("specials", {}).get("items", [])
    app_ids = [item.get("id") for item in items[:50] if item.get("id")]

    def load_game(app_id: int) -> dict[str, Any] | None:
        return game_from_details(app_id, get_game_details(app_id))

    # appdetails calls are independent; a small pool avoids blocking on 50 serial requests.
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="steam") as executor:
        loaded_games = list(executor.map(load_game, app_ids))
    games = []
    for game in loaded_games:
        if not game or game["discount_percent"] <= 0:
            continue
        games.append(game)
    with _cache_lock:
        _featured_deals_cache["games"] = games
        _featured_deals_cache["timestamp"] = time.monotonic()
    return games
