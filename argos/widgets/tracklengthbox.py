import gettext
import logging
from typing import Optional

from gi.repository import GLib, GObject, Gtk

from argos.message import MessageType
from argos.utils import ms_to_text

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/track_length_box.ui")
class TrackLengthBox(Gtk.Box):
    """Box to display time position and track length.

    The box has horizontal orientation.

    """

    __gtype_name__ = "TrackLengthBox"

    track_length_label: Gtk.Label = Gtk.Template.Child()
    time_position_label: Gtk.Label = Gtk.Template.Child()

    with_scale = GObject.Property(type=bool, default=True)

    def __init__(self, application: Gtk.Application, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._app = application
        self._model = application.model

        self._time_position_scale: Optional[Gtk.Scale] = None
        if self.props.with_scale:
            adjustment = Gtk.Adjustment(step_increment=1000, page_increment=10000)
            self._time_position_scale = Gtk.Scale(
                adjustment=adjustment,
                width_request=200,
                lower_stepper_sensitivity="on",
                upper_stepper_sensitivity="on",
                show_fill_level=True,
                restrict_to_fill_level=False,
                fill_level=0,
                draw_value=False,
            )
            self.pack_start(self._time_position_scale, True, True, 0)
            self.reorder_child(self._time_position_scale, 0)

            self._time_position_scale.connect(
                "change-value", self.on_time_position_scale_change_value
            )
            self._model.playback.connect(
                "notify::time-position", self._update_time_position_scale
            )

        self._time_position_scale_jumped_source_id: Optional[int] = None

        self.set_sensitive(self._model.network_available and self._model.connected)

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._update_playing_track_labels
        )
        self._model.playback.connect(
            "notify::time-position", self._update_time_position_label
        )

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)

    def _update_playing_track_labels(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        tlid = self._model.playback.props.current_tl_track_tlid
        tl_track = self._model.tracklist.get_tl_track(tlid) if tlid != -1 else None
        if tl_track is not None:
            self._update_track_length_label(tl_track.track.length)
        else:
            self._update_track_length_label()

    def _update_track_length_label(self, track_length: Optional[int] = None) -> None:
        pretty_length = ms_to_text(track_length if track_length is not None else -1)
        self.track_length_label.set_text(pretty_length)

        if self._time_position_scale is not None:
            adjustment = self._time_position_scale.props.adjustment
            if track_length and track_length != -1:
                adjustment.set_upper(track_length)
                self._time_position_scale.set_sensitive(True)
            else:
                adjustment.set_upper(0)
                self._time_position_scale.set_sensitive(False)

    def _update_time_position_label(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        time_position = model.props.time_position
        pretty_time_position = ms_to_text(time_position)
        self.time_position_label.set_text(pretty_time_position)

    def _update_time_position_scale(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        if self._time_position_scale is None:
            return

        if self._time_position_scale_jumped_source_id is not None:
            # User is adjusting time position, widget must not be updated
            return

        time_position = model.props.time_position
        adjustment = self._time_position_scale.props.adjustment
        adjustment.set_value(time_position if time_position != -1 else 0)

    def _on_time_position_scale_jumped(self) -> bool:
        if (
            self._time_position_scale is not None
            and self._time_position_scale_jumped_source_id is not None
        ):
            adjustment = self._time_position_scale.props.adjustment
            time_position = round(adjustment.props.value)
            self._app.send_message(MessageType.SEEK, {"time_position": time_position})
            self._time_position_scale_jumped_source_id = None
        return False  # means stop calling this callback

    def on_time_position_scale_change_value(
        self, widget: Gtk.Widget, scroll_type: Gtk.ScrollType, value: float
    ) -> bool:
        if scroll_type in (
            Gtk.ScrollType.JUMP,
            Gtk.ScrollType.STEP_BACKWARD,
            Gtk.ScrollType.STEP_FORWARD,
            Gtk.ScrollType.PAGE_BACKWARD,
            Gtk.ScrollType.PAGE_FORWARD,
        ):
            if self._time_position_scale_jumped_source_id is not None:
                GLib.source_remove(self._time_position_scale_jumped_source_id)

            self._time_position_scale_jumped_source_id = GLib.timeout_add(
                100,  # ms
                self._on_time_position_scale_jumped,
            )
            return False
        elif scroll_type in (
            Gtk.ScrollType.START,
            Gtk.ScrollType.END,
        ):
            time_position = round(value)
            self._app.send_message(MessageType.SEEK, {"time_position": time_position})
            return True

        LOGGER.warning(f"Unhandled scroll type {scroll_type!r}")
        return False
