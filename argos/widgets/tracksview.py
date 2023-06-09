import gettext
import logging
from typing import List, Optional

from gi.repository import Gio, GLib, GObject, Gtk

from argos.model import TrackModel
from argos.utils import ms_to_text
from argos.widgets.trackbox import TrackBox
from argos.widgets.utils import default_image_pixbuf

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

_DIRECTORY_IMAGE_SIZE = 200


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/tracks_view.ui")
class TracksView(Gtk.Box):

    __gtype_name__ = "TracksView"

    default_directory_image = default_image_pixbuf(
        "inode-directory", max_size=_DIRECTORY_IMAGE_SIZE
    )

    play_button: Gtk.Button = Gtk.Template.Child()
    track_selection_button: Gtk.MenuButton = Gtk.Template.Child()

    length_label: Gtk.Label = Gtk.Template.Child()
    track_count_label: Gtk.Label = Gtk.Template.Child()

    directory_image: Gtk.Image = Gtk.Template.Child()

    directory_name_label: Gtk.Label = Gtk.Template.Child()

    tracks_box: Gtk.ListBox = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        track_selection_menu = Gio.Menu()
        track_selection_menu.append(
            _("Add to tracklist"), "win.add-to-tracklist::tracks-view"
        )
        track_selection_menu.append(
            _("Add to playlist…"), "win.add-to-playlist::tracks-view"
        )
        self.track_selection_button.set_menu_model(track_selection_menu)

        self.set_sensitive(self._model.network_available and self._model.connected)

        self.directory_image.set_from_pixbuf(self.default_directory_image)

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

        self.connect("notify::uri", self._on_uri_changed)

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
        directory = self._model.get_directory(self.props.uri)
        directory_name = directory.name if directory is not None else None
        tracks = directory.tracks if directory is not None else None

        self._update_directory_name_label(directory_name)
        self._update_track_count_label(tracks)
        self._update_length_label(tracks)
        self.tracks_box.bind_model(tracks, self._create_track_box)

    def _update_directory_name_label(self, directory_name: Optional[str]) -> None:
        if directory_name:
            safe_directory_name = GLib.markup_escape_text(directory_name)
            directory_name_text = (
                f"""<span size="xx-large"><b>{safe_directory_name}</b></span>"""
            )
            self.directory_name_label.set_markup(directory_name_text)
            if not self._disable_tooltips:
                self.directory_name_label.set_has_tooltip(True)
                self.directory_name_label.set_tooltip_text(directory_name)
        else:
            self.directory_name_label.set_markup("")
            self.directory_name_label.set_has_tooltip(False)

        self.directory_name_label.show_now()

    def _update_track_count_label(self, tracks: Optional[Gio.ListStore] = None) -> None:
        if tracks is None:
            self.track_count_label.set_text("")
        else:
            self.track_count_label.set_text(str(len(tracks)))

        self.track_count_label.show_now()

    def _update_length_label(self, tracks: Optional[Gio.ListStore] = None) -> None:
        if tracks is None:
            self.length_label.set_text("")
        else:
            length = 0
            for track in tracks:
                if track.length == -1:
                    length = -1
                    break
                length += track.length

            pretty_length = ms_to_text(length)
            self.length_label.set_text(pretty_length)

        self.length_label.show_now()

    def _create_track_box(self, track: TrackModel) -> Gtk.Widget:
        widget = TrackBox(self._app, track=track)
        return widget

    def track_selection_to_uris(self) -> List[str]:
        """Returns the list of URIs for current track selection.

        When current track selection is empty, all URIs of the tracks box rows
        are returned.

        """
        uris: List[str] = []
        rows = self.tracks_box.get_selected_rows()
        if len(rows) == 0:
            rows = self.tracks_box.get_children()

        for row in rows:
            track_box = row.get_child()
            uri = track_box.props.uri if track_box else None
            if uri is not None:
                uris.append(uri)

        return uris

    @Gtk.Template.Callback()
    def on_button_clicked(self, button: Gtk.Button) -> None:
        if self._app.window is None:
            return

        # Better set button action but never manage to get it working...

        action_name: Optional[str] = None
        if button == self.play_button:
            action_name = "play-selection"

        target = GLib.Variant("s", "tracks-view")
        if action_name is not None:
            self._app.window.activate_action(action_name, target)

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
