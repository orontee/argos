import gettext
import logging
from pathlib import Path
from typing import Optional

from gi.repository import Gdk, GLib, GObject, Gtk

from argos.download import ImageDownloader
from argos.model import PlaybackState
from argos.widgets.tracklengthbox import TrackLengthBox
from argos.widgets.utils import default_image_pixbuf, scale_album_image
from argos.widgets.volumebutton import VolumeButton

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

TRACK_IMAGE_SIZE = 40


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/condensed_playing_box.ui")
class CondensedPlayingBox(Gtk.Box):
    __gtype_name__ = "CondensedPlayingBox"

    default_track_image = default_image_pixbuf(
        "audio-x-generic",
        max_size=TRACK_IMAGE_SIZE,
    )

    playing_track_image: Gtk.Image = Gtk.Template.Child()
    playing_track_image_event_box: Gtk.EventBox = Gtk.Template.Child()
    play_image: Gtk.Image = Gtk.Template.Child()
    pause_image: Gtk.Image = Gtk.Template.Child()

    track_name_label: Gtk.Label = Gtk.Template.Child()
    track_details_label: Gtk.Label = Gtk.Template.Child()

    prev_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    next_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._download: ImageDownloader = application.props.download
        self._disable_tooltips = application.props.disable_tooltips

        volume_button = VolumeButton(
            application, name="condensed-playing-box-volume-button"
        )
        self.pack_end(volume_button, False, False, 0)

        track_length_box = TrackLengthBox(application, with_scale=False)
        self.pack_end(track_length_box, False, False, 0)

        self.set_sensitive(self._model.server_reachable and self._model.connected)

        for widget in (
            self.prev_button,
            self.play_button,
            self.next_button,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self.playing_track_image_event_box.connect(
            "button-press-event", self.on_playing_track_image_pressed
        )

        self._model.connect("notify::server-reachable", self.handle_connection_changed)
        self._model.connect("notify::connected", self.handle_connection_changed)
        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._update_playing_track_labels
        )
        self._model.playback.connect("notify::state", self._update_play_button)
        self._model.playback.connect(
            "notify::image-uri", self._reset_playing_track_image
        )
        self._download.connect("image-downloaded", self._update_playing_track_image)

        self.show_all()

    def handle_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        sensitive = self._model.server_reachable and self._model.connected
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
            self._update_track_details_label(
                tl_track.track.artist_name, tl_track.track.album_name
            )
        else:
            self._update_track_name_label()
            self._update_track_details_label()

    def _reset_playing_track_image(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.playing_track_image.set_from_pixbuf(self.default_track_image)
        self.playing_track_image.show_now()

    def _update_playing_track_image(
        self,
        _1: ImageDownloader,
        image_uri: str,
    ) -> None:
        LOGGER.debug("Updating playing track image")
        match_playing_track = self._model.playback.image_uri == image_uri
        if not match_playing_track:
            return

        image_path = (
            Path(self._model.playback.image_path)
            if self._model.playback.image_path
            else None
        )
        scaled_pixbuf = None
        if image_path:
            scaled_pixbuf = scale_album_image(image_path, max_size=TRACK_IMAGE_SIZE)

        if scaled_pixbuf:
            self.playing_track_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.playing_track_image.set_from_pixbuf(self.default_track_image)

        self.playing_track_image.show_now()

    def _update_track_name_label(self, track_name: Optional[str] = None) -> None:
        if track_name:
            safe_track_name = GLib.markup_escape_text(track_name)
            track_name_text = f"""<b>{safe_track_name}</b>"""
            self.track_name_label.set_markup(track_name_text)
            if not self._disable_tooltips:
                self.track_name_label.set_has_tooltip(True)
                self.track_name_label.set_tooltip_text(track_name)
        else:
            self.track_name_label.set_markup("")
            self.track_name_label.set_has_tooltip(False)

        self.track_name_label.show_now()

    def _update_track_details_label(
        self, artist_name: Optional[str] = None, album_name: Optional[str] = None
    ) -> None:
        if artist_name:
            track_details = (
                f"{artist_name}, {album_name}" if album_name else artist_name
            )
            safe_track_details = GLib.markup_escape_text(track_details)
            self.track_details_label.set_markup(safe_track_details)
            if not self._disable_tooltips:
                self.track_details_label.set_has_tooltip(True)
                self.track_details_label.set_tooltip_markup(safe_track_details)
        else:
            self.track_details_label.set_markup("")
            self.track_details_label.set_has_tooltip(False)

        self.track_details_label.show_now()

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

    def on_playing_track_image_pressed(
        self,
        _1: Gtk.Widget,
        _2: Gdk.Event,
    ) -> bool:
        self._app.window.activate_action("goto-playing-page")
        return True
