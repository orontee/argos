import gettext
import logging
import time
from typing import Any, cast, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from ..message import consume, Message, MessageType
from ..model import PlaylistModel
from .base import ControllerBase
from .utils import parse_tracks

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


HISTORY_LENGTH = 30
RECENT_ADDITIONS_MAX_AGE = 3600 * 24 * 70  # s


class PlaylistsController(ControllerBase):
    """Controls playlists.

    This controller maintains the ``Model.playlist`` store.
    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._recent_additions_playlist = PlaylistModel(
            uri="argos:recent",
            name=_("Recent additions"),
        )

        self._history_playlist = PlaylistModel(
            uri="argos:history",
            name=_("History"),
        )

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

        extended_playlists = [playlist for playlist in parsed_playlists]
        extended_playlists.append(self._recent_additions_playlist)
        extended_playlists.append(self._history_playlist)

        self._model.update_playlists(extended_playlists)

        for playlist in parsed_playlists:
            result = await self._http.lookup_playlist(playlist.uri)
            if result is not None:
                await self._complete_playlist_from_mopidy_model(result)

        await self._complete_recent_additions_playlist()
        await self._complete_history_playlist()

    @consume(MessageType.TRACK_PLAYBACK_STARTED)
    async def update_history(self, message: Message) -> None:
        await self._complete_history_playlist()

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

    async def _complete_recent_additions_playlist(self) -> None:
        recent_refs = await self._http.browse_library(
            f"local:directory?max-age={RECENT_ADDITIONS_MAX_AGE}"
        )
        if recent_refs is None:
            return

        recent_refs_uris = [ref.get("uri") for ref in recent_refs if "uri" in ref]
        recent_track_refs_uris = []
        for uri in recent_refs_uris:
            track_refs = await self._http.browse_library(uri)
            if track_refs is None:
                continue
            recent_track_refs_uris += [
                cast(str, ref.get("uri")) for ref in track_refs if "uri" in ref
            ]

        recent_tracks = await self._http.lookup_library(recent_track_refs_uris)
        if recent_tracks is None:
            return
        parsed_recent_tracks = parse_tracks(recent_tracks)
        self._model.complete_playlist_description(
            self._recent_additions_playlist.uri,
            name=self._recent_additions_playlist.name,
            tracks=parsed_recent_tracks,
            last_modified=int(time.time()),
        )

    async def _complete_history_playlist(self) -> None:
        history = await self._http.get_history()
        if history is None:
            return

        history_refs = [
            history_item[1] for history_item in history[:20] if len(history_item) == 2
        ]
        history_refs_uris = [ref.get("uri") for ref in history_refs if "uri" in ref]
        history_tracks = await self._http.lookup_library(history_refs_uris)
        if history_tracks is None:
            return
        parsed_history_tracks = parse_tracks(history_tracks)
        self._model.complete_playlist_description(
            self._history_playlist.uri,
            name=self._history_playlist.name,
            tracks=parsed_history_tracks,
            last_modified=int(time.time()),
        )
