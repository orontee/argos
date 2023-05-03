import logging
import threading
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

from gi.repository import Gio, GLib, GObject

from argos.model.album import (
    AlbumInformationModel,
    AlbumModel,
    compare_albums_by_artist_name_func,
    compare_albums_by_last_modified_date_reversed_func,
    compare_albums_by_name_func,
    compare_albums_by_publication_date_func,
)
from argos.model.artist import ArtistModel, compare_artists_by_name_func
from argos.model.backends import (
    GenericBackend,
    MopidyBackend,
    MopidyBandcampBackend,
    MopidyPodcastBackend,
)
from argos.model.directory import DirectoryModel, compare_directories_func
from argos.model.library import LibraryModel
from argos.model.mixer import MixerModel
from argos.model.playback import PlaybackModel
from argos.model.playlist import PlaylistModel, compare_playlists_func
from argos.model.random import RandomTracksChoice, choose_random_tracks
from argos.model.searchresult import SearchResultModel
from argos.model.track import TrackModel, compare_tracks_by_name_func
from argos.model.tracklist import TracklistModel, TracklistTrackModel
from argos.model.utils import WithThreadSafePropertySetter

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)


class Model(WithThreadSafePropertySetter, GObject.Object):
    __gsignals__: Dict[str, Tuple[int, Any, Sequence]] = {
        "album-completed": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        "album-information-collected": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        "albums-sorted": (GObject.SIGNAL_RUN_FIRST, None, []),
        "directory-completion-progress": (
            GObject.SIGNAL_RUN_FIRST,
            None,
            (str, int, int),
        ),
        "directory-completed": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        "search-completed": (GObject.SIGNAL_RUN_FIRST, None, []),
    }

    network_available = GObject.Property(type=bool, default=False)
    connected = GObject.Property(type=bool, default=False)

    tracklist_loaded = GObject.Property(type=bool, default=False)

    library: LibraryModel
    playback: PlaybackModel
    mixer: MixerModel
    tracklist: TracklistModel
    playlists: Gio.ListStore
    backends: Gio.ListStore
    search_result: SearchResultModel

    def __init__(self, application: "Application", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._settings: Gio.Settings = application.props.settings

        self.library = LibraryModel()
        self.playback = PlaybackModel()
        self.mixer = MixerModel()
        self.tracklist = TracklistModel()
        self.playlists = Gio.ListStore.new(PlaylistModel)
        self.backends = Gio.ListStore.new(MopidyBackend)
        self.search_result = SearchResultModel()

        self.backends.append(MopidyPodcastBackend())
        self.backends.append(MopidyBandcampBackend())

        self.backends.append(GenericBackend())
        # Must be the last one!

        application._nm.connect("network-changed", self._on_nm_network_changed)

        self.playback.connect(
            "notify::current-tl-track-tlid",
            self._reset_current_tl_track_tlid_dependent_props,
        )

    def set_network_available(self, value: bool) -> None:
        self.set_property_in_gtk_thread("network_available", value)

    def set_connected(self, value: bool) -> None:
        self.set_property_in_gtk_thread("connected", value)

    def _on_nm_network_changed(
        self, network_monitor: Gio.NetworkMonitor, network_available: bool
    ) -> None:
        LOGGER.debug("Network monitor signal a network status change")
        self.set_property_in_gtk_thread("network_available", network_available)

    def _reset_current_tl_track_tlid_dependent_props(
        self, _1: GObject.Object, _2: GObject.ParamSpec
    ) -> None:
        self.playback.props.time_position = -1
        self.playback.props.image_path = ""
        self.playback.props.image_uri = ""

    def get_current_tl_track_uri(self) -> str:
        tlid = self.playback.props.current_tl_track_tlid
        tl_track = self.tracklist.get_tl_track(tlid)
        return tl_track.track.props.uri if tl_track else ""

    def _get_album_compare_func(
        self, album_sort_id: str
    ) -> Callable[[AlbumModel, AlbumModel, None], int]:
        if album_sort_id == "by_album_name":
            return compare_albums_by_name_func
        elif album_sort_id == "by_last_modified_date":
            return compare_albums_by_last_modified_date_reversed_func
        elif album_sort_id == "by_publication_date":
            return compare_albums_by_publication_date_func

        if album_sort_id != "by_artist_name":
            LOGGER.warning(f"Unexpecting album sort identifier {album_sort_id!r}")

        return compare_albums_by_artist_name_func

    def sort_albums(self, album_sort_id: str) -> None:
        def _sort_albums() -> None:
            compare_func = self._get_album_compare_func(album_sort_id)
            self.library.sort_albums(compare_func)

            LOGGER.info(f"Albums sorted with sort identifier {album_sort_id}")
            self.emit("albums-sorted")

        GLib.idle_add(_sort_albums)

    def complete_directory(
        self,
        uri: str,
        *,
        albums: List[AlbumModel],
        directories: List[DirectoryModel],
        playlists: List[PlaylistModel],
        tracks: List[TrackModel],
        wait_for_model_update: bool = False,
    ) -> None:
        event: Optional[threading.Event]
        if (
            wait_for_model_update
            and threading.current_thread() != threading.main_thread()
        ):
            # Main thread is dedicated to Gtk processing loop and
            # waiting for an event set from that thread would result
            # in a deadlock
            event = threading.Event()
        else:
            event = None

        def _complete_directory():
            directory = self.get_directory(uri)
            if directory is not None:
                directory.albums.remove_all()
                directory.directories.remove_all()
                directory.playlists.remove_all()
                directory.tracks.remove_all()

                album_sort_id = self._settings.get_string("album-sort")
                album_compare_func = self._get_album_compare_func(album_sort_id)
                for album in albums:
                    directory.albums.insert_sorted(album, album_compare_func, None)

                for subdir in directories:
                    directory.directories.insert_sorted(
                        subdir, compare_directories_func, None
                    )

                for playlist in playlists:
                    directory.playlists.insert_sorted(
                        playlist, compare_playlists_func, None
                    )

                for track in tracks:
                    directory.tracks.insert_sorted(
                        track, compare_tracks_by_name_func, None
                    )
            else:
                LOGGER.debug(f"Won't complete unknown directory with URI {uri}")

            if event is not None:
                event.set()

        GLib.idle_add(_complete_directory)

        if event is not None:
            event.wait(timeout=2.0)

    def complete_album_description(
        self,
        uri: str,
        *,
        artist_name: Optional[str],
        num_tracks: Optional[int],
        num_discs: Optional[int],
        date: Optional[str],
        last_modified: Optional[float],
        length: Optional[int],
        tracks: List[TrackModel],
    ) -> None:
        GLib.idle_add(
            partial(
                self._complete_album_description,
                uri,
                artist_name,
                num_tracks,
                num_discs,
                date,
                last_modified,
                length,
                tracks,
            )
        )

    def _complete_album_description(
        self,
        uri: str,
        artist_name: Optional[str],
        num_tracks: Optional[int],
        num_discs: Optional[int],
        date: Optional[str],
        last_modified: Optional[float],
        length: Optional[int],
        tracks: Sequence[TrackModel],
    ) -> None:
        album = self.get_album(uri)
        if album is None:
            return

        LOGGER.debug(f"Updating description of album with URI {uri!r}")
        album.artist_name = artist_name or ""
        album.num_tracks = num_tracks or -1
        album.num_discs = num_discs or -1
        album.date = date or ""
        album.last_modified = last_modified or -1
        album.length = length or -1

        album.tracks.remove_all()

        for track in tracks:
            album.tracks.append(track)

        GLib.idle_add(
            partial(
                self.emit,
                "album-completed",
                uri,
            )
        )

    def set_album_information(
        self,
        uri: str,
        album_abstract: Optional[str],
        artist_abstract: Optional[str],
    ) -> None:
        album = self.get_album(uri)
        if album is None:
            return

        def _set_album_information(
            model: "Model",
            information: AlbumInformationModel,
            album_abstract: str,
            artist_abstract: str,
        ):
            information.props.album_abstract = album_abstract
            information.props.artist_abstract = artist_abstract
            information.props.last_modified = datetime.now().timestamp()
            model.emit("album-information-collected", uri)

        LOGGER.debug(f"Setting album information of album with URI {uri!r}")
        GLib.idle_add(
            _set_album_information,
            self,
            album.information,
            album_abstract,
            artist_abstract,
        )

    def choose_random_album(self, strategy: str) -> RandomTracksChoice:
        return choose_random_tracks(self.library, strategy)

    def update_tracklist(
        self, version: Optional[int], tl_tracks: Sequence[TracklistTrackModel]
    ) -> None:
        GLib.idle_add(
            partial(
                self._update_tracklist,
                version,
                tl_tracks,
            )
        )

    def _update_tracklist(
        self, version: Optional[int], tl_tracks: Sequence[TracklistTrackModel]
    ) -> None:
        if version is None:
            version = -1

        if self.props.tracklist_loaded and self.tracklist.props.version == version:
            LOGGER.info(f"Tracklist with version {version} already loaded")
            return

        if self.props.tracklist_loaded:
            self.props.tracklist_loaded = False

        self.tracklist.tracks.remove_all()

        for tl_track in tl_tracks:
            self.tracklist.tracks.append(tl_track)

        LOGGER.debug(f"Tracklist with version {version} loaded")
        self.props.tracklist_loaded = True

    def update_playlists(self, playlists: Sequence[PlaylistModel]) -> None:
        GLib.idle_add(
            partial(
                self._update_playlists,
                playlists,
            )
        )

    def _update_playlists(self, playlists: Sequence[PlaylistModel]) -> None:
        self.playlists.remove_all()

        for playlist in playlists:
            self.playlists.insert_sorted(playlist, compare_playlists_func, None)

    def complete_playlist_description(
        self,
        playlist_uri: str,
        *,
        name: str,
        tracks: Sequence[TrackModel],
        last_modified: float,
        wait_for_model_update: bool = False,
    ) -> None:
        event: Optional[threading.Event]
        if (
            wait_for_model_update
            and threading.current_thread() != threading.main_thread()
        ):
            # Main thread is dedicated to Gtk processing loop and
            # waiting for an event set from that thread would result
            # in a deadlock
            event = threading.Event()
        else:
            event = None

        def _complete_playlist_description() -> None:
            LOGGER.debug(f"Completing playlist with URI {playlist_uri!r}")

            playlist = self.get_playlist(playlist_uri)
            if playlist is None:
                LOGGER.debug(f"Creation of playlist with URI {playlist_uri!r}")
                playlist = PlaylistModel(uri=playlist_uri, name=name)
                LOGGER.debug(f"Insertion of playlist with URI {playlist.uri!r}")
                self.playlists.insert_sorted(playlist, compare_playlists_func, None)
            else:
                if playlist.last_modified == last_modified:
                    LOGGER.debug(f"Playlist with URI {playlist_uri!r} is up-to-date")
                    return

                playlist.name = name
                playlist.tracks.remove_all()

            playlist.last_modified = last_modified
            for track in tracks:
                playlist.tracks.append(track)

        GLib.idle_add(_complete_playlist_description)

        if event is not None:
            event.wait(timeout=2.0)

    def get_album(self, uri: str) -> Optional[AlbumModel]:
        return self.library.get_album(uri)

    def get_directory(self, uri: Optional[str]) -> Optional[DirectoryModel]:
        return self.library.get_directory(uri)

    def get_track(self, uri: Optional[str]) -> Optional[TrackModel]:
        return self.library.get_track(uri)

    def get_playlist(self, uri: str) -> Optional[PlaylistModel]:
        found_playlist = [p for p in self.playlists if p.uri == uri]
        if len(found_playlist) == 0:
            LOGGER.debug(f"No playlist found with URI {uri!r}")
            return None
        elif len(found_playlist) > 1:
            LOGGER.warning(f"Ambiguous playlist URI {uri!r}")

        return found_playlist[0]

    def delete_playlist(self, uri: str) -> None:
        found_playlist = [
            (i, p) for (i, p) in enumerate(self.playlists) if p.uri == uri
        ]
        if len(found_playlist) == 0:
            LOGGER.debug(f"No playlist found with URI {uri!r}")
            return None
        elif len(found_playlist) > 1:
            LOGGER.warning(f"Ambiguous playlist URI {uri!r}")

        LOGGER.debug(f"Deletion of playlist with URI {uri!r}")

        GLib.idle_add(
            self.playlists.remove,
            found_playlist[0][0],
        )

    def complete_search_result(
        self,
        albums: Sequence[AlbumModel],
        artists: Sequence[ArtistModel],
        tracks: Sequence[TrackModel],
    ) -> None:
        def _complete_search_result() -> None:
            LOGGER.debug(
                f"Updating search results with {len(albums)} albums, "
                f"{len(artists)} artists, and {len(tracks)} tracks"
            )
            self.search_result.albums.remove_all()
            album_sort_id = self._settings.get_string("album-sort")
            album_compare_func = self._get_album_compare_func(album_sort_id)
            for album in albums:
                self.search_result.albums.insert_sorted(album, album_compare_func, None)

            self.search_result.artists.remove_all()
            for artist in artists:
                self.search_result.artists.insert_sorted(
                    artist, compare_artists_by_name_func, None
                )

            self.search_result.tracks.remove_all()
            for track in tracks:
                self.search_result.tracks.insert_sorted(
                    track, compare_tracks_by_name_func, None
                )

            self.emit("search-completed")

        GLib.idle_add(_complete_search_result)
