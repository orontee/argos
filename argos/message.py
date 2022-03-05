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
    SEEK = 5
    SET_VOLUME = 6
    LIST_PLAYLISTS = 7

    # Events (frow websocket)
    TRACK_PLAYBACK_STARTED = 20
    TRACK_PLAYBACK_PAUSED = 21
    TRACK_PLAYBACK_RESUMED = 22
    TRACK_PLAYBACK_ENDED = 23
    PLAYBACK_STATE_CHANGED = 24
    MUTE_CHANGED = 25
    VOLUME_CHANGED = 26
    TRACKLIST_CHANGED = 27
    SEEKED = 28

    # Events (internal)
    IMAGE_AVAILABLE = 40
    MODEL_CHANGED = 41
    MOPIDY_BASE_URL_CHANGED = 42
    MOPIDY_WEBSOCKET_CONNECTED = 43
    NETWORK_AVAILABLE_CHANGED = 44


@dataclass
class Message:
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
