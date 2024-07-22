import gettext
import logging
from typing import TYPE_CHECKING, Any, Optional

from gi.repository import Gdk, Gio, GLib, GObject, Gtk

if TYPE_CHECKING:
    from argos.app import Application

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext

SECONDS_PER_DAY = 3600 * 24


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/preferences.ui")
class PreferencesWindow(Gtk.Window):
    __gtype_name__ = "PreferencesWindow"

    mopidy_base_url_info_bar: Gtk.InfoBar = Gtk.Template.Child()
    mopidy_base_url_entry: Gtk.Entry = Gtk.Template.Child()
    service_discovery_info_bar: Gtk.InfoBar = Gtk.Template.Child()
    service_discovery_question_label: Gtk.Label = Gtk.Template.Child()
    service_discovery_set_button: Gtk.Button = Gtk.Template.Child()
    information_service_switch: Gtk.Switch = Gtk.Template.Child()
    index_mopidy_local_albums_button: Gtk.CheckButton = Gtk.Template.Child()
    history_playlist_check_button: Gtk.CheckButton = Gtk.Template.Child()
    history_playlist_max_length_label: Gtk.Label = Gtk.Template.Child()
    history_playlist_max_length_button: Gtk.SpinButton = Gtk.Template.Child()
    albums_image_size_scale: Gtk.Scale = Gtk.Template.Child()
    albums_image_size_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    prefer_dark_theme_switch: Gtk.Switch = Gtk.Template.Child()
    start_fullscreen_switch: Gtk.Switch = Gtk.Template.Child()

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__(application=application, transient_for=application.window)
        self.set_wmclass("Argos", "preferences")
        self._model = application.model
        self._albums_image_size_scale_jumped_id: Optional[int] = None

        self._settings: Gio.Settings = application.props.settings
        base_url = self._settings.get_string("mopidy-base-url")
        if base_url:
            self.mopidy_base_url_entry.set_text(base_url)

        information_service = self._settings.get_boolean("information-service")
        self.information_service_switch.set_active(information_service)

        index_mopidy_local_albums = self._settings.get_boolean(
            "index-mopidy-local-albums"
        )
        self.index_mopidy_local_albums_button.set_active(index_mopidy_local_albums)

        history_playlist = self._settings.get_boolean("history-playlist")
        self.history_playlist_check_button.set_active(history_playlist)

        history_max_length = self._settings.get_int("history-max-length")
        self.history_playlist_max_length_button.set_value(history_max_length)

        albums_image_size = self._settings.get_int("albums-image-size")
        self.albums_image_size_adjustment.set_value(albums_image_size)

        albums_image_size_min, albums_image_size_max = self._settings.get_range(
            "albums-image-size"
        )[1]
        # since of the form GLib.Variant('(sv)', ('range', <(50, 200)>))
        self.albums_image_size_scale.add_mark(
            albums_image_size_min, Gtk.PositionType.TOP, ""
        )
        self.albums_image_size_scale.add_mark(
            (albums_image_size_min + albums_image_size_max) // 2,
            Gtk.PositionType.TOP,
            "",
        )
        self.albums_image_size_scale.add_mark(
            albums_image_size_max, Gtk.PositionType.TOP, ""
        )

        self.albums_image_size_scale.connect(
            "change-value", self.on_albums_image_size_scale_change_value
        )

        prefer_dark_theme = self._settings.get_boolean("prefer-dark-theme")
        self.prefer_dark_theme_switch.set_active(prefer_dark_theme)

        start_fullscreen = self._settings.get_boolean("start-fullscreen")
        self.start_fullscreen_switch.set_active(start_fullscreen)

        sensitive = self._model.network_available and self._model.connected
        for widget in (
            self.history_playlist_check_button,
            self.history_playlist_max_length_label,
            self.history_playlist_max_length_button,
        ):
            widget.set_sensitive(sensitive)

        self.history_playlist_max_length_label.set_sensitive(
            sensitive and history_playlist
        )
        self.history_playlist_max_length_button.set_sensitive(
            sensitive and history_playlist
        )

        self._model.connect("notify::network-available", self.on_connection_changed)
        self._model.connect("notify::connected", self.on_connection_changed)

        # ⚠️ Don't connect signals to handlers automatically through
        # Gtk.Template since otherwise handlers will be called during
        # initialization from settings

        self.mopidy_base_url_entry.connect(
            "changed", self.on_mopidy_base_url_entry_changed
        )
        self.information_service_switch.connect(
            "notify::active", self.on_information_service_switch_activated
        )
        self.index_mopidy_local_albums_button.connect(
            "toggled", self.on_index_mopidy_local_albums_button_toggled
        )
        self.history_playlist_check_button.connect(
            "toggled", self.on_history_playlist_check_button_toggled
        )
        self.history_playlist_max_length_button.connect(
            "value-changed", self.on_history_playlist_max_length_button_value_changed
        )

        self.prefer_dark_theme_switch.connect(
            "notify::active", self.on_dark_theme_switch_activated
        )

        self.start_fullscreen_switch.connect(
            "notify::active", self.on_start_fullscreen_switch_activated
        )

        application._service_scanner.connect(
            "service-discovered", self.on_service_discovered
        )

        title_bar = Gtk.HeaderBar(title=_("Preferences"), show_close_button=True)
        self.set_titlebar(title_bar)

        self.show_all()
        self.mopidy_base_url_info_bar.set_revealed(
            self._model.network_available and not self._model.connected
        )

    def on_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.mopidy_base_url_info_bar.set_revealed(
            self._model.network_available and not self._model.connected
        )

        sensitive = self._model.network_available and self._model.connected
        widgets = (self.history_playlist_check_button,)
        for widget in widgets:
            widget.set_sensitive(sensitive)

        history_playlist = self._settings.get_boolean("history-playlist")
        self.history_playlist_max_length_label.set_sensitive(
            sensitive and history_playlist
        )
        self.history_playlist_max_length_button.set_sensitive(
            sensitive and history_playlist
        )

    def on_mopidy_base_url_entry_changed(self, entry: Gtk.Entry) -> None:
        base_url = entry.get_text()
        self._settings.set_string("mopidy-base-url", base_url)

    def on_service_discovered(
        self, scanner: Any, service_name: str, service_address: str
    ) -> None:
        if len(service_address) <= 0:
            return

        self.service_discovery_question_label.set_text(
            (
                _(
                    "Do you want to use the Mopidy HTTP service "
                    "discovered at {address}?"
                )
            ).format(address=service_address)
        )

        self.service_discovery_info_bar.set_revealed(True)

        mopidy_base_url_entry: Gtk.Entry = self.mopidy_base_url_entry

        def on_service_discovery_set_button_clicked(_1: Gtk.Button) -> None:
            LOGGER.debug("Base URL set to address of discovered service")
            mopidy_base_url_entry.set_text(f"http://{service_address}")

        self.service_discovery_set_button.connect(
            "clicked", on_service_discovery_set_button_clicked
        )

    def on_information_service_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: GObject.ParamSpec,
    ) -> None:
        information_service = switch.get_active()
        self._settings.set_boolean("information-service", information_service)

    def on_index_mopidy_local_albums_button_toggled(
        self, button: Gtk.CheckButton
    ) -> None:
        index_mopidy_local_albums = button.get_active()
        self._settings.set_boolean(
            "index-mopidy-local-albums", index_mopidy_local_albums
        )

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

    def _on_albums_image_size_scale_jumped(self) -> bool:
        if self._albums_image_size_scale_jumped_id is not None:
            value = self.albums_image_size_adjustment.props.value
            self._settings.set_int("albums-image-size", value)
            self._albums_image_size_scale_jumped_id = None
        return False  # means stop calling this callback

    def on_albums_image_size_scale_change_value(
        self,
        widget: Gtk.Widget,
        scroll_type: Gtk.ScrollType,
        value: float,
    ) -> bool:
        if scroll_type in (
            Gtk.ScrollType.JUMP,
            Gtk.ScrollType.STEP_BACKWARD,
            Gtk.ScrollType.STEP_FORWARD,
            Gtk.ScrollType.PAGE_BACKWARD,
            Gtk.ScrollType.PAGE_FORWARD,
        ):
            if self._albums_image_size_scale_jumped_id is not None:
                GLib.source_remove(self._albums_image_size_scale_jumped_id)

            self._albums_image_size_scale_jumped_id = GLib.timeout_add(
                100,  # ms
                self._on_albums_image_size_scale_jumped,
            )
            return False
        elif scroll_type in (
            Gtk.ScrollType.START,
            Gtk.ScrollType.END,
        ):
            self._settings.set_int("albums-image-size", value)
            return False

        LOGGER.warning(f"Unhandled scroll type {scroll_type!r}")
        return False

    def on_dark_theme_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: GObject.ParamSpec,
    ) -> None:
        prefer_dark_theme = switch.get_active()
        self._settings.set_boolean("prefer-dark-theme", prefer_dark_theme)

    def on_start_fullscreen_switch_activated(
        self,
        switch: Gtk.Switch,
        _1: GObject.ParamSpec,
    ) -> None:
        start_fullscreen = switch.get_active()
        self._settings.set_boolean("start-fullscreen", start_fullscreen)

    @Gtk.Template.Callback()
    def key_press_event_cb(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        # See /usr/include/gtk-3.0/gdk/gdkkeysyms.h for key definitions
        modifiers = event.get_state() & Gtk.accelerator_get_default_mod_mask()
        keyval = event.get_keyval()
        if not modifiers:
            if keyval == Gdk.KEY_Escape:
                # Better add a "close" signal to the class and call
                # Gtk.binding_entry_add_signall() because it would be
                # possible to edit the binding at runtime, but could
                # not find a way to get the class BindingSet required
                # as first argument (BindingSet.by_class() isn't
                # exposed to Python), see #155
                super().close()
                return True
        return False
