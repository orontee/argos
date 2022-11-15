import collections.abc
import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, TypeVar

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
    FETCH_ALBUM_IMAGES = 10
    BROWSE_ALBUMS = 11
    COMPLETE_ALBUM_DESCRIPTION = 12
    IDENTIFY_PLAYING_STATE = 14
    ADD_TO_TRACKLIST = 15
    REMOVE_FROM_TRACKLIST = 16
    CLEAR_TRACKLIST = 17
    GET_TRACKLIST = 18
    GET_CURRENT_TRACKLIST_TRACK = 19
    PLAY = 20
    SET_CONSUME = 21
    SET_RANDOM = 22
    SET_REPEAT = 23
    SET_SINGLE = 24
    LIST_PLAYLISTS = 30
    COMPLETE_PLAYLIST_DESCRIPTION = 31
    CREATE_PLAYLIST = 32
    SAVE_PLAYLIST = 33
    DELETE_PLAYLIST = 34

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
