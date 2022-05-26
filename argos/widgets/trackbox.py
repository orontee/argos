import logging

from gi.repository import GLib, GObject, Gtk

from ..model import TrackModel
from ..utils import ms_to_text

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/track_box.ui")
class TrackBox(Gtk.Box):
    __gtype_name__ = "TrackBox"

    uri = GObject.Property(type=str)

    track_name_label: Gtk.Label = Gtk.Template.Child()
    track_details_label: Gtk.Label = Gtk.Template.Child()
    track_length_label: Gtk.Label = Gtk.Template.Child()
    track_no_label: Gtk.Label = Gtk.Template.Child()
    playing_label: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        application: Gtk.Application,
        *,
        track: TrackModel,
        hide_track_no: bool = False,
    ):
        super().__init__()

        self.props.uri = track.uri

        track_name = track.name
        artist_name = track.artist_name
        album_name = track.album_name
        track_length = ms_to_text(track.length) if track.length else ""

        self.track_name_label.set_text(track_name)
        self.track_name_label.set_tooltip_markup(GLib.markup_escape_text(track_name))
        track_details = ", ".join(filter(lambda s: s, [artist_name, album_name]))
        self.track_details_label.set_text(track_details)
        self.track_details_label.set_tooltip_markup(
            GLib.markup_escape_text(track_details)
        )
        self.track_length_label.set_text(track_length)

        if hide_track_no:
            self.track_no_label.hide()
        else:
            track_no = str(track.track_no) if track.track_no != -1 else ""
            self.track_no_label.set_text(track_no)

        if application.props.disable_tooltips:
            for widget in (
                self.track_name_label,
                self.track_details_label,
            ):
                widget.props.has_tooltip = False
