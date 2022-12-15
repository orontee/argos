import asyncio
import collections.abc
import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.model import Model
from argos.session import HTTPSessionManager

LOGGER = logging.getLogger(__name__)

COMMAND_TIMEOUT: int = 10  # s
CLOSE_TIMEOUT: int = 10  # s
CONSECUTIVE_SEND_FAILURE_THRESHOLD = 5

_COMMAND_ID: int = 0


def parse_msg(msg: aiohttp.WSMessage) -> Dict[str, Any]:
    try:
        return msg.json()
    except json.JSONDecodeError:
        LOGGER.error(f"Failed to decode JSON string {msg.data!r}")
        return {}


class _URLUndefined(Exception):
    pass


class _WSClosed(Exception):
    pass


class MopidyWSConnection(GObject.GObject):
    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._http_session_manager: HTTPSessionManager = (
            application.http_session_manager
        )
        self._loop: asyncio.AbstractEventLoop = application.loop
        self._model: Model = application.props.model
        self._event_handler: Callable[
            [Dict[str, Any]], collections.abc.Awaitable[None]
        ] = application.props.ws_event_handler

        settings: Gio.Settings = application.props.settings

        mopidy_base_url = settings.get_string("mopidy-base-url")
        self._url = urljoin(mopidy_base_url, "/mopidy/ws") if mopidy_base_url else None
        settings.connect("changed::mopidy-base-url", self._on_mopidy_base_url_changed)

        connection_retry_delay = settings.get_int("connection-retry-delay")
        self._connection_retry_delay = connection_retry_delay
        self._consecutive_send_failures = 0

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._commands: Dict[int, asyncio.Future] = {}

    async def send_command(
        self,
        method: str,
        *,
        params: dict = None,
        timeout: int = None,
    ) -> Optional[Any]:
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

        if timeout is None:
            timeout = COMMAND_TIMEOUT

        data = {"jsonrpc": "2.0", "id": jsonrpc_id, "method": method}
        if params is not None:
            data["params"] = params

        future: asyncio.Future = asyncio.Future()
        self._commands[jsonrpc_id] = future

        LOGGER.debug(f"Sending JSON-RPC command {jsonrpc_id} with method {method}")
        try:
            try:
                await asyncio.wait_for(self._ws.send_json(data), timeout)
            except ConnectionResetError:
                LOGGER.warning(
                    f"Connection reset while sending JSON-RPC command {jsonrpc_id}"
                )
                future.cancel()
            except asyncio.exceptions.TimeoutError:
                LOGGER.warning(
                    f"Timeout {timeout}s exceeded while sending "
                    f"JSON-RPC command {jsonrpc_id} with method {method}"
                )
                future.cancel()

            try:
                await asyncio.wait_for(future, timeout)
            except asyncio.exceptions.TimeoutError:
                LOGGER.warning(
                    f"Timeout {timeout}s exceeded while waiting response of "
                    f"JSON-RPC command {jsonrpc_id} with method {method}"
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

            self._consecutive_send_failures += 1
            if self._consecutive_send_failures >= CONSECUTIVE_SEND_FAILURE_THRESHOLD:
                LOGGER.warning(
                    f"Closing Mopidy websocket connection after >{CONSECUTIVE_SEND_FAILURE_THRESHOLD} consecutive send failures"
                )
                await self._close_ws()
                self._consecutive_send_failures = 0
        else:
            self._consecutive_send_failures = 0

        return result

    def cancel_commands(self) -> None:
        for jsonrpc_id in list(self._commands.keys()):
            LOGGER.debug(f"Cancelling JSON-RPC command {jsonrpc_id}")
            future = self._commands.pop(jsonrpc_id)
            future.cancel()

    async def listen(self) -> None:
        async with self._http_session_manager.get_session() as session:
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
                        # Note that iteration stops when a CLOSE
                        # message is received
                        await self._handle(msg)

                    if self._ws.closed:
                        LOGGER.debug("Mopidy websocket connection closed")
                        raise _WSClosed()

                except (
                    _URLUndefined,
                    _WSClosed,
                    ConnectionError,
                    aiohttp.ClientResponseError,
                    aiohttp.client_exceptions.ClientConnectorError,
                    aiohttp.client_exceptions.ServerDisconnectedError,
                    aiohttp.client_exceptions.InvalidURL,
                    asyncio.exceptions.TimeoutError,
                ) as error:
                    self._model.set_property_in_gtk_thread("connected", False)

                    self.cancel_commands()

                    if isinstance(error, _WSClosed):
                        LOGGER.warning(
                            "New connection to be established after connection closed"
                        )
                    elif isinstance(error, _URLUndefined):
                        LOGGER.warning(
                            "Connection to be established later since URL not set"
                        )
                    else:
                        LOGGER.error(
                            f"Connection error (retry in {self._connection_retry_delay}s): {error}"
                        )

                    await asyncio.sleep(self._connection_retry_delay)

    async def _handle(self, msg: aiohttp.WSMessage) -> None:
        """Handle websocket message.

        When ``msg`` is a text message, then it is parsed. If the
        parsed message has an ``"event"`` key, then it is passed to
        the event handler; Otherwise, it tries to identify a JSON-RPC
        command the message is the response from.

        When ``msg`` isn't a text message, it simply logs.

        """
        if msg.type == aiohttp.WSMsgType.TEXT:
            parsed = parse_msg(msg)
            if "event" in parsed:
                await self._event_handler(parsed)
                return

            jsonrpc_id = parsed.get("id") if "jsonrpc" in parsed else None
            if jsonrpc_id:
                future = self._commands.pop(jsonrpc_id, None)
                # the default None value must be provided since, if
                # the future is cancelled due to connection reset or
                # timeout, then it may have been removed from
                # self._commands
                if future:
                    LOGGER.debug(f"Received result of JSON-RPC command {jsonrpc_id}")
                    future.set_result(parsed.get("result"))
                    return
                else:
                    LOGGER.debug(f"Unknown JSON-RPC command {jsonrpc_id}")
            else:
                LOGGER.debug(f"Message without id nor event {parsed!r}")

        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
            LOGGER.warning(f"Unexpected message {msg!r}")

        elif msg.type == aiohttp.WSMsgType.CLOSE:
            LOGGER.info(f"Close received with code {msg.data!r}, " f"{msg.extra!r}")

    def _on_mopidy_base_url_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        mopidy_base_url = settings.get_string(key)
        self._url = urljoin(mopidy_base_url, "/mopidy/ws") if mopidy_base_url else None
        LOGGER.warning("New connection to be established after URL change")
        asyncio.run_coroutine_threadsafe(self._close_ws(), self._loop)

    async def _close_ws(self) -> None:
        if not self._ws:
            return

        try:
            await asyncio.wait_for(self._ws.close(), CLOSE_TIMEOUT)
        except asyncio.exceptions.TimeoutError:
            LOGGER.warning(
                f"Timeout {CLOSE_TIMEOUT}s exceeded while closing Mopidy websocket connection"
            )
