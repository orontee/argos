import gettext
import logging
from enum import IntEnum
from pathlib import Path
from typing import List, Optional

from gi.repository import GLib, GObject, Gtk

from argos.download import ImageDownloader
from argos.model import PlaybackState
from argos.widgets.playingboxemptytracklistbox import PlayingBoxEmptyTracklistBox
from argos.widgets.tracklengthbox import TrackLengthBox
from argos.widgets.tracklistbox import TracklistBox
from argos.widgets.utils import default_image_pixbuf, scale_album_image
from argos.widgets.volumebutton import VolumeButton

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

TRACK_IMAGE_SIZE = 80


class TracklistStoreColumns(IntEnum):
    TLID = 0
    TRACK_NAME = 1
    ARTIST_NAME = 2
    ALBUM_NAME = 3
    LENGTH = 4
    TOOLTIP = 5


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/playing_box.ui")
class PlayingBox(Gtk.Box):
    __gtype_name__ = "PlayingBox"

    default_track_image = default_image_pixbuf(
        "audio-x-generic",
        max_size=TRACK_IMAGE_SIZE,
    )

    playing_track_image: Gtk.Image = Gtk.Template.Child()
    play_image: Gtk.Image = Gtk.Template.Child()
    pause_image: Gtk.Image = Gtk.Template.Child()

    left_pane_box: Gtk.Box = Gtk.Template.Child()
    track_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()

    prev_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    next_button: Gtk.Button = Gtk.Template.Child()

    tracklist_view_scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    tracklist_view_viewport: Gtk.Viewport = Gtk.Template.Child()

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
        self._download: ImageDownloader = application.props.download
        self._disable_tooltips = application.props.disable_tooltips

        track_length_box = TrackLengthBox(application)
        self.left_pane_box.pack_end(track_length_box, False, False, 0)

        volume_button = VolumeButton(application, name="playing-box-volume-button")
        track_length_box.pack_end(volume_button, False, False, 0)

        self.tracklist_view = TracklistBox(application)
        self.tracklist_view.set_placeholder(PlayingBoxEmptyTracklistBox(application))
        self.tracklist_view_viewport.add(self.tracklist_view)

        self.set_sensitive(self._model.server_reachable and self._model.connected)

        for widget in (
            self.prev_button,
            self.play_button,
            self.next_button,
            self.tracklist_view,
            self.clear_button,
            self.consume_button,
            self.random_button,
            self.repeat_button,
            self.single_button,
        ):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self._model.connect("notify::server-reachable", self.handle_connection_changed)
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
            self._update_artist_name_label(tl_track.track.artist_name)
        else:
            self._update_track_name_label()
            self._update_artist_name_label()

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
            rectangle = self.playing_track_image.get_allocation()
            max_size = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, max_size=max_size)

        if scaled_pixbuf:
            self.playing_track_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.playing_track_image.set_from_pixbuf(self.default_track_image)

        self.playing_track_image.show_now()

    def _update_track_name_label(self, track_name: Optional[str] = None) -> None:
        if track_name:
            safe_track_name = GLib.markup_escape_text(track_name)
            track_name_text = (
                f"""<span size="xx-large"><b>{safe_track_name}</b></span>"""
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
            safe_artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = f"""<span size="x-large">{safe_artist_name}</span>"""
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

        self.play_button.show_now()

    def _track_selection_to_tlids(self) -> List[int]:
        """Returns the tracklist identifiers of current track selection."""
        tlids: List[int] = []
        selected_rows = self.tracklist_view.get_selected_rows()
        for row in selected_rows:
            tl_track_box = row.get_child()
            tlid = tl_track_box.props.tlid if tl_track_box else None
            if tlid != -1:
                tlids.append(tlid)

        return tlids

    def remove_selected_tracks_from_tracklist(self) -> None:
        tlids = (
            self._track_selection_to_tlids()
            if not self.tracklist_view.get_activate_on_single_click()
            else []
        )
        self._app.activate_action("remove-from-tracklist", GLib.Variant("ai", tlids))

    @Gtk.Template.Callback()
    def on_clear_button_clicked(self, _1: Gtk.Button) -> None:
        self.remove_selected_tracks_from_tracklist()

    @Gtk.Template.Callback()
    def on_consume_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        consume = button.get_active()
        if self._model.tracklist.props.consume == consume:
            return
        self._app.activate_action("set-consume", GLib.Variant("b", button.get_active()))

    @Gtk.Template.Callback()
    def on_random_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        random = button.get_active()
        if self._model.tracklist.props.random == random:
            return
        self._app.activate_action("set-random", GLib.Variant("b", button.get_active()))

    @Gtk.Template.Callback()
    def on_repeat_button_toggled(self, button: Gtk.ToggleButton) -> None:
        repeat = button.get_active()
        if self._model.tracklist.props.repeat == repeat:
            return
        self._app.activate_action("set-repeat", GLib.Variant("b", button.get_active()))

    @Gtk.Template.Callback()
    def on_single_button_toggled(
        self,
        button: Gtk.ToggleButton,
    ) -> None:
        single = button.get_active()
        if self._model.tracklist.props.single == single:
            return
        self._app.activate_action("set-single", GLib.Variant("b", button.get_active()))
