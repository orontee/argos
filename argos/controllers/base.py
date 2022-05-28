import asyncio
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from ..http import MopidyHTTPClient
from ..message import Message, MessageType
from ..model import Model


class ControllerBase(GObject.Object):
    def __init__(
        self,
        application: "Application",
        *,
        logger: logging.Logger,
    ):
        super().__init__()

        self._http: MopidyHTTPClient = application.props.http
        self._loop: asyncio.AbstractEventLoop = application.loop
        self._message_queue: asyncio.Queue = application.message_queue
        self._model: Model = application.props.model

        self._logger = logger
        # for inherited methods to log using the module logger where
        # children classes are defined

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        processed = await self.do_process_message(message_type, message)
        if processed:
            self._logger.debug(f"Processed message of type {message_type}")

    async def do_process_message(
        self, message_type: MessageType, message: Message
    ) -> bool:
        ...

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)
