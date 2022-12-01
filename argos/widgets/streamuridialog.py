import gettext
import logging

from gi.repository import GObject, Gtk

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/stream_uri_dialog.ui")
class StreamUriDialog(Gtk.Dialog):
    """Dialog used to enter a stream URL."""

    __gtype_name__ = "StreamUriDialog"

    stream_uri_entry: Gtk.Entry = Gtk.Template.Child()
    play_button: Gtk.CheckButton = Gtk.Template.Child()

    stream_uri = GObject.Property(type=str, default="")
    play = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application, with_play_button: bool = False):
        super().__init__(application=application, transient_for=application.window)

        self.add_buttons(
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )

        validate_button = self.get_widget_for_response(Gtk.ResponseType.OK)
        validate_button.set_can_default(True)
        validate_button.grab_default()

        title_bar = Gtk.HeaderBar(title=_("Stream URI"), show_close_button=True)
        self.set_titlebar(title_bar)

        self.show_all()

        if not with_play_button:
            self.play_button.hide()

    @Gtk.Template.Callback()
    def on_StreamUriDialog_response(
        self,
        _1: Gtk.Dialog,
        response_id: int,
    ) -> None:
        self.props.stream_uri = self.stream_uri_entry.props.text
        self.props.play = self.play_button.props.active
