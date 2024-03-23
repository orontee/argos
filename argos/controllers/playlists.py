import asyncio
import gettext
import logging
import time
from operator import itemgetter
from typing import TYPE_CHECKING, Dict, List, Optional

from gi.repository import Gio

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.controllers.utils import call_by_slice, parse_tracks
from argos.controllers.visitors import PlaylistTrackNameFix
from argos.dto import PlaylistDTO
from argos.message import Message, MessageType, consume
from argos.model import PlaylistModel, TrackModel

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class PlaylistsController(ControllerBase):
    """Controls playlists.

    This controller maintains the ``Model.playlist`` store.
    """

    logger = LOGGER  # used by consume decorator

    HISTORY_PLAYLIST_URI = "argos:history"

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._history_playlist: Optional[PlaylistModel] = None
        if self._settings.get_boolean("history-playlist"):
            self._history_playlist = PlaylistModel(
                uri=PlaylistsController.HISTORY_PLAYLIST_URI,
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
        playlist_dto = PlaylistDTO.factory(message.data.get("playlist"))
        if playlist_dto is None:
            return

        # in case it's the selected playlist
        await self._complete_playlist_from(playlist_dto)

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
        refs = await self._http.list_playlists()

        if refs is None:
            LOGGER.debug("No playlist found")
        else:
            LOGGER.debug(f"Number of playlist found: {len(refs)}")

        playlists: List[PlaylistModel] = (
            [
                PlaylistModel(uri=ref.uri, name=ref.name)
                for ref in refs
                if ref.name is not None
            ]
            if refs is not None
            else []
        )

        if self._history_playlist:
            playlists.append(self._history_playlist)

        self._model.update_playlists(playlists)

    @consume(MessageType.CREATE_PLAYLIST)
    async def create_playlist(self, message: Message) -> None:
        name = message.data.get("name", "")
        uri_scheme = "m3u:"

        LOGGER.debug(f"Creation of a playlist with name {name!r}")

        playlist_dto = await self._http.create_playlist(name, uri_scheme=uri_scheme)
        if playlist_dto is None:
            return

        LOGGER.debug(f"Playlist with URI {playlist_dto.uri!r} created")

    @consume(MessageType.SAVE_PLAYLIST)
    async def save_playlist(self, message: Message) -> None:
        name = message.data.get("name")
        playlist_uri = message.data.get("uri", "")
        add_track_uris = message.data.get("add_track_uris", [])
        remove_track_uris = message.data.get("remove_track_uris", [])
        playlist_dto = await self._save_playlist(
            playlist_uri,
            name=name,
            add_track_uris=add_track_uris,
            remove_track_uris=remove_track_uris,
        )
        if playlist_dto is not None and playlist_dto.uri != playlist_uri:
            # happens when name is changed
            self._model.delete_playlist(playlist_uri)

    @consume(MessageType.DELETE_PLAYLIST)
    async def delete_playlist(self, message: Message) -> None:
        playlist_uri = message.data.get("uri", "")
        await self._http.delete_playlist(playlist_uri)

    async def _save_playlist(
        self,
        playlist_uri: str,
        *,
        name: Optional[str] = None,
        add_track_uris: Optional[List[str]] = None,
        remove_track_uris: Optional[List[str]] = None,
    ) -> Optional[PlaylistDTO]:
        playlist = self._model.get_playlist(playlist_uri)
        if playlist is None:
            return None

        if playlist.last_modified == -1:
            # The playlist hasn't been loaded
            playlist_dto = await self._http.lookup_playlist(playlist_uri)
            if playlist_dto is not None:
                await self._complete_playlist_from(
                    playlist_dto, wait_for_model_update=True
                )
                playlist = self._model.get_playlist(playlist_uri)
                if playlist is None:
                    return None

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
            "name": name or playlist.name,
            "last_modified": int(playlist.last_modified),
            "tracks": updated_tracks,
        }
        LOGGER.debug(f"Saving playlist with URI {playlist_uri!r}")
        playlist_dto = await self._http.save_playlist(updated_playlist)
        return playlist_dto

    @consume(MessageType.COMPLETE_PLAYLIST_DESCRIPTION)
    async def complete_playlist(self, message: Message) -> None:
        playlist_uri = message.data.get("uri")
        if playlist_uri is None:
            return

        LOGGER.debug(f"Completing description of playlist with URI {playlist_uri!r}")

        if self._history_playlist and playlist_uri == self._history_playlist.props.uri:
            await self._complete_history_playlist()
        else:
            playlist = self._model.get_playlist(playlist_uri)
            if playlist:
                playlist_dto = await self._http.lookup_playlist(playlist_uri)
                if playlist_dto is not None:
                    await self._complete_playlist_from(playlist_dto)
            else:
                LOGGER.warning(
                    f"Won't complete unkwnown playlist with URI {playlist_uri!r}"
                )

    async def _complete_playlist_from(
        self,
        playlist_dto: PlaylistDTO,
        wait_for_model_update: bool = False,
    ) -> None:
        track_uris = [t.uri for t in playlist_dto.tracks]
        if len(track_uris) > 0:
            LOGGER.debug(f"Fetching tracks of playlist with URI {playlist_dto.uri!r}")
            found_tracks_dto = await call_by_slice(
                self._http.lookup_library,
                params=track_uris,
            )
            parsed_tracks: List[TrackModel] = []
            for tracks in parse_tracks(
                found_tracks_dto, visitors=[PlaylistTrackNameFix(playlist_dto)]
            ).values():
                parsed_tracks += tracks
        else:
            parsed_tracks = []

        self._model.complete_playlist_description(
            playlist_dto.uri,
            name=playlist_dto.name,
            tracks=parsed_tracks,
            last_modified=playlist_dto.last_modified,
            wait_for_model_update=wait_for_model_update,
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
        if not self._history_playlist:
            return

        LOGGER.info("Begin of history playlist completion")
        history = await self._http.get_history()
        if history is None:
            return

        history.sort(key=itemgetter(0), reverse=True)
        # most recent item first

        history_max_length = self._settings.get_int("history-max-length")

        history_refs = [
            history_item[1]
            for history_item in history[:history_max_length]
            if len(history_item) == 2
        ]
        history_refs_uris = [ref.uri for ref in history_refs]
        unique_history_refs_uris = list(set(history_refs_uris))
        LOGGER.debug(
            f"{len(history_refs_uris)} URIs extracted from {len(history)} tracks "
            f"in raw history (max length {history_max_length}, "
            f"{len(history_refs_uris) - len(unique_history_refs_uris)} duplicates)"
        )

        history_tracks_dto = await call_by_slice(
            self._http.lookup_library,
            params=unique_history_refs_uris,
        )

        parsed_history_tracks_with_duplicates: List[TrackModel] = []
        parsed_history_tracks: Dict[str, List[TrackModel]] = parse_tracks(
            history_tracks_dto
        )
        for history_item in history:
            if len(parsed_history_tracks_with_duplicates) >= history_max_length:
                break

            timestamp = history_item[0]
            ref = history_item[1]
            tracks = parsed_history_tracks.get(ref.uri, [])
            for track in tracks:
                extended_track = TrackModel(
                    uri=track.uri,
                    name=track.name,
                    track_no=track.track_no,
                    disc_no=track.disc_no,
                    length=track.length,
                    album_name=track.album_name,
                    artist_name=track.artist_name,
                    last_modified=track.last_modified,
                    last_played=timestamp,
                )
                # mandatory copy since tracks may be duplicated with
                # different last_played value
                parsed_history_tracks_with_duplicates.append(extended_track)

        if not self._history_playlist:
            return

        self._model.complete_playlist_description(
            self._history_playlist.uri,
            name=self._history_playlist.name,
            tracks=parsed_history_tracks_with_duplicates,
            last_modified=time.time(),
        )
        LOGGER.info("End of history playlist completion")

    def _on_playlist_settings_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        if key == "history-playlist":
            if self._settings.get_boolean("history-playlist"):
                self._history_playlist = PlaylistModel(
                    uri=PlaylistsController.HISTORY_PLAYLIST_URI,
                    name=_("History"),
                )
            else:
                self._history_playlist = None

        if key == "history-playlist":
            self.send_message(MessageType.LIST_PLAYLISTS)
        elif key in ("history-max-length",):
            self.send_message(
                MessageType.COMPLETE_PLAYLIST_DESCRIPTION,
                data={"uri": PlaylistsController.HISTORY_PLAYLIST_URI},
            )
        else:
            LOGGER.warning(f"Unexpected setting {key!r}")
