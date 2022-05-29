import logging
from typing import Any, cast, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from ..message import consume, Message, MessageType
from ..model import PlaylistModel
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

    @consume(MessageType.PLAYLIST_CHANGED)
    async def update_model_playlist(self, message: Message) -> None:
        playlist = message.data.get("playlist")
        if playlist is None:
            return

        await self._complete_playlist_from_mopidy_model(playlist)

    @consume(MessageType.PLAYLIST_DELETED)
    async def remove_playlist_from_model(self, message: Message) -> None:
        playlist_uri = message.data.get("uri")
        if playlist_uri is None:
            return

        self._model.delete_playlist(playlist_uri)

    @consume(
        MessageType.LIST_PLAYLISTS,
        MessageType.PLAYLIST_LOADED,
    )
    async def list_playlists(self, message: Message) -> None:
        LOGGER.debug("Listing playlists")
        playlists = await self._http.list_playlists()

        parsed_playlists = []
        if playlists is not None:
            for playlist in playlists:
                assert "__model__" in playlist and playlist["__model__"] == "Ref"
                assert "type" in playlist and playlist["type"] == "playlist"

                name = playlist.get("name")
                uri = playlist.get("uri")
                if not name or not uri:
                    continue

                parsed_playlists.append(PlaylistModel(uri=uri, name=name))

        self._model.update_playlists(parsed_playlists)

        for playlist in parsed_playlists:
            result = await self._http.lookup_playlist(playlist.uri)
            if result is not None:
                await self._complete_playlist_from_mopidy_model(result)

    async def _complete_playlist_from_mopidy_model(
        self,
        model: Dict[str, Any],
    ) -> None:
        assert "__model__" in model and model["__model__"] == "Playlist"
        playlist_uri = model.get("uri", "")
        playlist_name = model.get("name", "")
        playlist_tracks = model.get("tracks", [])
        last_modified = model.get("last_modified", -1)

        LOGGER.debug(f"Completing description of playlist with URI {playlist_uri!r}")

        track_uris = [cast(str, t.get("uri")) for t in playlist_tracks if "uri" in t]
        if len(track_uris) > 0:
            LOGGER.debug(f"Fetching tracks of playlist with URI {playlist_uri!r}")
            found_tracks = await self._http.lookup_library(track_uris)
            if found_tracks is None:
                return

            parsed_tracks = parse_tracks(found_tracks)
        else:
            parsed_tracks = []

        self._model.complete_playlist_description(
            playlist_uri,
            name=playlist_name,
            tracks=parsed_tracks,
            last_modified=last_modified,
        )
