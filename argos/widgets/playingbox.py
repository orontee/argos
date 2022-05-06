from pathlib import Path
import logging

from gi.repository import GLib, GObject, Gtk

from ..message import MessageType
from ..model import PlaybackState
from ..utils import elide_maybe, ms_to_text
from .utils import scale_album_image

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/playing_box.ui")
class PlayingBox(Gtk.Box):
    __gtype_name__ = "PlayingBox"

    playing_track_image = Gtk.Template.Child()
    play_image = Gtk.Template.Child()
    pause_image = Gtk.Template.Child()

    track_name_label = Gtk.Template.Child()
    artist_name_label = Gtk.Template.Child()
    track_length_label = Gtk.Template.Child()

    prev_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    next_button = Gtk.Template.Child()

    time_position_scale = Gtk.Template.Child()
    time_position_adjustement = Gtk.Template.Child()
    time_position_label = Gtk.Template.Child()

    needs_attention = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        for widget in (
            self.prev_button,
            self.play_button,
            self.next_button,
        ):
            widget.set_sensitive(
                self._model.network_available and self._model.connected
            )
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.connect("notify::image-path", self.update_playing_track_image)
        self._model.connect("notify::track-name", self.update_track_name_label)
        self._model.connect("notify::track-length", self.update_track_length_label)
        self._model.connect("notify::artist-name", self.update_artist_name_label)
        self._model.connect("notify::state", self.update_play_button)
        self._model.connect(
            "notify::time-position", self.update_time_position_scale_and_label
        )

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        buttons = [
            self.prev_button,
            self.play_button,
            self.next_button,
        ]
        for button in buttons:
            button.set_sensitive(sensitive)

    def update_playing_track_image(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        image_path = Path(self._model.image_path)
        scaled_pixbuf = None
        if image_path:
            rectangle = self.playing_track_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.playing_track_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.playing_track_image.set_from_resource(
                "/app/argos/Argos/icons/welcome-music.svg"
            )

        self.playing_track_image.show_now()

    def update_track_name_label(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        track_name = self._model.track_name
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

    def update_artist_name_label(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        artist_name = self._model.artist_name
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

    def update_track_length_label(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        track_length = self._model.track_length
        pretty_length = ms_to_text(track_length)
        self.track_length_label.set_text(pretty_length)

        if track_length != -1:
            self.time_position_adjustement.set_upper(track_length)
            self.time_position_scale.set_sensitive(True)
        else:
            self.time_position_adjustement.set_upper(0)
            self.time_position_scale.set_sensitive(False)

        self.track_length_label.show_now()

    def update_time_position_scale_and_label(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        time_position = self._model.time_position
        pretty_time_position = ms_to_text(time_position)
        self.time_position_label.set_text(pretty_time_position)
        self.time_position_adjustement.set_value(
            time_position if time_position != -1 else 0
        )

        self.time_position_label.show_now()
        self.time_position_scale.show_now()

    def update_play_button(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        state = self._model.state
        if state in (
            PlaybackState.UNKNOWN,
            PlaybackState.PAUSED,
            PlaybackState.STOPPED,
        ):
            self.play_button.set_image(self.play_image)
        elif state == PlaybackState.PLAYING:
            self.play_button.set_image(self.pause_image)

    @Gtk.Template.Callback()
    def prev_button_clicked_cb(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_PREV_TRACK)

    @Gtk.Template.Callback()
    def play_button_clicked_cb(self, *args) -> None:
        self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)

    @Gtk.Template.Callback()
    def next_button_clicked_cb(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_NEXT_TRACK)

    @Gtk.Template.Callback()
    def time_position_scale_change_value_cb(
        self, widget: Gtk.Widget, scroll_type: Gtk.ScrollType, value: float
    ) -> None:
        time_position = round(value)
        self._app.send_message(MessageType.SEEK, {"time_position": time_position})
