import logging
import random
import threading
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, cast

from gi.repository import Gio, GLib, GObject

from argos.model.album import (
    AlbumModel,
    compare_by_album_name_func,
    compare_by_artist_name_func,
    compare_by_publication_date_func,
)
from argos.model.mixer import MixerModel
from argos.model.playback import PlaybackModel
from argos.model.playlist import PlaylistModel, playlist_compare_func
from argos.model.track import TrackModel
from argos.model.tracklist import TracklistModel, TracklistTrackModel
from argos.model.utils import PlaybackState, WithThreadSafePropertySetter

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)

__all__ = (
    "AlbumModel",
    "MixerModel",
    "Model",
    "PlaybackModel",
    "PlaybackState",
    "PlaylistModel",
    "TracklistModel",
    "TracklistTrackModel",
    "TrackModel",
)


class Model(WithThreadSafePropertySetter, GObject.Object):
    __gsignals__: Dict[str, Tuple[int, Any, Tuple]] = {
        "album-completed": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    network_available = GObject.Property(type=bool, default=False)
    connected = GObject.Property(type=bool, default=False)

    albums_loaded = GObject.Property(type=bool, default=False)
    tracklist_loaded = GObject.Property(type=bool, default=False)

    playback: PlaybackModel
    mixer: MixerModel
    albums: Gio.ListStore
    playlists: Gio.ListStore
    tracklist: TracklistModel

    def __init__(self, application: "Application", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.playback = PlaybackModel()
        self.mixer = MixerModel()
        self.albums = Gio.ListStore.new(AlbumModel)
        self.playlists = Gio.ListStore.new(PlaylistModel)
        self.tracklist = TracklistModel()

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

    def update_albums(self, albums: List[AlbumModel], album_sort_id: str) -> None:
        GLib.idle_add(
            partial(
                self._update_albums,
                albums,
                album_sort_id,
            )
        )

    def _get_album_compare_func(
        self, album_sort_id: str
    ) -> Callable[[AlbumModel, AlbumModel, None], int]:
        if album_sort_id == "by_album_name":
            return compare_by_album_name_func
        elif album_sort_id == "by_publication_date":
            return compare_by_publication_date_func

        if album_sort_id != "by_artist_name":
            LOGGER.warning(f"Unexpecting album sort identifier {album_sort_id!r}")

        return compare_by_artist_name_func

    def _update_albums(self, albums: List[AlbumModel], album_sort_id: str) -> None:
        if self.props.albums_loaded:
            self.props.albums_loaded = False

        compare_func = self._get_album_compare_func(album_sort_id)

        for album in albums:
            self.albums.insert_sorted(album, compare_func, None)

        LOGGER.info("Albums loaded")
        self.props.albums_loaded = True

    def sort_albums(self, album_sort_id: str) -> None:
        GLib.idle_add(
            partial(
                self._sort_albums,
                album_sort_id,
            )
        )

    def _sort_albums(self, album_sort_id: str) -> None:
        if self.props.albums_loaded:
            self.props.albums_loaded = False

        compare_func = self._get_album_compare_func(album_sort_id)
        self.albums.sort(compare_func, None)

        LOGGER.info("Albums sorted")
        self.props.albums_loaded = True

    def complete_album_description(
        self,
        album_uri: str,
        *,
        artist_name: Optional[str],
        num_tracks: Optional[int],
        num_discs: Optional[int],
        date: Optional[str],
        length: Optional[int],
        tracks: List[TrackModel],
    ) -> None:
        GLib.idle_add(
            partial(
                self._complete_album_description,
                album_uri,
                artist_name,
                num_tracks,
                num_discs,
                date,
                length,
                tracks,
            )
        )

    def _complete_album_description(
        self,
        album_uri: str,
        artist_name: Optional[str],
        num_tracks: Optional[int],
        num_discs: Optional[int],
        date: Optional[str],
        length: Optional[int],
        tracks: List[TrackModel],
    ) -> None:
        found = [album for album in self.albums if album.uri == album_uri]
        if len(found) == 0:
            LOGGER.warning(f"No album found with URI {album_uri!r}")
            return

        LOGGER.debug(f"Updating description of album with URI {album_uri!r}")
        album = found[0]

        album.artist_name = artist_name or ""
        album.num_tracks = num_tracks or -1
        album.num_discs = num_discs or -1
        album.date = date or ""
        album.length = length or -1

        for track in tracks:
            album.tracks.append(track)

        GLib.idle_add(
            partial(
                self.emit,
                "album-completed",
                album_uri,
            )
        )

    def choose_random_album(self) -> Optional[str]:
        def _choose_random_album_uri(event: threading.Event, uris: List[str]) -> None:
            try:
                album = random.choice(self.albums)
            except IndexError:
                pass
            uris.append(album.uri)
            event.set()

        event = threading.Event()
        uris: List[str] = []

        GLib.idle_add(_choose_random_album_uri, event, uris)
        return uris[0] if event.wait(timeout=1.0) else None

    def get_completed_album_uris(self) -> Optional[List[str]]:
        """Return URIs of completed albums.

        This function iterates on albums; It is guaranteed that the
        iteration is performed in the Gtk thread, so the album list is
        unchanged during the iteration.

        """

        def _collect_album_uris(event: threading.Event, uris: List[str]) -> None:
            for album in self.albums:
                if album.is_complete():
                    uris.append(album.uri)
            event.set()

        event = threading.Event()
        uris: List[str] = []

        GLib.idle_add(_collect_album_uris, event, uris)
        return uris if event.wait(timeout=1.0) else None

    def update_tracklist(self, version: Optional[int], tracks: Any) -> None:
        GLib.idle_add(
            partial(
                self._update_tracklist,
                version,
                tracks,
            )
        )

    def _update_tracklist(self, version: Optional[int], tracks: Any) -> None:
        if version is None:
            version = -1

        if self.props.tracklist_loaded and self.tracklist.props.version == version:
            LOGGER.info(f"Tracklist with version {version} already loaded")
            return

        if self.props.tracklist_loaded:
            self.props.tracklist_loaded = False

        self.tracklist.tracks.remove_all()

        for tl_track in tracks:
            tlid = cast(int, tl_track.get("tlid"))
            track = cast(Dict[str, Any], tl_track.get("track", {}))
            uri = cast(str, track.get("uri"))
            if not all([tlid, track, uri]):
                continue

            album = cast(Dict[str, Any], track.get("album", {}))
            artists = cast(
                List[Dict[str, Any]],
                track.get("artists", []) or album.get("artists", []),
            )
            artist = artists[0] if len(artists) > 0 else {}

            self.tracklist.tracks.append(
                TracklistTrackModel(
                    tlid=tlid,
                    uri=uri,
                    name=cast(str, track.get("name")),
                    track_no=cast(int, track.get("track_no", -1)),
                    disc_no=cast(int, track.get("disc_no", 1)),
                    length=cast(int, track.get("length", -1)),
                    artist_name=artist.get("name", ""),
                    album_name=album.get("name", ""),
                )
            )

        LOGGER.debug(f"Tracklist with {version} loaded")
        self.props.tracklist_loaded = True

    def update_playlists(self, playlists: List[PlaylistModel]) -> None:
        GLib.idle_add(
            partial(
                self._update_playlists,
                playlists,
            )
        )

    def _update_playlists(self, playlists: List[PlaylistModel]) -> None:
        self.playlists.remove_all()

        for playlist in playlists:
            self.playlists.append(playlist)

    def complete_playlist_description(
        self,
        playlist_uri: str,
        *,
        name: str,
        tracks: List[TrackModel],
        last_modified: GObject.TYPE_DOUBLE,
    ) -> None:
        GLib.idle_add(
            self._complete_playlist_description,
            playlist_uri,
            name,
            tracks,
            last_modified,
        )

    def _complete_playlist_description(
        self,
        playlist_uri: str,
        name: str,
        tracks: List[TrackModel],
        last_modified: GObject.TYPE_DOUBLE,
    ) -> None:
        LOGGER.debug(f"Completing playlist with URI {playlist_uri!r}")

        playlist = self.get_playlist(playlist_uri)
        if playlist is None:
            LOGGER.debug(f"Creation of playlist with URI {playlist_uri!r}")
            playlist = PlaylistModel(uri=playlist_uri, name=name)
            LOGGER.debug(f"Insertion of playlist with URI {playlist.uri!r}")
            self.playlists.insert_sorted(playlist, playlist_compare_func, None)
        else:
            if playlist.last_modified == last_modified:
                LOGGER.debug(f"Playlist with URI {playlist_uri!r} is up-to-date")
                return

            playlist.name = name
            playlist.tracks.remove_all()

        playlist.last_modified = last_modified
        for track in tracks:
            playlist.tracks.append(track)

    def get_album(self, uri: str) -> Optional[AlbumModel]:
        found_album = [a for a in self.albums if a.uri == uri]
        if len(found_album) == 0:
            LOGGER.debug(f"No album found with URI {uri!r}")
            return None
        elif len(found_album) > 1:
            LOGGER.warning(f"Ambiguous album URI {uri!r}")

        return found_album[0]

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
