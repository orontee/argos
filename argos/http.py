"""Mopidy HTTP client.

Fully implemented using Mopidy websocket.

"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from gi.repository import GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.model import PlaybackState
from argos.ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)


class MopidyHTTPClient(GObject.GObject):
    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._ws: MopidyWSConnection = application.props.ws

    # API of Mopidy's core.playback controller

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

    async def get_current_tl_track(self) -> Optional[Dict[str, Any]]:
        track = await self._ws.send_command("core.playback.get_current_tl_track")
        return track

    # Mopidy's API of core.library controller

    async def browse_library(self, uri: str = None) -> Optional[List[Dict[str, Any]]]:
        directories_and_tracks = cast(
            Optional[List[Dict[str, Any]]],
            await self._ws.send_command(
                "core.library.browse", params={"uri": uri}, timeout=60
            ),
        )
        return directories_and_tracks

    async def lookup_library(
        self, uris: List[str]
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        tracks = cast(
            Optional[Dict[str, List[Dict[str, Any]]]],
            await self._ws.send_command(
                "core.library.lookup", params={"uris": uris}, timeout=60
            ),
        )
        return tracks

    async def get_images(self, uris: List[str]) -> Optional[Dict[str, List[Any]]]:
        params = {"uris": uris}
        images = await self._ws.send_command("core.library.get_images", params=params)
        return images

    # Mopidy's API of core.tracklist controller

    async def get_eot_tlid(self) -> Optional[int]:
        eot_tlid = await self._ws.send_command("core.tracklist.get_eot_tlid")
        return int(eot_tlid) if eot_tlid is not None else None

    async def add_to_tracklist(self, uris: List[str]) -> None:
        """Add tracks to the tracklist.

        Args:
            uris: URIs of the tracks to add.

        """
        await self._ws.send_command("core.tracklist.add", params={"uris": uris})

    async def remove_from_tracklist(self, tlids: List[int]) -> None:
        """Remove tracks from the tracklist.

        Args:
            tlids: List of tracklist identifier of the tracks to remove.

        """
        await self._ws.send_command(
            "core.tracklist.remove", params={"criteria": {"tlid": tlids}}
        )

    async def clear_tracklist(self) -> None:
        """Clear the tracklist."""
        await self._ws.send_command("core.tracklist.clear")

    async def get_tracklist_tracks(self) -> Optional[Any]:
        """Get the tracklist tracks."""
        return await self._ws.send_command("core.tracklist.get_tl_tracks")

    async def get_tracklist_version(self) -> Optional[int]:
        """Get the version of the tracklist."""
        return await self._ws.send_command("core.tracklist.get_version")

    async def get_consume(self) -> Optional[bool]:
        consume = await self._ws.send_command("core.tracklist.get_consume")
        return bool(consume) if consume is not None else None

    async def set_consume(self, consume: bool) -> None:
        params = {"value": consume}
        await self._ws.send_command("core.tracklist.set_consume", params=params)

    async def get_random(self) -> Optional[bool]:
        random = await self._ws.send_command("core.tracklist.get_random")
        return bool(random) if random is not None else None

    async def set_random(self, random: bool) -> None:
        params = {"value": random}
        await self._ws.send_command("core.tracklist.set_random", params=params)

    async def get_repeat(self) -> Optional[bool]:
        repeat = await self._ws.send_command("core.tracklist.get_repeat")
        return bool(repeat) if repeat is not None else None

    async def set_repeat(self, repeat: bool) -> None:
        params = {"value": repeat}
        await self._ws.send_command("core.tracklist.set_repeat", params=params)

    async def get_single(self) -> Optional[bool]:
        single = await self._ws.send_command("core.tracklist.get_single")
        return bool(single) if single is not None else None

    async def set_single(self, single: bool) -> None:
        params = {"value": single}
        await self._ws.send_command("core.tracklist.set_single", params=params)

    async def play_tracks(self, uris: Optional[List[str]] = None) -> None:
        """Play tracks with given URIs.

        Args:
            uris: Optional URIs of the tracks, albums, etc. to play.

        """
        if uris is None or len(uris) == 0:
            return

        await self._ws.send_command("core.tracklist.clear")
        await self._ws.send_command("core.tracklist.add", params={"uris": uris})
        state = await self._ws.send_command("core.playback.get_state")
        if state != PlaybackState.PLAYING:
            await self._ws.send_command("core.playback.play")

    # Mopidy's API of core.mixer controller

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

    # Mopidy's API of core.playlists controller

    async def get_playlists_uri_schemes(self) -> Optional[List[str]]:
        return await self._ws.send_command("core.playlists.get_uri_schemes")

    async def list_playlists(self) -> Optional[List[Dict[str, Any]]]:
        list = await self._ws.send_command("core.playlists.as_list")
        return list

    async def lookup_playlist(self, uri: str) -> Optional[Dict[str, Any]]:
        playlist = cast(
            Optional[Dict[str, Any]],
            await self._ws.send_command("core.playlists.lookup", params={"uri": uri}),
        )
        return playlist

    async def create_playlist(
        self, name: str, *, uri_scheme: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        params = {"name": name}
        if uri_scheme is not None:
            params["uri_scheme"] = uri_scheme

        playlist = await self._ws.send_command("core.playlists.create", params=params)
        return playlist

    async def save_playlist(self, playlist: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = cast(
            Optional[Dict[str, Any]],
            await self._ws.send_command(
                "core.playlists.save", params={"playlist": playlist}
            ),
        )
        return result

    async def delete_playlist(self, uri: str) -> Optional[bool]:
        return await self._ws.send_command("core.playlists.delete", params={"uri": uri})

    # Mopidy's API of core.history controller

    async def get_history(self) -> Optional[List[Any]]:
        history = await self._ws.send_command("core.history.get_history", timeout=60)
        return history
