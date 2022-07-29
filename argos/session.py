import contextlib
import logging
from typing import Optional

import aiohttp

LOGGER = logging.getLogger(__name__)

_SESSION: Optional[aiohttp.ClientSession] = None


@contextlib.asynccontextmanager
async def get_session():
    global _SESSION
    try:
        if _SESSION is None or _SESSION.closed:
            LOGGER.debug("Starting a new HTTP session")
            _SESSION = aiohttp.ClientSession(raise_for_status=True)

        yield _SESSION
    except (ConnectionError, RuntimeError) as error:
        LOGGER.info(f"Not connected due to {error}")
        _SESSION = None

    # finally:
    #     if _SESSION:
    #         LOGGER.warning("Closing session")
    #         await _SESSION.close()
