import gettext
import logging
import re
from functools import partial
from pathlib import Path
from typing import List, Optional

from gi.repository import Gio, GLib, GObject, Gtk

from argos.model import AlbumModel, Model, TrackModel
from argos.utils import ms_to_text
from argos.widgets.trackbox import TrackBox
from argos.widgets.utils import (
    default_image_pixbuf,
    scale_album_image,
    set_list_box_header_with_disc_separator,
)

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

_ALBUM_IMAGE_SIZE = 200

_MISSING_INFO_MSG = _("Information not available")
_MISSING_INFO_MSG_WITH_MARKUP = f"""<span style="italic">{_MISSING_INFO_MSG}</span>"""


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/album_details_box.ui")
class AlbumDetailsBox(Gtk.Box):
    """Box gathering details on an album.

    The box has horizontal orientation, is homogeneous and has two
    children boxes: The left pane displays the album image and the
    album details; The right pane displays the album tracks view and a
    button box.

    """

    __gtype_name__ = "AlbumDetailsBox"

    default_album_image = default_image_pixbuf(
        "media-optical", max_size=_ALBUM_IMAGE_SIZE
    )

    play_button: Gtk.Button = Gtk.Template.Child()
    track_selection_button: Gtk.MenuButton = Gtk.Template.Child()

    album_image: Gtk.Image = Gtk.Template.Child()

    album_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()
    publication_label: Gtk.Label = Gtk.Template.Child()
    length_label: Gtk.Label = Gtk.Template.Child()
    track_count_label: Gtk.Label = Gtk.Template.Child()

    tracks_box: Gtk.ListBox = Gtk.Template.Child()

    information_button: Gtk.MenuButton = Gtk.Template.Child()
    album_information_label: Gtk.Label = Gtk.Template.Child()
    album_information_viewport: Gtk.Viewport = Gtk.Template.Child()
    artist_information_label: Gtk.Label = Gtk.Template.Child()
    artist_information_viewport: Gtk.Viewport = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.props.model
        self._disable_tooltips = application.props.disable_tooltips

        self.tracks_box.set_header_func(
            partial(
                set_list_box_header_with_disc_separator,
                on_disc_separator_clicked=self.on_disc_separator_clicked,
            )
        )
        self._clear_tracks_box_selection = False
        # Gtk automatically add first row to selection when a
        # non-empty model is bound to track_box; This flag is used to
        # remove that selection.

        track_selection_menu = Gio.Menu()
        track_selection_menu.append(
            _("Add to tracklist"), "win.add-to-tracklist::album-details-box"
        )
        track_selection_menu.append(
            _("Add to playlist…"), "win.add-to-playlist::album-details-box"
        )
        self.track_selection_button.set_menu_model(track_selection_menu)

        self.album_information_label.set_selectable(True)
        self.artist_information_label.set_selectable(True)

        self.set_sensitive(self._model.network_available and self._model.connected)

        for widget in (
            self.play_button,
            self.track_selection_button,
            self.tracks_box,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect(
            "notify::network-available", self._handle_connection_changed
        )
        self._model.connect("notify::connected", self._handle_connection_changed)
        self._model.connect("album-completed", self._on_album_completed)
        self._model.connect(
            "album-information-collected", self._on_album_information_collected
        )

        self.connect("notify::uri", self._on_uri_changed)

        settings: Gio.Settings = application.props.settings
        settings.connect(
            "changed::information-service", self.on_information_service_changed
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
        album = self._model.get_album(self.props.uri)
        if album is None:
            self._update_album_name_label(None)
            self._update_artist_name_label(None)
            self._update_publication_label(None)
            self._update_length_label(None)
            self._update_track_count_label(None)
            self._update_album_image(None)
            self._update_track_view(None)
            self._update_information_popup(None)
        else:
            self._update_album_name_label(album.name)
            self._update_artist_name_label(album.artist_name)
            self._update_publication_label(album.date)
            self._update_track_count_label(album.tracks)
            self._update_length_label(album.length)
            self._update_album_image(
                Path(album.image_path) if album.image_path else None
            )
            self._update_track_view(album)
            self._update_information_popup(album)

        self._app.activate_action(
            "collect-album-information", GLib.Variant("s", self.props.uri)
        )

    def _on_album_completed(self, model: Model, uri: str) -> None:
        if self.uri != uri:
            return

        album = self._model.get_album(self.props.uri)
        if album is None:
            return

        self._update_artist_name_label(album.artist_name)
        self._update_publication_label(album.date)
        self._update_track_count_label(album.tracks)
        self._update_length_label(album.length)
        self._update_album_image(Path(album.image_path) if album.image_path else None)
        self._update_track_view(album)

    def _on_album_information_collected(self, model: Model, uri: str) -> None:
        if self.uri != uri:
            return

        album = self._model.get_album(self.props.uri)
        if album is None:
            return

        self._update_information_popup(album)

    def _update_album_name_label(self, album_name: Optional[str]) -> None:
        if album_name:
            safe_album_name = GLib.markup_escape_text(album_name)
            album_name_text = (
                f"""<span size="xx-large"><b>{safe_album_name}</b></span>"""
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
            safe_artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = f"""<span size="x-large">{safe_artist_name}</span>"""
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
            self.publication_label.set_text(_("Not available"))

        self.publication_label.show_now()

    def _update_track_count_label(self, tracks: Optional[Gio.ListStore] = None) -> None:
        if tracks is None:
            self.track_count_label.set_text("")
        else:
            self.track_count_label.set_text(str(len(tracks)))

        self.track_count_label.show_now()

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
            scaled_pixbuf = scale_album_image(image_path, max_size=_ALBUM_IMAGE_SIZE)

        if scaled_pixbuf:
            self.album_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.album_image.set_from_pixbuf(self.default_album_image)

        self.album_image.show_now()

    def _update_track_view(self, album: Optional[AlbumModel]) -> None:
        if album is None:
            self.tracks_box.bind_model(
                None,
                None,
            )
        else:
            tracks = album.tracks
            self.tracks_box.bind_model(
                tracks,
                self._create_track_box,
                album,
            )

        self._clear_tracks_box_selection = True

    def _update_information_popup(self, album: Optional[AlbumModel]) -> None:
        information = album.information if album is not None else None
        self.album_information_label.set_markup(
            information.album_abstract
            if information and information.album_abstract
            else _MISSING_INFO_MSG_WITH_MARKUP
        )
        if self.album_information_viewport.props.hadjustment is not None:
            self.album_information_viewport.props.hadjustment.set_value(0)

        if self.album_information_viewport.props.vadjustment is not None:
            self.album_information_viewport.props.vadjustment.set_value(0)

        self.artist_information_label.set_markup(
            information.artist_abstract
            if information and information.artist_abstract
            else _MISSING_INFO_MSG_WITH_MARKUP
        )
        if self.artist_information_viewport.props.hadjustment is not None:
            self.artist_information_viewport.props.hadjustment.set_value(0)

        if self.artist_information_viewport.props.vadjustment is not None:
            self.artist_information_viewport.props.vadjustment.set_value(0)

    def _create_track_box(self, track: TrackModel, album: AlbumModel) -> Gtk.Widget:
        widget = TrackBox(self._app, album=album, track=track)
        return widget

    def track_selection_to_uris(self) -> List[str]:
        """Returns the list of URIs for current track selection.

        The returned list contains the album URI if current track
        selection is empty.

        """
        uris: List[str] = []
        selected_rows = self.tracks_box.get_selected_rows()
        for row in selected_rows:
            track_box = row.get_child()
            uri = track_box.props.uri if track_box else None
            if uri is not None:
                uris.append(uri)

        if len(uris) == 0:
            uris.append(self.uri)

        return uris

    def on_information_service_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        information_service = settings.get_boolean("information-service")
        self.information_button.set_visible(information_service)

        if information_service:
            self._app.activate_action(
                "collect-album-information", GLib.Variant("s", self.props.uri)
            )

    @Gtk.Template.Callback()
    def on_button_clicked(self, button: Gtk.Button) -> None:
        if self._app.window is None:
            return

        # Better set button action but never manage to get it working...

        action_name: Optional[str] = None
        if button == self.play_button:
            action_name = "play-selection"

        if action_name is not None:
            target = GLib.Variant("s", "album-details-box")
            self._app.window.activate_action(action_name, target)

    def on_disc_separator_clicked(
        self,
        label: Gtk.Button,
        user_data: GLib.Variant,
    ) -> None:
        disc_no = user_data.get_int32()
        LOGGER.debug(f"Selecting tracks for disc number {disc_no}")

        for row in self.tracks_box.get_children():
            track_box = row.get_child()
            if track_box is None:
                LOGGER.debug("Failed to find track box!")
                continue

            if track_box.props.disc_no == disc_no:
                if self._clear_tracks_box_selection:
                    self._clear_tracks_box_selection = False
                    # Disable hack to fix unwanted automatic selection
                    # otherwise first track of first disc is
                    # automatically unselected!!

                self.tracks_box.select_row(row)

    @Gtk.Template.Callback()
    def on_tracks_box_selected_rows_changed(
        self,
        _1: Gtk.ListBox,
    ) -> None:
        if not self._clear_tracks_box_selection:
            return

        # Hack to fix first row automatically added to selection on
        # model binding
        selected_rows = self.tracks_box.get_selected_rows()
        if len(selected_rows) == 1 and selected_rows[0].get_index() == 0:
            self.tracks_box.unselect_all()
        self._clear_tracks_box_selection = False

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
            self._app.activate_action("play-tracks", GLib.Variant("as", [uri]))
