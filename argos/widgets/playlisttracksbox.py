import logging
from typing import Optional

from gi.repository import Gio, Gtk, GObject

from ..message import MessageType
from ..model import Model, PlaylistModel, TrackModel
from .trackbox import TrackBox

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/playlist_tracks_box.ui")
class PlaylistTracksBox(Gtk.Box):
    __gtype_name__ = "PlaylistTracksBox"

    tracks_box: Gtk.Label = Gtk.Template.Child()

    add_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.tracks_box.set_header_func(self._set_header_func)
        self.tracks_box.set_activate_on_single_click(False)

        for widget in (
            self.play_button,
            self.add_button,
            self.tracks_box,
        ):
            widget.set_sensitive(
                self._model.network_available and self._model.connected
            )
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect(
            "notify::network-available", self._handle_connection_changed
        )
        self._model.connect("notify::connected", self._handle_connection_changed)
        self._model.connect("playlist-completed", self._on_playlist_completed)

        self.show_all()

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

    def _create_track_box(
        self,
        track: TrackModel,
    ) -> Gtk.Widget:
        widget = TrackBox(self._app, track=track)
        return widget

    def _set_header_func(
        self,
        row: Gtk.ListBox,
        before: Gtk.ListBox,
    ) -> None:
        current_header = row.get_header()
        if current_header:
            return

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.show()
        row.set_header(separator)

    def update_from_playlist(self, uri: Optional[str] = None) -> None:
        LOGGER.debug(f"Updating from playlist {uri!r}")
        self.props.uri = uri if uri is not None else ""

        playlist = self._model.get_playlist(uri)
        tracks = playlist.tracks if playlist and playlist.last_modified else None
        self._update_tracks_box(tracks)
        # will be updated when playlist is completed, see
        # _on_playlist_completed()

    def _update_tracks_box(self, tracks: Optional[Gio.ListStore] = None) -> None:
        self.tracks_box.bind_model(
            tracks,
            self._create_track_box,
        )

    def _on_playlist_completed(self, model: Model, uri: str) -> None:
        LOGGER.debug(f"Playlist with URI {uri!r} completed")
        if uri != self.uri:
            LOGGER.warning(f"Not displaying playlist tracks with URI {uri!r}")
            return

        playlist = self._model.get_playlist(uri)
        tracks = playlist.tracks if playlist else None
        self._update_tracks_box(tracks)

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, _1: Gtk.Button) -> None:
        playlist = self._model.get_playlist(self.props.uri)
        tracks = playlist.tracks if playlist else None
        if tracks is None:
            return

        uris = [t.props.uri for t in tracks]
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": uris})

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _1: Gtk.Button) -> None:
        playlist = self._model.get_playlist(self.props.uri)
        tracks = playlist.tracks if playlist else None
        if tracks is None:
            return

        uris = [t.props.uri for t in tracks]
        self._app.send_message(MessageType.ADD_TO_TRACKLIST, {"uris": uris})

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
