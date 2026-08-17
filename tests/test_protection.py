import unittest

from telegram import protection


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        protection.reset_for_tests()

    def test_rate_limit_blocks_a_fast_second_search(self):
        self.assertIsNone(protection.start_search("user-a", now=0))
        protection.finish_search("user-a")
        self.assertEqual(protection.start_search("user-a", now=1), "rate")

    def test_same_user_cannot_have_two_active_searches(self):
        self.assertIsNone(protection.start_search("user-a", now=0))
        self.assertEqual(protection.start_search("user-a", now=3), "active")
        protection.finish_search("user-a")

    def test_global_limit_rejects_fifth_concurrent_search(self):
        for user_id in range(protection.MAX_CONCURRENT_SEARCHES):
            self.assertIsNone(protection.start_search(user_id, now=0))
        self.assertEqual(protection.start_search("extra", now=0), "global")

    def test_users_have_independent_limits(self):
        self.assertIsNone(protection.start_search("user-a", now=0))
        self.assertIsNone(protection.start_search("user-b", now=0))
