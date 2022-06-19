import logging

from gi.repository import GObject, Gtk

from ..model import AlbumModel
from .albumbox import AlbumBox

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/albums_window.ui")
class AlbumsWindow(Gtk.ScrolledWindow):
    __gtype_name__ = "AlbumsWindow"

    __gsignals__ = {"album-selected": (GObject.SIGNAL_RUN_FIRST, None, (str,))}

    albums_flowbox: Gtk.FlowBox = Gtk.Template.Child()

    filtering_text = GObject.Property(type=str)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model

        self.albums_flowbox.bind_model(
            self._model.albums,
            self._create_album_box,
        )
        self.albums_flowbox.set_activate_on_single_click(application.props.single_click)
        application.props.download.connect("albums-images-loaded", self.update_images)

    def _create_album_box(
        self,
        album: AlbumModel,
    ) -> Gtk.Widget:
        widget = AlbumBox(self._app, album=album)
        return widget

    def set_filtering_text(self, text: str) -> None:
        stripped = text.strip()
        if stripped != self.props.filtering_text:
            LOGGER.debug(f"Filtering albums store according to {stripped}")

            self.props.filtering_text = stripped

    def update_images(self, _1: GObject.GObject) -> None:
        child_index = 0
        child = self.albums_flowbox.get_child_at_index(child_index)
        while child:
            album_box = child.get_child()
            album_box.update_image()
            child_index += 1
            child = self.albums_flowbox.get_child_at_index(child_index)

    @Gtk.Template.Callback()
    def on_albums_flowbox_child_activated(
        self, albums_flowbox: Gtk.FlowBox, child: Gtk.FlowBoxChild
    ) -> None:
        album_box = child.get_child() if child else None
        album = album_box.album if album_box else None
        if album:
            uri = album.uri
            self.emit("album-selected", uri)

    # @Gtk.Template.Callback()
    # def on_albums_flowbox_selected_children_changed(
    #     self, albums_flowbox: Gtk.FlowBox
    # ) -> None:
