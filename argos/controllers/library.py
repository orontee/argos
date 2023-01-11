import asyncio
import gettext
import logging
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.controllers.utils import call_by_slice, parse_tracks
from argos.controllers.visitors import AlbumMetadataCollector, LengthAcc
from argos.download import ImageDownloader
from argos.dto import RefDTO, RefType, TrackDTO
from argos.info import InformationService
from argos.message import Message, MessageType, consume
from argos.model import (
    AlbumModel,
    DirectoryModel,
    MopidyBackend,
    PlaylistModel,
    TrackModel,
)
from argos.model.library import MOPIDY_LOCAL_ALBUMS_URI

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


_DIRECTORY_NAMES = {
    "Files": _("Files"),
    "Local media": _("Local media"),
    "Podcasts": _("Podcasts"),
    "Albums": _("Albums"),
    "Artists": _("Artists"),
    "Composers": _("Composers"),
    "Genres": _("Genres"),
    "Performers": _("Performers"),
    "Release Years": _("Release Years"),
    "Last Week's Updates": _("Last Week's Updates"),
    "Last Month's Updates": _("Last Month's Updates"),
    "Discover by Genre": _("Discover by Genre"),
    "Discover by Tag": _("Discover by Tag"),
    "Collection": _("Collection"),
    "Wishlist": _("Wishlist"),
    "All": _("All"),
}


class LibraryController(ControllerBase):
    """Library controller.

    This controller maintains the ``Model.library`` store.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

        self._on_index_mopidy_local_albums_changed(
            self._settings, "index-mopidy-local-albums"
        )
        # Hack to set default_uri to its the value derived from user
        # settings

        for backend in self._model.backends:
            backend.connect("notify::activated", self._on_backend_activated_changed)

        self._settings.connect(
            "changed::index-mopidy-local-albums",
            self._on_index_mopidy_local_albums_changed,
        )
        self._model.library.connect(
            "notify::default-uri",
            self._on_library_default_uri_changed,
        )
        self._settings.connect("changed::album-sort", self._on_album_sort_changed)

    def _on_backend_activated_changed(
        self,
        _1: Gio.Settings,
        _2: str,
    ) -> None:
        self.send_message(MessageType.BROWSE_DIRECTORY, data={"force": True})

    def _on_index_mopidy_local_albums_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        index_mopidy_local_albums = settings.get_boolean(key)
        if self._model.mopidy_local_backend.props.activated:
            self._model.library.props.default_uri = (
                MOPIDY_LOCAL_ALBUMS_URI if index_mopidy_local_albums else ""
            )
        else:
            self._model.library.props.default_uri = ""

    def _on_library_default_uri_changed(
        self,
        _1: GObject.Object,
        _2: GObject.ParamSpec,
    ) -> None:
        default_uri = self._model.library.props.default_uri
        if default_uri not in (MOPIDY_LOCAL_ALBUMS_URI, ""):
            LOGGER.error(f"Default URI {default_uri!r} not supported")

    def _on_album_sort_changed(self, settings: Gio.Settings, key: str) -> None:
        album_sort_id = self._settings.get_string("album-sort")
        self._model.sort_albums(album_sort_id)

    def _get_backend(self, uri: Optional[str]) -> Optional[MopidyBackend]:
        for backend in self._model.backends:
            if backend.is_responsible_for(uri):
                if not backend.props.activated:
                    LOGGER.info(
                        f"Backend {backend} supports URI {uri!r} but is deactivated"
                    )
                    return None
                return backend

        LOGGER.warning(f"No backend found that supports URI {uri!r}")
        return None

    async def _preload_library(self) -> None:
        default_uri = self._model.library.props.default_uri
        if default_uri != MOPIDY_LOCAL_ALBUMS_URI:
            LOGGER.warning(f"Unexpected default URI {default_uri!r}")
            return

        await self._browse_directory("", wait_for_model_update=True)
        await self._browse_directory("local:directory", wait_for_model_update=True)

    @consume(MessageType.BROWSE_DIRECTORY)
    async def browse_directory(self, message: Message) -> None:
        default_uri = self._model.library.props.default_uri
        directory_uri = message.data.get("uri", default_uri)
        force = message.data.get("force", False)
        await self._browse_directory(directory_uri, force=force)
        GLib.idle_add(self._model.emit, "directory-completed", directory_uri)

    async def _browse_directory(
        self,
        directory_uri: str,
        *,
        force: bool = False,
        wait_for_model_update: bool = False,
    ) -> None:
        default_uri = self._model.library.props.default_uri
        directory = self._model.get_directory(directory_uri)
        if directory is None:
            if directory_uri == default_uri:
                await self._preload_library()

                directory = self._model.get_directory(directory_uri)
                if directory is None:
                    LOGGER.error(
                        f"Failed to load directory with default URI {default_uri!r}"
                    )
                    return
            else:
                LOGGER.warning(f"Unknown directory with URI {directory_uri!r}")
                return

        if not force and directory.is_complete():
            LOGGER.info(f"Directory with URI {directory_uri!r} already completed")
            return

        backend = self._get_backend(directory_uri)
        if directory_uri != "":
            if backend is None:
                return
            else:
                LOGGER.info(
                    f"Browsing directory {directory.name!r} managed by backend {backend}..."
                )
        else:
            # root directory
            assert backend is None
            LOGGER.info(f"Browsing directory {directory.name!r}")

        refs_dto = await self._http.browse_library(directory_uri)
        if refs_dto is None:
            LOGGER.warning("Failed to browse directory!")
            return

        LOGGER.debug(f"Directory {directory.name!r} has {len(refs_dto)} references")

        album_dtos: List[RefDTO] = []
        directories: List[DirectoryModel] = []
        playlists: List[PlaylistModel] = []
        track_dtos: List[RefDTO] = []

        for ref_dto in refs_dto:
            if backend is None:
                ref_backend = self._get_backend(ref_dto.uri)
                if ref_backend is None:
                    continue
                elif backend is not None and backend != ref_backend:
                    LOGGER.warn("Unexpected backend mess")
                    continue

            if backend is not None and backend.hides(ref_dto.uri):
                LOGGER.info(f"Backend {backend} hides ref with URI {ref_dto.uri!r}")
                continue

            if ref_dto.type == RefType.ALBUM:
                album_dtos.append(ref_dto)
            elif ref_dto.type in (
                RefType.DIRECTORY,
                RefType.ARTIST,
            ):
                subdir = DirectoryModel(
                    uri=ref_dto.uri,
                    name=_DIRECTORY_NAMES.get(ref_dto.name, ref_dto.name),
                )
                directories.append(subdir)
            elif ref_dto.type == RefType.PLAYLIST:
                pass
            elif ref_dto.type == RefType.TRACK:
                track_dtos.append(ref_dto)
            else:
                LOGGER.debug(f"Unsupported type {ref_dto.type.name!r}")

        stats = {
            "album": len(album_dtos),
            "directories": len(directories),
            "playlists": len(playlists),
            "tracks": len(track_dtos),
        }
        LOGGER.info(f"Found {stats}")

        albums: List[AlbumModel] = []
        tracks: List[TrackModel] = []
        if backend is not None:
            albums = await self._complete_albums(album_dtos, directory_uri, backend)
            tracks = await self._complete_tracks(track_dtos, directory_uri, backend)

        self._model.complete_directory(
            directory_uri,
            albums=albums,
            directories=directories,
            playlists=playlists,
            tracks=tracks,
            wait_for_model_update=wait_for_model_update,
        )

    async def _complete_albums(
        self,
        album_dtos: Sequence[RefDTO],
        directory_uri: str,
        backend: MopidyBackend,
    ) -> List[AlbumModel]:
        LOGGER.info(f"Completing albums for directory with URI {directory_uri!r}")

        album_uris = [dto.uri for dto in album_dtos]

        images = await call_by_slice(
            self._http.get_images,
            params=album_uris,
            call_size=50,
        )
        if images is None:
            LOGGER.warning("Failed to fetch URIs of images")

        length_acc = LengthAcc()
        metadata_collector = AlbumMetadataCollector()
        parsed_tracks: Dict[str, List[TrackModel]] = {}
        if backend.props.preload_album_tracks:
            LOGGER.debug(f"Fetching albums tracks")
            directory_tracks_dto = await call_by_slice(
                self._http.lookup_library,
                params=album_uris,
                call_size=50,
            )

            LOGGER.debug(f"Parsing albums tracks")
            parsed_tracks = parse_tracks(
                directory_tracks_dto, visitors=[length_acc, metadata_collector]
            )

        parsed_albums: List[AlbumModel] = []
        for album_dto in album_dtos:
            album_uri = album_dto.uri

            if (
                images is not None
                and album_uri in images
                and len(images[album_uri]) > 0
            ):
                image_uri = images[album_uri][0].uri
                filepath = self._download.get_image_filepath(image_uri)
            else:
                image_uri = ""
                filepath = None

            album_parsed_tracks = parsed_tracks.get(album_uri, [])
            album_parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

            album_name = album_dto.name
            artist_name = metadata_collector.artist_name(album_uri)
            if not artist_name:
                if hasattr(backend, "extract_artist_name"):
                    artist_name, album_name = backend.extract_artist_name(
                        album_dto.name
                    )

            album = AlbumModel(
                backend=backend,
                uri=album_uri,
                name=album_name,
                image_path=str(filepath) if filepath is not None else "",
                image_uri=image_uri,
                artist_name=artist_name,
                num_tracks=metadata_collector.num_tracks(album_uri),
                num_discs=metadata_collector.num_discs(album_uri),
                date=metadata_collector.date(album_uri),
                last_modified=metadata_collector.last_modified(album_uri),
                length=length_acc.length[album_uri],
                release_mbid=metadata_collector.release_mbid(album_uri),
                tracks=album_parsed_tracks,
            )
            parsed_albums.append(album)

        return parsed_albums

    async def _complete_tracks(
        self,
        track_dtos: Sequence[RefDTO],
        directory_uri: str,
        backend: MopidyBackend,
    ) -> List[TrackModel]:
        LOGGER.info(f"Completing tracks for directory with URI {directory_uri!r}")

        track_uris = [dto.uri for dto in track_dtos]

        LOGGER.debug(f"Fetching tracks")
        directory_tracks_dto = await call_by_slice(
            self._http.lookup_library,
            params=track_uris,
            call_size=50,
        )

        track_uris = [dto.uri for dto in track_dtos]
        images = await call_by_slice(
            self._http.get_images,
            params=track_uris,
            call_size=50,
        )
        if images is None:
            LOGGER.warning("Failed to fetch URIs of images")

        LOGGER.debug(f"Parsing tracks")
        parsed_tracks: List[TrackModel] = []
        for tracks in parse_tracks(directory_tracks_dto).values():
            for track in tracks:
                track_uri = track.uri
                if images is not None and len(images.get(track_uri, [])) > 0:
                    image_uri = images[track_uri][0].uri
                    track.props.image_uri = image_uri
                    track.props.image_path = self._download.get_image_filepath(
                        image_uri
                    )

                parsed_tracks.append(track)

        return parsed_tracks
