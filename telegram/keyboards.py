"""Inline keyboard builders."""


def main_menu() -> dict:
    return {"inline_keyboard": [
        [{"text": "🔥 Maiores descontos", "callback_data": "menu:deals"}, {"text": "🔎 Pesquisar jogo", "callback_data": "menu:search"}],
        [{"text": "💸 Até R$ 20", "callback_data": "menu:under20"}, {"text": "📉 80% ou mais", "callback_data": "menu:discount80"}],
        [{"text": "🔔 Alertas Best Deals", "callback_data": "bestdeals:menu"}],
        [{"text": "⭐ Minha Watchlist", "callback_data": "menu:watchlist"}],
    ]}


def search_menu() -> dict:
    return {"inline_keyboard": [
        [{"text": "✍️ Por nome", "callback_data": "search:name"}],
        [{"text": "🎯 Ação", "callback_data": "category:action"}, {"text": "🧙 RPG", "callback_data": "category:rpg"}],
        [{"text": "🏎️ Corrida", "callback_data": "category:racing"}, {"text": "🔫 FPS", "callback_data": "category:fps"}],
        [{"text": "🧠 Estratégia", "callback_data": "category:strategy"}, {"text": "🏕️ Survival", "callback_data": "category:survival"}],
        [{"text": "👻 Terror", "callback_data": "category:horror"}, {"text": "🕹️ Indie", "callback_data": "category:indie"}],
        [{"text": "⬅️ Voltar", "callback_data": "nav:main"}],
    ]}


def menu_button() -> dict:
    return {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "nav:main"}]]}


def unavailable_category_menu() -> dict:
    return {"inline_keyboard": [
        [{"text": "⬅️ Categorias", "callback_data": "nav:categories"}],
        [{"text": "🏠 Menu", "callback_data": "nav:main"}],
    ]}


def best_deals_menu(enabled: bool) -> dict:
    action = {"text": "🔕 Desativar alertas", "callback_data": "bestdeals:unsubscribe"} if enabled else {"text": "🔔 Ativar alertas", "callback_data": "bestdeals:subscribe"}
    return {"inline_keyboard": [[action], [{"text": "⬅️ Voltar", "callback_data": "nav:main"}]]}


def deal_keyboard(game: dict) -> dict:
    return {"inline_keyboard": [
        [{"text": "🎮 Abrir na Steam", "url": game["url"]}],
        [{"text": "⭐ Adicionar à Watchlist", "callback_data": f"watchlist:add:{game['app_id']}"}],
        [{"text": "🏠 Menu", "callback_data": "nav:main"}],
    ]}


def results_keyboard(kind: str, page: int, total_pages: int) -> dict:
    row = []
    if page > 0:
        row.append({"text": "◀️ Anterior", "callback_data": f"page:{kind}:{page - 1}"})
    row.append({"text": f"{page + 1}/{total_pages}", "callback_data": "nav:noop"})
    if page + 1 < total_pages:
        row.append({"text": "Próxima ▶️", "callback_data": f"page:{kind}:{page + 1}"})
    return {"inline_keyboard": [row, [{"text": "🏠 Menu", "callback_data": "nav:main"}]]}
