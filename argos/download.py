import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp

import xdg.BaseDirectory  # type: ignore

from .message import Message, MessageType
from .session import get_session

LOGGER = logging.getLogger(__name__)

MAX_DOWNLOAD_TASKS = 1024


class ImageDownloader:
    """Download track images.

    Currently only support tracks handled by Mopidy-Local.

    """

    def __init__(
        self,
        *,
        message_queue: asyncio.Queue,
        mopidy_base_url: Optional[str],
    ):
        self._message_queue = message_queue
        self._mopidy_base_url = mopidy_base_url

        self._image_dir = Path(xdg.BaseDirectory.save_cache_path("argos/images"))
        self._ongoing_task: Optional[asyncio.Task[None]] = None

    def set_mopidy_base_url(self, mopidy_base_url: Optional[str]) -> None:
        self._mopidy_base_url = mopidy_base_url

    def get_image_filepath(self, image_uri: str) -> Optional[Path]:
        if not image_uri.startswith("/local/"):
            LOGGER.warning(f"Unsupported URI scheme for images {image_uri!r}")
            return None

        filename = Path(image_uri).parts[-1]
        filepath = self._image_dir / filename
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
            url = urljoin(self._mopidy_base_url, image_uri)
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
        message_queue = self._message_queue

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

            message = Message(MessageType.ALBUM_IMAGES_UPDATED)
            await message_queue.put(message)

        if self._ongoing_task:
            if not self._ongoing_task.done() and not self._ongoing_task.cancelled():
                LOGGER.debug("Cancelling undone download task")
                self._ongoing_task.cancel()

        self._ongoing_task = asyncio.create_task(download())
        LOGGER.debug("Download task created")
