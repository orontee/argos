import logging
from typing import Optional

from gi.repository import Gdk, GLib, GObject, Gtk

LOGGER = logging.getLogger(__name__)

_CONFIGURE_EVENT_TIMEOUT = 1000  # ms


# This implementation has been taken from
# https://gitlab.gnome.org/GNOME/gnome-music/blob/master/gnomemusic/windowplacement.py#L28


class WindowPlacement(GObject.Object):
    __gtype_name__ = "WindowPlacement"

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._settings = application.props.settings
        self._window = application.window
        self._window_placement_update_timeout_tag: Optional[int] = None

        self._restore_window_state()

        self._window.connect("notify::is-maximized", self._on_maximized)
        self._window.connect("notify::is-fullscreen", self._on_is_fullscreen_changed)
        self._window.connect("configure-event", self._on_configure_event)

    def _restore_window_state(self) -> None:
        LOGGER.info("Restoring application window state")
        size = self._settings.get_value("window-size")
        if len(size) == 2 and isinstance(size[0], int) and isinstance(size[1], int):
            LOGGER.debug(f"Restoring application window size to {size}")
            self._window.resize(*size)

        position = self._settings.get_value("window-position")
        if (
            len(position) == 2
            and isinstance(position[0], int)
            and isinstance(position[1], int)
        ):
            LOGGER.debug(f"Restoring application window position to {position}")
            self._window.move(*position)

        if self._settings.get_boolean("window-maximized"):
            LOGGER.debug("Restoring application window maximize state")
            self._window.maximize()

        if self._settings.get_boolean("window-fullscreen"):
            LOGGER.debug("Restoring application window fullscreen state")
            self._window.fullscreen()

    def _on_configure_event(
        self, window: Gtk.Window, event: Gdk.EventConfigure
    ) -> None:
        if self._window_placement_update_timeout_tag is None:
            self._window_placement_update_timeout_tag = GLib.timeout_add(
                _CONFIGURE_EVENT_TIMEOUT, self._store_size_and_position, window
            )

    def _store_size_and_position(self, window: Gtk.Window) -> bool:
        LOGGER.debug("Storing application window size and position")
        size = window.get_size()
        self._settings.set_value("window-size", GLib.Variant("ai", [size[0], size[1]]))

        position = window.get_position()
        self._settings.set_value(
            "window-position", GLib.Variant("ai", [position[0], position[1]])
        )

        GLib.source_remove(self._window_placement_update_timeout_tag)
        self._window_placement_update_timeout_tag = None

        return False

    def _on_maximized(self, klass, value, data=None):
        LOGGER.debug("Storing application window maximize state")
        self._settings.set_boolean("window-maximized", self._window.is_maximized())

    def _on_is_fullscreen_changed(self, klass, value, data=None):
        LOGGER.debug("Storing application window fullscreen state")
        self._settings.set_boolean(
            "window-fullscreen", self._window.props.is_fullscreen
        )
