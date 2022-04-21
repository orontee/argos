from enum import IntEnum
import logging
import re
import threading

from gi.repository import GLib, GObject, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from ..utils import elide_maybe
from .utils import default_album_image_pixbuf, scale_album_image

LOGGER = logging.getLogger(__name__)

ALBUM_IMAGE_SIZE = 100


class AlbumStoreColumns(IntEnum):
    TEXT = 0
    TOOLTIP = 1
    URI = 2
    IMAGE_FILE_PATH = 3
    PIXBUF = 4
    FILTER_TEXT = 5


@Gtk.Template(resource_path="/app/argos/Argos/ui/albums_window.ui")
class AlbumsWindow(Gtk.ScrolledWindow):
    __gtype_name__ = "AlbumsWindow"

    __gsignals__ = {"album-selected": (GObject.SIGNAL_RUN_FIRST, None, (str,))}

    albums_view: Gtk.IconView = Gtk.Template.Child()

    filtered_albums_store = GObject.Property(type=Gtk.TreeModelFilter)
    filtering_text = GObject.Property(type=str)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._model = application.model

        albums_store = Gtk.ListStore(str, str, str, str, Pixbuf, str)
        self.props.filtered_albums_store = albums_store.filter_new()
        self.props.filtered_albums_store.set_visible_func(self._filter_album_row, None)
        self.albums_view.set_model(self.props.filtered_albums_store)

        self.albums_view.set_text_column(AlbumStoreColumns.TEXT)
        self.albums_view.set_tooltip_column(AlbumStoreColumns.TOOLTIP)
        self.albums_view.set_pixbuf_column(AlbumStoreColumns.PIXBUF)
        self.albums_view.set_item_width(ALBUM_IMAGE_SIZE)

        if application.props.disable_tooltips:
            self.albums_view.props.has_tooltip = False

        self._default_album_image = default_album_image_pixbuf(
            target_width=ALBUM_IMAGE_SIZE,
        )

        self._model.connect("notify::albums-loaded", self.update_album_list)
        application.props.download.connect("albums-images-loaded", self.update_images)

    def set_filtering_text(self, text: str) -> None:
        stripped = text.strip()
        if stripped != self.props.filtering_text:
            LOGGER.debug(f"Filtering albums store according to {stripped}")

            self.props.filtering_text = stripped
            self.props.filtered_albums_store.refilter()

    def _filter_album_row(
        self,
        model: Gtk.ListStore,
        iter: Gtk.TreeIter,
        data: None,
    ) -> bool:
        if not self.props.filtering_text:
            return True

        pattern = re.escape(self.props.filtering_text)
        text = model.get_value(iter, AlbumStoreColumns.FILTER_TEXT)
        return re.search(pattern, text, re.IGNORECASE) is not None

    def update_album_list(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        LOGGER.debug("Updating album list...")

        store = self.props.filtered_albums_store.get_model()
        store.clear()

        for album in self._model.albums:
            store.append(
                [
                    elide_maybe(album.name),
                    GLib.markup_escape_text(album.name),
                    album.uri,
                    str(album.image_path) if album.image_path else None,
                    self._default_album_image,
                    album.name,
                ]
            )

    def update_images(
        self,
        _1: GObject.GObject,
    ) -> None:
        thread = threading.Thread(target=self._update_images)
        thread.daemon = True
        thread.start()

    def _update_images(self) -> None:
        LOGGER.debug("Updating album images...")

        store = self.props.filtered_albums_store.get_model()

        def update_album_image(path: Gtk.TreePath, pixbuf: Pixbuf) -> None:
            store_iter = store.get_iter(path)
            store.set_value(store_iter, AlbumStoreColumns.PIXBUF, pixbuf)

        store_iter = store.get_iter_first()
        while store_iter is not None:
            image_path = store.get_value(store_iter, AlbumStoreColumns.IMAGE_FILE_PATH)
            if image_path:
                scaled_pixbuf = scale_album_image(
                    image_path,
                    target_width=ALBUM_IMAGE_SIZE,
                )
                path = store.get_path(store_iter)
                GLib.idle_add(update_album_image, path, scaled_pixbuf)
            else:
                uri = store.get_value(store_iter, AlbumStoreColumns.URI)
                LOGGER.debug(f"No image path for {uri}")
            store_iter = store.iter_next(store_iter)

    @Gtk.Template.Callback()
    def albums_view_item_activated_cb(
        self, icon_view: Gtk.IconView, path: Gtk.TreePath
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        if not sensitive:
            return

        filtered_store = icon_view.get_model()
        store_iter = filtered_store.get_iter(path)
        uri = filtered_store.get_value(store_iter, AlbumStoreColumns.URI)
        self.emit("album-selected", uri)
