from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class MessageType(Enum):
    # Commands
    TOGGLE_PLAYBACK_STATE = 0
    PLAY_PREV_TRACK = 1
    PLAY_NEXT_TRACK = 2
    ADD_TO_TRACKLIST = 3
    PLAY_TRACKS = 4
    PLAY_FAVORITE_PLAYLIST = 5
    SEEK = 6
    SET_VOLUME = 7
    LIST_PLAYLISTS = 8
    FETCH_TRACK_IMAGE = 9
    FETCH_ALBUM_IMAGES = 10
    IDENTIFY_PLAYING_STATE = 11
    BROWSE_ALBUMS = 12
    COMPLETE_ALBUM_DESCRIPTION = 13

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


@dataclass
class Message:
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
