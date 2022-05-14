import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from ..http import MopidyHTTPClient
from ..message import Message, MessageType
from ..model import Model


class ControllerBase(GObject.Object):
    def __init__(self, application: "Application"):
        super().__init__()

        self._http: MopidyHTTPClient = application.props.http
        self._loop: asyncio.AbstractEventLoop = application.loop
        self._message_queue: asyncio.Queue = application.message_queue
        self._model: Model = application.props.model

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        ...

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)
