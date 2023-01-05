import logging
from typing import Callable, List, Optional, Set

from gi.repository import Gio, GObject

from argos.model.album import AlbumModel
from argos.model.playlist import PlaylistModel
from argos.model.track import TrackModel

LOGGER = logging.getLogger(__name__)


class DirectoryModel(GObject.Object):
    """Model for a directory.

    The directory with URI equal to an empty string represents the
    "root directory" of the library.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)

    albums: Gio.ListStore
    directories: Gio.ListStore
    tracks: Gio.ListStore
    playlists: Gio.ListStore

    # TODO artists

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.albums = Gio.ListStore.new(AlbumModel)
        self.directories = Gio.ListStore.new(DirectoryModel)
        self.tracks = Gio.ListStore.new(TrackModel)
        self.playlists = Gio.ListStore.new(PlaylistModel)

    def sort_albums(
        self,
        compare_func: Callable[[AlbumModel, AlbumModel, None], int],
    ) -> None:
        self.albums.sort(compare_func, None)

        for directory in self.directories:
            directory.sort_albums(compare_func)

    def is_complete(self) -> bool:
        return (
            len(self.albums) > 0
            or len(self.directories) > 0
            or len(self.tracks) > 0
            or len(self.playlists) > 0
        )

    def collect_album_uris(
        self,
        *,
        excluded_backends: List[str] = None,
    ) -> Set[str]:
        LOGGER.debug(f"Collecting album URIs in directory {self.props.name}")
        if excluded_backends is None:
            excluded_backends = []

        uris: Set[str] = set(
            [
                album.uri
                for album in self.albums
                if album.backend.props.settings_key not in excluded_backends
            ]
        )
        # backend should be stored on directory, no?

        for directory in self.directories:
            uris |= directory.collect_album_uris(excluded_backends=excluded_backends)

        return uris

    def get_album(self, uri: str) -> Optional[AlbumModel]:
        """Recursively search for an album with given URI.

        Args:
            uri: URI of the album to return.

        Returns:
            Album with URI equal to ``uri`` or None if no
            album is found.

        """
        if self.props.uri != "":
            if not self._has_related_scheme(uri):
                # scheme is used by Mopidy to route browse requests to the
                # correct backend, thus no need to search if schemes
                # doesn't match
                return None

        for album in self.albums:
            if album.props.uri == uri:
                return album

        for directory in self.directories:
            found = directory.get_album(uri)
            if found is not None:
                return found

        return None

    def get_directory(self, uri: str) -> Optional["DirectoryModel"]:
        """Recursively search for a directory with given URI.

        Args:
            uri: URI of the directory to return.

        Returns:
            Directory with URI equal to ``uri`` or None if no
            directory is found.

        """
        if self.props.uri == uri:
            return self

        if self.props.uri != "":
            # not root directory

            if not self._has_related_scheme(uri):
                # scheme is used by Mopidy to route browse requests to
                # the correct backend, thus no need to search in child
                # directories if schemes doesn't match
                return None

        for directory in self.directories:
            found = directory.get_directory(uri)
            if found is not None:
                return found

        return None

    def get_playlist(self, uri: str) -> Optional[PlaylistModel]:
        """Recursively search for an playlist with given URI.

        Args:
            uri: URI of the playlist to return.

        Returns:
            Playlist with URI equal to ``uri`` or None if no
            playlist is found.

        """
        if self.props.uri != "":
            if not self._has_related_scheme(uri):
                # scheme is used by Mopidy to route browse requests to the
                # correct backend, thus no need to search if schemes
                # doesn't match
                return None

        for playlist in self.playlists:
            if playlist.props.uri == uri:
                return playlist

        for directory in self.directories:
            found = directory.get_playlist(uri)
            if found is not None:
                return found

        return None

    def get_track(self, uri: str) -> Optional[TrackModel]:
        """Recursively search for a track with given URI.

        Args:
            uri: URI of the track to return.

        Returns:
            Track with URI equal to ``uri`` or None if no
            track is found.

        """
        if self.props.uri != "":
            if not self._has_related_scheme(uri):
                # scheme is used by Mopidy to route browse requests to the
                # correct backend, thus no need to search if schemes
                # doesn't match
                return None

        for track in self.tracks:
            if track.props.uri == uri:
                return track

        for directory in self.directories:
            found = directory.get_track(uri)
            if found is not None:
                return found

        return None

    def _has_related_scheme(self, uri: str) -> bool:
        """Check whether the given URI has a scheme related to this directory.

        Args:
            uri: URI whose scheme is to be checked.

        Returns:
            True if ``uri`` has a scheme related to this directory.
        """
        scheme = self.props.uri.split(":")[0].split("+")[0]
        return uri.startswith(scheme)
