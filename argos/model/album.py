from gi.repository import Gio, GObject

from argos.backends import MopidyBackend
from argos.model.track import TrackModel
from argos.model.utils import WithThreadSafePropertySetter


class AlbumModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for an album.

    Setters are provided to change properties from any thread.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)

    artist_name = GObject.Property(type=str)
    num_tracks = GObject.Property(type=int)
    num_discs = GObject.Property(type=int)
    date = GObject.Property(type=str)
    length = GObject.Property(type=int)

    tracks: Gio.ListStore

    def __init__(
        self,
        *,
        uri: str,
        name: str,
        image_path: str,
        image_uri: str,
        backend: MopidyBackend,
    ):
        super().__init__(
            uri=uri,
            name=name,
            image_path=image_path,
            image_uri=image_uri,
        )
        self._backend = backend
        self.tracks = Gio.ListStore.new(TrackModel)

    def set_name(self, value: str) -> None:
        self.set_property_in_gtk_thread("name", value)

    def set_artist_name(self, value: str) -> None:
        self.set_property_in_gtk_thread("artist_name", value)

    def set_num_tracks(self, value: int) -> None:
        self.set_property_in_gtk_thread("num_tracks", value)

    def set_num_discs(self, value: int) -> None:
        self.set_property_in_gtk_thread("num_discs", value)

    def set_length(self, value: int) -> None:
        self.set_property_in_gtk_thread("length", value)

    def is_complete(self) -> bool:
        return self._backend.static_albums and len(self.tracks) > 0
