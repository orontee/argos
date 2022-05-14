import logging
from typing import cast, TYPE_CHECKING, Union

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from .base import ControllerBase
from ..download import ImageDownloader
from ..message import Message, MessageType
from ..model import PlaybackState

LOGGER = logging.getLogger(__name__)


class PlaybackController(ControllerBase):
    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

        self._model.connect("notify::network-available", self._on_connection_changed)
        self._model.connect("notify::connected", self._on_connection_changed)
        self._model.connect(
            "notify::tracklist-loaded", self._on_tracklist_loaded_changed
        )
        self._model.playback.connect(
            "notify::current-tl-track-tlid",
            self._on_playback_current_tl_track_tlid_changed,
        )

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        if message_type == MessageType.IDENTIFY_PLAYING_STATE:
            await self._identify_playback_state()

        elif message_type == MessageType.TOGGLE_PLAYBACK_STATE:
            await self._toggle_playback_state()

        elif message_type == MessageType.PLAYBACK_STATE_CHANGED:
            raw_state = cast(Union[int, str], message.data.get("new_state"))
            self._model.playback.set_state(raw_state)

        elif message_type == MessageType.TRACK_PLAYBACK_STARTED:
            tl_track = message.data.get("tl_track")
            tlid = tl_track.get("tlid") if tl_track else None
            self._model.playback.set_current_tl_track_tlid(tlid)

        elif message_type == MessageType.TRACK_PLAYBACK_PAUSED:
            self._model.playback.set_state("paused")

        elif message_type == MessageType.TRACK_PLAYBACK_RESUMED:
            self._model.playback.set_state("playing")

        elif message_type == MessageType.TRACK_PLAYBACK_ENDED:
            self._model.playback.set_current_tl_track_tlid(-1)

        elif message_type == MessageType.PLAY_PREV_TRACK:
            await self._http.previous()

        elif message_type == MessageType.PLAY_NEXT_TRACK:
            await self._http.next()

        elif message_type == MessageType.PLAY:
            tlid = message.data.get("tlid")
            await self._http.play(tlid)

        elif message_type == MessageType.PLAY_TRACKS:
            uris = message.data.get("uris")
            await self._http.play_tracks(uris)

        elif message_type == MessageType.PLAY_FAVORITE_PLAYLIST:
            await self._http.play_favorite_playlist()

        elif message_type == MessageType.SEEK:
            time_position = round(cast(int, message.data.get("time_position")))
            await self._http.seek(time_position)

        elif message_type == MessageType.SEEKED:
            time_position = cast(int, message.data.get("time_position"))
            self._model.playback.set_time_position(time_position)

        elif message_type == MessageType.FETCH_TRACK_IMAGE:
            track_uri = message.data.get("track_uri")
            if track_uri:
                await self._fetch_track_image(track_uri)

    async def _identify_playback_state(self) -> None:
        LOGGER.debug("Identifying playing state...")
        raw_state = await self._http.get_state()
        if raw_state is not None:
            self._model.playback.set_state(raw_state)

        time_position = await self._http.get_time_position()
        if time_position is not None:
            self._model.playback.set_time_position(time_position)

    async def _toggle_playback_state(self) -> None:
        state = self._model.playback.state

        if state == PlaybackState.PLAYING:
            await self._http.pause()

        elif state == PlaybackState.PAUSED:
            await self._http.resume()

        elif state == PlaybackState.STOPPED:
            await self._http.play()

        elif state == PlaybackState.UNKNOWN:
            await self._http.play()

    def _on_tracklist_loaded_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.send_message(MessageType.GET_CURRENT_TRACKLIST_TRACK)

    def _on_playback_current_tl_track_tlid_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        track_uri = self._model.get_current_tl_track_uri()
        self.send_message(MessageType.FETCH_TRACK_IMAGE, {"track_uri": track_uri})

    async def _fetch_track_image(self, track_uri: str) -> None:
        LOGGER.debug(f"Starting track image download for {track_uri}")
        images = await self._http.get_images([track_uri])
        image_path = None
        if images:
            track_images = images.get(track_uri)
            if track_images and len(track_images) > 0:
                image_uri = track_images[0]["uri"]
                image_path = await self._download.fetch_image(image_uri)

        if self._model.get_current_tl_track_uri() != track_uri:
            image_path = None

        self._model.playback.set_image_path(image_path)

    def _on_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self._schedule_track_list_update_maybe()
        self._schedule_browse_albums_maybe()

    def _schedule_track_list_update_maybe(self) -> None:
        if self._model.network_available and self._model.connected:
            LOGGER.debug("Will identify playing state since connected to Mopidy server")
            self.send_message(MessageType.IDENTIFY_PLAYING_STATE)
            self.send_message(MessageType.GET_TRACKLIST)
        else:
            LOGGER.debug("Clearing track playback state since not connected")
            self._model.playback.set_current_tl_track_tlid()

    def _schedule_browse_albums_maybe(self) -> None:
        if (
            self._model.network_available
            and self._model.connected
            and not self._model.albums_loaded
        ):
            LOGGER.debug("Will browse albums since connected to Mopidy server")
            self.send_message(MessageType.BROWSE_ALBUMS)
