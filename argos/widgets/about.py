import gettext
import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/about.ui")
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_wmclass("Argos", "about")

        if self.get_titlebar():
            LOGGER.debug("Client titlebar already set")
        else:
            title_bar = Gtk.HeaderBar(title=_("About"), show_close_button=True)
            self.set_titlebar(title_bar)

        self.show_all()
