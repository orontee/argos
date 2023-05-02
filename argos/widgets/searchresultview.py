import gettext
import logging
from enum import IntEnum
from typing import Tuple, Union

from gi.repository import Gio, GLib, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from argos.model import AlbumModel, ArtistModel, Model, TrackModel
from argos.utils import elide_maybe
from argos.widgets.trackbox import TrackBox
from argos.widgets.utils import default_image_pixbuf

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

_MAX_ALBUM_OR_ARTIST_ITEMS = 6


class StoreColumn(IntEnum):
    MARKUP = 0
    TOOLTIP = 1
    URI = 2
    IMAGE_FILE_PATH = 3
    PIXBUF = 4


class ItemType(IntEnum):
    ALBUM = 1
    ARTIST = 2
    TRACK = 3


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/search_result_view.ui")
class SearchResultView(Gtk.ScrolledWindow):

    __gtype_name__ = "SearchResultView"

    albums_icon_view: Gtk.IconView = Gtk.Template.Child()
    artists_icon_view: Gtk.IconView = Gtk.Template.Child()
    tracks_box: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model: Model = application.model
        self._settings: Gio.Settings = application.props.settings

        self.image_size = self._settings.get_int("albums-image-size") // 2
        self._settings.connect(
            "changed::albums-image-size", self._on_image_size_changed
        )
        self._init_default_images()
        self._init_stores()

        self.tracks_box.bind_model(
            self._model.search_result.tracks, self._create_track_box
        )

        self._model.connect("search-completed", lambda model: self._update_stores())

        self.show_all()

    def _init_default_images(self):
        self._default_images = {
            ItemType.ALBUM: default_image_pixbuf(
                "media-optical",
                max_size=self.image_size,
            ),
            ItemType.ARTIST: default_image_pixbuf(
                "avatar-default-symbolic",
                max_size=self.image_size,
            ),
            ItemType.TRACK: default_image_pixbuf(
                "audio-x-generic",
                max_size=self.image_size,
            ),
        }

    def _init_stores(self) -> None:
        for view in (
            self.albums_icon_view,
            self.artists_icon_view,
        ):
            store = Gtk.ListStore(str, str, str, str, Pixbuf)
            view.set_model(store)
            view.set_markup_column(StoreColumn.MARKUP)
            view.set_tooltip_column(StoreColumn.TOOLTIP)
            view.set_pixbuf_column(StoreColumn.PIXBUF)
            view.set_item_width(self.image_size)

    def _update_stores(self) -> None:
        LOGGER.debug("Requested to update search result stores")

        albums_store = self.albums_icon_view.get_model()
        albums_store.clear()
        for model in self._model.search_result.albums[:_MAX_ALBUM_OR_ARTIST_ITEMS]:
            albums_store.append(self._build_store_item(model, ItemType.ALBUM))

        artists_store = self.artists_icon_view.get_model()
        artists_store.clear()
        for model in self._model.search_result.artists[:_MAX_ALBUM_OR_ARTIST_ITEMS]:
            artists_store.append(self._build_store_item(model, ItemType.ARTIST))

    def _build_store_item(
        self,
        model: Union[AlbumModel, ArtistModel, TrackModel],
        type: ItemType,
    ) -> Tuple[str, str, str, str, Pixbuf]:
        artist_name = (
            model.get_property("artist_name")
            if type
            in (
                ItemType.ALBUM,
                ItemType.TRACK,
            )
            else None
        )
        # When type is ItemType.ARTIST, the artist name is read from
        # the property "name"

        image_path = str(model.get_property("image_path"))
        pixbuf = self._default_images[type]

        elided_escaped_name = GLib.markup_escape_text(elide_maybe(model.name))
        escaped_name = GLib.markup_escape_text(model.name)

        if artist_name is not None:
            escaped_artist_name = GLib.markup_escape_text(artist_name)
            elided_escaped_artist_name = GLib.markup_escape_text(
                elide_maybe(artist_name)
            )

            markup_text = f"<b>{elided_escaped_name}</b>\n{elided_escaped_artist_name}"
            tooltip_text = f"<b>{escaped_name}</b>\n{escaped_artist_name}"
        else:
            markup_text = f"<b>{elided_escaped_name}</b>"
            tooltip_text = f"<b>{escaped_name}</b>"

        return (
            markup_text,
            tooltip_text,
            model.uri,
            image_path,
            pixbuf,
        )

    def _create_track_box(self, track: TrackModel) -> Gtk.Widget:
        widget = TrackBox(self._app, track=track)
        return widget

    def _on_image_size_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        image_size = settings.get_int("albums-image-size") // 2
        if image_size == self.image_size:
            return

        self.image_size = image_size
        LOGGER.debug(f"Image size changed to {image_size}")
        self._init_default_images()

        self.albums_icon_view.set_item_width(self.image_size)
        self.artists_icon_view.set_item_width(self.image_size)
