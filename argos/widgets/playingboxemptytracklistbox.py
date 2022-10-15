import gettext
import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext

_BOTTOM_LABEL_MARKUP = _(
    """To populate the tracklist:

• <a href="argos:play-random-album">Play a random album</a>

• <a href="argos:add-stream">Add a music stream</a>

• Choose tracks from the library or playlists
"""
)


@Gtk.Template(
    resource_path="/io/github/orontee/Argos/ui/playing_box_empty_tracklist_box.ui"
)
class PlayingBoxEmptyTracklistBox(Gtk.Box):
    """Box to use as a placeholder for empty playing box tracks box.

    The box has vertical orientation and has two children, both being
    labels.

    """

    __gtype_name__ = "PlayingBoxEmptyTracklistBox"

    bottom_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application

        self.bottom_label.set_markup(_BOTTOM_LABEL_MARKUP)

        self.bottom_label.connect("activate-link", self.on_activate_link_cb)

    def on_activate_link_cb(self, label: Gtk.Label, uri: str) -> bool:
        LOGGER.debug(f"Link activated {uri}")

        scheme, action_name = uri.split(":")
        if scheme != "argos":
            return False

        if action_name in ("play-random-album", "add-stream"):
            action = self._app.lookup_action(action_name)
            if not action:
                return False

            action.activate()
            return True

        return False
