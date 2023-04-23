import asyncio
import json
import pathlib
import unittest
from unittest.mock import Mock

from argos.message import Message, MessageDispatchTask, MessageType, consume


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TrackPlaybackStartedMessageCounter:
    def __init__(self):
        self.counter = 0

    @consume(MessageType.TRACK_PLAYBACK_STARTED)
    async def increment(self, msg):
        self.counter += 1


class TestMessageDispatchTask(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.task = None

    def tearDown(self):
        if self.task is not None:
            self.task.cancel()

    async def test_dispatcher(self):
        app = Mock()
        app.message_queue = asyncio.Queue()
        consumer = TrackPlaybackStartedMessageCounter()
        app.props.controllers = [consumer]

        dispatcher = MessageDispatchTask(app)
        self.task = self.loop.create_task(dispatcher())

        parsed_ws_msg = load_json_data("track_playback_started.json")
        await app.message_queue.put(
            Message(MessageType.TRACK_PLAYBACK_STARTED, parsed_ws_msg)
        )

        parsed_ws_msg = load_json_data("track_playback_ended.json")
        await app.message_queue.put(
            Message(MessageType.TRACK_PLAYBACK_ENDED, parsed_ws_msg)
        )

        await asyncio.sleep(0.1)

        self.assertTrue(app.message_queue.empty())
        self.assertEqual(consumer.counter, 1)

    async def test_dispatcher_without_consumer(self):
        app = Mock()
        app.message_queue = asyncio.Queue()
        app.props.controllers = []

        dispatcher = MessageDispatchTask(app)
        self.task = self.loop.create_task(dispatcher())

        parsed_ws_msg = load_json_data("track_playback_started.json")
        msg = Message(MessageType.TRACK_PLAYBACK_STARTED, parsed_ws_msg)
        await app.message_queue.put(msg)
        await app.message_queue.put(msg)

        await asyncio.sleep(0.1)

        self.assertTrue(app.message_queue.empty())
