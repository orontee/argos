import logging
import random
from typing import Any, Dict, List
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio

from .session import get_session

LOGGER = logging.getLogger(__name__)

_COMMAND_ID = 0


class MopidyHTTPClient:
    settings = Gio.Settings.new("app.argos.Argos")

    def __init__(self):
        base_url = self.settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/rpc")

        self.settings.connect(
            "changed::mopidy-base-url", self.on_mopidy_base_url_changed
        )

    def on_mopidy_base_url_changed(self, settings, _):
        base_url = settings.get_string("mopidy-base-url")
        self._url = urljoin(base_url, "/mopidy/rpc")

    async def get_state(self) -> Any:
        state = await self._send_command("core.playback.get_state")
        return state

    async def pause(self) -> None:
        await self._send_command("core.playback.pause")

    async def resume(self) -> None:
        await self._send_command("core.playback.resume")

    async def play(self) -> None:
        await self._send_command("core.playback.play")

    async def seek(self, time_position: int) -> Any:
        params = {"time_position": time_position}
        successful = await self._send_command("core.playback.seek", params=params)
        return successful

    async def previous(self) -> None:
        await self._send_command("core.playback.previous")

    async def next(self) -> None:
        await self._send_command("core.playback.next")

    async def get_time_position(self) -> None:
        position = await self._send_command("core.playback.get_time_position")
        return position

    async def play_random_album(self) -> None:
        albums = await self._send_command(
            "core.library.browse", params={"uri": "local:directory?type=album"}
        )
        if albums is None:
            LOGGER.warning("No album found")
            return

        LOGGER.debug(f"Found {len(albums)} albums")
        album = random.choice(albums)
        LOGGER.debug(f"Will play {album['name']}")
        await self._send_command("core.tracklist.clear")
        await self._send_command("core.tracklist.add", params={"uris": [album["uri"]]})
        await self._send_command("core.playback.play")

    async def play_favorite_playlist(self) -> None:
        favorite_playlist_uri = self.settings.get_string("favorite-playlist-uri")
        if not favorite_playlist_uri:
            LOGGER.debug("Favorite playlist URI not set")
            return

        refs = await self._send_command(
            "core.playlists.get_items", params={"uri": favorite_playlist_uri}
        )
        await self._send_command("core.tracklist.clear")
        uris = [ref["uri"] for ref in refs]
        tltracks = await self._send_command(
            "core.tracklist.add", params={"uris": uris, "at_position": 0}
        )
        tltrack = tltracks[0]
        await self._send_command("core.playback.play", params={"tlid": tltrack["tlid"]})

    async def get_mute(self) -> Any:
        mute = await self._send_command("core.mixer.get_mute")
        return mute

    async def set_mute(self, mute: bool) -> None:
        params = {"mute": mute}
        await self._send_command("core.mixer.set_mute", params=params)

    async def get_volume(self) -> Any:
        volume = await self._send_command("core.mixer.get_volume")
        return volume

    async def set_volume(self, volume: int) -> None:
        params = {"volume": volume}
        await self._send_command("core.mixer.set_volume", params=params)

    async def list_playlists(self) -> List[Dict[str, Any]]:
        list = await self._send_command("core.playlists.as_list")
        return list

    async def get_current_tl_track(self) -> Any:
        track = await self._send_command("core.playback.get_current_tl_track")
        return track

    async def get_images(self, uri) -> Any:
        params = {"uris": [uri]}
        images = await self._send_command("core.library.get_images", params=params)
        return images and images[uri]

    async def _send_command(self, method: str, *, params: dict = None) -> Any:
        """Send a command to Mopidy RPC-JSON HTTP interface."""
        global _COMMAND_ID

        _COMMAND_ID += 1
        data = {"jsonrpc": "2.0", "id": _COMMAND_ID, "method": method}
        if params is not None:
            data["params"] = params

        async with get_session() as session:
            try:
                LOGGER.debug(f"Sending POST {self._url} {data}")
                async with session.post(self._url, json=data) as resp:
                    content = await resp.json()
                    LOGGER.debug(f"Received {content}")
                    if "result" in content:
                        return content["result"]
            except aiohttp.ClientError as err:
                LOGGER.error(f"Failed to request mopidy server, {err}")
