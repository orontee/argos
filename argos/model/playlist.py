from gi.repository import Gio, GObject

from argos.model.track import TrackModel
from argos.model.utils import WithThreadSafePropertySetter


def playlist_compare_func(
    a: "PlaylistModel",
    b: "PlaylistModel",
    user_data: None,
) -> int:
    # URIs with argos scheme are virtual playlists not handled by
    # Mopidy service, and are expected to always be at the end of
    # playlist lists.
    if a.uri.startswith("argos:") and not b.uri.startswith("argos:"):
        return 1
    elif not a.uri.startswith("argos:") and b.uri.startswith("argos:"):
        return -1
    elif a.name < b.name:
        return -1
    elif a.name > b.name:
        return 1
    # a.name == b.name
    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1
    # a.uri == b.uri
    return 0


class PlaylistModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for a playlist.

    Setters are provided to change properties from any thread.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)

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
