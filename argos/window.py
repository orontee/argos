import gettext
import logging
from pathlib import Path
import threading
from typing import Optional

from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from .message import MessageType
from .utils import compute_target_size, elide_maybe
from .widgets.topcontrolsbox import TopControlsBox
from .widgets.playingbox import PlayingBox

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ALBUM_STORE_TEXT_COLUMN = 0
ALBUM_STORE_TOOLTIP_COLUMN = 1
ALBUM_STORE_URI_COLUMN = 2
ALBUM_STORE_ICON_FILE_PATH = 3
ALBUM_STORE_PIXBUF_COLUMN = 4

ALBUM_ICON_SIZE = 100


def _default_album_icon_pixbuf() -> Pixbuf:
    pixbuf = Gtk.IconTheme.get_default().load_icon(
        "media-optical-cd-audio-symbolic", ALBUM_ICON_SIZE, 0
    )
    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=ALBUM_ICON_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


def _scale_album_icon(image_path: Path) -> Optional[Pixbuf]:
    pixbuf = None
    try:
        pixbuf = Pixbuf.new_from_file(str(image_path))
    except GLib.Error as error:
        LOGGER.warning(f"Failed to read image at {str(image_path)!r}: {error}")

    if pixbuf is None:
        return None

    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=ALBUM_ICON_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


@Gtk.Template(resource_path="/app/argos/Argos/ui/window.ui")
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ArgosWindow"

    top_box = Gtk.Template.Child()

    central_view = Gtk.Template.Child()
    albums_view = Gtk.Template.Child()

    volume_button = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)

        self.set_wmclass("Argos", "Argos")
        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        self._volume_button_value_changed_id = self.volume_button.connect(
            "value_changed", self.volume_button_value_changed_cb
        )

        albums_store = Gtk.ListStore(str, str, str, str, Pixbuf)
        self.albums_view.set_model(albums_store)
        self.albums_view.set_text_column(ALBUM_STORE_TEXT_COLUMN)
        self.albums_view.set_tooltip_column(ALBUM_STORE_TOOLTIP_COLUMN)
        self.albums_view.set_pixbuf_column(ALBUM_STORE_PIXBUF_COLUMN)
        self.albums_view.set_item_width(ALBUM_ICON_SIZE)

        top_controls_box = TopControlsBox(application)
        self.top_box.add(top_controls_box)

        playing_box = PlayingBox(application)
        self.central_view.add_titled(playing_box, "playing_page", _("Playing"))

        if self._disable_tooltips:
            for widget in (
                self.albums_view,
                self.volume_button,
            ):
                widget.props.has_tooltip = False

        self._default_album_icon = _default_album_icon_pixbuf()

        self._model.connect("notify::connection", self.handle_connection_changed)
        self._model.connect("notify::volume", self.update_volume)
        self._model.connect("notify::mute", self.update_volume)
        self._model.connect("notify::albums-loaded", self.update_album_list)

    def update_album_list(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        LOGGER.debug("Updating album list...")

        store = self.albums_view.get_model()
        store.clear()

        for album in self._model.albums:
            store.append(
                [
                    elide_maybe(album.name),
                    GLib.markup_escape_text(album.name),
                    album.uri,
                    str(album.image_path) if album.image_path else None,
                    self._default_album_icon,
                ]
            )

    def update_album_icons(self) -> None:
        thread = threading.Thread(target=self._update_album_icons)
        thread.daemon = True
        thread.start()

    def _update_album_icons(self) -> None:
        LOGGER.debug("Updating album icons...")

        store = self.albums_view.get_model()

        def update_album_icon(path: Gtk.TreePath, pixbuf: Pixbuf) -> None:
            store_iter = store.get_iter(path)
            store.set_value(store_iter, ALBUM_STORE_PIXBUF_COLUMN, pixbuf)

        store_iter = store.get_iter_first()
        while store_iter is not None:
            image_path = store.get_value(store_iter, ALBUM_STORE_ICON_FILE_PATH)
            if image_path:
                scaled_pixbuf = _scale_album_icon(image_path)
                path = store.get_path(store_iter)
                GLib.idle_add(update_album_icon, path, scaled_pixbuf)
            else:
                LOGGER.debug("No image path")
            store_iter = store.iter_next(store_iter)

    def update_volume(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        volume = self._model.volume
        if self._model.mute:
            volume = 0

        if volume != -1:
            with self.volume_button.handler_block(self._volume_button_value_changed_id):
                self.volume_button.set_value(volume / 100)

            self.volume_button.show_now()

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        buttons = [
            self.volume_button,
        ]
        for button in buttons:
            button.set_sensitive(sensitive)

    def volume_button_value_changed_cb(self, *args) -> None:
        volume = self.volume_button.get_value() * 100
        self._app.send_message(MessageType.SET_VOLUME, {"volume": volume})

    @Gtk.Template.Callback()
    def albums_view_item_activated_cb(
        self, icon_view: Gtk.IconView, path: Gtk.TreePath
    ) -> None:
        store = icon_view.get_model()
        store_iter = store.get_iter(path)
        uri = store.get_value(store_iter, ALBUM_STORE_URI_COLUMN)
        self._app.send_message(MessageType.PLAY_ALBUM, {"uri": uri})

    @Gtk.Template.Callback()
    def key_press_event_cb(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        # See /usr/include/gtk-3.0/gdk/gdkkeysyms.h for key definitions
        mod1_mask = Gdk.ModifierType.MOD1_MASK
        control_mask = Gdk.ModifierType.CONTROL_MASK
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        keyval = event.keyval
        if modifiers == mod1_mask:
            if keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]:
                self.central_view.set_visible_child_name("playing_page")
                return True
            elif keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self.central_view.set_visible_child_name("albums_page")
                return True
        elif modifiers == control_mask:
            if keyval in [Gdk.KEY_space, Gdk.KEY_KP_Space]:
                self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)
            elif keyval == Gdk.KEY_n:
                self._app.send_message(MessageType.PLAY_NEXT_TRACK)
            elif keyval == Gdk.KEY_p:
                self._app.send_message(MessageType.PLAY_PREV_TRACK)
        return False
