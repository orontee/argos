"""Zeroconf based scan.

Code derived from
https://github.com/python-zeroconf/python-zeroconf/blob/master/examples/async_apple_scanner.py

"""

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Tuple, cast

from gi.repository import GLib, GObject
from zeroconf import DNSQuestionType, IPVersion, ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

if TYPE_CHECKING:
    from argos.app import Application

MOPIDY_SERVICE: str = "_mopidy-http._tcp.local."

LOGGER = logging.getLogger(__name__)


class MopidyServiceScanner(GObject.Object):
    """Scan Mopidy HTTP services."""

    __gsignals__: Dict[str, Tuple[int, Any, Sequence]] = {
        "service-discovered": (GObject.SIGNAL_RUN_FIRST, None, (str, str)),
    }

    def __init__(self, application: "Application") -> None:
        super().__init__()

        self.aiobrowser: Optional[AsyncServiceBrowser] = None
        self.aiozc: Optional[AsyncZeroconf] = None

    async def __call__(self) -> None:
        LOGGER.debug("Scanning for Mopidy HTTP services")

        self.aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        self.aiobrowser = AsyncServiceBrowser(
            self.aiozc.zeroconf,
            [MOPIDY_SERVICE],
            handlers=[self.on_service_state_change],
        )

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.exceptions.CancelledError:
            LOGGER.debug("Won't scan for Mopidy HTTP services anymore")
            assert self.aiozc is not None
            assert self.aiobrowser is not None
            await self.aiobrowser.async_cancel()
            await self.aiozc.async_close()

    def on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        LOGGER.debug(f"New state {state_change} for service {name}")
        if state_change is not ServiceStateChange.Added:
            return
        asyncio.ensure_future(
            self.notify_service_discovered(zeroconf, service_type, name)
        )

    async def notify_service_discovered(
        self, zeroconf: Zeroconf, service_type: str, name: str
    ) -> None:
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 5000)
        if info:
            addresses = [
                "%s:%d" % (addr, cast(int, info.port))
                for addr in info.parsed_scoped_addresses()
            ]
            LOGGER.debug(f"Service {name} is listening at {addresses}")

            if len(addresses) < 1:
                return

            GLib.idle_add(partial(self.emit, "service-discovered", name, addresses[0]))
        else:
            LOGGER.warn(f"No info on {name} service")
