import asyncio
from functools import partial
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import urllib.parse

import aiohttp
import xdg.BaseDirectory  # type: ignore

from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from .app import Application
from .session import get_session

LOGGER = logging.getLogger(__name__)

MAX_DOWNLOAD_TASKS = 1024


class ImageDownloader(GObject.GObject):
    """Download track images.

    Currently only support tracks handled by Mopidy-Local.

    """

    __gsignals__: Dict[str, Tuple[int, Any, Tuple]] = {
        "albums-images-loaded": (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._model = application.model

        settings: Gio.Settings = application.props.settings

        mopidy_base_url = settings.get_string("mopidy-base-url")
        self._mopidy_base_url = mopidy_base_url
        settings.connect("changed::mopidy-base-url", self._on_mopidy_base_url_changed)

        self._image_dir = Path(xdg.BaseDirectory.save_cache_path("argos/images"))
        self._ongoing_task: Optional[asyncio.Task[None]] = None

    def get_image_filepath(self, image_uri: str) -> Optional[Path]:
        if image_uri.startswith("/local/"):
            filename = Path(image_uri).parts[-1]
        elif image_uri.startswith("https://"):
            filename = urllib.parse.quote(image_uri[8:], safe="")
        else:
            LOGGER.warning(f"Unsupported URI scheme {image_uri!r}")
            filename = None

        filepath = self._image_dir / filename if filename else None
        return filepath

    async def fetch_image(self, image_uri: str) -> Optional[Path]:
        """Fetch the image file."""
        if not self._mopidy_base_url:
            LOGGER.debug("Skipping image download since Mopidy base URL not set")
            return None

        filepath = self.get_image_filepath(image_uri)
        if not filepath:
            return None

        if not filepath.exists():
            url = urllib.parse.urljoin(self._mopidy_base_url, image_uri)
            async with get_session() as session:
                try:
                    LOGGER.debug(f"Sending GET {url}")
                    async with session.get(url) as resp:
                        LOGGER.debug(f"Writing image to {str(filepath)!r}")
                        with filepath.open("wb") as fd:
                            async for chunk in resp.content.iter_chunked(
                                MAX_DOWNLOAD_TASKS
                            ):
                                fd.write(chunk)
                except aiohttp.ClientError as err:
                    LOGGER.error(f"Failed to request image {image_uri}, {err}")
        return filepath

    async def fetch_images(self, image_uris: List[str]) -> None:
        """Fetch the image files."""
        if len(image_uris) == 0:
            return None

        paths: Dict[str, Path] = {}
        max_downloads = 10
        download_count = (len(image_uris) // max_downloads) + 1

        async def download() -> None:
            LOGGER.debug(f"Starting {download_count} batch of downloads")
            for task_nb in range(download_count):
                start = task_nb * max_downloads
                some_image_uris = image_uris[start : start + max_downloads]
                tasks = [self.fetch_image(image_uri) for image_uri in some_image_uris]
                filepaths = await asyncio.gather(*tasks)

                for image_uri, filepath in zip(some_image_uris, filepaths):
                    if image_uri is not None and filepath is not None:
                        paths[image_uri] = filepath

            GLib.idle_add(
                partial(
                    self.emit,
                    "albums-images-loaded",
                )
            )

        if self._ongoing_task:
            if not self._ongoing_task.done() and not self._ongoing_task.cancelled():
                LOGGER.debug("Cancelling undone download task")
                self._ongoing_task.cancel()

        self._ongoing_task = asyncio.create_task(download())
        LOGGER.debug("Download task created")

    def _on_mopidy_base_url_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        mopidy_base_url = settings.get_string(key)
        self._mopidy_base_url = mopidy_base_url
