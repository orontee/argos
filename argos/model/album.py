from typing import List, Optional

from gi.repository import Gio, GObject

from argos.model.backends import MopidyBackend
from argos.model.track import TrackModel
from argos.model.utils import WithThreadSafePropertySetter


def compare_by_album_name_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.name < b.name:
        return -1
    elif a.name > b.name:
        return 1
    # a.name == b.name
    if a.artist_name < b.artist_name:
        return -1
    elif a.artist_name > b.artist_name:
        return 1
    # a.artist_name == b.artist_name
    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1
    # a.uri == b.uri
    return 0


def compare_by_artist_name_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.artist_name < b.artist_name:
        return -1
    elif a.artist_name > b.artist_name:
        return 1
    # a.artist_name == b.artist_name
    if a.date < b.date:
        return -1
    elif a.date > b.date:
        return 1
    # a.date == b.date
    if a.name < b.name:
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


def compare_by_last_modified_date_reversed_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.last_modified > b.last_modified:
        return -1
    elif a.last_modified < b.last_modified:
        return 1
    # a.last_modified == b.last_modified
    if a.name < b.name:
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


def compare_by_publication_date_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.date < b.date:
        return -1
    elif a.date > b.date:
        return 1
    # a.date == b.date
    if a.name < b.name:
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


class AlbumModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for an album.

    Setters are provided to change properties from any thread.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)
    backend = GObject.Property(type=MopidyBackend)
    artist_name = GObject.Property(type=str)
    num_tracks = GObject.Property(type=int)
    num_discs = GObject.Property(type=int)
    date = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)
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
        artist_name: Optional[str] = None,
        num_tracks: Optional[int] = None,
        num_discs: Optional[int] = None,
        date: Optional[str] = None,
        last_modified: Optional[float] = None,
        length: Optional[int] = None,
        tracks: Optional[List[TrackModel]] = None,
    ):
        super().__init__(
            uri=uri,
            name=name,
            image_path=image_path,
            image_uri=image_uri,
            backend=backend,
        )
        self.tracks = Gio.ListStore.new(TrackModel)
        self.artist_name = artist_name or ""
        self.num_tracks = num_tracks or -1
        self.num_discs = num_discs or -1
        self.date = date or ""
        self.last_modified = last_modified or -1
        self.length = length or -1

        if tracks is not None:
            for t in tracks:
                self.tracks.append(t)

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
        return self.backend.static_albums and len(self.tracks) > 0
