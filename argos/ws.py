import asyncio
import json
import logging
from typing import Optional
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio

from .message import Message, MessageType
from .session import get_session

LOGGER = logging.getLogger(__name__)

EVENT_TO_MESSAGE_TYPE = {
    "track_playback_started": MessageType.TRACK_PLAYBACK_STARTED,
    "track_playback_paused": MessageType.TRACK_PLAYBACK_PAUSED,
    "track_playback_resumed": MessageType.TRACK_PLAYBACK_RESUMED,
    "playback_state_changed": MessageType.PLAYBACK_STATE_CHANGED,
    "mute_changed": MessageType.MUTE_CHANGED,
    "volume_changed": MessageType.VOLUME_CHANGED,
    "tracklist_changed": MessageType.TRACKLIST_CHANGED,
    "track_playback_ended": MessageType.TRACK_PLAYBACK_ENDED,
    "seeked": MessageType.SEEKED
}


def parse_msg(msg: aiohttp.WSMessage) -> dict:
    try:
        return msg.json()
    except json.JSONDecodeError:
        LOGGER.error(f"Failed to decode JSON string {msg.data!r}")
        return None


def convert_to_message(msg: aiohttp.WSMessage) -> Optional[Message]:
    """Convert a websocket message to an ``Message`` instance.

    Mopidy websocket message have an ``event`` property which is
    used to do the conversion using ``EVENT_TO_MESSAGE_TYPE``.

    """
    if msg.type == aiohttp.WSMsgType.TEXT:
        parsed = parse_msg(msg)
        event = parsed.get("event")
        message_type = EVENT_TO_MESSAGE_TYPE.get(event)
        if message_type:
            return Message(message_type, parsed)
        else:
            LOGGER.debug(f"Unhandled event {parsed!r}")

    elif msg.type in (aiohttp.WSMsgType.ERROR,
                      aiohttp.WSMsgType.CLOSED_FRAME):
        LOGGER.warning(f"Unexpected message {msg!r}")

    elif msg.type == aiohttp.WSMsgType.CLOSE:
        LOGGER.info(f"Close received with code {msg.data!r}, "
                    f"{msg.extra!r}")


class MopidyWSListener:
    settings = Gio.Settings("app.argos.Argos")

    def __init__(self, *,
                 message_queue: asyncio.Queue):
        base_url = self.settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/ws")
        self._message_queue = message_queue

        self.settings.connect("changed::mopidy-base-url",
                              self.on_mopidy_base_url_changed)

    def on_mopidy_base_url_changed(self, settings, _):
        base_url = settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/ws")

    async def listen(self) -> None:
        async with get_session() as session:
            while True:
                try:
                    async with session.ws_connect(self._url,
                                                  ssl=False,
                                                  timeout=None) as ws:
                        LOGGER.debug(f"Connected to mopidy websocket at {self._url}")
                        async for msg in ws:
                            message = convert_to_message(msg)
                            if message:
                                await self._message_queue.put(message)
                except aiohttp.ClientResponseError:
                    LOGGER.warning("Connection failure!")
                    connection_retry_delay = self.settings.get_int(
                        "connection-retry-delay"
                    )
                    await asyncio.sleep(connection_retry_delay)
