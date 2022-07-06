import logging
from typing import TYPE_CHECKING

from gi.repository import Gio, GObject, Gtk

if TYPE_CHECKING:
    from ..app import Application

LOGGER = logging.getLogger(__name__)


SECONDS_PER_DAY = 3600 * 24


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/preferences.ui")
class PreferencesWindow(Gtk.Window):
    __gtype_name__ = "PreferencesWindow"

    mopidy_base_url_entry: Gtk.Entry = Gtk.Template.Child()
    mopidy_local_switch: Gtk.Switch = Gtk.Template.Child()
    mopidy_local_label: Gtk.Label = Gtk.Template.Child()
    mopidy_bandcamp_switch: Gtk.Switch = Gtk.Template.Child()
    mopidy_bandcamp_label: Gtk.Label = Gtk.Template.Child()
    mopidy_podcast_switch: Gtk.Switch = Gtk.Template.Child()
    mopidy_podcast_label: Gtk.Label = Gtk.Template.Child()
    history_playlist_check_button: Gtk.CheckButton = Gtk.Template.Child()
    history_playlist_max_length_label: Gtk.Label = Gtk.Template.Child()
    history_playlist_max_length_button: Gtk.SpinButton = Gtk.Template.Child()
    recent_additions_playlist_check_button: Gtk.CheckButton = Gtk.Template.Child()
    recent_additions_playlist_max_age_label: Gtk.Label = Gtk.Template.Child()
    recent_additions_playlist_max_age_button: Gtk.SpinButton = Gtk.Template.Child()

    def __init__(
        self,
        application: "Application",
    ):
        Gtk.Window.__init__(self)
        self.set_wmclass("Argos", "Argos")
        self._app = application
        self._model = application.model

        self._settings: Gio.Settings = application.props.settings
        base_url = self._settings.get_string("mopidy-base-url")
        if base_url:
            self.mopidy_base_url_entry.set_text(base_url)

        mopidy_local = self._settings.get_boolean("mopidy-local")
        self.mopidy_local_switch.set_active(mopidy_local)

        mopidy_bandcamp = self._settings.get_boolean("mopidy-bandcamp")
        self.mopidy_bandcamp_switch.set_active(mopidy_bandcamp)

        mopidy_podcast = self._settings.get_boolean("mopidy-podcast")
        self.mopidy_podcast_switch.set_active(mopidy_podcast)

        history_playlist = self._settings.get_boolean("history-playlist")
        self.history_playlist_check_button.set_active(history_playlist)
        self.history_playlist_max_length_label.set_sensitive(history_playlist)
        self.history_playlist_max_length_button.set_sensitive(history_playlist)

        history_max_length = self._settings.get_int("history-max-length")
        self.history_playlist_max_length_button.set_value(history_max_length)

        recent_additions_playlist = self._settings.get_boolean(
            "recent-additions-playlist"
        )
        self.recent_additions_playlist_check_button.set_active(
            recent_additions_playlist
        )
        self.recent_additions_playlist_max_age_label.set_sensitive(
            recent_additions_playlist
        )
        self.recent_additions_playlist_max_age_button.set_sensitive(
            recent_additions_playlist
        )

        recent_additions_max_age = self._settings.get_int("recent-additions-max-age")
        self.recent_additions_playlist_max_age_button.set_value(
            recent_additions_max_age // SECONDS_PER_DAY
        )

        for widget in (
            self.mopidy_local_switch,
            self.mopidy_local_label,
            self.mopidy_bandcamp_switch,
            self.mopidy_bandcamp_label,
            self.mopidy_podcast_switch,
            self.mopidy_podcast_label,
            self.history_playlist_check_button,
            self.history_playlist_max_length_label,
            self.history_playlist_max_length_button,
            self.recent_additions_playlist_check_button,
            self.recent_additions_playlist_max_age_label,
            self.recent_additions_playlist_max_age_button,
        ):
            widget.set_sensitive(
                self._model.network_available and self._model.connected
            )

        self._model.connect("notify::network-available", self.on_connection_changed)
        self._model.connect("notify::connected", self.on_connection_changed)
        self.mopidy_base_url_entry.connect(
            "changed", self.on_mopidy_base_url_entry_changed
        )
        self.mopidy_local_switch.connect(
            "notify::active", self.on_mopidy_local_switch_activated
        )
        self.mopidy_bandcamp_switch.connect(
            "notify::active", self.on_mopidy_bandcamp_switch_activated
        )
        self.mopidy_podcast_switch.connect(
            "notify::active", self.on_mopidy_podcast_switch_activated
        )
        self.history_playlist_check_button.connect(
            "toggled", self.on_history_playlist_check_button_toggled
        )
        self.history_playlist_max_length_button.connect(
            "value-changed", self.on_history_playlist_max_length_button_value_changed
        )
        self.recent_additions_playlist_check_button.connect(
            "toggled", self.on_recent_additions_playlist_check_button_toggled
        )
        self.recent_additions_playlist_max_age_button.connect(
            "value-changed",
            self.on_recent_additions_playlist_max_age_button_value_changed,
        )

        # TODO listen to settings changes

    def on_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        widgets = (
            self.mopidy_local_switch,
            self.mopidy_local_label,
            self.mopidy_bandcamp_switch,
            self.mopidy_bandcamp_label,
            self.mopidy_podcast_switch,
            self.mopidy_podcast_label,
            self.history_playlist_check_button,
            self.history_playlist_max_length_label,
            self.history_playlist_max_length_button,
            self.recent_additions_playlist_check_button,
            self.recent_additions_playlist_max_age_label,
            self.recent_additions_playlist_max_age_button,
        )
        for widget in widgets:
            widget.set_sensitive(sensitive)

    def on_mopidy_base_url_entry_changed(self, entry: Gtk.Entry) -> None:
        base_url = entry.get_text()
        self._settings.set_string("mopidy-base-url", base_url)

    def on_mopidy_local_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: bool,
    ) -> None:
        mopidy_local = switch.get_active()
        self._settings.set_boolean("mopidy-local", mopidy_local)

    def on_mopidy_bandcamp_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: bool,
    ) -> None:
        mopidy_bandcamp = switch.get_active()
        self._settings.set_boolean("mopidy-bandcamp", mopidy_bandcamp)

    def on_mopidy_podcast_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: bool,
    ) -> None:
        mopidy_podcast = switch.get_active()
        self._settings.set_boolean("mopidy-podcast", mopidy_podcast)

    def on_history_playlist_check_button_toggled(self, button: Gtk.CheckButton) -> None:
        history_playlist = button.get_active()
        self._settings.set_boolean("history-playlist", history_playlist)
        self.history_playlist_max_length_label.set_sensitive(history_playlist)
        self.history_playlist_max_length_button.set_sensitive(history_playlist)

    def on_history_playlist_max_length_button_value_changed(
        self, button: Gtk.CheckButton
    ) -> None:
        history_max_length = button.get_value()
        self._settings.set_int("history-max-length", history_max_length)

    def on_recent_additions_playlist_check_button_toggled(
        self, button: Gtk.CheckButton
    ) -> None:
        recent_additions_playlist = button.get_active()
        self._settings.set_boolean(
            "recent-additions-playlist", recent_additions_playlist
        )
        self.recent_additions_playlist_max_age_label.set_sensitive(
            recent_additions_playlist
        )
        self.recent_additions_playlist_max_age_button.set_sensitive(
            recent_additions_playlist
        )

    def on_recent_additions_playlist_max_age_button_value_changed(
        self, button: Gtk.CheckButton
    ) -> None:
        recent_additions_max_age = button.get_value() * SECONDS_PER_DAY
        self._settings.set_int("recent-additions-max-age", recent_additions_max_age)
