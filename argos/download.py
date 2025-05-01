import asyncio
import logging
import urllib.parse
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import aiohttp
import xdg.BaseDirectory  # type: ignore
from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.session import HTTPSessionManager

LOGGER = logging.getLogger(__name__)

MAX_DATA_CHUNK_SIZE = 1024  # bytes
MAX_SIMULTANEOUS_DOWNLOADS = 10


class ImageDownloader(GObject.GObject):
    """Download track, album, directory, etc images."""

    __gsignals__: Dict[str, Tuple[int, Any, Tuple]] = {
        "image-downloaded": (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        "images-downloaded": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }
    # This signal is guaranteed to be emitted from the main (UI)
    # thread

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._http_session_manager: HTTPSessionManager = (
            application.http_session_manager
        )
        self._model = application.model

        settings: Gio.Settings = application.props.settings

        mopidy_base_url = settings.get_string("mopidy-base-url")
        self._mopidy_base_url = mopidy_base_url
        settings.connect("changed::mopidy-base-url", self._on_mopidy_base_url_changed)

        self._image_dir = Path(xdg.BaseDirectory.save_cache_path("argos/images"))
        self._ongoing_task: Optional[asyncio.Task[None]] = None

    def get_image_filepath(self, image_uri: Optional[str]) -> Optional[Path]:
        if image_uri == "" or image_uri is None:
            filename = None
        elif image_uri.startswith("/local/"):
            filename = Path(image_uri).parts[-1]
        elif image_uri.startswith("https://"):
            filename = urllib.parse.quote(image_uri[8:], safe="")
        elif image_uri.startswith("http://"):
            filename = urllib.parse.quote(image_uri[7:], safe="")
        else:
            LOGGER.warning(f"Unsupported URI scheme {image_uri!r}")
            filename = None

        filepath = self._image_dir / filename if filename else None
        return filepath

    async def fetch_image(self, image_uri: str) -> Optional[Path]:
        """Fetch the image file and notify.

        The notification consists in emitting the ``images-downloaded`` signal. Note
        that the notification is emitted even after some downloads fail.

        An image availability must be done by checking that the corresponding file
        exists.

        The file name or ``None`` is returned."""
        if not self._mopidy_base_url:
            LOGGER.debug("Skipping image download since Mopidy base URL not set")
            return None

        filepath = self.get_image_filepath(image_uri)
        success = False
        if filepath is not None:
            success = filepath.exists()
            if not success:
                url = urllib.parse.urljoin(self._mopidy_base_url, image_uri)
                success = await self._fetch_image(image_uri, filepath)
            else:
                LOGGER.debug(f"Image file already exists {str(filepath)!r}")
        else:
            LOGGER.debug("Image URI not supported")

        GLib.idle_add(
            partial(
                self.emit,
                "image-downloaded",
                image_uri,
            )
        )
        return filepath if success else None

    async def _fetch_image(self, image_uri: str, filepath: Path) -> bool:
        """Fetch and write the image file.

        The file at path ``filepath`` is overwritten if it exists.

        Return ``True`` iff the image download succeed.
        """
        if not self._mopidy_base_url:
            LOGGER.debug("Skipping image download since Mopidy base URL not set")
            return False

        url = urllib.parse.urljoin(self._mopidy_base_url, image_uri)

        options: Any = {}
        if self._http_session_manager.cache:
            options["expire_after"] = 0
            LOGGER.debug(
                "Skip writing image to the cache since it'll be written to file system"
            )

        async with self._http_session_manager.get_session() as session:
            try:
                LOGGER.debug(f"Sending GET {url}")
                async with session.get(url, **options) as resp:
                    LOGGER.debug(f"Writing image to {str(filepath)!r}")
                    with filepath.open("wb") as fd:
                        async for chunk in resp.content.iter_chunked(
                            MAX_DATA_CHUNK_SIZE
                        ):
                            fd.write(chunk)
            except aiohttp.ClientError as err:
                LOGGER.error(f"Failed to request image {image_uri}, {err}")
                return False
            except OSError as err:
                LOGGER.error(f"Failed to write image file {str(filepath)!r}, {err}")
                return False
        return True

    async def fetch_images(self, image_uris: List[str]) -> None:
        """Fetch multiple image files and notify.

        The notification consists in emitting the ``images-downloaded`` signal. Note
        that the notification is emitted even after some downloads fail.

        An image availability must be done by checking that the corresponding file
        exists (See ``get_image_filepath()``)."""
        to_download: Dict[str, Path] = {}

        for image_uri in image_uris:
            filepath = self.get_image_filepath(image_uri)
            if not filepath:
                continue

            if not filepath.exists():
                to_download[image_uri] = filepath

        LOGGER.info(f"To download vs URIs count: {len(to_download)}/{len(image_uris)}")

        async def download() -> None:
            uris = list(to_download.keys())
            if len(uris) > 0:
                download_count = (len(uris) // MAX_SIMULTANEOUS_DOWNLOADS) + 1

                LOGGER.info(f"Starting {download_count} batch of images downloads")
                for task_nb in range(download_count):
                    start = task_nb * MAX_SIMULTANEOUS_DOWNLOADS
                    some_image_uris = uris[start : start + MAX_SIMULTANEOUS_DOWNLOADS]
                    tasks = [
                        self.fetch_image(image_uri) for image_uri in some_image_uris
                    ]
                    await asyncio.gather(*tasks)
                    LOGGER.info("Images have been downloaded")

            GLib.idle_add(
                partial(
                    self.emit,
                    "images-downloaded",
                )
            )

        if self._ongoing_task:
            if not self._ongoing_task.done() and not self._ongoing_task.cancelled():
                LOGGER.debug("Cancelling undone download task")
                self._ongoing_task.cancel()

        self._ongoing_task = asyncio.create_task(download())
        LOGGER.debug("Download task created")

        # A download task is created even if no image has to be downloaded, just to emit
        # the ``images-downloaded`` signal!

    def _on_mopidy_base_url_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        mopidy_base_url = settings.get_string(key)
        self._mopidy_base_url = mopidy_base_url
