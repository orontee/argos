import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.download import ImageDownloader
from argos.message import Message, MessageType, consume

LOGGER = logging.getLogger(__name__)


class ImagesController(ControllerBase):
    """Images controller."""

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

    @consume(MessageType.FETCH_IMAGES)
    async def fetch_images(self, message: Message) -> None:
        LOGGER.debug("Starting images download...")
        image_uris = message.data.get("image_uris", [])
        await self._download.fetch_images(image_uris)
