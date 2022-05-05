import gettext
import logging
from pathlib import Path
import threading
from typing import Optional

from gi.repository import GdkPixbuf, GLib, GObject, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from ..message import MessageType
from ..utils import compute_target_size, elide_maybe

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ALBUM_STORE_TEXT_COLUMN = 0
ALBUM_STORE_TOOLTIP_COLUMN = 1
ALBUM_STORE_URI_COLUMN = 2
ALBUM_STORE_IMAGE_FILE_PATH = 3
ALBUM_STORE_PIXBUF_COLUMN = 4

ALBUM_IMAGE_SIZE = 100


def _default_album_image_pixbuf() -> Pixbuf:
    pixbuf = Gtk.IconTheme.get_default().load_icon(
        "media-optical-cd-audio-symbolic", ALBUM_IMAGE_SIZE, 0
    )
    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=ALBUM_IMAGE_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


def _scale_album_image(image_path: Path) -> Optional[Pixbuf]:
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
        target_width=ALBUM_IMAGE_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


@Gtk.Template(resource_path="/app/argos/Argos/ui/albums_window.ui")
class AlbumsWindow(Gtk.ScrolledWindow):
    __gtype_name__ = "AlbumsWindow"

    albums_view = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        albums_store = Gtk.ListStore(str, str, str, str, Pixbuf)
        self.albums_view.set_model(albums_store)
        self.albums_view.set_text_column(ALBUM_STORE_TEXT_COLUMN)
        self.albums_view.set_tooltip_column(ALBUM_STORE_TOOLTIP_COLUMN)
        self.albums_view.set_pixbuf_column(ALBUM_STORE_PIXBUF_COLUMN)
        self.albums_view.set_item_width(ALBUM_IMAGE_SIZE)

        if self._disable_tooltips:
            self.albums_view.props.has_tooltip = False

        self._default_album_image = _default_album_image_pixbuf()

        self._model.connect("notify::albums-loaded", self.update_album_list)
        self._model.connect("notify::albums-images-loaded", self.update_images)

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
                    self._default_album_image,
                ]
            )

    def update_images(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if not self._model.albums_images_loaded:
            return

        thread = threading.Thread(target=self._update_images)
        thread.daemon = True
        thread.start()

    def _update_images(self) -> None:
        LOGGER.debug("Updating album images...")

        store = self.albums_view.get_model()

        def update_album_image(path: Gtk.TreePath, pixbuf: Pixbuf) -> None:
            store_iter = store.get_iter(path)
            store.set_value(store_iter, ALBUM_STORE_PIXBUF_COLUMN, pixbuf)

        store_iter = store.get_iter_first()
        while store_iter is not None:
            image_path = store.get_value(store_iter, ALBUM_STORE_IMAGE_FILE_PATH)
            if image_path:
                scaled_pixbuf = _scale_album_image(image_path)
                path = store.get_path(store_iter)
                GLib.idle_add(update_album_image, path, scaled_pixbuf)
            else:
                LOGGER.debug("No image path")
            store_iter = store.iter_next(store_iter)

    @Gtk.Template.Callback()
    def albums_view_item_activated_cb(
        self, icon_view: Gtk.IconView, path: Gtk.TreePath
    ) -> None:
        store = icon_view.get_model()
        store_iter = store.get_iter(path)
        uri = store.get_value(store_iter, ALBUM_STORE_URI_COLUMN)
        self._app.send_message(MessageType.PLAY_ALBUM, {"uri": uri})
