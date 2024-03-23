import logging

from gi.repository import Gdk, GLib, GObject, Gtk

from ..message import MessageType
from ..model import PlaylistModel

LOGGER = logging.getLogger(__name__)


class PlaylistLabel(Gtk.Stack):
    __gtype_name__ = "PlaylistLabel"

    playlist = GObject.Property(type=PlaylistModel)

    label: Gtk.Label
    entry: Gtk.Entry

    def __init__(self, application: Gtk.Application, *, playlist: PlaylistModel):
        super().__init__()

        self._app = application
        self._disable_tooltips = application.props.disable_tooltips
        self.props.playlist = playlist

        self.label = Gtk.Label()
        self.label.props.halign = Gtk.Align.START
        self.label.props.margin_top = 5
        self.label.props.margin_bottom = 5
        self.label.props.use_underline = False
        self.label.props.use_markup = False
        self.label.set_text(self.playlist.name)
        self.label.show()

        wrapped_label = Gtk.EventBox(child=self.label)
        wrapped_label.show()
        self.add_named(wrapped_label, "label")
        self.set_visible_child_name("label")

        if not playlist.is_virtual:
            self.entry = Gtk.Entry()
            self.entry.show()
            self.add_named(self.entry, "entry")

            self.entry.connect("key-press-event", self._on_entry_key_pressed)
            wrapped_label.connect("button-press-event", self._on_label_button_pressed)

        self.set_homogeneous(True)

        self.playlist.connect("notify::name", self._on_playlist_name_changed)

        if not self._disable_tooltips:
            self.set_tooltip_text(self.playlist.name)

    @property
    def is_virtual(self) -> bool:
        return self.playlist.is_virtual

    def _on_playlist_name_changed(
        self, _1: GObject.Object, _2: GObject.ParamSpec
    ) -> None:
        self.label.set_text(self.playlist.name)

        if not self._disable_tooltips:
            self.set_tooltip_text(self.playlist.name)

    def _on_label_button_pressed(self, _1: Gtk.EventBox, event: Gdk.EventButton):
        if event.type != Gdk.EventType._2BUTTON_PRESS or event.button != 1:
            return

        self.entry.props.text = self.playlist.name
        self.entry.set_position(-1)
        self.set_visible_child_name("entry")

    def _on_entry_key_pressed(self, _1: Gtk.Entry, event: Gdk.EventKey):
        keyval = event.keyval
        if keyval == Gdk.KEY_Return:
            LOGGER.debug("Saving playlist name")
            self._app.activate_action(
                "save-playlist",
                GLib.Variant(
                    "(ssasas)",
                    (
                        self.playlist.uri,
                        self.entry.props.text,
                        [],
                        [],
                    ),
                ),
            )
            self.set_visible_child_name("label")
        elif keyval == Gdk.KEY_Escape:
            LOGGER.debug("Aborting playlist name edition")
            self.set_visible_child_name("label")
