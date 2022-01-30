"""Messages.

"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class MessageType(Enum):
    # Commands
    TOGGLE_PLAYBACK_STATE = 0
    PLAY_PREV_TRACK = 1
    PLAY_NEXT_TRACK = 2
    PLAY_RANDOM_ALBUM = 3
    PLAY_FAVORITE_PLAYLIST = 4
    SET_VOLUME = 5

    # Events (frow websocket)
    TRACK_PLAYBACK_STARTED = 6
    TRACK_PLAYBACK_PAUSED = 7
    TRACK_PLAYBACK_RESUMED = 8
    TRACK_PLAYBACK_ENDED = 9
    PLAYBACK_STATE_CHANGED = 10
    MUTE_CHANGED = 11
    VOLUME_CHANGED = 12
    TRACKLIST_CHANGED = 13

    # Events (internal)
    IMAGE_AVAILABLE = 14
    MODEL_CHANGED = 15


@dataclass
class Message:
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
