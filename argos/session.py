import contextlib
import logging
from typing import TYPE_CHECKING, Optional

import aiohttp
from gi.repository import GObject

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)


class HTTPSessionManager(GObject.Object):
    def __init__(self, application: "Application"):
        super().__init__()

        self._session: Optional[aiohttp.ClientSession] = None

        version: str = application.props.version
        self._user_agent = f"Argos/{version} ( https://orontee.github.io/argos/ )"

    @contextlib.asynccontextmanager
    async def get_session(self) -> aiohttp.ClientSession:
        try:
            if self._session is None or self._session.closed:
                LOGGER.debug("Starting a new HTTP session")
                self._session = aiohttp.ClientSession(
                    raise_for_status=True,
                    headers={"User-Agent": self._user_agent},
                )
            yield self._session
        except (ConnectionError, RuntimeError) as error:
            LOGGER.info(f"Not connected due to {error}")
            self._session = None
