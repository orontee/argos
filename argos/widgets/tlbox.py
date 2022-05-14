import logging

from gi.repository import GObject, Gtk

from ..message import MessageType
from ..model import TracklistTrackModel
from ..utils import ms_to_text
from .tltrackbox import TracklistTrackBox

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/tracklist_box.ui")
class TracklistBox(Gtk.ListBox):
    __gtype_name__ = "TracklistBox"

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.bind_model(self._model.tracklist.tracks, self._create_tracklist_track_box)
        self.set_header_func(self._set_header_func)

        self.connect("row-activated", self._on_row_activated)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._on_current_tl_track_tlid_changed
        )

    def _create_tracklist_track_box(
        self,
        tl_track: TracklistTrackModel,
    ) -> Gtk.Widget:
        track = tl_track.track
        widget = TracklistTrackBox(
            self._app,
            tlid=tl_track.tlid,
            track_name=track.name,
            artist_name=tl_track.artist_name,
            album_name=tl_track.album_name,
            track_length=ms_to_text(track.length) if track.length else "",
        )
        return widget

    def _set_header_func(
        self,
        row: Gtk.ListBox,
        before: Gtk.ListBox,
    ) -> None:
        current_header = row.get_header()
        if current_header:
            return

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.show()
        row.set_header(separator)

    def _on_current_tl_track_tlid_changed(
        self,
        _1: GObject.Object,
        _2: GObject.ParamSpec,
    ) -> None:
        tlid = self._model.playback.current_tl_track_tlid
        row_index = 0
        row = self.get_row_at_index(row_index)
        while row:
            track_box = row.get_child()
            track_box.playing_label.set_visible(tlid == track_box.props.tlid)
            row_index += 1
            row = self.get_row_at_index(row_index)

    def _on_row_activated(
        self,
        box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        if not sensitive:
            return

        track_box = row.get_child()
        tlid = track_box.props.tlid if track_box else None
        if tlid is not None:
            self._app.send_message(MessageType.PLAY, {"tlid": tlid})
