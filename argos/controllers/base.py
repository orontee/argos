import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.helper import ModelHelper
from argos.http import MopidyHTTPClient
from argos.message import Message, MessageType
from argos.model import Model
from argos.notify import Notifier


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
        self._settings: Gio.Settings = application.props.settings

        self.helper = ModelHelper()

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)
