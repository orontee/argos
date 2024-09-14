import locale

from gi.repository import Gio, GObject

from argos.model.status import ModelFlag
from argos.model.track import TrackModel


def compare_playlists_func(
    a: "PlaylistModel",
    b: "PlaylistModel",
    user_data: None,
) -> int:
    # Virtual playlists aren't handled by Mopidy service, and are
    # expected to always be at the end of playlist lists
    if a.is_virtual and not b.is_virtual:
        return 1
    elif not a.is_virtual and b.is_virtual:
        return -1

    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1
    # a.uri == b.uri
    return 0


class PlaylistModel(GObject.Object):
    """Model for a playlist."""

    uri = GObject.Property(type=str)
    flags = GObject.Property(type=GObject.TYPE_INT, default=ModelFlag.NO_FLAG.value)
    name = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)
    tracks: Gio.ListStore

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracks = Gio.ListStore.new(TrackModel)

    @property
    def is_virtual(self) -> bool:
        return self.uri.startswith("argos:")
