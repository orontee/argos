import logging
from typing import List

from gi.repository import GObject, Gtk

from argos.message import MessageType
from argos.model import TrackModel
from argos.widgets.trackbox import TrackBox
from argos.widgets.utils import set_list_box_header_with_separator

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlist_tracks_box.ui")
class PlaylistTracksBox(Gtk.Box):
    """Box to act on a playlist.

    The box has vertical orientation and has two children boxes: A
    pane displaying the playlist tracks; And a button box.

    """

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
        if application.props.single_click:
            self.tracks_box.set_activate_on_single_click(True)
            self.tracks_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        else:
            self.tracks_box.set_activate_on_single_click(False)
            self.tracks_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

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

    def _track_selection_to_uris(self) -> List[str]:
        """Returns the list of URIs for current track selection.

        The returned list contains the URIs of the tracks of current
        playlist if current track selection is empty.

        """
        uris: List[str] = []
        selected_rows = self.tracks_box.get_selected_rows()
        for row in selected_rows:
            track_box = row.get_child()
            uri = track_box.props.uri if track_box else None
            if uri is not None:
                uris.append(uri)

        if len(uris) == 0:
            return self._playlist_track_uris()

        return uris

    def _playlist_track_uris(self) -> List[str]:
        """Returns the list of URIs for the tracks of current playlist."""
        uris: List[str] = []
        playlist = self._model.get_playlist(self.props.uri)
        tracks = playlist.tracks if playlist else None
        if tracks is not None:
            for t in tracks:
                uris.append(t.props.uri)
        return uris

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, _1: Gtk.Button) -> None:
        uris = (
            self._track_selection_to_uris()
            if not self.tracks_box.get_activate_on_single_click()
            else self._playlist_track_uris()
        )
        if len(uris) > 0:
            self._app.send_message(MessageType.PLAY_TRACKS, {"uris": uris})

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _1: Gtk.Button) -> None:
        uris = (
            self._track_selection_to_uris()
            if not self.tracks_box.get_activate_on_single_click()
            else self._playlist_track_uris()
        )
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
