import gettext
import logging
from typing import List

from gi.repository import Gio, GObject, Gtk

from argos.message import MessageType
from argos.model import TrackModel
from argos.widgets.playlistemptytracksbox import PlaylistEmptyTracksBox
from argos.widgets.streamuridialog import StreamUriDialog
from argos.widgets.trackbox import TrackBox
from argos.widgets.utils import set_list_box_header_with_date_separator

_ = gettext.gettext

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
    edit_button: Gtk.Button = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips
        self._empty_tracks_placeholder = PlaylistEmptyTracksBox(application)

        self.tracks_box.set_header_func(set_list_box_header_with_date_separator)
        self.tracks_box.set_placeholder(self._empty_tracks_placeholder)

        edition_menu = Gio.Menu()
        edition_menu.append(_("Add stream to playlist…"), "win.add-stream-to-playlist")
        edition_menu.append(_("Remove selected tracks"), "win.remove-from-playlist")
        edition_menu.append(_("Delete playlist…"), "win.remove-playlist")
        self.edit_button.set_menu_model(edition_menu)

        self.set_sensitive(self._model.network_available and self._model.connected)

        for widget in (
            self.play_button,
            self.add_button,
            self.tracks_box,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect(
            "notify::network-available", self._handle_connection_changed
        )
        self._model.connect("notify::connected", self._handle_connection_changed)

        self.show_all()

    def _is_playlist_removable(self) -> bool:
        playlist = self._model.get_playlist(self.props.uri)
        return playlist is not None and not playlist.is_virtual

    def _handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)
        self.edit_button.set_sensitive(self._is_playlist_removable())

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

        # Since playlist model missed a "loaded" property, the tracks
        # emptyness must be completed by a check to last_modified
        # value...
        self._empty_tracks_placeholder.props.loading = (
            playlist is not None and playlist.props.last_modified == -1
        )

        def update_placeholder_loading_prop(
            playlist: GObject.GObject, _2: GObject.GParamSpec
        ) -> None:
            if playlist.props.last_modified != -1:
                self._empty_tracks_placeholder.props.loading = False

        playlist.connect("notify::last-modified", update_placeholder_loading_prop)

        self.play_button.set_sensitive(playlist is not None)
        self.add_button.set_sensitive(playlist is not None)
        self.edit_button.set_sensitive(self._is_playlist_removable())

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
        uris = self._track_selection_to_uris()
        if len(uris) > 0:
            self._app.send_message(MessageType.PLAY_TRACKS, {"uris": uris})

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _1: Gtk.Button) -> None:
        uris = self._track_selection_to_uris()
        if len(uris) > 0:
            self._app.send_message(MessageType.ADD_TO_TRACKLIST, {"uris": uris})

    def on_add_stream_to_playlist_activated(
        self,
        _1: Gio.SimpleAction,
        _2: None,
    ) -> None:
        dialog = StreamUriDialog(self._app)
        response = dialog.run()
        stream_uri = dialog.props.stream_uri if response == Gtk.ResponseType.OK else ""
        dialog.destroy()

        if not stream_uri:
            LOGGER.debug("Aborting adding stream to playlist")
            return

        self._app.send_message(
            MessageType.SAVE_PLAYLIST,
            {
                "uri": self.props.uri,
                "add_track_uris": [stream_uri],
            },
        )

    def on_remove_from_playlist_activated(
        self,
        _1: Gio.SimpleAction,
        _2: None,
    ) -> None:
        track_uris = self._track_selection_to_uris()
        if len(track_uris) > 0:
            self._app.send_message(
                MessageType.SAVE_PLAYLIST,
                {
                    "uri": self.props.uri,
                    "remove_track_uris": track_uris,
                },
            )

    @Gtk.Template.Callback()
    def on_tracks_box_row_activated(
        self,
        box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        track_box = row.get_child()
        uri = track_box.props.uri
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [uri]})
