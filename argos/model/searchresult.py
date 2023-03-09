import logging

from gi.repository import Gio, GObject

from argos.model.album import AlbumModel
from argos.model.artist import ArtistModel
from argos.model.track import TrackModel

LOGGER = logging.getLogger(__name__)


class SearchResultModel(GObject.Object):
    """Model for search result."""

    albums: Gio.ListStore
    artists: Gio.ListStore
    tracks: Gio.ListStore

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.albums = Gio.ListStore.new(AlbumModel)
        self.artists = Gio.ListStore.new(ArtistModel)
        self.tracks = Gio.ListStore.new(TrackModel)
