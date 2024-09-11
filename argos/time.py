import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from gi.repository import GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.http import MopidyHTTPClient
from argos.model import Model, PlaybackState

LOGGER = logging.getLogger(__name__)

DELAY = 10  # s
SYNCHRONIZATION_TIMEOUT = 4  # s


class TimePositionTracker(GObject.Object):
    """Track time position.

    Periodic synchronization with Mopidy server happens every
    ``DELAY`` seconds.

    """

    _last_sync: Optional[datetime] = None

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._model: Model = application.props.model
        self._http: MopidyHTTPClient = application.props.http

        self._time_position_changed_handler_id = self._model.playback.connect(
            "notify::time-position",
            self._on_time_position_changed,
        )

    def _on_time_position_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.ParamSpec,
    ) -> None:
        LOGGER.debug("Storing timestamp of last time position synchronization")
        self._last_sync = datetime.now()

    def _is_server_playing(self) -> bool:
        return all(
            [
                self._model.server_reachable,
                self._model.connected,
                self._model.playback.state == PlaybackState.PLAYING,
            ]
        )

    async def __call__(self) -> None:
        LOGGER.debug("Tracking time position...")
        try:
            while True:
                await asyncio.sleep(1)
                if not self._is_server_playing():
                    if self._last_sync:
                        self._last_sync = None
                    continue

                time_position: Optional[int] = -1
                if self._model.playback.time_position != -1 and self._last_sync:
                    time_position = self._model.playback.time_position + 1000
                    delta = (datetime.now() - self._last_sync).total_seconds()
                    needs_sync = delta >= DELAY
                else:
                    needs_sync = True

                synced = False
                if needs_sync:
                    LOGGER.debug("Trying to synchronize time position")
                    try:
                        time_position = await asyncio.wait_for(
                            self._http.get_time_position(),
                            SYNCHRONIZATION_TIMEOUT,
                        )
                        synced = True
                    except asyncio.exceptions.TimeoutError:
                        time_position = None
                else:
                    LOGGER.debug("No need to synchronize time position")

                if time_position is None:
                    time_position = -1

                if not synced:
                    LOGGER.debug("Won't signal time position change to sync handler")
                    args = {"block_handler": self._time_position_changed_handler_id}
                else:
                    args = {}

                self._model.playback.set_time_position(time_position, **args)
        except asyncio.exceptions.CancelledError:
            LOGGER.debug("Won't track time position anymore")
