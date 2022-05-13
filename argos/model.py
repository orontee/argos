import contextlib
from dataclasses import dataclass, field
from enum import IntEnum
from functools import partial
import logging
from typing import (
    Any,
    cast,
    ContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    TYPE_CHECKING,
)

from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from .app import Application

LOGGER = logging.getLogger(__name__)


class HasPropertiesProtocol(Protocol):
    def get_property(self, name: str) -> Any:
        ...

    def set_property(self, name: str, value: Any) -> None:
        ...

    def handler_block(self, handler_id: int) -> ContextManager:
        ...


class WithSafePropertySetterMixin:
    def set_property_in_gtk_thread(
        self: HasPropertiesProtocol,
        name: str,
        value: Any,
        *,
        force: bool = False,
        block_handler: Optional[int] = None,
    ) -> None:
        current_value = self.get_property(name)
        if force or current_value != value:
            if block_handler is not None:
                cm = self.handler_block(block_handler)
            else:
                cm = contextlib.nullcontext()

            def wrapped_setter() -> None:
                LOGGER.debug(f"Updating {name!r} from {current_value!r} to {value!r}")
                with cm:
                    self.set_property(name, value)

            GLib.idle_add(wrapped_setter)
        else:
            LOGGER.debug(f"Property {name!r} already equal to {value!r}")


class PlaybackState(IntEnum):
    UNKNOWN = 0
    PLAYING = 1
    PAUSED = 2
    STOPPED = 3

    @staticmethod
    def from_string(value: str) -> "PlaybackState":
        if value == "playing":
            state = PlaybackState.PLAYING
        elif value == "paused":
            state = PlaybackState.PAUSED
        elif value == "stopped":
            state = PlaybackState.STOPPED
        else:
            state = PlaybackState.UNKNOWN
            LOGGER.error(f"Unexpected state {value!r}")
        return state


@dataclass
class Track:
    uri: str
    name: str
    track_no: int
    disc_no: int = 1
    length: Optional[int] = None


@dataclass
class TracklistTrack:
    tlid: int
    track: Track
    artist_name: str
    album_name: str


@dataclass
class Tracklist:
    version: int = -1
    tracks: List[TracklistTrack] = field(default_factory=list)


@dataclass
class Album:
    uri: str
    name: str
    image_path: str
    image_uri: str
    artist_name: Optional[str] = None
    num_tracks: Optional[int] = None
    num_discs: Optional[int] = None
    date: Optional[str] = None
    length: Optional[int] = None
    tracks: List[Track] = field(default_factory=list)


class PlaybackModel(GObject.GObject, WithSafePropertySetterMixin):
    state = GObject.Property(type=int, default=PlaybackState.UNKNOWN)
    time_position = GObject.Property(type=int, default=-1)  # ms
    current_tl_track_tlid = GObject.Property(type=int, default=-1)

    def set_state(self, value: str) -> None:
        state = PlaybackState.from_string(value)
        self.set_property_in_gtk_thread("state", state)

    def set_time_position(
        self, value: int, *, block_handler: Optional[int] = None
    ) -> None:
        self.set_property_in_gtk_thread(
            "time_position", value, block_handler=block_handler
        )


class MixerModel(GObject.GObject, WithSafePropertySetterMixin):
    volume = GObject.Property(type=int, default=0)
    mute = GObject.Property(type=bool, default=False)

    def set_volume(self, value: str) -> None:
        self.set_property_in_gtk_thread("volume", value)

    def set_mute(self, value: str) -> None:
        self.set_property_in_gtk_thread("mute", value)


class Model(GObject.GObject, WithSafePropertySetterMixin):
    __gsignals__ = {"album-completed": (GObject.SIGNAL_RUN_FIRST, None, (str,))}

    network_available = GObject.Property(type=bool, default=False)
    connected = GObject.Property(type=bool, default=False)

    playback: PlaybackModel
    mixer: MixerModel

    consume = GObject.Property(type=bool, default=False)
    random = GObject.Property(type=bool, default=False)
    repeat = GObject.Property(type=bool, default=False)
    single = GObject.Property(type=bool, default=False)

    track_uri = GObject.Property(type=str, default="")
    track_name = GObject.Property(type=str, default="")
    track_length = GObject.Property(type=int, default=-1)

    artist_uri = GObject.Property(type=str, default="")
    artist_name = GObject.Property(type=str, default="")

    image_path = GObject.Property(type=str, default="")

    albums_loaded = GObject.Property(type=bool, default=False)
    albums_images_loaded = GObject.Property(type=bool, default=False)
    tracklist_loaded = GObject.Property(type=bool, default=False)

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self.network_available = application._nm.get_network_available()
        application._nm.connect("network-changed", self._on_nm_network_changed)

        self.playback = PlaybackModel()
        self.mixer = MixerModel()

        self.albums: List[Album] = []
        self.tracklist: Tracklist = Tracklist()

    def clear_track_playback_state(self) -> None:
        self.set_property_in_gtk_thread("track_uri", "")
        self.set_property_in_gtk_thread("track_name", "")
        self.set_property_in_gtk_thread("track_length", -1)
        self.playback.set_time_position(-1)
        self.set_property_in_gtk_thread("artist_uri", "")
        self.set_property_in_gtk_thread("artist_name", "")
        self.set_property_in_gtk_thread("image_path", "")

    def complete_album_description(
        self,
        album_uri: str,
        *,
        artist_name: Optional[str],
        num_tracks: Optional[int],
        num_discs: Optional[int],
        date: Optional[str],
        length: Optional[int],
        tracks: List[Track],
    ) -> None:
        found = [album for album in self.albums if album.uri == album_uri]
        if len(found) == 0:
            LOGGER.warning(f"No album found with URI {album_uri}")
            return

        LOGGER.debug(f"Updating description of album with URI {album_uri}")
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
        if self.tracklist.version == version:
            return

        if self.tracklist_loaded:
            self.set_property_in_gtk_thread("tracklist_loaded", False)

        self.tracklist.tracks.clear()
        if not version:
            self.tracklist.version = -1
            return

        self.tracklist.version = version

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
                TracklistTrack(
                    tlid,
                    Track(
                        uri,
                        cast(str, track.get("name")),
                        cast(int, track.get("track_no")),
                        cast(int, track.get("disc_no", 1)),
                        track.get("length"),
                    ),
                    artist.get("name", ""),
                    album.get("name", ""),
                )
            )
        if len(tracks) == 0:
            self.clear_track_playback_state()

        self.set_property_in_gtk_thread("tracklist_loaded", True, force=True)

    def set_albums(self, value: Any) -> None:
        if self.albums_loaded:
            self.set_property_in_gtk_thread("albums_loaded", False)
            self.set_property_in_gtk_thread("albums_images_loaded", False)
            self.albums.clear()

        for v in value:
            name = v.get("name")
            uri = v.get("uri")
            if not all([name, uri]):
                continue

            album = Album(
                uri,
                name,
                v.get("image_path", ""),
                v.get("image_uri", ""),
            )
            self.albums.append(album)

        self.set_property_in_gtk_thread("albums_loaded", True, force=True)

    def _on_nm_network_changed(
        self, network_monitor: Gio.NetworkMonitor, network_available: bool
    ) -> None:
        LOGGER.debug("Network monitor signal a network status change")
        self.set_property_in_gtk_thread("network_available", network_available)
