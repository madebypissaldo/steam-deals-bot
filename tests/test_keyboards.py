import unittest

from telegram.keyboards import main_menu, results_keyboard, search_menu, unavailable_category_menu


class KeyboardTests(unittest.TestCase):
    def test_main_menu_has_expected_callbacks(self):
        callbacks = {button["callback_data"] for row in main_menu()["inline_keyboard"] for button in row}
        self.assertTrue({"menu:deals", "menu:search", "menu:under20", "menu:discount80", "bestdeals:menu", "menu:watchlist"} <= callbacks)

    def test_search_menu_has_navigation(self):
        callbacks = {button["callback_data"] for row in search_menu()["inline_keyboard"] for button in row}
        self.assertIn("search:name", callbacks)
        self.assertIn("nav:main", callbacks)

    def test_results_keyboard_paginates(self):
        callbacks = {button["callback_data"] for row in results_keyboard("deals", 1, 3)["inline_keyboard"] for button in row}
        self.assertIn("page:deals:0", callbacks)
        self.assertIn("page:deals:2", callbacks)

    def test_results_keyboard_has_correct_first_and_last_navigation(self):
        first = {button["callback_data"] for row in results_keyboard("deals", 0, 5)["inline_keyboard"] for button in row if "callback_data" in button}
        last = {button["callback_data"] for row in results_keyboard("deals", 4, 5)["inline_keyboard"] for button in row if "callback_data" in button}
        self.assertNotIn("page:deals:-1", first)
        self.assertIn("page:deals:1", first)
        self.assertIn("page:deals:3", last)
        self.assertNotIn("page:deals:5", last)

    def test_unavailable_category_menu_has_back_button(self):
        callbacks = {button["callback_data"] for row in unavailable_category_menu()["inline_keyboard"] for button in row}
        self.assertIn("nav:categories", callbacks)
