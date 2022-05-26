import gettext
import logging
from pathlib import Path
import re
from typing import Optional

from gi.repository import Gio, GLib, GObject, Gtk

from ..message import MessageType
from ..model import Model, TrackModel
from ..utils import elide_maybe, ms_to_text
from .trackbox import TrackBox
from .utils import (
    default_album_image_pixbuf,
    scale_album_image,
    set_list_box_header_with_separator,
)

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ALBUM_IMAGE_SIZE = 80


@Gtk.Template(resource_path="/app/argos/Argos/ui/album_box.ui")
class AlbumBox(Gtk.Box):
    __gtype_name__ = "AlbumBox"

    add_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()

    album_image: Gtk.Image = Gtk.Template.Child()

    album_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()
    publication_label: Gtk.Label = Gtk.Template.Child()
    length_label: Gtk.Label = Gtk.Template.Child()

    tracks_box: Gtk.ListBox = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.tracks_box.set_header_func(set_list_box_header_with_separator)

        for widget in (
            self.add_button,
            self.play_button,
            self.tracks_box,
        ):
            widget.set_sensitive(
                self._model.network_available and self._model.connected
            )
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._default_album_image = default_album_image_pixbuf(
            target_width=ALBUM_IMAGE_SIZE,
        )

        self._model.connect(
            "notify::network-available", self._handle_connection_changed
        )
        self._model.connect("notify::connected", self._handle_connection_changed)
        self._model.connect("album-completed", self._on_album_completed)

    def _handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        widgets = [
            self.play_button,
            self.add_button,
            self.tracks_box,
        ]
        for widget in widgets:
            widget.set_sensitive(sensitive)

    def _on_album_completed(self, model: Model, uri: str) -> None:
        if self.uri != uri:
            return

        found = [album for album in model.albums if album.uri == uri]
        if len(found) == 0:
            LOGGER.warning(f"No album found with URI {uri}")
            return

        album = found[0]
        self._update_album_name_label(album.name)
        self._update_artist_name_label(album.artist_name)
        self._update_publication_label(album.date)
        self._update_length_label(album.length)
        self._update_album_image(Path(album.image_path) if album.image_path else None)
        self._update_track_view(album.tracks)

    def _update_album_name_label(self, album_name: Optional[str]) -> None:
        if album_name:
            short_album_name = GLib.markup_escape_text(elide_maybe(album_name))
            album_name_text = (
                f"""<span size="xx-large"><b>{short_album_name}</b></span>"""
            )
            self.album_name_label.set_markup(album_name_text)
            if not self._disable_tooltips:
                self.album_name_label.set_has_tooltip(True)
                self.album_name_label.set_tooltip_text(album_name)
        else:
            self.album_name_label.set_markup("")
            self.album_name_label.set_has_tooltip(False)

        self.album_name_label.show_now()

    def _update_artist_name_label(self, artist_name: Optional[str]) -> None:
        if artist_name:
            short_artist_name = GLib.markup_escape_text(elide_maybe(artist_name))
            artist_name_text = f"""<span size="x-large">{short_artist_name}</span>"""
            self.artist_name_label.set_markup(artist_name_text)
            if not self._disable_tooltips:
                self.artist_name_label.set_has_tooltip(True)
                self.artist_name_label.set_tooltip_text(artist_name)
        else:
            self.artist_name_label.set_markup("")
            self.artist_name_label.set_has_tooltip(False)

        self.artist_name_label.show_now()

    def _update_publication_label(self, date: Optional[str]) -> None:
        year = None
        if date:
            match = re.search("[12][0-9]{3}", date)
            if match:
                year = match.group(0)
        if year:
            self.publication_label.set_text(year)
        else:
            self.publication_label.set_text("")

        self.publication_label.show_now()

    def _update_length_label(self, length: Optional[int]) -> None:
        if length:
            pretty_length = ms_to_text(length)
            self.length_label.set_text(pretty_length)
        else:
            self.length_label.set_text("")

        self.length_label.show_now()

    def _update_album_image(self, image_path: Optional[Path]) -> None:
        scaled_pixbuf = None
        if image_path:
            rectangle = self.album_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.album_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.album_image.set_from_pixbuf(self._default_album_image)

        self.album_image.show_now()

    def _update_track_view(self, tracks: Gio.ListStore) -> None:
        self.tracks_box.bind_model(
            tracks,
            self._create_track_box,
        )

    def _create_track_box(
        self,
        track: TrackModel,
    ) -> Gtk.Widget:
        widget = TrackBox(self._app, track=track)
        return widget

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, _1: Gtk.Button) -> None:
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [self.uri]})

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _1: Gtk.Button) -> None:
        self._app.send_message(MessageType.ADD_TO_TRACKLIST, {"uris": [self.uri]})

    @Gtk.Template.Callback()
    def on_tracks_box_row_activated(
        self,
        box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        if not sensitive:
            return

        track_box = row.get_child()
        uri = track_box.props.uri if track_box else None
        if uri is not None:
            self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [uri]})
