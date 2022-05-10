import logging

from gi.repository import GObject, Gtk

from ..message import MessageType

LOGGER = logging.getLogger(__name__)


class VolumeButton(Gtk.VolumeButton):
    __gtype_name__ = "VolumeButton"

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        self._value_changed_connection_id = self.connect(
            "value_changed", self.value_changed_cb
        )

        self.props.margin_start = 5
        self.props.margin_end = 5
        self.props.halign = Gtk.Align.END

        if self._disable_tooltips:
            self.props.has_tooltip = False

        self.set_sensitive(self._model.network_available and self._model.connected)

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.connect("notify::volume", self.update_value)
        self._model.connect("notify::mute", self.update_value)

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)

    def update_value(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        volume = self._model.volume
        if self._model.mute:
            volume = 0

        if volume != -1:
            with self.handler_block(self._value_changed_connection_id):
                self.set_value(volume / 100)

            self.show_now()

    def value_changed_cb(self, *args) -> None:
        volume = self.get_value() * 100
        self._app.send_message(MessageType.SET_VOLUME, {"volume": volume})
