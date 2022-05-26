from gi.repository import Gio, GObject

from .track import TrackModel
from .utils import WithThreadSafePropertySetter


class PlaylistModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for a playlist.

    Setters are provided to change properties from any thread.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    last_modified = GObject.Property(type=str, default="")
    # Should use GObject.TYPE_LONG but conversion to gint fails on
    # Raspberry Pi 2 ARMv7 processor which is 32 bits

    tracks: Gio.ListStore

    def __init__(
        self,
        *,
        uri: str,
        name: str,
    ):
        super().__init__(
            uri=uri,
            name=name,
        )

        self.tracks = Gio.ListStore.new(TrackModel)
