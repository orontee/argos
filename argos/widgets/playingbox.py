from enum import IntEnum
import gettext
import logging
from pathlib import Path
from typing import Optional

from gi.repository import GLib, GObject, Gtk

from ..message import MessageType
from ..model import PlaybackState
from ..utils import elide_maybe, ms_to_text
from .tlbox import TracklistBox
from .utils import scale_album_image

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


class TracklistStoreColumns(IntEnum):
    TLID = 0
    TRACK_NAME = 1
    ARTIST_NAME = 2
    ALBUM_NAME = 3
    LENGTH = 4
    TOOLTIP = 5


@Gtk.Template(resource_path="/app/argos/Argos/ui/playing_box.ui")
class PlayingBox(Gtk.Box):
    __gtype_name__ = "PlayingBox"

    playing_track_image: Gtk.Image = Gtk.Template.Child()
    play_image: Gtk.Image = Gtk.Template.Child()
    pause_image: Gtk.Image = Gtk.Template.Child()

    track_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()
    track_length_label: Gtk.Label = Gtk.Template.Child()

    prev_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    next_button: Gtk.Button = Gtk.Template.Child()

    time_position_scale: Gtk.Scale = Gtk.Template.Child()
    time_position_adjustement: Gtk.Adjustment = Gtk.Template.Child()
    time_position_label: Gtk.Label = Gtk.Template.Child()

    tracklist_view_scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()

    clear_button: Gtk.Button = Gtk.Template.Child()
    consume_button: Gtk.ToggleButton = Gtk.Template.Child()
    random_button: Gtk.ToggleButton = Gtk.Template.Child()
    repeat_button: Gtk.ToggleButton = Gtk.Template.Child()
    single_button: Gtk.ToggleButton = Gtk.Template.Child()

    needs_attention = GObject.Property(type=bool, default=False)

    tracklist_view: TracklistBox

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.tracklist_view = TracklistBox(application)
        self.tracklist_view.set_activate_on_single_click(application.props.single_click)
        self.tracklist_view_scrolled_window.add(self.tracklist_view)

        for widget in (
            self.prev_button,
            self.play_button,
            self.next_button,
            self.tracklist_view,
        ):
            widget.set_sensitive(
                self._model.network_available and self._model.connected
            )
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.tracklist.connect("notify::consume", self.handle_consume_changed)
        self._model.tracklist.connect("notify::random", self.handle_random_changed)
        self._model.tracklist.connect("notify::repeat", self.handle_repeat_changed)
        self._model.tracklist.connect("notify::single", self.handle_single_changed)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._update_playing_track_labels
        )
        self._model.playback.connect("notify::state", self._update_play_button)
        self._model.playback.connect(
            "notify::time-position", self._update_time_position_scale_and_label
        )
        self._model.playback.connect(
            "notify::image-path", self._update_playing_track_image
        )

        self.show_all()

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        widgets = (
            self.prev_button,
            self.play_button,
            self.next_button,
            self.tracklist_view,
            self.clear_button,
            self.consume_button,
            self.random_button,
            self.repeat_button,
            self.single_button,
        )
        for widget in widgets:
            widget.set_sensitive(sensitive)

    def handle_consume_changed(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        if model.props.consume != self.consume_button.get_active():
            self.consume_button.set_active(model.props.consume)

    def handle_random_changed(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        if model.props.random != self.random_button.get_active():
            self.random_button.set_active(model.props.random)

    def handle_repeat_changed(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        if model.props.repeat != self.repeat_button.get_active():
            self.repeat_button.set_active(model.props.repeat)

    def handle_single_changed(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        if model.props.single != self.single_button.get_active():
            self.single_button.set_active(model.props.single)

    def _update_playing_track_labels(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        tlid = self._model.playback.props.current_tl_track_tlid
        tl_track = self._model.tracklist.get_tl_track(tlid) if tlid != -1 else None
        if tl_track is not None:
            self._update_track_name_label(tl_track.track.name)
            self._update_track_length_label(tl_track.track.length)
            self._update_artist_name_label(tl_track.track.artist_name)
        else:
            self._update_track_name_label()
            self._update_track_length_label()
            self._update_artist_name_label()

    def _update_playing_track_image(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        image_path = (
            Path(self._model.playback.image_path)
            if self._model.playback.image_path
            else None
        )
        scaled_pixbuf = None
        if image_path:
            rectangle = self.playing_track_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.playing_track_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.playing_track_image.set_from_icon_name(
                "image-x-generic-symbolic",
                Gtk.IconSize.DIALOG,
            )

        self.playing_track_image.show_now()

    def _update_track_name_label(self, track_name: Optional[str] = None) -> None:
        if track_name:
            short_track_name = GLib.markup_escape_text(elide_maybe(track_name))
            track_name_text = (
                f"""<span size="xx-large"><b>{short_track_name}</b></span>"""
            )
            self.track_name_label.set_markup(track_name_text)
            if not self._disable_tooltips:
                self.track_name_label.set_has_tooltip(True)
                self.track_name_label.set_tooltip_text(track_name)
        else:
            self.track_name_label.set_markup("")
            self.track_name_label.set_has_tooltip(False)

        self.track_name_label.show_now()

    def _update_artist_name_label(self, artist_name: Optional[str] = None) -> None:
        if artist_name:
            short_artist_name = GLib.markup_escape_text(elide_maybe(artist_name))
            artist_name_text = f"""<span size="x-large">{short_artist_name}</span>"""
            self.artist_name_label.set_markup(artist_name_text)
            if not self._disable_tooltips:
                self.artist_name_label.set_has_tooltip(True)
                self.artist_name_label.set_tooltip_text(artist_name)
        else:
            self.artist_name_label.set_markup("")
            self.artist_name_label.set_has_tooltip(False)

        self.artist_name_label.show_now()

    def _update_track_length_label(self, track_length: Optional[int] = None) -> None:
        pretty_length = ms_to_text(track_length if track_length is not None else -1)
        self.track_length_label.set_text(pretty_length)

        if track_length and track_length != -1:
            self.time_position_adjustement.set_upper(track_length)
            self.time_position_scale.set_sensitive(True)
        else:
            self.time_position_adjustement.set_upper(0)
            self.time_position_scale.set_sensitive(False)

        self.track_length_label.show_now()

    def _update_time_position_scale_and_label(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        time_position = model.props.time_position
        pretty_time_position = ms_to_text(time_position)
        self.time_position_label.set_text(pretty_time_position)
        self.time_position_adjustement.set_value(
            time_position if time_position != -1 else 0
        )

        self.time_position_label.show_now()
        self.time_position_scale.show_now()

    def _update_play_button(
        self,
        model: GObject.GObject,
        _1: GObject.GParamSpec,
    ) -> None:
        state = model.props.state
        if state in (
            PlaybackState.UNKNOWN,
            PlaybackState.PAUSED,
            PlaybackState.STOPPED,
        ):
            self.play_button.set_image(self.play_image)
        elif state == PlaybackState.PLAYING:
            self.play_button.set_image(self.pause_image)

    @Gtk.Template.Callback()
    def on_clear_button_clicked(self, _1: Gtk.Button) -> None:
        self._app.send_message(MessageType.CLEAR_TRACKLIST)

    @Gtk.Template.Callback()
    def on_prev_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_PREV_TRACK)

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)

    @Gtk.Template.Callback()
    def on_next_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_NEXT_TRACK)

    @Gtk.Template.Callback()
    def on_time_position_scale_change_value(
        self, widget: Gtk.Widget, scroll_type: Gtk.ScrollType, value: float
    ) -> None:
        time_position = round(value)
        self._app.send_message(MessageType.SEEK, {"time_position": time_position})

    @Gtk.Template.Callback()
    def on_consume_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        self._app.send_message(
            MessageType.SET_CONSUME, {"consume": button.get_active()}
        )

    @Gtk.Template.Callback()
    def on_random_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        self._app.send_message(MessageType.SET_RANDOM, {"random": button.get_active()})

    @Gtk.Template.Callback()
    def on_repeat_button_toggled(self, button: Gtk.ToggleButton) -> None:
        self._app.send_message(MessageType.SET_REPEAT, {"repeat": button.get_active()})

    @Gtk.Template.Callback()
    def on_single_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        self._app.send_message(MessageType.SET_SINGLE, {"single": button.get_active()})
