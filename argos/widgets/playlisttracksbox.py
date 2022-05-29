import logging

from gi.repository import Gtk, GObject

from ..message import MessageType
from ..model import TrackModel
from .trackbox import TrackBox
from .utils import set_list_box_header_with_separator

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/playlist_tracks_box.ui")
class PlaylistTracksBox(Gtk.Box):
    __gtype_name__ = "PlaylistTracksBox"

    tracks_box: Gtk.ListBox = Gtk.Template.Child()

    add_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.tracks_box.set_header_func(set_list_box_header_with_separator)
        self.tracks_box.set_activate_on_single_click(application.props.single_click)

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
        widget = TrackBox(self._app, track=track, hide_track_no=True)
        return widget

    def bind_model_to_playlist_tracks(self, uri: str) -> None:
        if self.props.uri == uri:
            return

        self.props.uri = uri

        playlist = self._model.get_playlist(uri)
        tracks = playlist.tracks if playlist else None
        self.tracks_box.bind_model(
            tracks,
            self._create_track_box,
        )

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
        if len(uris) > 0:
            self._app.send_message(MessageType.ADD_TO_TRACKLIST, {"uris": uris})

    @Gtk.Template.Callback()
    def on_tracks_box_row_activated(
        self,
        box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        track_box = row.get_child()
        uri = track_box.props.uri
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [uri]})
