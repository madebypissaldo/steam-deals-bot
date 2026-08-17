import unittest

from telegram import states


class StateTests(unittest.TestCase):
    def setUp(self):
        states.user_states.clear()

    def test_state_lifecycle(self):
        states.set_state(123, states.WAITING_GAME_SEARCH, query="Elden Ring")
        self.assertEqual(states.get_state("123"), {"state": states.WAITING_GAME_SEARCH, "query": "Elden Ring"})
        states.clear_state(123)
        self.assertIsNone(states.get_state(123))

    def test_each_chat_has_independent_state(self):
        states.set_state(1, states.WAITING_GAME_SEARCH, query="Elden Ring")
        states.set_state(2, "results", query="Cyberpunk 2077")
        self.assertEqual(states.get_state(1)["query"], "Elden Ring")
        self.assertEqual(states.get_state(2)["query"], "Cyberpunk 2077")
