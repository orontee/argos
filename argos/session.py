import contextlib
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Optional, Type, cast

import aiohttp
import xdg.BaseDirectory  # type: ignore

try:
    import aiosqlite  # noqa
    from aiohttp_client_cache import CachedSession, SQLiteBackend
except ImportError:
    CachedSession = None  # type: ignore
    SQLiteBackend = None  # type: ignore
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

        cache_path = (
            Path(xdg.BaseDirectory.save_cache_path("argos")) / "aiohttp-requests.db"
        )

        self._session_klass: Type[aiohttp.ClientSession]
        if SQLiteBackend is not None and CachedSession is not None:
            delay = 7 * 24 * 60 * 60
            cache = SQLiteBackend(
                cache_name=str(cache_path),
                expire_after=delay,
            )
            self._session_klass = cast(
                Type[aiohttp.ClientSession],
                partial(
                    CachedSession,
                    cache=cache,
                ),
            )
        else:
            self._session_klass = aiohttp.ClientSession

    @contextlib.asynccontextmanager
    async def get_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        try:
            if self._session is None or self._session.closed:
                LOGGER.debug(f"Starting a new HTTP session using {self._session_klass}")
                self._session = self._session_klass(
                    raise_for_status=True,
                    headers={"User-Agent": self._user_agent},
                )
            yield self._session
        except (ConnectionError, RuntimeError) as error:
            LOGGER.info(f"Not connected due to {error}")
            self._session = None
