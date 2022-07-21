from enum import IntEnum
import gettext
import logging
import re

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

    playlist_name_tree_view: Gtk.EntryCompletion = Gtk.Template.Child()

    playlist_uri = GObject.Property(type=str, default="")

    filtered_albums_store = GObject.Property(type=Gtk.TreeModelFilter)
    filtering_text = GObject.Property(type=str)

    def __init__(self, application: Gtk.Application):
        super().__init__(transient_for=application.window)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self._app = application

        store = Gtk.ListStore(str, str)
        for playlist in self._app.props.model.playlists:
            if playlist.is_virtual:
                continue
            store.append([playlist.name, playlist.uri])

        self.props.filtered_albums_store = store.filter_new()
        self.props.filtered_albums_store.set_visible_func(self._filter_album_row, None)
        self.playlist_name_tree_view.set_model(self.props.filtered_albums_store)
        self.playlist_name_tree_view.set_activate_on_single_click(True)
        self.playlist_name_tree_view.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(
            cell_renderer=renderer, text=PlaylistNameStoreColumn.NAME
        )
        self.playlist_name_tree_view.append_column(column)

    @Gtk.Template.Callback()
    def on_name_entry_search_changed(self, search_entry: Gtk.SearchEntry) -> None:
        filtering_text = search_entry.props.text
        stripped = filtering_text.strip()
        if stripped != self.props.filtering_text:
            LOGGER.debug(f"Filtering playlist names store according to {stripped!r}")

            self.props.filtering_text = stripped
            self.props.filtered_albums_store.refilter()

    def _filter_album_row(
        self,
        model: Gtk.ListStore,
        iter: Gtk.TreeIter,
        data: None,
    ) -> bool:
        if not self.props.filtering_text:
            return True

        pattern = re.escape(self.props.filtering_text)
        text = model.get_value(iter, PlaylistNameStoreColumn.NAME)
        return re.search(pattern, text, re.IGNORECASE) is not None

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
