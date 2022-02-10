import asyncio
import logging
from pathlib import Path
from typing import Any, Set

from .message import Message, MessageType
from .model import Model, PlaybackState

LOGGER = logging.getLogger(__name__)


class ModelAccessor:
    def __init__(self, *, model: Model, message_queue: asyncio.Queue):
        self._model = model
        self._message_queue = message_queue
        self._changed: Set[str] = set()

    async def __aenter__(self) -> "ModelAccessor":
        return self

    async def __aexit__(self, *args) -> bool:
        if len(self._changed):
            LOGGER.debug(f"Model changed properties: {self._changed}")
            await self._message_queue.put(
                Message(MessageType.MODEL_CHANGED, {"changed": self._changed})
            )

        self._changed = set()
        return False

    def clear_tl(self) -> None:
        if self._model.track_uri:
            self._model.track_uri = None
            self._changed.add("track_uri")

        if self._model.track_name:
            self._model.track_name = None
            self._changed.add("track_name")

        if self._model.track_length:
            self._model.track_length = None
            self._changed.add("track_length")

        if self._model.time_position:
            self._model.time_position = 0
            self._changed.add("time_position")

        if self._model.artist_uri:
            self._model.artist_uri = None
            self._changed.add("artist_uri")

        if self._model.artist_name:
            self._model.artist_name = None
            self._changed.add("artist_name")

        if self._model.image_path:
            self._model.image_path = None
            self._changed.add("image_path")

    def update_from(
        self,
        *,
        connected: Any = None,
        raw_state: Any = None,
        mute: Any = None,
        volume: Any = None,
        time_position: Any = None,
        tl_track: Any = None,
        image_path: Any = None,
    ) -> None:
        if connected is not None:
            connected = True if connected is True else False
            if self._model.connected != connected:
                self._model.connected = connected
                self._changed.add("connected")

        if raw_state is not None:
            try:
                state = PlaybackState(raw_state)
            except ValueError:
                LOGGER.error(f"Unexpected state {raw_state!r}")
                state = None

            if self._model.state != state:
                self._model.state = state
                self._changed.add("state")

        props = {"mute": mute, "volume": volume}
        for prop_name in props:
            value = props[prop_name]
            if value is not None:
                if getattr(self._model, prop_name) != value:
                    setattr(self._model, prop_name, value)
                    self._changed.add(prop_name)

        if time_position is not None:
            if self._model.time_position != time_position:
                self._model.time_position = time_position
                self._changed.add("time_position")

        if tl_track is not None:
            # TODO check dict
            track = tl_track.get("track", {})

            track_uri = track.get("uri")
            track_name = track.get("name")
            track_length = track.get("length")
            if self._model.track_uri != track_uri:
                self._model.track_uri = track_uri
                self._model.track_name = track_name
                self._model.track_length = track_length
                self._model.image_path = None
                self._changed |= set(
                    [
                        "track_uri",
                        "track_name",
                        "track_length",
                        "time_position",
                        "image_path",
                    ]
                )

            artists = track.get("artists", [{}])
            artist = artists[0]
            artist_uri = artist.get("uri")
            artist_name = artist.get("name")
            if self._model.artist_uri != artist_uri:
                self._model.artist_uri = artist_uri
                self._model.artist_name = artist_name
                self._changed |= set(["artist_uri", "artist_name"])

        if image_path is not None:
            path = Path(image_path)
            if self._model.image_path != path:
                self._model.image_path = path
                self._changed.add("image_path")
