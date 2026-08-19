import unittest
from unittest.mock import patch

from telegram import protection, states
from telegram.handlers import PAGE_SIZE, format_deals, format_game, handle_callback, handle_message


GAME = {
    "app_id": 1091500, "name": "Cyberpunk 2077", "initial_formatted": "R$ 199,90",
    "final_formatted": "R$ 99,95", "final_cents": 9995, "discount_percent": 50,
    "genres": {"ação"}, "url": "https://store.steampowered.com/app/1091500/",
}


class HandlerFormattingTests(unittest.TestCase):
    def setUp(self):
        protection.reset_for_tests()
        states.user_states.clear()
    def test_format_game_includes_price_and_discount(self):
        text = format_game(GAME)
        self.assertIn("Cyberpunk 2077", text)
        self.assertIn("R$ 99,95", text)
        self.assertIn("50%", text)

    def test_format_deals_only_returns_current_page(self):
        games = [dict(GAME, name=f"Jogo {number}") for number in range(6)]
        text = format_deals("Ofertas", games, 1)
        self.assertIn("Jogo 5", text)
        self.assertNotIn("Jogo 0", text)

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    def test_callback_uses_callback_query_id_not_chat_id(self, edit_message, answer_callback):
        handle_callback({
            "id": "callback-id-123",
            "data": "menu:search",
            "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42},
        })
        answer_callback.assert_called_once_with("callback-id-123")
        edit_message.assert_called_once()

    @patch("telegram.handlers.send_message")
    def test_start_is_public_for_private_chat(self, send_message):
        handle_message({"chat": {"id": 999, "type": "private"}, "from": {"id": 111}, "text": "/start"})
        send_message.assert_called_once()

    @patch("telegram.handlers.send_message")
    @patch("telegram.handlers.steam.search_game")
    def test_group_message_does_not_run_search(self, search_game, send_message):
        states.set_state(999, states.WAITING_GAME_SEARCH)
        handle_message({"chat": {"id": 999, "type": "group"}, "from": {"id": 111}, "text": "Elden Ring"})
        search_game.assert_not_called()
        send_message.assert_not_called()

    @patch("telegram.handlers.send_message")
    @patch("telegram.handlers.steam.search_game")
    def test_long_game_name_is_rejected(self, search_game, send_message):
        states.set_state(999, states.WAITING_GAME_SEARCH)
        handle_message({"chat": {"id": 999, "type": "private"}, "from": {"id": 111}, "text": "x" * 101})
        search_game.assert_not_called()
        self.assertIn("muito longo", send_message.call_args.args[0])

    @patch("telegram.handlers.send_message")
    def test_unexpected_message_is_handled(self, send_message):
        handle_message({"chat": {"id": 999, "type": "private"}, "from": {"id": 111}, "sticker": {"file_id": "abc"}})
        send_message.assert_called_once()

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    def test_unknown_callback_is_controlled(self, edit_message, answer_callback):
        handle_callback({"id": "callback-id", "data": "unexpected:value", "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}})
        answer_callback.assert_called_once_with("callback-id")
        edit_message.assert_not_called()

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    @patch("telegram.handlers.steam.search_deals", return_value=[])
    def test_supported_category_starts_a_search(self, search_deals, edit_message, _answer_callback):
        handle_callback({"id": "callback-id", "data": "category:action", "from": {"id": 111}, "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}})
        search_deals.assert_called_once()
        self.assertEqual(search_deals.call_args.kwargs["category"], "action")
        edit_message.assert_called()

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    @patch("telegram.handlers.steam.search_deals")
    def test_tag_categories_show_unavailable_screen(self, search_deals, edit_message, _answer_callback):
        for category in ("fps", "horror", "survival"):
            with self.subTest(category=category):
                handle_callback({"id": f"callback-id-{category}", "data": f"category:{category}", "from": {"id": 111}, "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}})
                self.assertIn("ainda não está disponível", edit_message.call_args.args[2])
        search_deals.assert_not_called()

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    def test_pagination_allows_page_five_but_not_six(self, edit_message, _answer_callback):
        games = [dict(GAME, name=f"Jogo {number}") for number in range(PAGE_SIZE * 5)]
        states.set_state(999, "results", results=games, title="Ofertas", kind="deals", page=0)
        callback = {"id": "callback-id", "from": {"id": 111}, "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}}
        handle_callback({**callback, "data": "page:deals:4"})
        self.assertEqual(states.get_state(999)["page"], 4)
        self.assertTrue(edit_message.called)
        edit_message.reset_mock()
        handle_callback({**callback, "data": "page:deals:5"})
        edit_message.assert_not_called()

    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    def test_same_page_does_not_edit_message_again(self, edit_message, _answer_callback):
        states.set_state(999, "results", results=[GAME], title="Ofertas", kind="deals", page=0)
        handle_callback({"id": "callback-id", "data": "page:deals:0", "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}})
        edit_message.assert_not_called()

    @patch("telegram.handlers.database.set_subscription")
    @patch("telegram.handlers.answer_callback_query")
    @patch("telegram.handlers.edit_message_text")
    @patch("telegram.handlers.best_deals.send_current_best_deals")
    def test_best_deals_subscription_callback(self, send_current, edit_message, _answer_callback, set_subscription):
        handle_callback({"id": "callback-id", "data": "bestdeals:subscribe", "from": {"id": 111}, "message": {"chat": {"id": 999, "type": "private"}, "message_id": 42}})
        set_subscription.assert_called_once_with(111, 999, True)
        send_current.assert_called_once_with(999)
        self.assertIn("ativados", edit_message.call_args.args[2])
