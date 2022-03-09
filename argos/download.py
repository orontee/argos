import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp

from gi.repository import Gio

import xdg.BaseDirectory  # type: ignore

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
        settings: Gio.Settings,
    ):
        self.settings = settings
        self._image_dir = Path(xdg.BaseDirectory.save_cache_path("argos/images"))
        self._base_url = self.settings.get_string("mopidy-base-url")

        self.settings.connect(
            "changed::mopidy-base-url", self.on_mopidy_base_url_changed
        )

    def on_mopidy_base_url_changed(self, settings, _):
        self._base_url = settings.get_string("mopidy-base-url")

    async def fetch_first_image(
        self, *, images: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Path]:
        """Fetch the first image."""
        if not images or len(images) == 0:
            return None

        image_uri = images[0].get("uri")
        if not image_uri:
            return None

        if not image_uri.startswith("/local/"):
            LOGGER.warning(f"Unsupported URI scheme for images {image_uri!r}")
            return None

        filename = Path(image_uri).parts[-1]
        filepath = self._image_dir / filename
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
        return filepath
