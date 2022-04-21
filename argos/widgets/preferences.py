import logging
from typing import Any, Dict, List, TYPE_CHECKING

from gi.repository import Gio, Gtk

if TYPE_CHECKING:
    from ..app import Application
from ..message import MessageType

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/preferences.ui")
class PreferencesWindow(Gtk.Window):
    __gtype_name__ = "PreferencesWindow"

    mopidy_base_url_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(
        self,
        application: "Application",
    ):
        Gtk.Window.__init__(self)
        self.set_wmclass("Argos", "Argos")
        self._app = application

        mopidy_base_url_entry_changed_id = self.mopidy_base_url_entry.connect(
            "changed", self.mopidy_base_url_entry_changed_cb
        )

        self._settings: Gio.Settings = application.props.settings
        base_url = self._settings.get_string("mopidy-base-url")
        if base_url:
            with self.mopidy_base_url_entry.handler_block(
                mopidy_base_url_entry_changed_id
            ):
                self.mopidy_base_url_entry.set_text(base_url)

        # TODO listen to settings changes

    def mopidy_base_url_entry_changed_cb(self, entry: Gtk.Entry) -> None:
        base_url = entry.get_text()
        self._settings.set_string("mopidy-base-url", base_url)
