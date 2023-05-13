import gettext
import logging

from gi.repository import GObject, Gtk

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlist_creation_dialog.ui")
class PlaylistCreationDialog(Gtk.Dialog):
    """Dialog used before playlist creation."""

    __gtype_name__ = "PlaylistCreationDialog"

    name_entry: Gtk.Entry = Gtk.Template.Child()
    name_completion: Gtk.EntryCompletion = Gtk.Template.Child()

    playlist_name = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application, transient_for=application.window)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        store = Gtk.ListStore(str)
        for playlist in self.props.application.props.model.playlists:
            if playlist.is_virtual:
                continue
            store.append([playlist.name])

        self.name_completion.set_model(store)

        title_bar = Gtk.HeaderBar(title=_("Playlist creation"), show_close_button=True)
        self.set_titlebar(title_bar)

        self.show_all()

    @Gtk.Template.Callback()
    def on_PlaylistCreationDialog_response(
        self,
        _1: Gtk.Dialog,
        response_id: int,
    ) -> None:
        playlist_name = self.name_entry.get_text()
        if not playlist_name or response_id != Gtk.ResponseType.OK:
            self.props.playlist_name = ""
            return

        self.props.playlist_name = playlist_name
        LOGGER.debug(f"Playlist name {playlist_name!r} entered")
