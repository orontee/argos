import gettext
import logging
from typing import Optional

from gi.repository import Gio, GLib, GObject, Gtk

from ..model import PlaylistModel
from ..utils import elide_maybe, ms_to_text
from .playlisttracksbox import PlaylistTracksBox

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


class PlaylistLabel(Gtk.Label):
    __gtype_name__ = "PlaylistLabel"

    playlist = GObject.Property(type=PlaylistModel)

    def __init__(self, application: Gtk.Application, *, playlist: PlaylistModel):
        super().__init__()

        self._app = application
        self._disable_tooltips = application.props.disable_tooltips
        self.props.playlist = playlist
        self.props.margin_top = 5
        self.props.margin_bottom = 5
        self.props.halign = Gtk.Align.START
        self.props.use_underline = False
        self.props.use_markup = False

        self._is_virtual = self.playlist.uri.startswith("argos:")

        self.set_text(elide_maybe(self.playlist.name))

        self.playlist.connect("notify::name", self._on_playlist_name_changed)

        if not self._disable_tooltips:
            self.set_tooltip_text(self.playlist.name)

    def is_virtual(self):
        return self._is_virtual

    def _on_playlist_name_changed(
        self, _1: GObject.Object, _2: GObject.ParamSpec
    ) -> None:
        self.set_text(elide_maybe(self.playlist.name))
        if not self._disable_tooltips:
            self.set_tooltip_text(self.playlist.name)


def _set_list_box_header_with_virtual_playlist_separator(
    row: Gtk.ListBox,
    before: Gtk.ListBox,
) -> None:
    current_header = row.get_header()
    if current_header:
        return

    playlist_label = row.get_child()
    if not playlist_label.is_virtual() or before is None:
        return

    before_label = before.get_child()
    if before_label.is_virtual():
        return

    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.show()
    row.set_header(separator)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlists_box.ui")
class PlaylistsBox(Gtk.Box):
    __gtype_name__ = "PlaylistsBox"

    playlists_view: Gtk.TreeView = Gtk.Template.Child()
    playlist_tracks_box = GObject.Property(type=PlaylistTracksBox)

    playlist_name_label: Gtk.Label = Gtk.Template.Child()
    length_label: Gtk.Label = Gtk.Template.Child()
    track_count_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.playlists_view.bind_model(
            self._model.playlists,
            self._create_playlist_box,
        )
        self.playlists_view.set_header_func(
            _set_list_box_header_with_virtual_playlist_separator
        )

        self.props.playlist_tracks_box = PlaylistTracksBox(application)
        self.add(self.props.playlist_tracks_box)

        for widget in (
            self.playlists_view,
            self.playlist_name_label,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self.show_all()

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.playlists_view.set_sensitive(sensitive)

    def _create_playlist_box(
        self,
        playlist: PlaylistModel,
    ) -> Gtk.Widget:
        widget = PlaylistLabel(self._app, playlist=playlist)
        return widget

    @Gtk.Template.Callback()
    def on_playlists_view_row_selected(
        self,
        box: Gtk.ListBox,
        row: Optional[Gtk.ListBoxRow],
    ) -> None:
        playlist_label = row.get_child() if row else None
        playlist = playlist_label.playlist if playlist_label else None
        playlist_name = playlist.props.name if playlist is not None else None

        self._update_playlist_name_label(playlist_name)

        tracks = playlist.tracks if playlist is not None else None
        self._update_track_count_label(tracks)
        self._update_length_label(tracks)

        uri = playlist.uri if playlist else None
        self.props.playlist_tracks_box.bind_model_to_playlist_tracks(uri)

        if playlist is not None:
            playlist.connect("notify::name", self._on_playlist_name_changed)
            playlist.tracks.connect(
                "items-changed", self._on_playlist_tracks_items_changed
            )
            # would be cleaner to disconnect on selection changes...

    def _update_playlist_name_label(self, playlist_name: Optional[str] = None) -> None:
        if playlist_name:
            short_playlist_name = GLib.markup_escape_text(elide_maybe(playlist_name))
            track_name_text = (
                f"""<span size="xx-large"><b>{short_playlist_name}</b></span>"""
            )
            self.playlist_name_label.set_markup(track_name_text)
            if not self._disable_tooltips:
                self.playlist_name_label.set_has_tooltip(True)
                self.playlist_name_label.set_tooltip_text(playlist_name)
        else:
            self.playlist_name_label.set_markup(
                """<span size="xx-large"><b> </b></span>"""
            )
            # blank markup required for widget to have constant height
            self.playlist_name_label.set_has_tooltip(False)

        self.playlist_name_label.show_now()

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

    def _on_playlist_name_changed(
        self, changed_playlist: PlaylistModel, _2: GObject.ParamSpec
    ) -> None:
        selected_row = self.playlists_view.get_selected_row()
        if selected_row is None:
            return

        playlist_label = selected_row.get_child()
        playlist = playlist_label.playlist if playlist_label else None
        if playlist is None:
            return

        if changed_playlist != playlist:
            return

        self._update_playlist_name_label(changed_playlist.name)

    def _on_playlist_tracks_items_changed(
        self,
        changed_tracks: Gio.ListModel,
        position: int,
        removed: int,
        added: int,
    ) -> None:
        selected_row = self.playlists_view.get_selected_row()
        if selected_row is None:
            return

        playlist_label = selected_row.get_child()
        playlist = playlist_label.playlist if playlist_label else None
        if playlist is None:
            return

        if changed_tracks != playlist.tracks:
            return

        self._update_length_label(changed_tracks)
        self._update_track_count_label(changed_tracks)
