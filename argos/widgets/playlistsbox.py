from enum import IntEnum
import gettext
import logging
from typing import Optional

from gi.repository import Gio, GLib, GObject, Gtk, Pango

from ..message import MessageType
from ..model import Model
from ..utils import elide_maybe, ms_to_text
from .playlisttracksbox import PlaylistTracksBox

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


class PlaylistsStoreColumns(IntEnum):
    TEXT = 0
    TOOLTIP = 1
    URI = 2


@Gtk.Template(resource_path="/app/argos/Argos/ui/playlists_box.ui")
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

        albums_store = Gtk.ListStore(str, str, str)
        self.playlists_view.set_model(albums_store)
        self.playlists_view.set_tooltip_column(PlaylistsStoreColumns.TOOLTIP)

        for widget in (
            self.playlists_view,
            self.playlist_name_label,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        renderer = Gtk.CellRendererText(
            xpad=5,
            ypad=5,
            ellipsize=Pango.EllipsizeMode.END,
        )
        column = Gtk.TreeViewColumn(_("Playlist"), renderer, text=0)
        self.playlists_view.append_column(column)

        self.props.playlist_tracks_box = PlaylistTracksBox(application)
        self.add(self.props.playlist_tracks_box)

        self.show_all()

        selection = self.playlists_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self._on_playlists_view_selection_changed)

        self._model.connect("notify::playlists-loaded", self._update_playlist_list)
        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.connect("playlist-completed", self._on_playlist_completed)

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.playlists_view.set_sensitive(sensitive)

    def _update_playlist_list(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        LOGGER.debug("Updating playlist store")

        store = self.playlists_view.get_model()
        store.clear()

        playlists = self._model.playlists
        for playlist in playlists:
            store.append(
                [
                    playlist.name,
                    playlist.name,
                    playlist.uri,
                ]
            )

    def _on_playlists_view_selection_changed(
        self,
        selection: Gtk.TreeSelection,
    ) -> None:
        store, store_iter = selection.get_selected()
        if store_iter is not None:
            uri = store.get_value(store_iter, PlaylistsStoreColumns.URI)
            LOGGER.debug(f"Playlist with URI {uri!r} selected")
        else:
            uri = None

        self._update_from_playlist(uri)
        self.props.playlist_tracks_box.update_from_playlist(uri)

        sensitive = self._model.network_available and self._model.connected
        if uri and sensitive:
            self._app.send_message(
                MessageType.COMPLETE_PLAYLIST_DESCRIPTION, {"playlist_uri": uri}
            )

    def _update_from_playlist(self, uri: Optional[str] = None) -> None:
        LOGGER.debug(f"Updating from playlist {uri!r}")
        playlist = self._model.get_playlist(uri) if uri is not None else None
        playlist_name = playlist.props.name if playlist is not None else None
        self._update_playlist_name_label(playlist_name)

        if playlist is not None and playlist.props.last_modified:
            tracks = playlist.tracks
        else:
            tracks = None
        self._update_track_count_label(tracks)
        self._update_length_label(tracks)
        # those widgets will be updated when playlist is completed,
        # see _on_playlist_completed()

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

    def _on_playlist_completed(self, model: Model, uri: str) -> None:
        LOGGER.debug(f"Playlist with URI {uri!r} completed")

        selection = self.playlists_view.get_selection()
        store, store_iter = selection.get_selected()
        if store_iter is None:
            return

        selected_playlist_uri = store.get_value(store_iter, PlaylistsStoreColumns.URI)

        if uri != selected_playlist_uri:
            LOGGER.warning(f"Not displaying playlist with URI {uri!r}")
            return

        playlist = self._model.get_playlist(uri)
        tracks = playlist.tracks if playlist else None
        self._update_track_count_label(tracks)
        self._update_length_label(tracks)
