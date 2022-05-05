import asyncio
from datetime import datetime
import logging
from typing import Optional, TYPE_CHECKING

from gi.repository import GObject

if TYPE_CHECKING:
    from .app import Application
from .http import MopidyHTTPClient
from .model import Model, PlaybackState

LOGGER = logging.getLogger(__name__)

DELAY = 10  # s


class TimePositionTracker(GObject.GObject):
    """Track time position.

    Periodic synchronization with Mopidy server happens every
    ``DELAY`` seconds.

    """

    last_sync: Optional[datetime] = None

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._model: Model = application.props.model
        self._http: MopidyHTTPClient = application.props.http

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
                time_position: Optional[int] = -1
                if self._model.time_position != -1 and self.last_sync:
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
                        time_position = None
                    else:
                        self.time_position_synced()
                else:
                    LOGGER.debug("No need to synchronize time position")

                if time_position is None:
                    time_position = -1
                self._model.set_property_in_gtk_thread("time_position", time_position)

            await asyncio.sleep(1)
