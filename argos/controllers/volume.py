import logging
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import Application
from .base import ControllerBase
from ..message import Message, MessageType

LOGGER = logging.getLogger(__name__)


class MixerController(ControllerBase):
    def __init__(self, application: "Application"):
        super().__init__(application)

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        if message_type == MessageType.IDENTIFY_PLAYING_STATE:
            await self.identify_mixer_state()

        elif message_type == MessageType.VOLUME_CHANGED:
            volume = cast(int, message.data.get("volume"))
            self._model.mixer.set_volume(volume)

        elif message_type == MessageType.MUTE_CHANGED:
            mute = cast(bool, message.data.get("mute"))
            self._model.mixer.set_mute(mute)

        elif message_type == MessageType.SET_VOLUME:
            volume = round(cast(int, message.data.get("volume")))
            await self._http.set_volume(volume)

    async def identify_mixer_state(self) -> None:
        LOGGER.debug("Identifying mixer state...")
        mute = await self._http.get_mute()
        if mute is not None:
            self._model.mixer.set_mute(mute)

        volume = await self._http.get_volume()
        if volume is not None:
            self._model.mixer.set_volume(volume)
