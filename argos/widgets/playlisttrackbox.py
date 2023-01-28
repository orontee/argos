import logging

from gi.repository import GLib, GObject, Gtk

from argos.model import TrackModel
from argos.utils import ms_to_text

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playlist_track_box.ui")
class PlaylistTrackBox(Gtk.Box):
    """Box displaying a playlist track.

    The ``last_played`` property is meant for use by list box header
    functions."""

    __gtype_name__ = "PlaylistTrackBox"

    uri = GObject.Property(type=str)
    last_played = GObject.Property(type=GObject.TYPE_DOUBLE)

    track_name_label: Gtk.Label = Gtk.Template.Child()
    track_details_label: Gtk.Label = Gtk.Template.Child()
    track_length_label: Gtk.Label = Gtk.Template.Child()

    def __init__(
        self,
        application: Gtk.Application,
        *,
        track: TrackModel,
    ):
        super().__init__()

        self.props.uri = track.uri
        self.props.last_played = track.last_played
        # can be used by list box header functions

        track_name = track.name if track.name else track.uri
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

        if application.props.disable_tooltips:
            for widget in (
                self.track_name_label,
                self.track_details_label,
            ):
                widget.props.has_tooltip = False
