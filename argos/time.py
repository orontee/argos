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
        *,
        model: Model,
        message_queue: asyncio.Queue,
        http: MopidyHTTPClient,
    ):
        self._model = model
        self._message_queue = message_queue
        # message queue used by WithModelAccessor mixin!
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
                    time_position = self._model.time_position + 1000
                    delta = (datetime.now() - self.last_sync).total_seconds()
                    needs_sync = delta >= DELAY
                else:
                    needs_sync = True

                if needs_sync:
                    LOGGER.debug("Trying to synchronize time position")
                    try:
                        time_position = await asyncio.wait_for(
                            self._http.get_time_position(),
                            1,
                        )
                    except asyncio.exceptions.TimeoutError:
                        if time_position:
                            time_position += 1000
                    else:
                        self.time_position_synced()
                else:
                    LOGGER.debug("No need to synchronize time position")

                async with self.model_accessor as model:
                    model.update_from(time_position=time_position)

            await asyncio.sleep(1)
