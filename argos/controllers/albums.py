import logging
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.backends import (
    MopidyBackend,
    MopidyBandcampBackend,
    MopidyLocalBackend,
    MopidyPodcastBackend,
)
from argos.controllers.base import ControllerBase
from argos.controllers.utils import call_by_slice, parse_tracks
from argos.controllers.visitors import AlbumMetadataCollector, LengthAcc
from argos.download import ImageDownloader
from argos.message import Message, MessageType, consume
from argos.model import AlbumModel

LOGGER = logging.getLogger(__name__)


class AlbumsController(ControllerBase):
    """Albums controller.

    This controller maintains the ``Model.albums`` store.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

        backends: List[MopidyBackend] = [
            MopidyLocalBackend(),
            MopidyPodcastBackend(),
            MopidyBandcampBackend(),
        ]
        self._backends: Dict[MopidyBackend, bool] = {}
        for backend in backends:
            settings_key = backend.settings_key
            activated = self._settings.get_boolean(settings_key)
            self._backends[backend] = activated

            self._settings.connect(
                f"changed::{settings_key}", self._on_backend_settings_changed
            )

        self._model.connect("notify::albums-loaded", self._on_albums_loaded)

    def _get_directory_backend(
        self, directory_uri: Optional[str]
    ) -> Tuple[Optional[MopidyBackend], Optional[str]]:
        for backend, activated in self._backends.items():
            albums_uri = backend.get_albums_uri(directory_uri)
            if albums_uri:
                if not activated:
                    LOGGER.info(
                        f"Backend {backend} supports URI {albums_uri!r} but is deactivated"
                    )
                    return backend, None
                else:
                    LOGGER.info(f"Backend {backend} supports URI {albums_uri!r}")
                return backend, albums_uri

        LOGGER.warning(f"No known backend supports URI {directory_uri!r}")
        return None, None

    def _on_backend_settings_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        for backend in self._backends:
            if backend.settings_key != key:
                continue

            activated = self._settings.get_boolean(key)
            self._backends[backend] = activated
            if activated:
                LOGGER.debug(f"Backend {backend} activated")
            else:
                LOGGER.debug(f"Backend {backend} deactivated")

            self.send_message(MessageType.BROWSE_ALBUMS)

    @consume(MessageType.COMPLETE_ALBUM_DESCRIPTION)
    async def complete_album_description(self, message: Message) -> None:
        album_uri = message.data.get("album_uri", "")
        if not album_uri:
            return

        album = self._model.get_album(album_uri)
        if album is None:
            LOGGER.warning(f"Attempt to complete unknow album with URI {album_uri!r}")
            return

        LOGGER.debug(f"Completing description of album with uri {album_uri!r}")

        if album.is_complete():
            LOGGER.warning(f"Album with URI {album_uri!r} already completed")
            return

        tracks = await self._http.lookup_library([album_uri])
        if tracks is None:
            return

        album_tracks = tracks.get(album_uri)
        if album_tracks and len(album_tracks) > 0:
            length_acc = LengthAcc()
            metadata_collector = AlbumMetadataCollector()
            parsed_tracks = parse_tracks(
                tracks, visitors=[length_acc, metadata_collector]
            ).get(album_uri, [])

            parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

            length = length_acc.length[album_uri]
            artist_name = metadata_collector.artist_name(album_uri)
            num_tracks = metadata_collector.num_tracks(album_uri)
            num_discs = metadata_collector.num_discs(album_uri)
            date = metadata_collector.date(album_uri)

            self._model.complete_album_description(
                album_uri,
                artist_name=artist_name,
                num_tracks=num_tracks,
                num_discs=num_discs,
                date=date,
                length=length,
                tracks=parsed_tracks,
            )

    @consume(MessageType.BROWSE_ALBUMS)
    async def browse_albums(self, message: Message) -> None:
        LOGGER.info("Starting to browse albums...")
        directories = await self._http.browse_library()
        if not directories:
            return None

        parsed_albums: List[AlbumModel] = []
        for directory in directories:
            assert "__model__" in directory and directory["__model__"] == "Ref"
            assert "type" in directory and directory["type"] == "directory"

            directory_uri = directory.get("uri")
            if directory_uri is None:
                continue

            backend, albums_uri = self._get_directory_backend(directory_uri)
            if backend is None or albums_uri is None:
                LOGGER.warning(
                    f"Skipping unsupported directory with URI {directory_uri!r}"
                )
                continue

            directory_albums = await self._http.browse_library(albums_uri)
            if directory_albums is None:
                continue

            if len(directory_albums) == 0:
                LOGGER.warning(
                    f"No album found for directory with URI {directory_uri!r}"
                )
                continue

            LOGGER.info(
                f"Found {len(directory_albums)} albums in directory "
                f"with URI {directory_uri!r}"
            )

            album_uris = [a["uri"] for a in directory_albums]
            images = await self._http.get_images(album_uris)
            if not images:
                continue

            LOGGER.info(
                f"Collecting album descriptions for directory with URI {directory_uri!r}"
            )
            directory_tracks = await call_by_slice(
                self._http.lookup_library,
                params=album_uris,
                call_size=50,
            )

            LOGGER.debug(f"Parsing tracks for directory with URI {directory_uri!r}")
            length_acc = LengthAcc()
            metadata_collector = AlbumMetadataCollector()
            parsed_tracks = parse_tracks(
                directory_tracks,
                visitors=[length_acc, metadata_collector]
            )
            for a in directory_albums:
                assert "__model__" in a and a["__model__"] == "Ref"
                assert "type" in a and a["type"] == "album"

                album_uri = a["uri"]
                album_tracks = directory_tracks.get(album_uri)
                if album_tracks is None or len(album_tracks) == 0:
                    continue

                album = album_tracks[0].get("album")

                length = length_acc.length[album_uri]
                artist_name = metadata_collector.artist_name(album_uri)
                num_tracks = metadata_collector.num_tracks(album_uri)
                num_discs = metadata_collector.num_discs(album_uri)
                date = metadata_collector.date(album_uri)

                if album_uri in images and len(images[album_uri]) > 0:
                    image_uri = images[album_uri][0].get("uri", "")
                    filepath = self._download.get_image_filepath(image_uri)
                else:
                    image_uri = ""
                    filepath = None

                album_parsed_tracks = parsed_tracks.get(album_uri, [])
                album_parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

                album = AlbumModel(
                    backend=backend,
                    uri=album_uri,
                    name=a.get("name", ""),
                    image_path=str(filepath) if filepath is not None else "",
                    image_uri=image_uri,
                    artist_name=artist_name,
                    num_tracks=num_tracks,
                    num_discs=num_discs,
                    date=date,
                    length=length,
                    tracks=album_parsed_tracks,
                )
                parsed_albums.append(album)

        self._model.update_albums(parsed_albums)

    @consume(MessageType.PLAY_RANDOM_ALBUM)
    async def play_random_album(self, message: Message) -> None:
        album_uri = self._model.choose_random_album()
        if album_uri is None:
            LOGGER.warning("Won't play random album since albums list is empty")
            return

        LOGGER.debug(f"Album with URI {album_uri!r} choosen")
        await self._http.play_tracks([album_uri])

    def _on_albums_loaded(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if self._model.albums_loaded:
            LOGGER.debug("Will fetch album images since albums were just loaded")
            image_uris = [a.image_uri for a in self._model.albums]
            self.send_message(
                MessageType.FETCH_ALBUM_IMAGES, data={"image_uris": image_uris}
            )

    @consume(MessageType.FETCH_ALBUM_IMAGES)
    async def fetch_album_images(self, message: Message) -> None:
        LOGGER.debug("Starting album images download...")
        image_uris = message.data.get("image_uris", [])
        await self._download.fetch_images(image_uris)
