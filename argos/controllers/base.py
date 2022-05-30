import asyncio
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
)

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from ..http import MopidyHTTPClient
from ..message import Message, MessageType
from ..model import Model
from ..notify import Notifier


class ControllerBase(GObject.Object):
    """Base class for controllers.

    Use the ``consume`` decorator on children class methods for the
    application to identify those methods as being message
    consumers. As a result messages will be automatically dispatched
    to those methods.

    """

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._http: MopidyHTTPClient = application.props.http
        self._loop: asyncio.AbstractEventLoop = application.loop
        self._message_queue: asyncio.Queue = application.message_queue
        self._model: Model = application.props.model
        self._notifier: Notifier = application.props.notifier

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)
