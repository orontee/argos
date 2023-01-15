import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from argos.app import Application

from gi.repository import GObject

from argos.message import Message, MessageType

LOGGER = logging.getLogger(__name__)

_WS_EVENT_TO_MESSAGE: Dict[str, MessageType] = {
    "track_playback_started": MessageType.TRACK_PLAYBACK_STARTED,
    "track_playback_paused": MessageType.TRACK_PLAYBACK_PAUSED,
    "track_playback_resumed": MessageType.TRACK_PLAYBACK_RESUMED,
    "track_playback_ended": MessageType.TRACK_PLAYBACK_ENDED,
    "playback_state_changed": MessageType.PLAYBACK_STATE_CHANGED,
    "mute_changed": MessageType.MUTE_CHANGED,
    "volume_changed": MessageType.VOLUME_CHANGED,
    "tracklist_changed": MessageType.TRACKLIST_CHANGED,
    "seeked": MessageType.SEEKED,
    "options_changed": MessageType.OPTIONS_CHANGED,
    "playlist_changed": MessageType.PLAYLIST_CHANGED,
    "playlist_deleted": MessageType.PLAYLIST_DELETED,
    "playlist_loaded": MessageType.PLAYLIST_LOADED,
}


class MopidyWSEventHandler(GObject.Object):
    """Handle Mopidy events received through websocket.

    When a Mopidy event is processed, a ``Message`` is instantiated and put in
    the application message queue.

    The dispatch of message to their consumers is done by a dedicated task
    implemented in ``MessageDispatchTask``.

    """

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()
        self._message_queue: asyncio.Queue = application.message_queue

    async def __call__(self, parsed_ws_msg: Dict[str, Any]) -> None:
        event = parsed_ws_msg.get("event")
        message_type = _WS_EVENT_TO_MESSAGE.get(event) if event else None
        if message_type:
            message = Message(message_type, parsed_ws_msg)
            LOGGER.debug(f"Enqueuing message with type {message.type!r}")
            await self._message_queue.put(message)
        else:
            LOGGER.debug(f"Unhandled event type {event!r}")
