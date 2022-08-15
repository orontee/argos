import gettext
import logging
from enum import IntEnum

from gi.repository import GObject, Gtk

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


class PlaylistNameStoreColumn(IntEnum):
    NAME = 0
    URI = 1


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlist_selection_dialog.ui")
class PlaylistSelectionDialog(Gtk.Dialog):
    """Dialog used to enter a playlist name."""

    __gtype_name__ = "PlaylistSelectionDialog"

    playlist_name_tree_view: Gtk.TreeView = Gtk.Template.Child()

    playlist_uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__(transient_for=application.window)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self._app = application

        store = Gtk.ListStore(str, str)
        for playlist in self._app.props.model.playlists:
            if playlist.is_virtual:
                continue
            store.append([playlist.name, playlist.uri])

        self.playlist_name_tree_view.set_model(store)
        self.playlist_name_tree_view.set_activate_on_single_click(True)
        self.playlist_name_tree_view.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(
            cell_renderer=renderer, text=PlaylistNameStoreColumn.NAME
        )
        self.playlist_name_tree_view.append_column(column)

        self.playlist_name_tree_view.set_enable_search(True)
        self.playlist_name_tree_view.set_search_column(PlaylistNameStoreColumn.NAME)

    @Gtk.Template.Callback()
    def on_playlist_name_tree_view_row_activated(
        self, _1: Gtk.TreeView, _2: Gtk.TreePath, _3: Gtk.TreeViewColumn
    ) -> None:
        self.response(Gtk.ResponseType.OK)

    @Gtk.Template.Callback()
    def on_PlaylistSelectionDialog_response(
        self,
        _1: Gtk.Dialog,
        response_id: int,
    ) -> None:
        selection = self.playlist_name_tree_view.get_selection()
        store, store_iter = selection.get_selected()
        if not store_iter or response_id != Gtk.ResponseType.OK:
            self.props.playlist_uri = ""
            return

        playlist_name = store.get_value(store_iter, PlaylistNameStoreColumn.NAME)
        self.props.playlist_uri = store.get_value(
            store_iter, PlaylistNameStoreColumn.URI
        )
        LOGGER.debug(f"Playlist name {playlist_name!r} selected")
