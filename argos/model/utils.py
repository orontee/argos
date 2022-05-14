import contextlib
from enum import IntEnum
import logging
from typing import (
    Any,
    ContextManager,
    Optional,
    Protocol,
)

from gi.repository import GLib


LOGGER = logging.getLogger(__name__)


class HasPropertiesProtocol(Protocol):
    def get_property(self, name: str) -> Any:
        ...

    def set_property(self, name: str, value: Any) -> None:
        ...

    def handler_block(self, handler_id: int) -> ContextManager:
        ...


class WithThreadSafePropertySetter:
    def set_property_in_gtk_thread(
        self: HasPropertiesProtocol,
        name: str,
        value: Any,
        *,
        force: bool = False,
        block_handler: Optional[int] = None,
    ) -> None:
        current_value = self.get_property(name)
        if force or current_value != value:
            if block_handler is not None:
                cm = self.handler_block(block_handler)
            else:
                cm = contextlib.nullcontext()

            def wrapped_setter() -> None:
                LOGGER.debug(f"Updating {name!r} from {current_value!r} to {value!r}")
                with cm:
                    self.set_property(name, value)

            GLib.idle_add(wrapped_setter)
        else:
            LOGGER.debug(f"Property {name!r} already equal to {value!r}")


class PlaybackState(IntEnum):
    UNKNOWN = 0
    PLAYING = 1
    PAUSED = 2
    STOPPED = 3

    @staticmethod
    def from_string(value: str) -> "PlaybackState":
        if value == "playing":
            state = PlaybackState.PLAYING
        elif value == "paused":
            state = PlaybackState.PAUSED
        elif value == "stopped":
            state = PlaybackState.STOPPED
        else:
            state = PlaybackState.UNKNOWN
            LOGGER.error(f"Unexpected state {value!r}")
        return state
