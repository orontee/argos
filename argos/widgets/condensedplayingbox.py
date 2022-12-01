import gettext
import logging
from pathlib import Path
from typing import Optional

from gi.repository import GLib, GObject, Gtk

from argos.message import MessageType
from argos.model import PlaybackState
from argos.utils import elide_maybe
from argos.widgets.utils import default_image_pixbuf, scale_album_image
from argos.widgets.volumebutton import VolumeButton

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

TRACK_IMAGE_SIZE = 40


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/condensed_playing_box.ui")
class CondensedPlayingBox(Gtk.Box):
    __gtype_name__ = "CondensedPlayingBox"

    default_track_image = default_image_pixbuf(
        "image-x-generic-symbolic",
        target_width=TRACK_IMAGE_SIZE,
    )

    playing_track_image: Gtk.Image = Gtk.Template.Child()
    play_image: Gtk.Image = Gtk.Template.Child()
    pause_image: Gtk.Image = Gtk.Template.Child()

    track_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()

    prev_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    next_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application.props.disable_tooltips

        self.volume_button = VolumeButton(application)
        self.pack_end(self.volume_button, False, False, 0)

        self.set_sensitive(self._model.network_available and self._model.connected)

        for widget in (
            self.prev_button,
            self.play_button,
            self.next_button,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect("notify::network-available", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._update_playing_track_labels
        )
        self._model.playback.connect("notify::state", self._update_play_button)
        self._model.playback.connect(
            "notify::image-path", self._update_playing_track_image
        )

        self._update_playing_track_labels()
        self._update_playing_track_image()
        self._update_play_button()
        # This widget may be instantiated after we received the first
        # current-tl-track-tlid notification
        self.show_all()

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.network_available and self._model.connected
        self.set_sensitive(sensitive)

    def _update_playing_track_labels(
        self,
        _1: GObject.GObject = None,
        _2: GObject.GParamSpec = None,
    ) -> None:
        tlid = self._model.playback.props.current_tl_track_tlid
        tl_track = self._model.tracklist.get_tl_track(tlid) if tlid != -1 else None
        if tl_track is not None:
            self._update_track_name_label(tl_track.track.name)
            self._update_artist_name_label(tl_track.track.artist_name)
        else:
            self._update_track_name_label()
            self._update_artist_name_label()

    def _update_playing_track_image(
        self,
        _1: GObject.GObject = None,
        _2: GObject.GParamSpec = None,
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
            self.playing_track_image.set_from_pixbuf(self.default_track_image)

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

    def _update_play_button(
        self,
        _2: GObject.GObject = None,
        _1: GObject.GParamSpec = None,
    ) -> None:
        state = self._model.playback.props.state
        if state in (
            PlaybackState.UNKNOWN,
            PlaybackState.PAUSED,
            PlaybackState.STOPPED,
        ):
            self.play_button.set_image(self.play_image)
        elif state == PlaybackState.PLAYING:
            self.play_button.set_image(self.pause_image)

        self.play_button.show_now()

    @Gtk.Template.Callback()
    def on_prev_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_PREV_TRACK)

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)

    @Gtk.Template.Callback()
    def on_next_button_clicked(self, *args) -> None:
        self._app.send_message(MessageType.PLAY_NEXT_TRACK)
