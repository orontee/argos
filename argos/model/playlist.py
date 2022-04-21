from gi.repository import Gio, GObject

from .track import TrackModel
from .utils import WithThreadSafePropertySetter


class PlaylistModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for a playlist.

    Setters are provided to change properties from any thread.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)

    # TODO store last_modified

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
