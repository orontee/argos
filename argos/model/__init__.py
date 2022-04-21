from functools import partial
import logging
from typing import Any, cast, Dict, List, Optional, Tuple, TYPE_CHECKING

from gi.repository import Gio, GLib, GObject

from .album import AlbumModel
from .mixer import MixerModel
from .playback import PlaybackModel
from .playlist import PlaylistModel
from .track import TrackModel
from .tracklist import TracklistModel, TracklistTrackModel
from .utils import PlaybackState, WithThreadSafePropertySetter

if TYPE_CHECKING:
    from ..app import Application

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
        "playlist-completed": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    network_available = GObject.Property(type=bool, default=False)
    connected = GObject.Property(type=bool, default=False)

    albums_loaded = GObject.Property(type=bool, default=False)
    tracklist_loaded = GObject.Property(type=bool, default=False)
    playlists_loaded = GObject.Property(type=bool, default=False)

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

    def update_albums(self, value: Any) -> None:
        GLib.idle_add(
            partial(
                self._update_albums,
                value,
            )
        )

    def _update_albums(self, value: Any) -> None:
        if self.props.albums_loaded:
            self.props.albums_loaded = False
            self.albums.remove_all()

        for v in value:
            name = v.get("name")
            uri = v.get("uri")
            if not name or not uri:
                continue

            image_path = v.get("image_path", "")
            image_uri = v.get("image_uri", "")
            album = AlbumModel(
                uri=uri, name=name, image_path=image_path, image_uri=image_uri
            )
            self.albums.append(album)

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
        found = [album for album in self.albums if album.uri == album_uri]
        if len(found) == 0:
            LOGGER.warning(f"No album found with URI {album_uri!r}")
            return

        LOGGER.debug(f"Updating description of album with URI {album_uri!r}")
        album = found[0]

        album.artist_name = artist_name
        album.num_tracks = num_tracks
        album.num_discs = num_discs
        album.date = date
        album.length = length
        album.tracks = tracks

        GLib.idle_add(
            partial(
                self.emit,
                "album-completed",
                album_uri,
            )
        )

    def update_tracklist(self, version: Optional[int], tracks: Any) -> None:
        GLib.idle_add(
            partial(
                self._update_tracklist,
                version,
                tracks,
            )
        )

    def _update_tracklist(self, version: Optional[int], tracks: Any) -> None:
        if self.tracklist.props.version == version:
            return

        if self.props.tracklist_loaded:
            self.props.tracklist_loaded = False

        self.tracklist.tracks.remove_all()

        if not version:
            self.tracklist.props.version = -1
            return

        for tl_track in tracks:
            tlid = cast(int, tl_track.get("tlid"))
            track = cast(Dict[str, Any], tl_track.get("track", {}))
            uri = cast(str, track.get("uri"))
            if not all([tlid, track, uri]):
                continue

            album = cast(Dict[str, Any], track.get("album", {}))
            artists = cast(List[Dict[str, Any]], album.get("artists", []))
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

        self.props.tracklist_loaded = True

    def update_playlists(self, value: Any) -> None:
        GLib.idle_add(
            partial(
                self._update_playlists,
                value,
            )
        )

    def _update_playlists(self, value: Any) -> None:
        if self.props.playlists_loaded:
            self.props.playlists_loaded = False
            self.playlists.remove_all()

        for v in value:
            name = v.get("name")
            uri = v.get("uri")
            if not name or not uri:
                continue

            playlist = PlaylistModel(uri=uri, name=name)
            self.playlists.append(playlist)

        self.props.playlists_loaded = True

    def complete_playlist_description(
        self,
        playlist_uri: str,
        *,
        tracks: List[TrackModel],
    ) -> None:
        found = [
            playlist for playlist in self.playlists if playlist.uri == playlist_uri
        ]
        if len(found) == 0:
            LOGGER.warning(f"No playlist found with URI {playlist_uri!r}")
            return

        LOGGER.debug(f"Updating description of playlist with URI {playlist_uri!r}")
        playlist = found[0]

        playlist.tracks.remove_all()

        for track in tracks:
            playlist.tracks.append(track)

        GLib.idle_add(
            partial(
                self.emit,
                "playlist-completed",
                playlist_uri,
            )
        )

    def get_playlist(self, uri: str) -> Optional[PlaylistModel]:
        found_playlist = [p for p in self.playlists if p.uri == uri]
        if len(found_playlist) == 0:
            LOGGER.warning(f"Playlist URI not found, {uri!r}")
            return None
        elif len(found_playlist) > 1:
            LOGGER.warning(f"Ambiguous playlist URI {uri!r}")

        return found_playlist[0]
