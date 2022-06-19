import logging

from gi.repository import GLib, GObject, Gtk

from ..model import AlbumModel
from ..utils import elide_maybe
from .utils import default_album_image_pixbuf, scale_album_image

LOGGER = logging.getLogger(__name__)

ALBUM_IMAGE_SIZE = 100


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/album_box.ui")
class AlbumBox(Gtk.Box):
    __gtype_name__ = "AlbumBox"

    default_album_image = default_album_image_pixbuf(
        target_width=ALBUM_IMAGE_SIZE,
    )

    album = GObject.Property(type=AlbumModel)

    album_image: Gtk.Label = Gtk.Template.Child()
    album_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application, *, album: AlbumModel):
        super().__init__()

        self._app = application
        self._disable_tooltips = application.props.disable_tooltips
        self.props.album = album

        self.album_image.set_from_pixbuf(self.default_album_image)

        self.album_name_label.set_text(elide_maybe(album.name))
        if not self._disable_tooltips:
            self.album_name_label.set_tooltip_markup(
                GLib.markup_escape_text(album.name)
            )
        self.artist_name_label.set_text(elide_maybe(album.artist_name))
        if not self._disable_tooltips:
            self.artist_name_label.set_tooltip_markup(
                GLib.markup_escape_text(album.artist_name)
            )

        if not self._disable_tooltips:
            self.set_tooltip_text(self.album.name)
        else:
            for widget in (
                self.album_name_label,
                self.artist_name_label,
            ):
                widget.props.has_tooltip = False

    def update_image(self) -> None:
        scaled_pixbuf = None
        image_path = self.album.image_path
        if image_path:
            scaled_pixbuf = scale_album_image(
                image_path,
                target_width=ALBUM_IMAGE_SIZE,
            )

        if scaled_pixbuf:
            self.album_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.album_image.set_from_pixbuf(self.default_album_image)

        self.album_image.show_now()
