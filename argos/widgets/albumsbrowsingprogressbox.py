import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)


@Gtk.Template(
    resource_path="/io/github/orontee/Argos/ui/albums_browsing_progress_box.ui"
)
class AlbumsBrowsingProgressBox(Gtk.Box):
    __gtype_name__ = "AlbumsBrowsingProgressBox"
