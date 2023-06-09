import logging
from typing import TYPE_CHECKING

from argos.controllers.base import ControllerBase
from argos.info import InformationService
from argos.message import Message, MessageType, consume

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)


class ArtistsController(ControllerBase):
    """Artists controller."""

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._information: InformationService = application.props.information

    @consume(MessageType.COLLECT_ARTIST_INFORMATION)
    async def collect_artist_information(self, message: Message) -> None:
        information_service = self._settings.get_boolean("information-service")
        if not information_service:
            return

        artist_uri = message.data.get("artist_uri", "")
        if not artist_uri:
            return

        artist = self._model.get_artist(artist_uri)
        if artist is None:
            LOGGER.warning(
                f"Attempt to collect info on unknown artist with URI {artist_uri!r}"
            )
            return

        if artist.information.last_modified != -1:
            LOGGER.debug(
                f"Information already collected for artist with URI {artist_uri!r}"
            )
            return

        LOGGER.debug(f"Collecting info of artist with uri {artist_uri!r}")
        artist_abstract = await self._information.get_artist_information(
            artist.artist_mbid
        )
        self._model.set_artist_information(artist_uri, artist_abstract)
