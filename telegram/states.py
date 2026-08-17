"""In-memory conversational state; replaceable by Redis or a database later."""

import threading

WAITING_GAME_SEARCH = "waiting_game_search"
user_states: dict[str, dict[str, object]] = {}
_lock = threading.RLock()


def set_state(chat_id: int | str, state: str, **data: object) -> None:
    with _lock:
        user_states[str(chat_id)] = {"state": state, **data}


def get_state(chat_id: int | str) -> dict[str, object] | None:
    with _lock:
        state = user_states.get(str(chat_id))
        return state.copy() if state else None


def clear_state(chat_id: int | str) -> None:
    with _lock:
        user_states.pop(str(chat_id), None)
