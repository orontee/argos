from collections import defaultdict
import logging
from operator import attrgetter
import random
from typing import Any, cast, Dict, List, Optional, Tuple, TYPE_CHECKING

from gi.repository import Gio, GObject

if TYPE_CHECKING:
    from ..app import Application
from ..backends import (
    MopidyBackend,
    MopidyLocalBackend,
    MopidyBandcampBackend,
    MopidyPodcastBackend,
)
from ..download import ImageDownloader
from ..message import consume, Message, MessageType
from ..model import AlbumModel
from .base import ControllerBase
from .utils import parse_tracks

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
                        f"Backend {backend.__class__!r} supports URI {albums_uri!r} but is deactivated"
                    )
                    return backend, None
                else:
                    LOGGER.debug(
                        f"Backend {backend.__class__!r} supports URI {albums_uri!r}"
                    )
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
                LOGGER.debug(f"Backend {backend!r} activated")
            else:
                LOGGER.debug(f"Backend {backend!r} deactivated")

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
            album = album_tracks[0].get("album")
            if not album:
                return

            artists = cast(List[Dict[str, Any]], album_tracks[0].get("artists", []))
            artist_name = artists[0].get("name") if len(artists) > 0 else None
            num_tracks = album.get("num_tracks")
            num_discs = album.get("num_discs")
            date = album.get("date")

            class LengthAcc:
                length = 0

                def __call__(self, t: Dict[str, Any]) -> None:
                    if self.length != -1 and "length" in t:
                        self.length += int(t["length"])
                    else:
                        self.length = -1

            length_acc = LengthAcc()
            parsed_tracks = parse_tracks(tracks, visitor=length_acc)

            parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

            self._model.complete_album_description(
                album_uri,
                artist_name=artist_name,
                num_tracks=num_tracks,
                num_discs=num_discs,
                date=date,
                length=length_acc.length,
                tracks=parsed_tracks,
            )

    @consume(MessageType.BROWSE_ALBUMS)
    async def browse_albums(self, message: Message) -> None:
        LOGGER.debug("Starting to browse albums...")
        directories = await self._http.browse_library()
        if not directories:
            return None

        albums_by_backend: Dict[MopidyBackend, List[Any]] = defaultdict(list)
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

            LOGGER.debug(
                f"Found {len(directory_albums)} albums in directory "
                f"with URI {directory_uri!r}"
            )
            albums_by_backend[backend] += directory_albums

        if len(albums_by_backend.values()) == 0:
            return

        album_uris = [a["uri"] for album in albums_by_backend.values() for a in album]
        images = await self._http.get_images(album_uris)
        if not images:
            return

        parsed_albums = []
        for backend in albums_by_backend:
            albums = albums_by_backend[backend]
            for a in albums:
                assert "__model__" in a and a["__model__"] == "Ref"
                assert "type" in a and a["type"] == "album"

                album_uri = a["uri"]
                if album_uri in images and len(images[album_uri]) > 0:
                    image_uri = images[album_uri][0].get("uri", "")
                    filepath = self._download.get_image_filepath(image_uri)
                else:
                    image_uri = ""
                    filepath = None

                album = AlbumModel(
                    uri=album_uri,
                    name=a.get("name", ""),
                    image_path=str(filepath) if filepath is not None else "",
                    image_uri=image_uri,
                    backend=backend,
                )
                parsed_albums.append(album)

        self._model.update_albums(parsed_albums)

    @consume(MessageType.PLAY_RANDOM_ALBUM)
    async def play_random_album(self, message: Message) -> None:
        if len(self._model.albums) == 0:
            LOGGER.warning("Won't play random album since albums list is empty")
            return

        album = random.choice(self._model.albums)
        LOGGER.debug(f"Album with URI {album.uri!r} choosen")

        await self._http.play_tracks([album.uri])

    def _on_albums_loaded(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if self._model.albums_loaded:
            LOGGER.debug("Will fetch album images since albums were just loaded")
            self.send_message(MessageType.FETCH_ALBUM_IMAGES)

    @consume(MessageType.FETCH_ALBUM_IMAGES)
    async def fetch_album_images(self, message: Message) -> None:
        LOGGER.debug("Starting album images download...")
        albums = self._model.albums
        image_uris = [albums.get_item(i).image_uri for i in range(albums.get_n_items())]
        await self._download.fetch_images(image_uris)
