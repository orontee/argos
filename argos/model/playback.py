from pathlib import Path
from typing import Optional, Union

from gi.repository import GObject

from argos.model.utils import PlaybackState, WithThreadSafePropertySetter


class PlaybackModel(WithThreadSafePropertySetter, GObject.Object):
    """Playback model.

    Setters are safe to be called from any thread.

    """

    state = GObject.Property(type=int)
    time_position = GObject.Property(type=int, default=-1)
    current_tl_track_tlid = GObject.Property(type=int, default=-1)

    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)

    def set_state(self, value: Union[int, str]) -> None:
        state = (
            PlaybackState.from_string(value)
            if isinstance(value, str)
            else PlaybackState(value)
        )

        self.set_property_in_gtk_thread("state", state)

    def set_time_position(
        self, value: int, *, block_handler: Optional[int] = None
    ) -> None:
        self.set_property_in_gtk_thread(
            "time_position",
            value,
            block_handler=block_handler,
        )

    def set_current_tl_track_tlid(self, value: Optional[int] = None) -> None:
        if value is None:
            value = -1
        self.set_property_in_gtk_thread("current_tl_track_tlid", value, force=True)
        # Force update since current tracklist track is requested
        # after events notifying that tracklist has changed and views
        # may lost the current track list track identifier while
        # updating the tracklist.

    def set_image_path(self, value: Union[str, Path, None]) -> None:
        if isinstance(value, Path):
            path = str(value)
        elif value is None:
            path = ""
        else:
            path = value
        self.set_property_in_gtk_thread("image_path", path)

    def set_image_uri(self, value: str) -> None:
        self.set_property_in_gtk_thread("image_uri", value)
