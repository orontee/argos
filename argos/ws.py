"""Listen to mopidy websocket.

"""
import asyncio
import json
import logging
from urllib.parse import urljoin

import aiohttp

from .conf import MOPIDY_URL
from .message import Message, MessageType
from .session import get_session

LOGGER = logging.getLogger(__name__)


def parse_msg(msg: aiohttp.WSMessage) -> dict:
    try:
        return msg.json()
    except json.JSONDecodeError:
        LOGGER.error(f"Failed to decode JSON string {msg.data!r}")
        return None


class MopidyWSListener:
    def __init__(self, *,
                 message_queue: asyncio.Queue):
        self._url = urljoin(MOPIDY_URL, "/mopidy/ws")
        self._message_queue = message_queue

    async def listen(self) -> None:
        async with get_session() as session:
            async with session.ws_connect(self._url,
                                          ssl=False,
                                          timeout=None) as ws:
                LOGGER.debug(f"Connected to mopidy websocket at {self._url}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        parsed_data = parse_msg(msg)
                        event = parsed_data.get("event")
                        if event == "track_playback_started":
                            await self._message_queue.put(
                                Message(MessageType.TRACK_PLAYBACK_STARTED,
                                        parsed_data))
                        elif event == "track_playback_paused":
                            await self._message_queue.put(
                                Message(MessageType.TRACK_PLAYBACK_PAUSED,
                                        parsed_data))
                        elif event == "track_playback_resumed":
                            await self._message_queue.put(
                                Message(MessageType.TRACK_PLAYBACK_RESUMED,
                                        parsed_data))
                        elif event == "playback_state_changed":
                            await self._message_queue.put(
                                Message(MessageType.PLAYBACK_STATE_CHANGED,
                                        parsed_data))
                        elif event == "mute_changed":
                            await self._message_queue.put(
                                Message(MessageType.MUTE_CHANGED,
                                        parsed_data))
                        elif event == "volume_changed":
                            await self._message_queue.put(
                                Message(MessageType.VOLUME_CHANGED,
                                        parsed_data))
                        elif event == "tracklist_changed":
                            await self._message_queue.put(
                                Message(MessageType.VOLUME_CHANGED,
                                        parsed_data))
                        elif event == "track_playback_ended":
                            await self._message_queue.put(
                                Message(MessageType.VOLUME_CHANGED,
                                        parsed_data))
                        else:
                            LOGGER.debug(f"Unhandled event {parsed_data}")

                    elif msg.type in (aiohttp.WSMsgType.ERROR,
                                      aiohttp.WSMsgType.CLOSED_FRAME):
                        LOGGER.warning(f"Unexpected message {msg}")

                    elif msg.type == aiohttp.WSMsgType.CLOSE:
                        LOGGER.info(f"Close received with code {msg.data}, "
                                    f"{msg.extra}")
