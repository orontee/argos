import logging

from gi.repository import GObject, Gtk

from argos.message import MessageType
from argos.model import TracklistTrackModel
from argos.widgets.tracklisttrackbox import TracklistTrackBox
from argos.widgets.utils import set_list_box_header_with_separator

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/tracklist_box.ui")
class TracklistBox(Gtk.ListBox):
    __gtype_name__ = "TracklistBox"

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.bind_model(self._model.tracklist.tracks, self._create_tracklist_track_box)
        self.set_header_func(set_list_box_header_with_separator)

        self.connect("row-activated", self._on_row_activated)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._on_current_tl_track_tlid_changed
        )

    def _create_tracklist_track_box(
        self,
        tl_track: TracklistTrackModel,
    ) -> Gtk.Widget:
        widget = TracklistTrackBox(self._app, tl_track=tl_track)
        return widget

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
            track_box.playing_image.set_visible(tlid == track_box.props.tlid)
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
        if tlid is None:
            return

        consume = self._model.tracklist.props.consume
        current_tl_track_tlid = self._model.playback.props.current_tl_track_tlid
        if consume and current_tl_track_tlid == tlid:
            return

        self._app.send_message(MessageType.PLAY, {"tlid": tlid})
