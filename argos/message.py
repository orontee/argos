from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class MessageType(Enum):
    # Commands
    TOGGLE_PLAYBACK_STATE = 0
    PLAY_PREV_TRACK = 1
    PLAY_NEXT_TRACK = 2
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
    ADD_TO_TRACKLIST = 14
    REMOVE_FROM_TRACKLIST = 15
    CLEAR_TRACKLIST = 16
    GET_TRACKLIST = 17
    GET_CURRENT_TRACKLIST_TRACK = 18
    PLAY = 19
    SET_CONSUME = 20
    SET_RANDOM = 21
    SET_REPEAT = 22
    SET_SINGLE = 23

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


@dataclass
class Message:
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
