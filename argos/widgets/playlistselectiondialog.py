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

    playlist_name_entry_completion: Gtk.EntryCompletion = Gtk.Template.Child()
    create_new_playlist_switch: Gtk.Switch = Gtk.Template.Child()

    playlist_name = GObject.Property(type=str, default="")
    playlist_uri = GObject.Property(type=str, default="")
    create_playlist = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application):
        super().__init__(transient_for=application.window)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self._app = application

        store = Gtk.ListStore(str, str)
        for playlist in self._app.props.model.playlists:
            if playlist.is_virtual:
                continue
            store.append([playlist.name, playlist.uri])

        self.playlist_name_entry_completion.set_model(store)
        self.playlist_name_entry_completion.set_text_column(
            PlaylistNameStoreColumn.NAME
        )

    @Gtk.Template.Callback()
    def on_playlist_name_entry_completion_match_selected(
        self,
        _1: Gtk.EntryCompletion,
        model: Gtk.TreeModel,
        iter: Gtk.TreeIter,
    ) -> None:
        self.props.playlist_name = model.get_value(iter, PlaylistNameStoreColumn.NAME)
        self.props.playlist_uri = model.get_value(iter, PlaylistNameStoreColumn.URI)
        self.create_new_playlist_switch.props.active = False

    @Gtk.Template.Callback()
    def on_create_new_playlist_switch_active_notify(
        self,
        switch: Gtk.Switch,
        _1: GObject.ParamSpec,
    ) -> None:
        self.props.create_playlist = switch.props.active
