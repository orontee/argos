import asyncio
import json
import pathlib
import unittest
from unittest.mock import Mock

from argos.message import Message, MessageType
from argos.wseventhandler import MopidyWSEventHandler


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestWSEventHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        app = Mock()
        app.message_queue = asyncio.Queue()
        self.message_queue = app.message_queue
        self.event_handler = MopidyWSEventHandler(app)

    async def test_call_with_known_event(self):
        parsed_ws_msg = load_json_data("track_playback_started.json")
        await self.event_handler(parsed_ws_msg)
        self.assertEqual(self.message_queue.qsize(), 1)
        msg = await self.message_queue.get()
        self.assertEqual(
            msg, Message(MessageType.TRACK_PLAYBACK_STARTED, parsed_ws_msg)
        )

    async def test_call_with_unknown_event(self):
        parsed_ws_msg = {"event": "started_playtrack_back"}
        await self.event_handler(parsed_ws_msg)
        self.assertEqual(self.message_queue.qsize(), 0)
