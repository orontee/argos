import gettext
import logging
from typing import List, Optional

from gi.repository import Gio, GObject, Gtk

from argos.message import MessageType
from argos.model import PlaylistModel, TrackModel
from argos.utils import ms_to_text
from argos.widgets.condensedplayingbox import CondensedPlayingBox
from argos.widgets.playlistemptytracksbox import PlaylistEmptyTracksBox
from argos.widgets.playlistlabel import PlaylistLabel
from argos.widgets.playlisttrackbox import PlaylistTrackBox
from argos.widgets.streamuridialog import StreamUriDialog
from argos.widgets.utils import set_list_box_header_with_date_separator

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


def _set_list_box_header_with_virtual_playlist_separator(
    row: Gtk.ListBox,
    before: Gtk.ListBox,
) -> None:
    current_header = row.get_header()
    if current_header:
        return

    playlist_label = row.get_child()
    if not playlist_label.is_virtual or before is None:
        return

    before_label = before.get_child()
    if before_label.is_virtual:
        return

    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.show()
    row.set_header(separator)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlists_box.ui")
class PlaylistsBox(Gtk.Box):
    """Box to act on a playlist.

    The box has vertical orientation and has two children boxes: A
    pane displaying the playlist tracks; And a button box.

    """

    __gtype_name__ = "PlaylistsBox"

    playlists_view: Gtk.TreeView = Gtk.Template.Child()

    length_label: Gtk.Label = Gtk.Template.Child()
    track_count_label: Gtk.Label = Gtk.Template.Child()

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

        self.add(CondensedPlayingBox(application))

        self.set_sensitive(self._model.network_available and self._model.connected)

        PlaylistLabel.set_css_name("playlistlabel")

        self.playlists_view.bind_model(
            self._model.playlists,
            self._create_playlist_box,
        )
        self.playlists_view.set_header_func(
            _set_list_box_header_with_virtual_playlist_separator
        )

        self.tracks_box.set_header_func(set_list_box_header_with_date_separator)
        self.tracks_box.set_placeholder(self._empty_tracks_placeholder)

        edition_menu = Gio.Menu()
        edition_menu.append(_("Add stream to playlist…"), "win.add-stream-to-playlist")
        edition_menu.append(_("Remove selected tracks"), "win.remove-from-playlist")
        edition_menu.append(_("Delete playlist…"), "win.remove-playlist")
        self.edit_button.set_menu_model(edition_menu)

        for widget in (
            self.add_button,
            self.play_button,
            self.playlists_view,
            self.tracks_box,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self.show_all()

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)

    def _is_playlist_removable(self) -> bool:
        playlist = self._model.get_playlist(self.props.uri)
        return playlist is not None and not playlist.is_virtual

    def _create_track_box(
        self,
        track: TrackModel,
    ) -> Gtk.Widget:
        widget = PlaylistTrackBox(self._app, track=track)
        return widget

    def bind_model_to_playlist_tracks(self, uri: str) -> None:
        if self.props.uri == uri:
            return

        self.props.uri = uri

        playlist = self._model.get_playlist(uri)
        tracks = playlist.tracks if playlist else None
        self.tracks_box.bind_model(
            tracks,
            self._create_track_box if tracks is not None else None,
        )

        # Since playlist model missed a "loaded" property, the tracks
        # emptyness must be completed by a check to last_modified
        # value...
        self._empty_tracks_placeholder.props.loading = (
            playlist is not None and playlist.props.last_modified == -1
        )

        if playlist is not None:

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

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)

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

        if playlist is not None:
            self._app.send_message(
                MessageType.COMPLETE_PLAYLIST_DESCRIPTION,
                {"uri": playlist.uri},
            )

        tracks = playlist.tracks if playlist is not None else None
        self._update_track_count_label(tracks)
        self._update_length_label(tracks)

        uri = playlist.uri if playlist else None
        self.bind_model_to_playlist_tracks(uri)

        if playlist is not None:
            playlist.connect("notify::name", self._on_playlist_name_changed)
            playlist.tracks.connect(
                "items-changed", self._on_playlist_tracks_items_changed
            )
            # would be cleaner to disconnect on selection changes...

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

    def _get_selected_playlist(self) -> Optional[PlaylistModel]:
        selected_row = self.playlists_view.get_selected_row()
        playlist_label = selected_row.get_child() if selected_row else None
        playlist = playlist_label.playlist if playlist_label else None
        return playlist

    def _on_playlist_tracks_items_changed(
        self,
        changed_tracks: Gio.ListModel,
        position: int,
        removed: int,
        added: int,
    ) -> None:
        playlist = self._get_selected_playlist()
        if playlist is None:
            return

        if changed_tracks != playlist.tracks:
            return

        self._update_length_label(changed_tracks)
        self._update_track_count_label(changed_tracks)

    def on_remove_playlist_activated(
        self,
        _1: Gio.SimpleAction,
        _2: None,
    ) -> None:
        LOGGER.debug("Handling remove playlist request")

        playlist = self._get_selected_playlist()
        if playlist is None:
            return

        dialog = Gtk.MessageDialog(
            transient_for=self._app.window,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=_("Confirm the deletion of the {!r} playlist").format(playlist.name),
        )
        dialog.format_secondary_text(_("The deletion can't be reverted."))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            LOGGER.debug(f"Will delete playlist with URI {playlist.uri!r}")
            self._app.send_message(
                MessageType.DELETE_PLAYLIST,
                {"uri": playlist.uri},
            )
        elif response == Gtk.ResponseType.CANCEL:
            LOGGER.debug(f"Aborting deletion of playlist with URI {playlist.uri!r}")

        dialog.destroy()

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
