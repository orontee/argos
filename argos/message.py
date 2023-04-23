import asyncio
import collections.abc
import functools
import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, Sequence, TypeVar

from gi.repository import GObject

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class MessageType(Enum):
    # Commands
    TOGGLE_PLAYBACK_STATE = 0
    PLAY_PREV_TRACK = 1
    PLAY_NEXT_TRACK = 2
    PLAY_TRACKS = 4
    SEEK = 6
    SET_VOLUME = 7
    FETCH_TRACK_IMAGE = 9
    FETCH_IMAGES = 10
    BROWSE_DIRECTORY = 11
    COMPLETE_ALBUM_DESCRIPTION = 13
    COLLECT_ALBUM_INFORMATION = 14

    IDENTIFY_PLAYING_STATE = 20
    ADD_TO_TRACKLIST = 21
    REMOVE_FROM_TRACKLIST = 22
    CLEAR_TRACKLIST = 23
    GET_TRACKLIST = 24
    GET_CURRENT_TRACKLIST_TRACK = 25
    PLAY = 26
    SET_CONSUME = 27
    SET_RANDOM = 28
    SET_REPEAT = 29
    SET_SINGLE = 30

    LIST_PLAYLISTS = 31
    COMPLETE_PLAYLIST_DESCRIPTION = 32
    CREATE_PLAYLIST = 33
    SAVE_PLAYLIST = 34
    DELETE_PLAYLIST = 35

    # Events (frow websocket)
    TRACK_PLAYBACK_STARTED = 40
    TRACK_PLAYBACK_PAUSED = 41
    TRACK_PLAYBACK_RESUMED = 42
    TRACK_PLAYBACK_ENDED = 43
    PLAYBACK_STATE_CHANGED = 44
    MUTE_CHANGED = 45
    VOLUME_CHANGED = 46
    TRACKLIST_CHANGED = 47
    SEEKED = 48
    OPTIONS_CHANGED = 49
    PLAYLIST_CHANGED = 50
    PLAYLIST_DELETED = 51
    PLAYLIST_LOADED = 52


@dataclass
class Message:
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)


def consume(
    *args: MessageType,
) -> Callable[
    [Callable[[T, Message], collections.abc.Awaitable[None]]],
    Callable[[T, Message], collections.abc.Awaitable[None]],
]:
    """Decorator that identifies message consumers.

    It is expected to be applied to class methods.

    Once the decorator is applied, a message consumer can be
    identified among all class methods of a given class by inspecting
    the presence of the ``consume_message`` attribute. This attribute
    value is the list of message type handled by the consumer.

    Note that it's the message dispatcher responsibility to feed
    consumers with message of type they expect.

    Warning: With current lazzy implementation of
    ``Application._identify_message_consumers_from_controllers()``,
    this decorator must be the last operator applied to a class method
    for the consumer identifier to successfully identify a decorated
    class method as being a consumer.

    """

    def decorator(
        method: Callable[[T, Message], collections.abc.Awaitable[None]]
    ) -> Callable[[T, Message], collections.abc.Awaitable[None]]:
        @functools.wraps(method)
        async def inner(ref: T, message: Message) -> None:
            assert message.type in args
            logger = getattr(ref, "logger", None)
            if logger is not None:
                logger.debug(f"Processing message of type {message.type}")
            return await method(ref, message)

        setattr(inner, "consume_messages", args)

        return inner

    return decorator


class MessageDispatchTask(GObject.Object):
    """Dispatch messages to consumers."""

    def __init__(self, application: "Application"):
        super().__init__()
        self._message_queue: asyncio.Queue = application.message_queue

        self._identify_message_consumers_from_objects(application.props.controllers)

    def _identify_message_consumers_from_objects(
        self,
        objects: Sequence[Any],
    ) -> None:
        LOGGER.debug("Identifying message consumers")
        self._consumers = defaultdict(list)
        for obj in objects:
            for name in dir(obj):
                subject = getattr(obj, name)
                if callable(subject) and hasattr(subject, "consume_messages"):
                    for message_type in subject.consume_messages:
                        self._consumers[message_type].append(subject)
                        LOGGER.debug(
                            f"New consumer of {message_type}: {inspect.unwrap(subject)}"
                        )

    async def __call__(self) -> None:
        LOGGER.debug("Waiting for new messages...")
        try:
            while True:
                message = await self._message_queue.get()
                message_type = message.type
                LOGGER.debug(f"Dispatching message of type {message_type}")

                consumers = self._consumers.get(message_type)
                if consumers is None:
                    LOGGER.warning(f"No consumer for message of type {message_type}")
                else:
                    for consumer in consumers:
                        await consumer(message)
        except asyncio.exceptions.CancelledError:
            LOGGER.debug("Won't dispatch messages anymore")
