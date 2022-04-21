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
        application: Application,
    ):
        super().__init__()

        self._ws: MopidyWSConnection = application.props.ws

        settings: Gio.Settings = application.props.settings

        favorite_playlist_uri = settings.get_string("favorite-playlist-uri")
        self._favorite_playlist_uri = favorite_playlist_uri
        settings.connect(
            "changed::favorite-playlist-uri", self._on_favorite_playlist_uri_changed
        )

    async def get_state(self) -> Optional[PlaybackState]:
        state = await self._ws.send_command("core.playback.get_state")
        return PlaybackState(state) if state is not None else None

    async def pause(self) -> None:
        await self._ws.send_command("core.playback.pause")

    async def resume(self) -> None:
        await self._ws.send_command("core.playback.resume")

    async def play(self) -> None:
        await self._ws.send_command("core.playback.play")

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

    async def browse_libraries(self) -> Optional[List[Dict[str, Any]]]:
        libraries = cast(
            Optional[List[Dict[str, Any]]],
            await self._ws.send_command("core.library.browse", params={"uri": None}),
        )
        if libraries is None:
            LOGGER.warning("No library found")
        else:
            LOGGER.debug(f"Found {len(libraries)} libraries")

        return libraries

    async def browse_albums(self) -> Optional[List[Any]]:
        libraries = await self.browse_libraries()
        if not libraries:
            return None

        albums = []
        for library in libraries:
            name = library.get("name")
            uri = library.get("uri")
            if not name or not uri:
                LOGGER.debug(f"Skipping unexpected library {library!r}")
                continue

            library_albums = await self._ws.send_command(
                "core.library.browse", params={"uri": f"{uri}?type=album"}
            )
            if library_albums is None:
                LOGGER.warning(f"No album found for library {name!r}")
            else:
                LOGGER.debug(f"Found {len(library_albums)} albums in library {name!r}")
                albums += library_albums

        return albums

    async def play_album(self, uri: str = None) -> None:
        """Play album with given URI.

        When ``uri`` is ``None``, then a random album is choosen.

        Args:
            uri: Optional URI of the album to play.

        """
        if uri is None:
            albums = await self.browse_albums()

            if not albums or not len(albums):
                return

            album = random.choice(albums)
            LOGGER.debug(f"Will play {album['name']}")
            uri = album["uri"]

        await self._ws.send_command("core.tracklist.clear")
        await self._ws.send_command("core.tracklist.add", params={"uris": [uri]})
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
