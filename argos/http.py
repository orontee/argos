"""Mopidy HTTP client.

Fully implemented using Mopidy websocket.

"""

import logging
import random
from typing import Any, Dict, List

from gi.repository import Gio

from .ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)


class MopidyHTTPClient:
    settings = Gio.Settings("app.argos.Argos")

    def __init__(self, ws: MopidyWSConnection):
        self._ws = ws

    async def get_state(self) -> Any:
        state = await self._ws.send_command("core.playback.get_state")
        return state

    async def pause(self) -> None:
        await self._ws.send_command("core.playback.pause")

    async def resume(self) -> None:
        await self._ws.send_command("core.playback.resume")

    async def play(self) -> None:
        await self._ws.send_command("core.playback.play")

    async def seek(self, time_position: int) -> Any:
        params = {"time_position": time_position}
        successful = await self._ws.send_command("core.playback.seek", params=params)
        return successful

    async def previous(self) -> None:
        await self._ws.send_command("core.playback.previous")

    async def next(self) -> None:
        await self._ws.send_command("core.playback.next")

    async def get_time_position(self) -> None:
        position = await self._ws.send_command("core.playback.get_time_position")
        return position

    async def get_eot_tlid(self) -> Any:
        eot_tlid = await self._ws.send_command("core.tracklist.get_eot_tlid")
        return eot_tlid

    async def play_random_album(self) -> None:
        albums = await self._ws.send_command(
            "core.library.browse", params={"uri": "local:directory?type=album"}
        )
        if albums is None:
            LOGGER.warning("No album found")
            return

        LOGGER.debug(f"Found {len(albums)} albums")
        album = random.choice(albums)
        LOGGER.debug(f"Will play {album['name']}")
        await self._ws.send_command("core.tracklist.clear")
        await self._ws.send_command(
            "core.tracklist.add", params={"uris": [album["uri"]]}
        )
        await self._ws.send_command("core.playback.play")

    async def play_favorite_playlist(self) -> None:
        favorite_playlist_uri = self.settings.get_string("favorite-playlist-uri")
        if not favorite_playlist_uri:
            LOGGER.debug("Favorite playlist URI not set")
            return

        refs = await self._ws.send_command(
            "core.playlists.get_items", params={"uri": favorite_playlist_uri}
        )
        if not refs:
            return

        await self._ws.send_command("core.tracklist.clear")
        uris = [ref["uri"] for ref in refs]
        tltracks = await self._ws.send_command(
            "core.tracklist.add", params={"uris": uris, "at_position": 0}
        )
        tltrack = tltracks[0]
        await self._ws.send_command(
            "core.playback.play", params={"tlid": tltrack["tlid"]}
        )

    async def get_mute(self) -> Any:
        mute = await self._ws.send_command("core.mixer.get_mute")
        return mute

    async def set_mute(self, mute: bool) -> None:
        params = {"mute": mute}
        await self._ws.send_command("core.mixer.set_mute", params=params)

    async def get_volume(self) -> Any:
        volume = await self._ws.send_command("core.mixer.get_volume")
        return volume

    async def set_volume(self, volume: int) -> None:
        params = {"volume": volume}
        await self._ws.send_command("core.mixer.set_volume", params=params)

    async def list_playlists(self) -> List[Dict[str, Any]]:
        list = await self._ws.send_command("core.playlists.as_list")
        return list

    async def get_current_tl_track(self) -> Any:
        track = await self._ws.send_command("core.playback.get_current_tl_track")
        return track

    async def get_images(self, uri) -> Any:
        params = {"uris": [uri]}
        images = await self._ws.send_command("core.library.get_images", params=params)
        return images and images[uri]
