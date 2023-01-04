from gi.repository import Gio, GObject

from argos.model.album import AlbumModel
from argos.model.playlist import PlaylistModel
from argos.model.track import TrackModel


class DirectoryModel(GObject.Object):
    """Model for a directory."""

    albums: Gio.ListStore
    directories: Gio.ListStore
    tracks: Gio.ListStore
    playlists: Gio.ListStore

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.albums = Gio.ListStore.new(AlbumModel)
        self.directories = Gio.ListStore.new(DirectoryModel)
        self.tracks = Gio.ListStore.new(TrackModel)
        self.playlists = Gio.ListStore.new(PlaylistModel)
