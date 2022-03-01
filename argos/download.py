import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio

from .message import Message, MessageType
from .session import get_session

LOGGER = logging.getLogger(__name__)

CHUNK_SIZE = 1024

# TODO Keep files for a limited time


class ImageDownloader:
    """Download track images.

    Currently only support tracks handled by Mopidy-Local.

    """

    def __init__(
        self,
        *,
        message_queue: asyncio.Queue,
        settings: Gio.Settings,
    ):
        self.settings = settings
        self._image_dir = TemporaryDirectory()
        self._message_queue = message_queue
        self._base_url = self.settings.get_string("mopidy-base-url")

        self.settings.connect(
            "changed::mopidy-base-url", self.on_mopidy_base_url_changed
        )

    def on_mopidy_base_url_changed(self, settings, _):
        self._base_url = settings.get_string("mopidy-base-url")

    async def fetch_first_image(
        self, *, track_uri: str, track_images: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Fetch the first image."""
        if not track_images or len(track_images) == 0:
            return

        image_uri = track_images[0].get("uri")
        if not image_uri:
            return

        if not image_uri.startswith("/local/"):
            LOGGER.warning(f"Unsupported URI scheme for images {image_uri!r}")
            return

        filename = Path(image_uri).parts[-1]
        filepath = Path(self._image_dir.name) / filename
        if not filepath.exists():
            url = urljoin(self._base_url, image_uri)
            async with get_session() as session:
                try:
                    LOGGER.debug(f"Sending GET {url}")
                    async with session.get(url) as resp:
                        LOGGER.debug(f"Writing image to {str(filepath)!r}")
                        with filepath.open("wb") as fd:
                            async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                                fd.write(chunk)
                except aiohttp.ClientError as err:
                    LOGGER.error(f"Failed to request local image, {err}")

        await self._message_queue.put(
            Message(
                MessageType.IMAGE_AVAILABLE,
                {"track_uri": track_uri, "image_path": filepath},
            )
        )
