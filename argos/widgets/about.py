import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/about.ui")
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "ArgosAbout"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_wmclass("Argos", "Argos")
