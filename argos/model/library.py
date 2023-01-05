import logging
from typing import Callable, List, Optional

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

    def get_album(self, uri: str) -> Optional[AlbumModel]:
        return self.props.root_directory.get_album(uri)

    def get_album_uris(
        self, *, excluded_backends: Optional[List[str]] = None
    ) -> List[str]:
        return list(
            self.props.root_directory.collect_album_uris(
                excluded_backends=excluded_backends
            )
        )

    def get_directory(self, uri: Optional[str]) -> Optional[DirectoryModel]:
        return self.props.root_directory.get_directory(uri)

    def get_track(self, uri: Optional[str]) -> Optional[TrackModel]:
        return self.props.root_directory.get_track(uri)

    def get_parent_uris(self, uri: str) -> List[str]:
        if uri == MOPIDY_LOCAL_ALBUMS_URI:
            return ["", "local:directory"]
        elif uri == "":
            return []
        raise NotImplementedError
