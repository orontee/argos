import gettext
import logging
from typing import Optional

from gi.repository import Gio, GLib, GObject, Gtk

from argos.model import ArtistModel, Model

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

_MISSING_INFO_MSG = _("Information not available")
_MISSING_INFO_MSG_WITH_MARKUP = f"""<span style="italic">{_MISSING_INFO_MSG}</span>"""


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/artist_view.ui")
class ArtistView(Gtk.Box):

    __gtype_name__ = "ArtistView"

    artist_image: Gtk.Image = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()

    artist_information_label: Gtk.Label = Gtk.Template.Child()
    artist_information_viewport: Gtk.Viewport = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.set_sensitive(self._model.network_available and self._model.connected)

        for widget in (
            self.artist_image,
            self.artist_name_label,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect(
            "notify::network-available", self._handle_connection_changed
        )
        self._model.connect("notify::connected", self._handle_connection_changed)
        self._model.connect("artist-completed", self._on_artist_completed)
        self._model.connect(
            "artist-information-collected", self._on_artist_information_collected
        )

        self.connect("notify::uri", self._on_uri_changed)

        settings: Gio.Settings = application.props.settings
        settings.connect(
            "changed::information-service", self.on_information_service_changed
        )
        application.props.download.connect(
            "images-downloaded", self._update_artist_image
        )

    def _handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)

    def _on_uri_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        artist = self._model.get_artist(self.props.uri)
        if artist is None:
            self._update_artist_name_label(None)
            self._update_information_label(None)
        else:
            self._app.activate_action(
                "complete-artist-description", GLib.Variant("s", artist.uri)
            )
            self._app.activate_action(
                "collect-artist-information", GLib.Variant("s", artist.uri)
            )
            self._update_artist_name_label(artist.name)
            self._update_information_label(artist)

    def _on_artist_completed(self, model: Model, uri: str) -> None:
        if self.props.uri != uri:
            return

    def _on_artist_information_collected(self, model: Model, uri: str) -> None:
        if self.props.uri != uri:
            return

        artist = self._model.get_artist(self.props.uri)
        if artist is None:
            return

        self._update_information_label(artist)

    def _update_artist_name_label(self, artist_name: Optional[str]) -> None:
        if artist_name:
            safe_artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = (
                f"""<span size="xx-large"><b>{safe_artist_name}</b></span>"""
            )
            self.artist_name_label.set_markup(artist_name_text)
            if not self._disable_tooltips:
                self.artist_name_label.set_has_tooltip(True)
                self.artist_name_label.set_tooltip_text(artist_name)
        else:
            self.artist_name_label.set_markup(_("Unknown artist"))
            self.artist_name_label.set_has_tooltip(False)

        self.artist_name_label.show_now()

    def _update_artist_image(
        self, _1: Optional[GObject.GObject] = None, *, force: bool = False
    ) -> None:
        LOGGER.debug("Image downloaded!")
        artist = self._model.get_artist(self.props.uri)
        if artist is not None:
            LOGGER.debug(f"Artist image path: {artist.image_path}")

    def _update_information_label(self, artist: Optional[ArtistModel]) -> None:
        information = artist.information if artist is not None else None
        self.artist_information_label.set_markup(
            information.abstract
            if information and information.abstract
            else _MISSING_INFO_MSG_WITH_MARKUP
        )

        if self.artist_information_viewport.props.hadjustment is not None:
            self.artist_information_viewport.props.hadjustment.set_value(0)

        if self.artist_information_viewport.props.vadjustment is not None:
            self.artist_information_viewport.props.vadjustment.set_value(0)

    def on_information_service_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        information_service = settings.get_boolean("information-service")
        self.information_button.set_visible(information_service)

        if information_service:
            self._app.activate_action(
                "collect-artist-information", GLib.Variant("s", self.props.uri)
            )
