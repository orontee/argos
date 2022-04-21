import logging
from typing import cast, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from .base import ControllerBase
from ..message import Message, MessageType
from ..model import TrackModel

LOGGER = logging.getLogger(__name__)


class PlaylistsController(ControllerBase):
    def __init__(self, application: "Application"):
        super().__init__(application)

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        if message_type == MessageType.LIST_PLAYLISTS:
            playlists = await self._http.list_playlists()
            self._model.update_playlists(playlists)

        elif message_type == MessageType.COMPLETE_PLAYLIST_DESCRIPTION:
            playlist_uri = message.data.get("playlist_uri", "")
            if playlist_uri:
                await self._describe_playlist(playlist_uri)

    async def _describe_playlist(self, uri: str) -> None:
        LOGGER.debug(f"Completing description of playlist with uri {uri!r}")

        result = await self._http.lookup_playlist(uri)
        # TODO compare last modified; signal must be emitted in any
        # case...

        playlist_tracks = result.get("tracks") if result else None
        if playlist_tracks and len(playlist_tracks) > 0:
            uris = [cast(str, t.get("uri")) for t in playlist_tracks if "uri" in t]
            found_tracks = await self._http.lookup_library(uris)
            if found_tracks is None:
                return

            parsed_tracks: List[TrackModel] = []
            for track_uri in found_tracks:
                tracks = found_tracks[track_uri]

                if len(tracks) > 0:
                    t = tracks[0]

                    parsed_tracks.append(
                        TrackModel(
                            uri=cast(str, t.get("uri")),
                            name=cast(str, t.get("name")),
                            track_no=cast(int, t.get("track_no", -1)),
                            disc_no=cast(int, t.get("disc_no", 1)),
                            length=t.get("length", -1),
                        )
                    )

            self._model.complete_playlist_description(
                uri,
                tracks=parsed_tracks,
            )
