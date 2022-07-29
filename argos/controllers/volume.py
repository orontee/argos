import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ..app import Application

from ..message import Message, MessageType, consume
from .base import ControllerBase

LOGGER = logging.getLogger(__name__)


class MixerController(ControllerBase):
    """Controls the mixer.

    This controller maintains the ``Model.mixer`` property.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

    @consume(MessageType.IDENTIFY_PLAYING_STATE)
    async def identify_mixer_state(self, message: Message) -> None:
        LOGGER.debug("Identifying mixer state...")
        mute = await self._http.get_mute()
        if mute is not None:
            self._model.mixer.set_mute(mute)

        volume = await self._http.get_volume()
        self._model.mixer.set_volume(volume if volume is not None else -1)

    @consume(MessageType.VOLUME_CHANGED)
    async def update_model_volume(self, message: Message) -> None:
        volume = message.data.get("volume", -1)
        self._model.mixer.set_volume(volume)

    @consume(MessageType.MUTE_CHANGED)
    async def update_model_mute(self, message: Message) -> None:
        mute = message.data.get("mute")
        if mute is not None:
            self._model.mixer.set_mute(mute)

    @consume(MessageType.SET_VOLUME)
    async def set_volume(self, message: Message) -> None:
        volume = round(cast(int, message.data.get("volume")))
        await self._http.set_volume(volume)
