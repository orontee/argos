"""Mopidy HTTP client.

Fully implemented using Mopidy websocket.

"""

import logging
import random
from typing import Any, cast, Dict, List, Optional, TYPE_CHECKING

from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from .app import Application
from .model import PlaybackState
from .ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)


class MopidyHTTPClient(GObject.GObject):
    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._ws: MopidyWSConnection = application.props.ws

        settings: Gio.Settings = application.props.settings

        favorite_playlist_uri = settings.get_string("favorite-playlist-uri")
        self._favorite_playlist_uri = favorite_playlist_uri
        settings.connect(
            "changed::favorite-playlist-uri", self._on_favorite_playlist_uri_changed
        )

    async def get_state(self) -> Optional[str]:
        return await self._ws.send_command("core.playback.get_state")

    async def pause(self) -> None:
        await self._ws.send_command("core.playback.pause")

    async def resume(self) -> None:
        await self._ws.send_command("core.playback.resume")

    async def play(self, tlid: Optional[int] = None) -> None:
        params = {}
        if tlid is not None:
            params["tlid"] = tlid

        await self._ws.send_command("core.playback.play", params=params)

    async def seek(self, time_position: int) -> Optional[bool]:
        params = {"time_position": time_position}
        successful = await self._ws.send_command("core.playback.seek", params=params)
        return bool(successful) if successful is not None else None

    async def previous(self) -> None:
        await self._ws.send_command("core.playback.previous")

    async def next(self) -> None:
        await self._ws.send_command("core.playback.next")

    async def get_time_position(self) -> Optional[int]:
        position = await self._ws.send_command("core.playback.get_time_position")
        return int(position) if position is not None else None

    async def get_eot_tlid(self) -> Optional[int]:
        eot_tlid = await self._ws.send_command("core.tracklist.get_eot_tlid")
        return int(eot_tlid) if eot_tlid is not None else None

    async def browse_library(self, uri: str = None) -> Optional[List[Dict[str, Any]]]:
        directories_and_tracks = cast(
            Optional[List[Dict[str, Any]]],
            await self._ws.send_command("core.library.browse", params={"uri": uri}),
        )
        if directories_and_tracks is None:
            LOGGER.warning("No directories nor tracks found")
        else:
            LOGGER.debug(f"Found {len(directories_and_tracks)} directories and tracks")

        return directories_and_tracks

    async def lookup_library(
        self, uris: List[str]
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        tracks = cast(
            Optional[Dict[str, List[Dict[str, Any]]]],
            await self._ws.send_command("core.library.lookup", params={"uris": uris}),
        )
        if tracks is None:
            LOGGER.warning("No tracks found")
        else:
            LOGGER.debug(f"Found tracks for {len(tracks)} URIs")

        return tracks

    async def browse_albums(self) -> Optional[List[Any]]:
        directories = await self.browse_library()
        if not directories:
            return None

        albums = []
        for dir in directories:
            name = dir.get("name")
            uri = dir.get("uri")
            if not name or not uri:
                LOGGER.debug(f"Skipping unexpected library {dir!r}")
                continue

            dir_albums = await self._ws.send_command(
                "core.library.browse", params={"uri": f"{uri}?type=album"}
            )
            if dir_albums is None:
                LOGGER.warning(f"No album found for directory {name!r}")
            else:
                LOGGER.debug(f"Found {len(dir_albums)} albums in directory {name!r}")
                albums += dir_albums

        return albums

    async def add_to_tracklist(self, uris: List[str]) -> None:
        """Add tracks to the tracklist.

        Args:
            uris: URIs of the tracks to add.

        """
        await self._ws.send_command("core.tracklist.add", params={"uris": uris})

    async def clear_tracklist(self) -> None:
        """Clear the tracklist."""
        await self._ws.send_command("core.tracklist.clear")

    async def get_tracklist_tracks(self) -> Optional[Any]:
        """Get the tracklist tracks."""
        return await self._ws.send_command("core.tracklist.get_tl_tracks")

    async def get_tracklist_version(self) -> Optional[int]:
        """Get the version of the tracklist."""
        return await self._ws.send_command("core.tracklist.get_version")

    async def play_tracks(self, uris: Optional[List[str]] = None) -> None:
        """Play tracks with given URIs.

        When ``uris`` is ``None``, a random album is choosen.

        Args:
            uris: Optional URIs of the tracks to play.

        """
        if uris is None:
            albums = await self.browse_albums()

            if not albums or not len(albums):
                return

            album = random.choice(albums)
            LOGGER.debug(f"Will play {album['name']}")
            uris = [album["uri"]]

        await self._ws.send_command("core.tracklist.clear")
        await self._ws.send_command("core.tracklist.add", params={"uris": uris})
        state = await self._ws.send_command("core.playback.get_state")
        if state != PlaybackState.PLAYING:
            await self._ws.send_command("core.playback.play")

    async def play_favorite_playlist(self) -> None:
        if not self._favorite_playlist_uri:
            LOGGER.debug("Favorite playlist URI not set")
            return

        refs = await self._ws.send_command(
            "core.playlists.get_items", params={"uri": self._favorite_playlist_uri}
        )
        if not refs:
            return

        await self._ws.send_command("core.tracklist.clear")
        uris = [ref["uri"] for ref in refs]
        tltracks = await self._ws.send_command(
            "core.tracklist.add", params={"uris": uris, "at_position": 0}
        )
        if not tltracks or not len(tltracks):
            return None

        tltrack = tltracks[0]
        await self._ws.send_command(
            "core.playback.play", params={"tlid": tltrack["tlid"]}
        )

    async def get_mute(self) -> Optional[bool]:
        mute = await self._ws.send_command("core.mixer.get_mute")
        return bool(mute) if mute is not None else None

    async def set_mute(self, mute: bool) -> None:
        params = {"mute": mute}
        await self._ws.send_command("core.mixer.set_mute", params=params)

    async def get_volume(self) -> Optional[int]:
        volume = await self._ws.send_command("core.mixer.get_volume")
        return int(volume) if volume is not None else None

    async def set_volume(self, volume: int) -> None:
        params = {"volume": volume}
        await self._ws.send_command("core.mixer.set_volume", params=params)

    async def list_playlists(self) -> Optional[List[Dict[str, Any]]]:
        list = await self._ws.send_command("core.playlists.as_list")
        return list

    async def get_current_tl_track(self) -> Optional[Dict[str, Any]]:
        track = await self._ws.send_command("core.playback.get_current_tl_track")
        return track

    async def get_images(self, uris: List[str]) -> Optional[Dict[str, List[Any]]]:
        params = {"uris": uris}
        images = await self._ws.send_command("core.library.get_images", params=params)
        return images

    def _on_favorite_playlist_uri_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        favorite_playlist_uri = settings.get_string(key)
        self._favorite_playlist_uri = favorite_playlist_uri
