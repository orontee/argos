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

    def _set_model_attr(self, name, value) -> None:
        if not hasattr(self._model, name):
            LOGGER.warning(f"Attempt to set unexpected attribute {name}")

        if getattr(self._model, name) != value:
            setattr(self._model, name, value)
            self._changed.add(name)

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
        self._set_model_attr("track_uri", None)
        self._set_model_attr("track_name", None)
        self._set_model_attr("track_length", None)
        self._set_model_attr("time_position", None)
        self._set_model_attr("artist_uri", None)
        self._set_model_attr("artist_name", None)
        self._set_model_attr("image_path", None)

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
            self._set_model_attr("connected", connected)

        if raw_state is not None:
            try:
                state = PlaybackState(raw_state)
            except ValueError:
                LOGGER.error(f"Unexpected state {raw_state!r}")
                state = None

            self._set_model_attr("state", state)

        props = {"mute": mute, "volume": volume}
        for prop_name in props:
            value = props[prop_name]
            if value is not None:
                self._set_model_attr(prop_name, value)

        if time_position is not None:
            self._set_model_attr("time_position", time_position)

        if tl_track is not None:
            # TODO check dict
            track = tl_track.get("track", {})

            track_uri = track.get("uri")
            track_name = track.get("name")
            track_length = track.get("length")

            self._set_model_attr("track_uri", track_uri)
            self._set_model_attr("track_name", track_name)
            self._set_model_attr("track_length", track_length)
            self._set_model_attr("time_position", None)
            self._set_model_attr("image_path", None)

            artists = track.get("artists", [{}])
            artist = artists[0]
            artist_uri = artist.get("uri")
            artist_name = artist.get("name")

            self._set_model_attr("artist_uri", artist_uri)
            self._set_model_attr("artist_name", artist_name)

        if image_path is not None:
            path = Path(image_path)
            self._set_model_attr("image_path", path)
