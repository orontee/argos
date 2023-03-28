import logging
from operator import attrgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.controllers.utils import parse_tracks
from argos.controllers.visitors import AlbumMetadataCollector, LengthAcc
from argos.info import InformationService
from argos.message import Message, MessageType, consume

LOGGER = logging.getLogger(__name__)


class AlbumsController(ControllerBase):
    """Albums controller."""

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._information: InformationService = application.props.information

    @consume(MessageType.COMPLETE_ALBUM_DESCRIPTION)
    async def complete_album_description(self, message: Message) -> None:
        album_uri = message.data.get("album_uri", "")
        if not album_uri:
            return

        album = self._model.get_album(album_uri)
        if album is None:
            LOGGER.warning(f"Attempt to complete unknown album with URI {album_uri!r}")
            return

        LOGGER.debug(f"Completing description of album with uri {album_uri!r}")

        if album.is_complete():
            LOGGER.info(f"Album with URI {album_uri!r} already completed")
            return

        tracks_dto = await self._http.lookup_library([album_uri])
        if tracks_dto is None:
            return

        album_tracks_dto = tracks_dto.get(album_uri)
        if album_tracks_dto is None or len(album_tracks_dto) == 0:
            return

        length_acc = LengthAcc()
        metadata_collector = AlbumMetadataCollector()
        parsed_tracks = parse_tracks(
            tracks_dto, visitors=[length_acc, metadata_collector]
        ).get(album_uri, [])

        parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

        length = length_acc.length[album_uri]
        artist_name = metadata_collector.artist_name(album_uri)
        num_tracks = metadata_collector.num_tracks(album_uri)
        num_discs = metadata_collector.num_discs(album_uri)
        date = metadata_collector.date(album_uri)
        last_modified = metadata_collector.last_modified(album_uri)

        self._model.complete_album_description(
            album_uri,
            artist_name=artist_name,
            num_tracks=num_tracks,
            num_discs=num_discs,
            date=date,
            last_modified=last_modified,
            length=length,
            tracks=parsed_tracks,
        )

    @consume(MessageType.COLLECT_ALBUM_INFORMATION)
    async def collect_album_information(self, message: Message) -> None:
        information_service = self._settings.get_boolean("information-service")
        if not information_service:
            return

        album_uri = message.data.get("album_uri", "")
        if not album_uri:
            return

        album = self._model.get_album(album_uri)
        if album is None:
            LOGGER.warning(
                f"Attempt to collect info on unknown album with URI {album_uri!r}"
            )
            return

        if album.information.last_modified != -1:
            LOGGER.debug(
                f"Information already collected for album with URI {album_uri!r}"
            )
            return

        LOGGER.debug(f"Collecting info of album with uri {album_uri!r}")
        album_abstract, artist_abstract = await self._information.get_album_information(
            album.release_mbid
        )
        self._model.set_album_information(album_uri, album_abstract, artist_abstract)
