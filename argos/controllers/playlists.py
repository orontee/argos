import logging
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from ..message import consume, Message, MessageType
from .base import ControllerBase
from .utils import parse_tracks

LOGGER = logging.getLogger(__name__)


class PlaylistsController(ControllerBase):
    """Controls playlists.

    This controller maintains the ``Model.playlist`` store.
    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

    @consume(MessageType.LIST_PLAYLISTS)
    async def list_playlists(self, message: Message) -> None:
        LOGGER.debug("Listing playlists")
        playlists = await self._http.list_playlists()
        self._model.update_playlists(playlists)

    @consume(MessageType.COMPLETE_PLAYLIST_DESCRIPTION)
    async def complete_playlist_description(self, message: Message) -> None:
        playlist_uri = message.data.get("playlist_uri", "")
        if not playlist_uri:
            return

        LOGGER.debug(f"Completing description of playlist with URI {playlist_uri!r}")
        scheme = playlist_uri.split(":")[0]
        playlists_schemes = await self._http.get_playlists_uri_schemes()
        if playlists_schemes is None:
            return

        if scheme not in playlists_schemes:
            return

        result = await self._http.lookup_playlist(playlist_uri)
        if result is None:
            return

        playlist_tracks = result.get("tracks")
        last_modified = result.get("last_modified", -1)

        if playlist_tracks and len(playlist_tracks) > 0:
            uris = [cast(str, t.get("uri")) for t in playlist_tracks if "uri" in t]
            found_tracks = await self._http.lookup_library(uris)
            if found_tracks is None:
                return

            parsed_tracks = parse_tracks(found_tracks)

            self._model.complete_playlist_description(
                playlist_uri,
                tracks=parsed_tracks,
                last_modified=last_modified,
            )
