import asyncio
from datetime import datetime
import logging
from typing import Optional

from .accessor import WithModelAccessor
from .http import MopidyHTTPClient
from .model import Model, PlaybackState

LOGGER = logging.getLogger(__name__)

DELAY = 10  # s


class TimePositionTracker(WithModelAccessor):
    """Track time position.

    Periodic synchronization with Mopidy server happens every
    ``DELAY`` seconds.

    """

    last_sync: Optional[datetime] = None

    def __init__(
        self,
        model: Model,
        message_queue: asyncio.Queue,
        http: MopidyHTTPClient,
    ):
        self._model = model
        self._message_queue = message_queue
        self._http = http

    def time_position_synced(self) -> None:
        LOGGER.debug("Storing timestamp of last time position synchronization")
        self.last_sync = datetime.now()

    async def track(self) -> None:
        LOGGER.debug("Tracking time position...")
        while True:
            if (
                self._model.network_available
                and self._model.connected
                and self._model.state == PlaybackState.PLAYING
            ):
                time_position = None
                if self._model.time_position is not None and self.last_sync:
                    delta = (datetime.now() - self.last_sync).total_seconds()
                    if delta < DELAY:
                        time_position = self._model.time_position + 1000

                if not time_position:
                    time_position = await self._http.get_time_position()
                    self.time_position_synced()

                async with self.model_accessor as model:
                    model.update_from(time_position=time_position)

            await asyncio.sleep(1)