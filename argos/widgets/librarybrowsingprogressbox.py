import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)


@Gtk.Template(
    resource_path="/io/github/orontee/Argos/ui/library_browsing_progress_box.ui"
)
class LibraryBrowsingProgressBox(Gtk.Box):
    __gtype_name__ = "LibraryBrowsingProgressBox"
