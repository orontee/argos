import logging

from gi.repository import GLib, GObject, Gtk

from ..model import TracklistTrackModel
from ..utils import ms_to_text

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/tracklist_track_box.ui")
class TracklistTrackBox(Gtk.Box):
    __gtype_name__ = "TracklistTrackBox"

    tlid = GObject.Property(type=int, default=-1)

    track_name_label: Gtk.Label = Gtk.Template.Child()
    track_details_label: Gtk.Label = Gtk.Template.Child()
    track_length_label: Gtk.Label = Gtk.Template.Child()
    playing_label: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        application: Gtk.Application,
        *,
        tl_track: TracklistTrackModel,
    ):
        super().__init__()

        self.props.tlid = tl_track.tlid

        track = tl_track.track
        track_name = track.name
        artist_name = track.artist_name
        album_name = track.album_name
        track_length = ms_to_text(track.length) if track.length else ""

        self.track_name_label.set_text(track_name)
        self.track_name_label.set_tooltip_markup(GLib.markup_escape_text(track_name))
        track_details = f"{artist_name}, {album_name}" if album_name else artist_name
        self.track_details_label.set_text(track_details)
        self.track_details_label.set_tooltip_markup(
            GLib.markup_escape_text(track_details)
        )
        self.track_length_label.set_text(track_length)

        if application.props.disable_tooltips:
            for widget in (
                self.track_name_label,
                self.track_details_label,
            ):
                widget.props.has_tooltip = False
