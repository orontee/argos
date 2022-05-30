import logging
from typing import Optional, TYPE_CHECKING

from gi.repository import Gio, GLib, GObject

if TYPE_CHECKING:
    from .app import Application

LOGGER = logging.getLogger(__name__)


class Notifier(GObject.Object):

    expiration_timeout = -1
    # expiration depends on notification server settings

    def __init__(self, application: "Application"):
        super().__init__()

        self._application_name = "Argos"
        self._app = application
        self._nid = None  # identifier of last sent notification
        self._disable = False

    def send_notification(
        self,
        summary: str,
        *,
        body: Optional[str] = None,
        invisible_playing_page: Optional[bool] = False,
    ) -> None:
        if self._disable:
            LOGGER.warning("Sending notifications is disabled")
            return

        if all(
            [
                invisible_playing_page,
                not self._app.window or self._app.window.is_playing_page_visible(),
            ]
        ):
            return

        try:
            proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name="org.freedesktop.Notifications",
                object_path="/org/freedesktop/Notifications",
                interface_name="org.freedesktop.Notifications",
                cancellable=None,
            )
        except GLib.Error:
            LOGGER.error("Failed to initialize DBus proxy", exc_info=True)
            self._disable = True
            return

        parameters_type = "(susssasa{sv}i)"
        # https://lazka.github.io/pgi-docs/GLib-2.0/classes/VariantType.html

        parameters = GLib.Variant(
            parameters_type,
            (
                self._application_name,
                self._nid if self._nid is not None else 0,
                "media-optical",
                summary,
                body if body else "",
                [],
                {},
                self.expiration_timeout,
            ),
        )
        # https://specifications.freedesktop.org/notification-spec/notification-spec-latest.html

        try:
            res = proxy.call_sync(
                method_name="Notify",
                parameters=parameters,
                flags=Gio.DBusCallFlags.NONE,
                timeout_msec=-1,
                cancellable=None,
            )
        except GLib.Error:
            LOGGER.error("Failed to send notification", exc_info=True)
            self._disable = True
        else:
            res_type = res.get_type()
            if res_type.equal(GLib.VariantType("(u)")):
                self._nid = res.get_child_value(0).get_uint32()
            else:
                LOGGER.warning(f"Unexpected result type {res.get_type_string()!r}")
