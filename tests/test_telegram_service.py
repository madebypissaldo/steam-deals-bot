import unittest
from unittest.mock import patch

import requests

from services.telegram import edit_message_text


class FakeResponse:
    status_code = 400

    def __init__(self, description):
        self.description = description

    def raise_for_status(self):
        raise requests.HTTPError(response=self)

    def json(self):
        return {"error_code": 400, "description": self.description}


class TelegramServiceTests(unittest.TestCase):
    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"})
    @patch("services.telegram._api_session.post")
    def test_message_not_modified_is_a_successful_no_op(self, post):
        post.return_value = FakeResponse("Bad Request: message is not modified")
        self.assertTrue(edit_message_text(1, 2, "mesmo texto"))

    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"})
    @patch("services.telegram._api_session.post")
    def test_other_http_400_remains_an_error(self, post):
        post.return_value = FakeResponse("Bad Request: chat not found")
        self.assertFalse(edit_message_text(1, 2, "texto"))
