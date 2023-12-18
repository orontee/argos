import asyncio
import gettext
import logging
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.controllers.base import ControllerBase
from argos.controllers.progress import (
    DirectoryCompletionProgressNotifier,
    ProgressNotifierProtocol,
)
from argos.controllers.utils import call_by_slice, parse_tracks
from argos.controllers.visitors import AlbumMetadataCollector, LengthAcc
from argos.download import ImageDownloader
from argos.dto import RefDTO, RefType
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
    "Tracks": _("Tracks"),
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

        self._tasks: Dict[str, Optional[asyncio.Task]] = {}

        self._on_index_mopidy_local_albums_changed(
            self._settings, "index-mopidy-local-albums"
        )
        # Hack to set default_uri to the value derived from user settings

        self._settings.connect(
            "changed::index-mopidy-local-albums",
            self._on_index_mopidy_local_albums_changed,
        )
        self._model.library.connect(
            "notify::default-uri",
            self._on_library_default_uri_changed,
        )
        self._settings.connect("changed::album-sort", self._on_album_sort_changed)
        self._settings.connect("changed::track-sort", self._on_track_sort_changed)

    def _on_index_mopidy_local_albums_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        index_mopidy_local_albums = settings.get_boolean(key)
        self._model.library.props.default_uri = (
            MOPIDY_LOCAL_ALBUMS_URI if index_mopidy_local_albums else ""
        )

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

    def _on_track_sort_changed(self, settings: Gio.Settings, key: str) -> None:
        track_sort_id = self._settings.get_string("track-sort")
        self._model.sort_tracks(track_sort_id)

    def _get_backend(self, uri: Optional[str]) -> Optional[MopidyBackend]:
        for backend in self._model.backends:
            if backend.is_responsible_for(uri):
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

        # no need to notify of directories completion since they're
        # just parent of the default directory to load at startup, see
        # _browse_directory()

    @consume(MessageType.BROWSE_DIRECTORY)
    async def browse_directory(self, message: Message) -> None:
        default_uri = self._model.library.props.default_uri
        directory_uri = message.data.get("uri", default_uri)
        force = message.data.get("force", False)

        task = self._tasks.get(directory_uri)
        if task is not None:
            if not task.done():
                if not force:
                    LOGGER.debug(
                        f"Found ongoing task browsing directory {directory_uri!r}"
                    )
                    return
                else:
                    LOGGER.debug(
                        f"Will cancel ongoing task browsing directory {directory_uri!r}"
                    )
                    task.cancel()

        task_name = f"browse_and_notify@{directory_uri}"

        async def browse_and_notify() -> None:
            try:
                await self._browse_directory(directory_uri, force=force)
                GLib.idle_add(self._model.emit, "directory-completed", directory_uri)
            except asyncio.CancelledError:
                LOGGER.debug(f"Cancel of task {task_name!r}")
                raise

            # note that GLib event loop will update model THEN emit the
            # directory-completed signal

        task = asyncio.create_task(browse_and_notify(), name=task_name)
        self._tasks[directory_uri] = task

        self._forget_done_tasks()

    def _forget_done_tasks(self) -> None:
        for directory_uri in self._tasks:
            task = self._tasks[directory_uri]
            if task is not None and task.done():
                self._tasks[directory_uri] = None

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
        subdir_dtos: List[RefDTO] = []
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
            elif ref_dto.type in (RefType.DIRECTORY, RefType.ARTIST):
                subdir_dtos.append(ref_dto)
            elif ref_dto.type == RefType.PLAYLIST:
                LOGGER.warning("Library playlists aren't currently supported")
            elif ref_dto.type == RefType.TRACK:
                track_dtos.append(ref_dto)
            else:
                LOGGER.debug(f"Unsupported type {ref_dto.type.name!r}")

        notifier = DirectoryCompletionProgressNotifier(
            self._model,
            directory_uri=directory_uri,
            step_count=len(album_dtos) + len(track_dtos),
        )

        albums: List[AlbumModel] = []
        if backend is not None and len(album_dtos) > 0:
            albums = await self._complete_albums(
                album_dtos, directory_uri, backend, notifier=notifier
            )

        subdirs: List[DirectoryModel] = []
        if len(subdir_dtos) > 0:
            subdirs = await self._complete_subdirs(subdir_dtos, directory_uri)

        tracks: List[TrackModel] = []
        if backend is not None and len(track_dtos) > 0:
            tracks = await self._complete_tracks(
                track_dtos, directory_uri, backend, notifier=notifier
            )

        playlists: List[PlaylistModel] = []

        self._model.complete_directory(
            directory_uri,
            albums=albums,
            directories=subdirs,
            playlists=playlists,
            tracks=tracks,
            wait_for_model_update=wait_for_model_update,
        )

    async def _complete_albums(
        self,
        album_dtos: Sequence[RefDTO],
        directory_uri: str,
        backend: MopidyBackend,
        *,
        notifier: Optional[ProgressNotifierProtocol],
    ) -> List[AlbumModel]:
        LOGGER.info(
            f"Completing {len(album_dtos)} albums "
            f"for directory with URI {directory_uri!r}"
        )

        album_uris = [dto.uri for dto in album_dtos]

        images = await call_by_slice(
            self._http.get_images,
            params=album_uris,
        )
        if images is None:
            LOGGER.warning("Failed to fetch URIs of images")

        length_acc = LengthAcc()
        metadata_collector = AlbumMetadataCollector()
        parsed_tracks: Dict[str, List[TrackModel]] = {}
        if backend.props.preload_album_tracks:
            LOGGER.debug("Fetching albums tracks")
            directory_tracks_dto = await call_by_slice(
                self._http.lookup_library,
                params=album_uris,
                notifier=notifier,
            )

            LOGGER.debug("Parsing albums tracks")
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

    async def _complete_subdirs(
        self, subdir_dtos: Sequence[RefDTO], directory_uri: str
    ) -> List[DirectoryModel]:
        LOGGER.info(
            f"Completing {len(subdir_dtos)} sub-directories of directory "
            f"with URI {directory_uri!r}"
        )

        subdir_uris = [dto.uri for dto in subdir_dtos]

        images = await call_by_slice(
            self._http.get_images,
            params=subdir_uris,
        )
        if images is None:
            LOGGER.warning("Failed to fetch URIs of images")

        subdirs: List[DirectoryModel] = []
        for subdir_dto in subdir_dtos:
            subdir_uri = subdir_dto.uri

            if (
                images is not None
                and subdir_uri in images
                and len(images[subdir_uri]) > 0
            ):
                image_uri = images[subdir_uri][0].uri
                filepath = self._download.get_image_filepath(image_uri)
            else:
                image_uri = ""
                filepath = None

            subdir = DirectoryModel(
                uri=subdir_uri,
                name=_DIRECTORY_NAMES.get(subdir_dto.name, subdir_dto.name),
                image_path=str(filepath) if filepath is not None else "",
                image_uri=image_uri,
            )
            subdirs.append(subdir)

        return subdirs

    async def _complete_tracks(
        self,
        track_dtos: Sequence[RefDTO],
        directory_uri: str,
        backend: MopidyBackend,
        *,
        notifier: Optional[ProgressNotifierProtocol],
    ) -> List[TrackModel]:
        LOGGER.info(
            f"Completing {len(track_dtos)} tracks "
            f"for directory with URI {directory_uri!r}"
        )

        track_uris = [dto.uri for dto in track_dtos]

        LOGGER.debug("Fetching tracks")
        directory_tracks_dto = await call_by_slice(
            self._http.lookup_library,
            params=track_uris,
            notifier=notifier,
        )

        track_uris = [dto.uri for dto in track_dtos]
        images = await call_by_slice(
            self._http.get_images,
            params=track_uris,
        )
        if images is None:
            LOGGER.warning("Failed to fetch URIs of images")

        LOGGER.debug("Parsing tracks")
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
