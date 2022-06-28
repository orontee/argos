import asyncio
import gettext
import logging
from operator import attrgetter
import time
from typing import Any, Callable, cast, Coroutine, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from ..message import consume, Message, MessageType
from ..model import PlaylistModel
from .base import ControllerBase
from .utils import parse_tracks

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext

_CALL_SIZE = 20


async def _call_by_slice(
    func: Callable[[List[str]], Coroutine[Any, Any, Optional[Dict[str, Any]]]],
    *,
    params: List[str],
) -> Dict[str, Any]:
    """Make multiple synchronous calls.

    The argument ``params`` is splitted in slices of bounded length.

    """
    call_count = len(params) // _CALL_SIZE + (0 if len(params) % _CALL_SIZE == 0 else 1)
    result: Dict[str, Any] = {}
    for i in range(call_count):
        ith_result = await func(params[i * _CALL_SIZE : (i + 1) * _CALL_SIZE])
        if ith_result is None:
            break
        result.update(ith_result)
    return result


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
        self._ongoing_complete_history_playlist_task: Optional[
            asyncio.Task[None]
        ] = None

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
            found_tracks = await _call_by_slice(
                self._http.lookup_library,
                params=track_uris,
            )
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
        recent_additions_max_age = self._settings.get_int("recent-additions-max-age")
        recent_refs = await self._http.browse_library(
            f"local:directory?max-age={recent_additions_max_age}"
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

        recent_tracks = await _call_by_slice(
            self._http.lookup_library,
            params=recent_track_refs_uris,
        )
        if recent_tracks is None:
            return
        parsed_recent_tracks = parse_tracks(recent_tracks)
        parsed_recent_tracks.sort(
            key=attrgetter("last_modified", "disc_no", "track_no")
        )
        self._model.complete_playlist_description(
            self._recent_additions_playlist.uri,
            name=self._recent_additions_playlist.name,
            tracks=parsed_recent_tracks,
            last_modified=time.time(),
        )

    async def _complete_history_playlist(self) -> None:
        ongoing_task = self._ongoing_complete_history_playlist_task
        if ongoing_task:
            if not ongoing_task.done() and not ongoing_task.cancelled():
                LOGGER.debug("Cancelling complete history playlist task")
                ongoing_task.cancel()

        self._ongoing_complete_history_playlist_task = asyncio.create_task(
            self.__complete_history_playlist()
        )
        LOGGER.debug("Complete history playlist task created")

    async def __complete_history_playlist(self) -> None:
        await asyncio.sleep(10)

        LOGGER.info("Begin of history playlist completion")
        history = await self._http.get_history()
        if history is None:
            return

        history_max_length = self._settings.get_int("history-max-length")

        history_refs = [
            history_item[1]
            for history_item in history[:history_max_length]
            if len(history_item) == 2
        ]
        history_refs_uris = [ref.get("uri") for ref in history_refs if "uri" in ref]

        history_tracks = await _call_by_slice(
            self._http.lookup_library,
            params=history_refs_uris,
        )
        if history_tracks is None:
            return
        parsed_history_tracks = parse_tracks(history_tracks)
        self._model.complete_playlist_description(
            self._history_playlist.uri,
            name=self._history_playlist.name,
            tracks=parsed_history_tracks,
            last_modified=time.time(),
        )
        LOGGER.info("End of history playlist completion")
