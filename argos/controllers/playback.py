import gettext
import logging
from typing import TYPE_CHECKING, Union, cast

from gi.repository import GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.download import ImageDownloader
from argos.message import Message, MessageType, consume
from argos.model import PlaybackState

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class PlaybackController(ControllerBase):
    """Controls playback.

    This controller maintains the ``Model.playback`` property according
    to received message from Mopidy websocket or connection state changes.

    It also responsible for sending JSON-RPC commands with
    ``core.playback`` scope.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._must_browse_sources = True
        self._download: ImageDownloader = application.props.download

        self._model.connect("notify::server-reachable", self._on_connection_changed)
        self._model.connect("notify::connected", self._on_connection_changed)
        self._model.connect(
            "notify::tracklist-loaded", self._on_tracklist_loaded_changed
        )
        self._model.playback.connect(
            "notify::current-tl-track-tlid",
            self._on_playback_current_tl_track_tlid_changed,
        )

    @consume(MessageType.IDENTIFY_PLAYING_STATE)
    async def identify_playing_state(self, message: Message) -> None:
        LOGGER.debug("Identifying playing state...")
        raw_state = await self._http.get_state()
        if raw_state is not None:
            self._model.playback.set_state(raw_state)

        time_position = await self._http.get_time_position()
        if time_position is not None:
            self._model.playback.set_time_position(time_position)

    @consume(MessageType.TOGGLE_PLAYBACK_STATE)
    async def toggle_playback_state(self, message: Message) -> None:
        state = self._model.playback.state

        if state == PlaybackState.PLAYING:
            await self._http.pause()

        elif state == PlaybackState.PAUSED:
            await self._http.resume()

        elif state == PlaybackState.STOPPED:
            await self._http.play()

        elif state == PlaybackState.UNKNOWN:
            await self._http.play()

    @consume(MessageType.PLAYBACK_STATE_CHANGED)
    async def update_model_playback_state(self, message: Message) -> None:
        raw_state = cast(Union[int, str], message.data.get("new_state"))
        self._model.playback.set_state(raw_state)

    @consume(MessageType.TRACK_PLAYBACK_STARTED)
    async def identify_current_tracklist_track(self, message: Message) -> None:
        tl_track = message.data.get("tl_track")
        tlid = tl_track.get("tlid") if tl_track else None
        self._model.playback.set_current_tl_track_tlid(tlid)

    @consume(MessageType.TRACK_PLAYBACK_PAUSED)
    async def acknowledge_playback_paused(self, message: Message) -> None:
        self._model.playback.set_state("paused")

    @consume(MessageType.TRACK_PLAYBACK_RESUMED)
    async def acknowledge_playback_playing(self, message: Message) -> None:
        self._model.playback.set_state("playing")

    @consume(MessageType.TRACK_PLAYBACK_ENDED)
    async def acknowledge_playback_ended(self, message: Message) -> None:
        self._model.playback.set_current_tl_track_tlid(-1)

    @consume(MessageType.PLAY_PREV_TRACK)
    async def play_preview_track(self, message: Message) -> None:
        await self._http.previous()

    @consume(MessageType.PLAY_NEXT_TRACK)
    async def play_next_track(self, message: Message) -> None:
        eot_tlid = await self._http.get_eot_tlid()
        if eot_tlid is not None:
            await self._http.next()
        else:
            self.send_message(MessageType.CLEAR_TRACKLIST)

    @consume(MessageType.PLAY)
    async def play(self, message: Message) -> None:
        tlid = message.data.get("tlid")
        await self._http.play(tlid)

    @consume(MessageType.PLAY_TRACKS)
    async def play_tracks(self, message: Message) -> None:
        uris = message.data.get("uris")
        await self._http.play_tracks(uris)

    @consume(MessageType.SEEK)
    async def seek_time_position(self, message: Message) -> None:
        time_position = round(cast(int, message.data.get("time_position")))
        await self._http.seek(time_position)

    @consume(MessageType.SEEKED)
    async def acknowledge_time_position_seeked(self, message: Message) -> None:
        time_position = cast(int, message.data.get("time_position"))
        self._model.playback.set_time_position(time_position)

    @consume(MessageType.FETCH_TRACK_IMAGE)
    async def fetch_track_image(self, message: Message) -> None:
        track_uri = message.data.get("track_uri")
        if not track_uri:
            return

        LOGGER.debug(f"Starting track image download for {track_uri}")
        images = await self._http.get_images([track_uri])
        image_path = None
        if images:
            track_images = images.get(track_uri)
            if track_images and len(track_images) > 0:
                image_uri = track_images[0].uri
                image_path = await self._download.fetch_image(image_uri)

        if self._model.get_current_tl_track_uri() != track_uri:
            image_path = None

        self._model.playback.set_image_path(image_path)

    def _on_tracklist_loaded_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if self._model.props.tracklist_loaded:
            self.send_message(MessageType.GET_CURRENT_TRACKLIST_TRACK)
            self._browse_sources_maybe()
            # For best user experience we wait to have the current
            # tracklist known before starting to browse sources, which
            # can be long

    def _on_playback_current_tl_track_tlid_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        track_uri = self._model.get_current_tl_track_uri()
        if not track_uri:
            return

        self.send_message(MessageType.FETCH_TRACK_IMAGE, {"track_uri": track_uri})

        # send notification
        current_tl_track_tlid = self._model.playback.current_tl_track_tlid
        current_tl_track = self._model.tracklist.get_tl_track(current_tl_track_tlid)
        track = current_tl_track.track if current_tl_track is not None else None
        if not track:
            return

        track_name = track.name
        artist_name = track.artist_name
        album_name = track.album_name
        summary = _("Started to play {}").format(track_name)
        body = ", ".join(filter(lambda s: s, [artist_name, album_name]))
        self._notifier.send_notification(
            summary, body=body, invisible_playing_page=True, is_playing=True
        )

    def _on_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self._schedule_track_list_update_maybe()
        self._must_browse_sources = True

    def _schedule_track_list_update_maybe(self) -> None:
        if self._model.server_reachable and self._model.connected:
            LOGGER.debug("Will identify playing state since connected to Mopidy server")
            self.send_message(MessageType.IDENTIFY_PLAYING_STATE)
            self.send_message(MessageType.GET_TRACKLIST)
        else:
            LOGGER.debug("Clearing track playback state since not connected")
            self._model.playback.set_current_tl_track_tlid()

    def _browse_sources_maybe(self) -> None:
        if all(
            [
                self._model.server_reachable,
                self._model.connected,
                self._must_browse_sources,
            ]
        ):
            LOGGER.debug("Will browse sources")
            self.send_message(MessageType.BROWSE_DIRECTORY)
            self.send_message(MessageType.LIST_PLAYLISTS)
            self._must_browse_sources = False
