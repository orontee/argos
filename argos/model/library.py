import logging
from typing import Callable

from gi.repository import GObject

from argos.model.album import AlbumModel
from argos.model.directory import DirectoryModel
from argos.model.track import TrackModel

LOGGER = logging.getLogger(__name__)

MOPIDY_LOCAL_ALBUMS_URI = "local:directory?type=album"


class LibraryModel(GObject.Object):
    """Model for whole library."""

    default_uri = GObject.Property(type=str)
    root_directory = GObject.Property(
        type=DirectoryModel,
        default=DirectoryModel(uri="", name="root"),
        flags=GObject.ParamFlags.READABLE,
    )

    def sort_albums(
        self,
        compare_func: Callable[[AlbumModel, AlbumModel, None], int],
    ) -> None:
        self.props.root_directory.sort_albums(compare_func)

    def get_album(self, uri: str) -> AlbumModel | None:
        return self.props.root_directory.get_album(uri)

    def visit_albums(
        self, *, visitor=Callable[[AlbumModel, DirectoryModel], None]
    ) -> None:
        self.props.root_directory.visit_albums(visitor=visitor)

    def get_directory(self, uri: str | None) -> DirectoryModel | None:
        return self.props.root_directory.get_directory(uri)

    def sort_tracks(
        self,
        compare_func: Callable[[TrackModel, TrackModel, None], int],
    ) -> None:
        self.props.root_directory.sort_tracks(compare_func)

    def get_track(self, uri: str | None) -> TrackModel | None:
        return self.props.root_directory.get_track(uri)

    def get_parent_uris(self, uri: str) -> list[str]:
        if uri == MOPIDY_LOCAL_ALBUMS_URI:
            return ["", "local:directory"]
        elif uri == "":
            return []
        raise NotImplementedError
