import locale
from typing import Optional, Sequence

from gi.repository import Gio, GObject

from argos.model.backends import MopidyBackend
from argos.model.track import TrackModel


def compare_albums_by_name_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    artist_names_comp = locale.strcoll(a.artist_name, b.artist_name)
    if artist_names_comp != 0:
        return artist_names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


def compare_albums_by_artist_name_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    artist_names_comp = locale.strcoll(a.artist_name, b.artist_name)
    if artist_names_comp != 0:
        return artist_names_comp

    if a.date < b.date:
        return -1
    elif a.date > b.date:
        return 1

    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


def compare_albums_by_last_modified_date_reversed_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.last_modified > b.last_modified:
        return -1
    elif a.last_modified < b.last_modified:
        return 1

    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


def compare_albums_by_publication_date_func(
    a: "AlbumModel",
    b: "AlbumModel",
    user_data: None,
) -> int:
    if a.date < b.date:
        return -1
    elif a.date > b.date:
        return 1

    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


class AlbumInformationModel(GObject.Object):
    """Model for album information."""

    album_abstract = GObject.Property(type=str)
    artist_abstract = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)


class AlbumModel(GObject.Object):
    """Model for an album."""

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)
    backend = GObject.Property(type=MopidyBackend)
    artist_name = GObject.Property(type=str)
    num_tracks = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    num_discs = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    date = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)
    length = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    release_mbid = GObject.Property(type=str)
    information = GObject.Property(type=AlbumInformationModel)

    tracks: Gio.ListStore

    def __init__(
        self,
        *args,
        artist_name: Optional[str] = None,
        num_tracks: Optional[int] = None,
        num_discs: Optional[int] = None,
        date: Optional[str] = None,
        last_modified: Optional[float] = None,
        length: Optional[int] = None,
        tracks: Optional[Sequence[TrackModel]] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if artist_name is not None:
            self.artist_name = artist_name

        if num_tracks is not None:
            self.num_tracks = num_tracks

        if num_discs is not None:
            self.num_discs = num_discs

        if date is not None:
            self.date = date

        if last_modified is not None:
            self.last_modified = last_modified

        if length is not None:
            self.length = length

        self.information = AlbumInformationModel()
        self.tracks = Gio.ListStore.new(TrackModel)

        if tracks is not None:
            for t in tracks:
                self.tracks.append(t)

    def is_complete(self) -> bool:
        return self.backend.static_albums and len(self.tracks) > 0
