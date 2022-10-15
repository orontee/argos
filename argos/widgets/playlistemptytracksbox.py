import gettext
import logging

from gi.repository import GObject, Gtk

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlist_empty_tracks_box.ui")
class PlaylistEmptyTracksBox(Gtk.Box):
    """Box to use as a placeholder for empty playlist tracks box.

    The box has vertical orientation and has two children boxes: An
    active spinner and a label.

    """

    __gtype_name__ = "PlaylistEmptyTracksBox"

    progress_label: Gtk.Label = Gtk.Template.Child()
    progress_spinner: Gtk.Spinner = Gtk.Template.Child()

    loading = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self.connect("notify::loading", self._handle_loading_changed)

    def _handle_loading_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if self.props.loading:
            self.progress_spinner.start()
            self.progress_label.set_text(_("Loading playlist tracks…"))
        else:
            self.progress_spinner.stop()
            self.progress_label.set_text("")
