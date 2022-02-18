import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio

from .message import Message, MessageType
from .session import get_session

LOGGER = logging.getLogger(__name__)

EVENT_TO_MESSAGE_TYPE: Dict[str, MessageType] = {
    "track_playback_started": MessageType.TRACK_PLAYBACK_STARTED,
    "track_playback_paused": MessageType.TRACK_PLAYBACK_PAUSED,
    "track_playback_resumed": MessageType.TRACK_PLAYBACK_RESUMED,
    "track_playback_ended": MessageType.TRACK_PLAYBACK_ENDED,
    "playback_state_changed": MessageType.PLAYBACK_STATE_CHANGED,
    "mute_changed": MessageType.MUTE_CHANGED,
    "volume_changed": MessageType.VOLUME_CHANGED,
    "tracklist_changed": MessageType.TRACKLIST_CHANGED,
    "seeked": MessageType.SEEKED,
}

_COMMAND_ID: int = 0


def parse_msg(msg: aiohttp.WSMessage) -> Dict[str, Any]:
    try:
        return msg.json()
    except json.JSONDecodeError:
        LOGGER.error(f"Failed to decode JSON string {msg.data!r}")
        return {}


class MopidyWSConnection:
    settings = Gio.Settings("app.argos.Argos")

    def __init__(self, *, message_queue: asyncio.Queue):
        base_url = self.settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/ws")
        self._message_queue = message_queue
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

        self._commands: Dict[int, asyncio.Future] = {}

        self.settings.connect(
            "changed::mopidy-base-url", self.on_mopidy_base_url_changed
        )

    def on_mopidy_base_url_changed(self, settings, _):
        base_url = settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/ws")

    async def send_command(self, method: str, *, params: dict = None) -> Any:
        global _COMMAND_ID

        if not self._ws:
            LOGGER.warning("Cannot send command!")
            return None

        _COMMAND_ID += 1
        data = {"jsonrpc": "2.0", "id": _COMMAND_ID, "method": method}
        if params is not None:
            data["params"] = params

        future: asyncio.Future = asyncio.Future()
        self._commands[_COMMAND_ID] = future

        LOGGER.debug(f"Sending JSON-RPC command {_COMMAND_ID} with method {method}")
        await self._ws.send_json(data)
        result = await future
        return result

    async def _enqueue(self, message: Message) -> None:
        LOGGER.debug(f"Enqueing message with type {message.type}")
        await self._message_queue.put(message)

    async def listen(self) -> None:
        async with get_session() as session:
            while True:
                try:
                    url = self._url
                    self._ws = await session.ws_connect(url, ssl=False, timeout=None)
                    await self._enqueue(
                        Message(
                            MessageType.MOPIDY_WEBSOCKET_CONNECTED,
                            {"connected": True},
                        )
                    )
                    assert self._ws
                    LOGGER.debug(f"Connected to mopidy websocket at {self._url}")
                    async for msg in self._ws:
                        message = self._handle(msg)
                        if isinstance(message, Message):
                            await self._enqueue(message)

                        if url != self._url:
                            LOGGER.debug(
                                "New websocket connection required due to URL change"
                            )
                            raise RuntimeError()

                except (
                    RuntimeError,
                    aiohttp.ClientResponseError,
                    aiohttp.client_exceptions.ClientConnectorError,
                ):
                    await self._message_queue.put(
                        Message(
                            MessageType.MOPIDY_WEBSOCKET_CONNECTED,
                            {"connected": False},
                        )
                    )
                    connection_retry_delay = self.settings.get_int(
                        "connection-retry-delay"
                    )
                    LOGGER.warning(
                        f"Connection error (retry in {connection_retry_delay}s)"
                    )
                    await asyncio.sleep(connection_retry_delay)

    def _handle(self, msg: aiohttp.WSMessage) -> Optional[Union[Message, bool]]:
        """Handle websocket message.

        The websocket message is parsed.

        Then attempt is made to:

        - Convert the message to an ``Message`` instance in case it's
          a Mopidy event,

        - Find the JSON-RPC command it's the response from.

        A websocket message for a Mopidy event has an ``event``
        property which is used to do the conversion using
        ``EVENT_TO_MESSAGE_TYPE``.

        """
        if msg.type == aiohttp.WSMsgType.TEXT:
            parsed = parse_msg(msg)
            event = parsed.get("event")
            message_type = EVENT_TO_MESSAGE_TYPE.get(event) if event else None
            if message_type:
                return Message(message_type, parsed)

            jsonrpc_id = parsed.get("id") if "jsonrpc" in parsed else None
            if jsonrpc_id:
                future = self._commands.pop(jsonrpc_id)
                if future:
                    LOGGER.debug(f"Received result of JSON-RPC command id {jsonrpc_id}")
                    future.set_result(parsed.get("result"))
                    return True
                else:
                    LOGGER.debug(f"Unknown JSON-RPC command id {jsonrpc_id}")
            else:
                LOGGER.debug(f"Unhandled event {parsed!r}")

        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
            LOGGER.warning(f"Unexpected message {msg!r}")

        elif msg.type == aiohttp.WSMsgType.CLOSE:
            LOGGER.info(f"Close received with code {msg.data!r}, " f"{msg.extra!r}")

        return None
