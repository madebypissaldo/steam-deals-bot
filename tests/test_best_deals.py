import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from services import best_deals
from scheduler import best_deals as scheduler
from storage import database
from telegram import protection


PAID_FREE = {"app_id": 1, "name": "Pago grátis", "initial_cents": 5999, "final_cents": 0, "discount_percent": 100, "initial_formatted": "R$ 59,99", "final_formatted": "Grátis", "url": "https://example.test/1"}
CHEAP = {"app_id": 2, "name": "Barato", "initial_cents": 9999, "final_cents": 499, "discount_percent": 95, "initial_formatted": "R$ 99,99", "final_formatted": "R$ 4,99", "url": "https://example.test/2"}


class BestDealsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict("os.environ", {"BEST_DEALS_DB_PATH": str(Path(self.directory.name) / "bot.sqlite3")})
        self.environment.start()
        database.initialize()
        protection.reset_for_tests()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_detector_criteria_and_permanently_free_product(self):
        self.assertTrue(best_deals.is_best_deal(PAID_FREE))
        self.assertTrue(best_deals.is_best_deal(CHEAP))
        self.assertFalse(best_deals.is_best_deal(dict(CHEAP, discount_percent=80)))
        self.assertFalse(best_deals.is_best_deal(dict(CHEAP, final_cents=3000)))
        self.assertFalse(best_deals.is_best_deal(dict(PAID_FREE, initial_cents=0)))

    def test_subscriptions_persist_without_duplicates(self):
        database.set_subscription(10, 20, True)
        database.set_subscription(10, 20, True)
        self.assertTrue(database.is_subscribed(10))
        self.assertEqual(len(database.active_subscribers()), 1)
        database.set_subscription(10, 20, False)
        self.assertFalse(database.is_subscribed(10))

    def test_deduplication_allows_changed_offer(self):
        database.mark_notified(CHEAP)
        self.assertEqual(best_deals.find_best_deals([CHEAP]), [])
        changed = dict(CHEAP, final_cents=0, discount_percent=100)
        self.assertEqual(best_deals.find_best_deals([changed]), [changed])

    @patch("services.best_deals.steam.search_deals", return_value=[PAID_FREE])
    def test_broadcast_continues_after_failure(self, _search_deals):
        database.set_subscription(1, 101, True)
        database.set_subscription(2, 102, True)
        chats = []
        def sender(_message, chat_id, _keyboard):
            chats.append(chat_id)
            return str(chat_id) == "102"
        best_deals.run_daily_scan(send=sender)
        self.assertEqual(chats, ["101", "102"])
        self.assertTrue(database.was_notified(PAID_FREE))

    @patch("services.best_deals.steam.search_deals", return_value=[PAID_FREE])
    def test_new_subscriber_receives_current_deal_even_if_already_notified(self, _search_deals):
        database.mark_notified(PAID_FREE)
        chats = []
        best_deals.send_current_best_deals(101, send=lambda _message, chat_id, _keyboard: chats.append(chat_id) or True)
        self.assertEqual(chats, [101])

    @patch("scheduler.best_deals.run_daily_scan")
    def test_scheduler_runs_once_per_day_and_recovers_missed_time(self, scan):
        now = datetime(2026, 8, 19, 15, 0)
        self.assertTrue(scheduler.run_if_due(now))
        self.assertFalse(scheduler.run_if_due(now))
        scan.assert_called_once()

    @patch("scheduler.best_deals.run_daily_scan", side_effect=RuntimeError("steam unavailable"))
    def test_failed_scheduler_scan_is_not_recorded_as_success(self, _scan):
        now = datetime(2026, 8, 19, 15, 0)
        self.assertFalse(scheduler.run_if_due(now))
        self.assertIsNone(database.last_scan_date())
