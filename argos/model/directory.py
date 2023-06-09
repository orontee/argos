import locale
import logging
from typing import Callable, Optional

from gi.repository import Gio, GObject

from argos.model.album import AlbumModel
from argos.model.artist import ArtistModel
from argos.model.playlist import PlaylistModel
from argos.model.track import TrackModel

LOGGER = logging.getLogger(__name__)


def compare_directories_func(
    a: "DirectoryModel",
    b: "DirectoryModel",
    user_data: None,
) -> int:
    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1
    # a.uri == b.uri
    return 0


class DirectoryModel(GObject.Object):
    """Model for a directory.

    The directory with URI equal to an empty string represents the
    "root directory" of the library.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)

    albums: Gio.ListStore
    artists: Gio.ListStore
    directories: Gio.ListStore
    tracks: Gio.ListStore
    playlists: Gio.ListStore

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.albums = Gio.ListStore.new(AlbumModel)
        self.artists = Gio.ListStore.new(ArtistModel)
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
        return any(
            [
                len(self.albums) > 0,
                len(self.artists) > 0,
                len(self.directories) > 0,
                len(self.tracks) > 0,
                len(self.playlists) > 0,
            ]
        )

    def visit_albums(
        self,
        *,
        visitor: Callable[[AlbumModel, "DirectoryModel"], None],
    ) -> None:
        LOGGER.debug(f"Visiting albums in directory {self.props.name}")

        for album in self.albums:
            visitor(album, self)

        for directory in self.directories:
            directory.visit_albums(visitor=visitor)

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

    def get_artist(self, uri: str) -> Optional[ArtistModel]:
        """Recursively search for an artist with given URI.

        Args:
            uri: URI of the artist to return.

        Returns:
            Artist with URI equal to ``uri`` or None if no
            artist is found.

        """
        if self.props.uri != "":
            if not self._has_related_scheme(uri):
                # scheme is used by Mopidy to route browse requests to the
                # correct backend, thus no need to search if schemes
                # doesn't match
                return None

        for artist in self.artists:
            if artist.props.uri == uri:
                return artist

        for directory in self.directories:
            found = directory.get_artist(uri)
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

        for album in self.albums:
            for track in album.tracks:
                if track.props.uri == uri:
                    return track

        for playlist in self.playlists:
            for track in playlist.tracks:
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
