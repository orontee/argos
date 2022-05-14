import logging
from typing import cast, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from .base import ControllerBase
from ..message import Message, MessageType

LOGGER = logging.getLogger(__name__)


class TracklistController(ControllerBase):
    def __init__(self, application: "Application"):
        super().__init__(application)

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        if message_type == MessageType.IDENTIFY_PLAYING_STATE:
            await self._get_options()

        elif message_type == MessageType.ADD_TO_TRACKLIST:
            uris = cast(List[str], message.data.get("uris"))
            await self._http.add_to_tracklist(uris=uris)

        elif message_type == MessageType.CLEAR_TRACKLIST:
            await self._http.clear_tracklist()

        elif message_type == MessageType.GET_TRACKLIST:
            await self._get_tracklist()

        elif message_type == MessageType.TRACKLIST_CHANGED:
            await self._get_tracklist()

        elif message_type == MessageType.GET_CURRENT_TRACKLIST_TRACK:
            await self._get_current_tl_track()

        elif message_type == MessageType.SET_CONSUME:
            consume = cast(bool, message.data.get("consume"))
            await self._http.set_consume(consume)

        elif message_type == MessageType.SET_RANDOM:
            random = cast(bool, message.data.get("random"))
            await self._http.set_random(random)

        elif message_type == MessageType.SET_REPEAT:
            repeat = cast(bool, message.data.get("repeat"))
            await self._http.set_repeat(repeat)

        elif message_type == MessageType.SET_SINGLE:
            single = cast(bool, message.data.get("single"))
            await self._http.set_single(single)

        elif message_type == MessageType.OPTIONS_CHANGED:
            await self._get_options(),

    async def _get_current_tl_track(self) -> None:
        tl_track = await self._http.get_current_tl_track()
        tlid = tl_track.get("tlid") if tl_track else None
        self._model.playback.set_current_tl_track_tlid(tlid)

    async def _get_tracklist(self) -> None:
        version = await self._http.get_tracklist_version()
        tracks = await self._http.get_tracklist_tracks()
        self._model.update_tracklist(version, tracks)

    async def _get_options(self) -> None:
        consume = await self._http.get_consume()
        if consume is not None:
            self._model.tracklist.set_consume(consume)

        random = await self._http.get_random()
        if random is not None:
            self._model.tracklist.set_random(random)

        repeat = await self._http.get_repeat()
        if repeat is not None:
            self._model.tracklist.set_repeat(repeat)

        single = await self._http.get_single()
        if single is not None:
            self._model.tracklist.set_single(single)
