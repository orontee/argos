import logging
from typing import Optional

from gi.repository import GLib, GObject, Gtk

from argos.model import AlbumModel, TrackModel
from argos.utils import ms_to_text

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/track_box.ui")
class TrackBox(Gtk.Box):
    """Box displaying a track."""

    __gtype_name__ = "TrackBox"

    uri = GObject.Property(type=str)
    num_discs = GObject.Property(type=GObject.TYPE_INT64)
    track_no = GObject.Property(type=GObject.TYPE_INT64)
    disc_no = GObject.Property(type=GObject.TYPE_INT64)

    track_name_label: Gtk.Label = Gtk.Template.Child()
    track_details_label: Gtk.Label = Gtk.Template.Child()
    track_length_label: Gtk.Label = Gtk.Template.Child()
    track_no_label: Gtk.Label = Gtk.Template.Child()

    def __init__(
        self,
        application: Gtk.Application,
        *,
        track: TrackModel,
        album: Optional[AlbumModel] = None,
    ):
        super().__init__()

        self.props.uri = track.uri
        self.props.num_discs = album.num_discs if album is not None else -1
        self.props.track_no = track.track_no
        self.props.disc_no = track.disc_no

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

        track_no = str(track.track_no) if track.track_no != -1 else ""
        self.track_no_label.set_text(track_no)

        if application.props.disable_tooltips:
            for widget in (
                self.track_name_label,
                self.track_details_label,
            ):
                widget.props.has_tooltip = False
