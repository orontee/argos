import logging
from typing import cast, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from ..message import consume, Message, MessageType
from .base import ControllerBase

LOGGER = logging.getLogger(__name__)


class TracklistController(ControllerBase):
    """Controls the tracklist.

    This controller maintains the ``Model.tracklist`` property.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

    @consume(
        MessageType.IDENTIFY_PLAYING_STATE,
        MessageType.OPTIONS_CHANGED,
    )
    async def get_options(self, message: Message) -> None:
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

    @consume(MessageType.ADD_TO_TRACKLIST)
    async def add_to_tracklist(self, message: Message) -> None:
        uris = cast(List[str], message.data.get("uris"))
        await self._http.add_to_tracklist(uris=uris)

    @consume(MessageType.CLEAR_TRACKLIST)
    async def clear_tracklist(self, message: Message) -> None:
        await self._http.clear_tracklist()

    @consume(
        MessageType.GET_TRACKLIST,
        MessageType.TRACKLIST_CHANGED,
    )
    async def get_tracklist(self, message: Message) -> None:
        version = await self._http.get_tracklist_version()
        tracks = await self._http.get_tracklist_tracks()
        self._model.update_tracklist(version, tracks)

    @consume(MessageType.GET_CURRENT_TRACKLIST_TRACK)
    async def get_current_tracklist_track(self, message: Message) -> None:
        tl_track = await self._http.get_current_tl_track()
        tlid = tl_track.get("tlid") if tl_track else None
        self._model.playback.set_current_tl_track_tlid(tlid)

    @consume(MessageType.SET_CONSUME)
    async def set_consume(self, message: Message) -> None:
        consume = cast(bool, message.data.get("consume"))
        await self._http.set_consume(consume)

    @consume(MessageType.SET_RANDOM)
    async def set_random(self, message: Message) -> None:
        random = cast(bool, message.data.get("random"))
        await self._http.set_random(random)

    @consume(MessageType.SET_REPEAT)
    async def set_repeat(self, message: Message) -> None:
        repeat = cast(bool, message.data.get("repeat"))
        await self._http.set_repeat(repeat)

    @consume(MessageType.SET_SINGLE)
    async def set_single(self, message: Message) -> None:
        single = cast(bool, message.data.get("single"))
        await self._http.set_single(single)
