import asyncio
import gettext
import logging
import time
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional, cast

from gi.repository import Gio

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.controllers.utils import parse_tracks
from argos.message import Message, MessageType, consume
from argos.model import PlaylistModel

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

        self._recent_additions_playlist: Optional[PlaylistModel] = None
        if self._settings.get_boolean("recent-additions-playlist"):
            self._recent_additions_playlist = PlaylistModel(
                uri="argos:recent",
                name=_("Recent additions"),
            )
        self._settings.connect(
            "changed::recent-additions-playlist", self._on_playlist_settings_changed
        )
        self._settings.connect(
            "changed::recent-additions-max-age", self._on_playlist_settings_changed
        )

        self._history_playlist: Optional[PlaylistModel] = None
        if self._settings.get_boolean("history-playlist"):
            self._history_playlist = PlaylistModel(
                uri="argos:history",
                name=_("History"),
            )
        self._settings.connect(
            "changed::history-playlist", self._on_playlist_settings_changed
        )
        self._settings.connect(
            "changed::history-max-length", self._on_playlist_settings_changed
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
        if self._recent_additions_playlist:
            extended_playlists.append(self._recent_additions_playlist)
        if self._history_playlist:
            extended_playlists.append(self._history_playlist)

        self._model.update_playlists(extended_playlists)

        for playlist in parsed_playlists:
            result = await self._http.lookup_playlist(playlist.uri)
            if result is not None:
                await self._complete_playlist_from_mopidy_model(result)

        if self._recent_additions_playlist:
            await self._complete_recent_additions_playlist()

        if self._history_playlist:
            await self._complete_history_playlist()

    @consume(MessageType.CREATE_PLAYLIST)
    async def create_playlist(self, message: Message) -> None:
        name = message.data.get("name", "")
        uri_scheme = "m3u:"

        LOGGER.debug(f"Creation of a playlist with name {name!r}")

        playlist = await self._http.create_playlist(name, uri_scheme=uri_scheme)
        if playlist is None:
            return

        assert "__model__" in playlist and playlist["__model__"] == "Playlist"
        playlist_uri = playlist.get("uri", "")
        LOGGER.debug(f"Playlist with URI {playlist_uri!r} created")

    @consume(MessageType.SAVE_PLAYLIST)
    async def save_playlist(self, message: Message) -> None:
        playlist_uri = message.data.get("uri", "")
        add_track_uris = message.data.get("add_track_uris", [])
        remove_track_uris = message.data.get("remove_track_uris", [])
        await self._save_playlist(
            playlist_uri,
            add_track_uris=add_track_uris,
            remove_track_uris=remove_track_uris,
        )

    @consume(MessageType.DELETE_PLAYLIST)
    async def delete_playlist(self, message: Message) -> None:
        playlist_uri = message.data.get("uri", "")
        await self._http.delete_playlist(playlist_uri)

    async def _save_playlist(
        self,
        playlist_uri: str,
        *,
        add_track_uris: Optional[List[str]] = None,
        remove_track_uris: Optional[List[str]] = None,
    ) -> None:
        playlist = self._model.get_playlist(playlist_uri)
        if playlist is None:
            return

        if add_track_uris is None:
            add_track_uris = []

        if remove_track_uris is None:
            remove_track_uris = []

        updated_tracks = [
            {"__model__": "Track", "uri": t.uri}
            for t in playlist.tracks
            if t.uri not in remove_track_uris
        ] + [{"__model__": "Track", "uri": uri} for uri in add_track_uris]

        updated_playlist = {
            "__model__": "Playlist",
            "uri": playlist.uri,
            "name": playlist.name,
            "last_modified": int(playlist.last_modified),
            "tracks": updated_tracks,
        }
        LOGGER.debug(f"Saving playlist with URI {playlist_uri!r}")
        await self._http.save_playlist(updated_playlist)

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
        if not self._recent_additions_playlist:
            return

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
        if not self._history_playlist:
            return

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
        await asyncio.sleep(11)

        if not self._history_playlist:
            return

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
        if not self._history_playlist:
            return

        self._model.complete_playlist_description(
            self._history_playlist.uri,
            name=self._history_playlist.name,
            tracks=parsed_history_tracks,
            last_modified=time.time(),
        )
        LOGGER.info("End of history playlist completion")

    def _on_playlist_settings_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        if key == "recent-additions-playlist":
            if self._settings.get_boolean("recent-additions-playlist"):
                self._recent_additions_playlist = PlaylistModel(
                    uri="argos:recent",
                    name=_("Recent additions"),
                )
            else:
                self._recent_additions_playlist = None
        elif key == "history-playlist":
            if self._settings.get_boolean("history-playlist"):
                self._history_playlist = PlaylistModel(
                    uri="argos:history",
                    name=_("History"),
                )
            else:
                self._history_playlist = None

        if key in (
            "recent-additions-playlist",
            "recent-additions-max-age",
            "history-playlist",
            "history-max-length",
        ):
            self.send_message(MessageType.LIST_PLAYLISTS)
        else:
            LOGGER.warning(f"Unexpected setting {key!r}")
