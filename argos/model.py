"""Model.

"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PlaybackState(Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class Model:
    # TODO connected
    state: Optional[str] = None

    mute: Optional[bool] = None
    volume: Optional[int] = None

    track_uri: Optional[str] = field(default=None, repr=False)
    track_name: Optional[str] = None

    artist_uri: Optional[str] = field(default=None, repr=False)
    artist_name: Optional[str] = None

    image_path: Optional[Path] = field(default=None, compare=False)
