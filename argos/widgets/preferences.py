import asyncio
import logging
from typing import Any, Dict, List

from gi.repository import Gio, Gtk

from ..message import Message, MessageType

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/preferences.ui")
class PreferencesWindow(Gtk.Window):
    __gtype_name__ = "ArgosPreferences"

    settings: Gio.Settings = Gio.Settings.new("app.argos.Argos")

    mopidy_base_url_entry: Gtk.Entry = Gtk.Template.Child()
    favorite_playlist_combo: Gtk.ComboBoxText = Gtk.Template.Child()
    favorite_playlist_spinner: Gtk.Spinner = Gtk.Template.Child()

    def __init__(
        self,
        *,
        message_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
    ):
        Gtk.Window.__init__(self)
        self.set_wmclass("Argos", "Argos")
        self._message_queue = message_queue
        self._loop = loop
        self._favorite_playlist_model = Gtk.ListStore(str, str)

        self.favorite_playlist_combo.set_id_column(1)
        self.favorite_playlist_combo.set_model(self._favorite_playlist_model)
        self._favorite_playlist_combo_changed_id = self.favorite_playlist_combo.connect(
            "changed", self.favorite_playlist_combo_changed_cb
        )

        mopidy_base_url_entry_changed_id = self.mopidy_base_url_entry.connect(
            "changed", self.mopidy_base_url_entry_changed_cb
        )

        base_url = self.settings.get_string("mopidy-base-url")
        if base_url:
            with self.mopidy_base_url_entry.handler_block(
                mopidy_base_url_entry_changed_id
            ):
                self.mopidy_base_url_entry.set_text(base_url)

        self.list_playlists()

    def mopidy_base_url_entry_changed_cb(self, entry: Gtk.Entry) -> None:
        base_url = entry.get_text()
        self.settings.set_string("mopidy-base-url", base_url)
        # TODO self.list_playlists() once connected

    def favorite_playlist_combo_changed_cb(self, combo: Gtk.ComboBox) -> None:
        favorite_playlist_uri = combo.get_active_id()
        self.settings.set_string("favorite-playlist-uri", favorite_playlist_uri)

    def list_playlists(self) -> None:
        self.favorite_playlist_combo.set_sensitive(False)
        self.favorite_playlist_spinner.start()
        self._loop.call_soon_threadsafe(
            self._message_queue.put_nowait,
            Message(MessageType.LIST_PLAYLISTS),
        )

    def update_favorite_playlist_completion(
        self, playlists: List[Dict[str, Any]]
    ) -> None:
        with self.favorite_playlist_combo.handler_block(
            self._favorite_playlist_combo_changed_id
        ):
            self._favorite_playlist_model.clear()

            for playlist in playlists:
                name = playlist.get("name")
                uri = playlist.get("uri")
                if name and uri:
                    self._favorite_playlist_model.append([name, uri])

            favorite_playlist_uri = self.settings.get_string("favorite-playlist-uri")
            self.favorite_playlist_combo.set_active_id(favorite_playlist_uri)

        self.favorite_playlist_spinner.stop()
        self.favorite_playlist_combo.set_sensitive(True)
