import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from .app import Application
from .message import Message, MessageType
from .model import Model
from .session import get_session

LOGGER = logging.getLogger(__name__)

COMMAND_TIMEOUT: int = 10  # s

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


class _URLChanged(Exception):
    pass


class _URLUndefined(Exception):
    pass


class MopidyWSConnection(GObject.GObject):
    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._model: Model = application.props.model
        self._message_queue: asyncio.Queue = application.message_queue

        settings: Gio.Settings = application.props.settings

        mopidy_base_url = settings.get_string("mopidy-base-url")
        self._url = urljoin(mopidy_base_url, "/mopidy/ws") if mopidy_base_url else None
        settings.connect("changed::mopidy-base-url", self._on_mopidy_base_url_changed)

        connection_retry_delay = settings.get_int("connection-retry-delay")
        self._connection_retry_delay = connection_retry_delay

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._commands: Dict[int, asyncio.Future] = {}

    async def send_command(self, method: str, *, params: dict = None) -> Optional[Any]:
        """Invoke a JSON-RPC command.

        Args:
            method: Method to invoke.

            params: Parameters of the JSON-RPC command.

        Returns:
            Result of the invoked method.

        """
        global _COMMAND_ID

        if not self._ws:
            LOGGER.warning("Cannot send command!")
            return None

        _COMMAND_ID += 1
        jsonrpc_id = _COMMAND_ID

        data = {"jsonrpc": "2.0", "id": jsonrpc_id, "method": method}
        if params is not None:
            data["params"] = params

        future: asyncio.Future = asyncio.Future()
        self._commands[jsonrpc_id] = future

        LOGGER.debug(f"Sending JSON-RPC command {jsonrpc_id} with method {method}")
        try:
            try:
                await asyncio.wait_for(self._ws.send_json(data), COMMAND_TIMEOUT)
            except ConnectionResetError:
                LOGGER.warning(
                    f"Connection reset while sending JSON-RPC command {jsonrpc_id}"
                )
                future.cancel()
            except asyncio.exceptions.TimeoutError:
                LOGGER.warning(f"Timeout while sending JSON-RPC command {jsonrpc_id}")
                future.cancel()

            try:
                await asyncio.wait_for(future, COMMAND_TIMEOUT)
            except asyncio.exceptions.TimeoutError:
                LOGGER.warning(
                    f"Timeout while waiting response of JSON-RPC command {jsonrpc_id}"
                )
                future.cancel()

            result = future.result()

        except asyncio.exceptions.CancelledError:
            LOGGER.debug(f"JSON-RPC command {jsonrpc_id} cancelled")
            self._commands.pop(jsonrpc_id, None)
            # the default None value must be provided since, if the
            # future is cancelled due to network availability changed
            # (see cancel_commands()), then it may have been removed
            # from self._commands
            result = None
        return result

    def cancel_commands(self) -> None:
        for jsonrpc_id in list(self._commands.keys()):
            LOGGER.debug(f"Cancelling JSON-RPC command {jsonrpc_id}")
            future = self._commands.pop(jsonrpc_id)
            future.cancel()

    async def _enqueue(self, message: Message) -> None:
        LOGGER.debug(f"Enqueing message with type {message.type}")
        await self._message_queue.put(message)

    async def listen(self) -> None:
        async with get_session() as session:
            while True:
                try:
                    if not self._url:
                        raise _URLUndefined()

                    url = self._url
                    self._ws = await session.ws_connect(url, ssl=False, timeout=None)
                    assert self._ws
                    LOGGER.debug(f"Connected to mopidy websocket at {self._url}")

                    self._model.set_property_in_gtk_thread("connected", True)

                    async for msg in self._ws:
                        message = self._handle(msg)
                        if isinstance(message, Message):
                            await self._enqueue(message)

                        if url != self._url:
                            LOGGER.debug(
                                "New websocket connection required due to URL change"
                            )
                            raise _URLChanged()

                except (
                    _URLChanged,
                    _URLUndefined,
                    ConnectionError,
                    aiohttp.ClientResponseError,
                    aiohttp.client_exceptions.ClientConnectorError,
                ) as error:
                    self._model.set_property_in_gtk_thread("connected", False)

                    self.cancel_commands()

                    if isinstance(error, _URLChanged):
                        LOGGER.warning(
                            "New connection to be established after URL change"
                        )
                    elif isinstance(error, _URLUndefined):
                        LOGGER.warning(
                            "Connection to be established later since URL not set"
                        )
                    else:
                        LOGGER.error(
                            f"Connection error (retry in {self._connection_retry_delay}): {error}"
                        )

                    await asyncio.sleep(self._connection_retry_delay)

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
                future = self._commands.pop(jsonrpc_id, None)
                # the default None value must be provided since, if
                # the future is cancelled due to connection reset or
                # timeout, then it may have been removed from
                # self._commands
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

    def _on_mopidy_base_url_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        mopidy_base_url = settings.get_string(key)
        self._url = urljoin(mopidy_base_url, "/mopidy/ws") if mopidy_base_url else None
