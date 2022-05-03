import logging
from pathlib import Path
import threading
from typing import Optional

from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from .message import MessageType
from .model import PlaybackState
from .utils import compute_target_size, elide_maybe, ms_to_text
from .widgets.topcontrolsbox import TopControlsBox

LOGGER = logging.getLogger(__name__)

ALBUM_STORE_TEXT_COLUMN = 0
ALBUM_STORE_TOOLTIP_COLUMN = 1
ALBUM_STORE_URI_COLUMN = 2
ALBUM_STORE_ICON_FILE_PATH = 3
ALBUM_STORE_PIXBUF_COLUMN = 4

ALBUM_ICON_SIZE = 100


def _default_album_icon_pixbuf() -> Pixbuf:
    pixbuf = Gtk.IconTheme.get_default().load_icon(
        "media-optical-cd-audio-symbolic", ALBUM_ICON_SIZE, 0
    )
    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=ALBUM_ICON_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


def _scale_album_icon(image_path: Path) -> Optional[Pixbuf]:
    pixbuf = None
    try:
        pixbuf = Pixbuf.new_from_file(str(image_path))
    except GLib.Error as error:
        LOGGER.warning(f"Failed to read image at {str(image_path)!r}: {error}")

    if pixbuf is None:
        return None

    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=ALBUM_ICON_SIZE,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


@Gtk.Template(resource_path="/app/argos/Argos/ui/window.ui")
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ArgosWindow"

    top_box = Gtk.Template.Child()

    central_view = Gtk.Template.Child()
    albums_view = Gtk.Template.Child()

    playing_track_image = Gtk.Template.Child()
    play_image = Gtk.Template.Child()
    pause_image = Gtk.Template.Child()

    track_name_label = Gtk.Template.Child()
    artist_name_label = Gtk.Template.Child()
    track_length_label = Gtk.Template.Child()

    volume_button = Gtk.Template.Child()
    prev_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    next_button = Gtk.Template.Child()

    time_position_scale = Gtk.Template.Child()
    time_position_adjustement = Gtk.Template.Child()
    time_position_label = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)

        self.set_wmclass("Argos", "Argos")
        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        self._volume_button_value_changed_id = self.volume_button.connect(
            "value_changed", self.volume_button_value_changed_cb
        )

        albums_store = Gtk.ListStore(str, str, str, str, Pixbuf)
        self.albums_view.set_model(albums_store)
        self.albums_view.set_text_column(ALBUM_STORE_TEXT_COLUMN)
        self.albums_view.set_tooltip_column(ALBUM_STORE_TOOLTIP_COLUMN)
        self.albums_view.set_pixbuf_column(ALBUM_STORE_PIXBUF_COLUMN)
        self.albums_view.set_item_width(ALBUM_ICON_SIZE)

        top_controls_box = TopControlsBox(application)
        self.top_box.add(top_controls_box)

        if self._disable_tooltips:
            for widget in (
                self.albums_view,
                self.volume_button,
                self.prev_button,
                self.play_button,
                self.next_button,
            ):
                widget.props.has_tooltip = False

        self._default_album_icon = _default_album_icon_pixbuf()

        self._model.connect("notify::connection", self.handle_connection_changed)
        self._model.connect("notify::image-path", self.update_playing_track_image)
        self._model.connect("notify::track-name", self.update_track_name_label)
        self._model.connect("notify::track-length", self.update_track_length_label)
        self._model.connect("notify::artist-name", self.update_artist_name_label)
        self._model.connect("notify::volume", self.update_volume)
        self._model.connect("notify::mute", self.update_volume)
        self._model.connect("notify::state", self.update_play_button)
        self._model.connect(
            "notify::time-position", self.update_time_position_scale_and_label
        )
        self._model.connect("notify::albums-loaded", self.update_album_list)

    def update_album_list(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        LOGGER.debug("Updating album list...")

        store = self.albums_view.get_model()
        store.clear()

        for album in self._model.albums:
            store.append(
                [
                    elide_maybe(album.name),
                    GLib.markup_escape_text(album.name),
                    album.uri,
                    str(album.image_path) if album.image_path else None,
                    self._default_album_icon,
                ]
            )

    def update_album_icons(self) -> None:
        thread = threading.Thread(target=self._update_album_icons)
        thread.daemon = True
        thread.start()

    def _update_album_icons(self) -> None:
        LOGGER.debug("Updating album icons...")

        store = self.albums_view.get_model()

        def update_album_icon(path: Gtk.TreePath, pixbuf: Pixbuf) -> None:
            store_iter = store.get_iter(path)
            store.set_value(store_iter, ALBUM_STORE_PIXBUF_COLUMN, pixbuf)

        store_iter = store.get_iter_first()
        while store_iter is not None:
            image_path = store.get_value(store_iter, ALBUM_STORE_ICON_FILE_PATH)
            if image_path:
                scaled_pixbuf = _scale_album_icon(image_path)
                path = store.get_path(store_iter)
                GLib.idle_add(update_album_icon, path, scaled_pixbuf)
            else:
                LOGGER.debug("No image path")
            store_iter = store.iter_next(store_iter)

    def update_playing_track_image(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        image_path = self._model.image_path
        if not image_path:
            self.playing_track_image.set_from_resource(
                "/app/argos/Argos/icons/welcome-music.svg"
            )
        else:
            try:
                pixbuf = Pixbuf.new_from_file(image_path)
            except GLib.Error as error:
                LOGGER.warning(f"Failed to read image at {image_path!r}: {error}")
                self.playing_track_image.set_from_resource(
                    "/app/argos/Argos/icons/welcome-music.svg"
                )
            else:
                rectangle = self.playing_track_image.get_allocation()
                target_width = min(rectangle.width, rectangle.height)
                width, height = compute_target_size(
                    pixbuf.get_width(), pixbuf.get_height(), target_width=target_width
                )
                scaled_pixbuf = pixbuf.scale_simple(
                    width, height, GdkPixbuf.InterpType.BILINEAR
                )
                self.playing_track_image.set_from_pixbuf(scaled_pixbuf)

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

    def update_volume(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        volume = self._model.volume
        if self._model.mute:
            volume = 0

        if volume != -1:
            with self.volume_button.handler_block(self._volume_button_value_changed_id):
                self.volume_button.set_value(volume / 100)

            self.volume_button.show_now()

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
            self.volume_button,
        ]
        for button in buttons:
            button.set_sensitive(sensitive)

    def volume_button_value_changed_cb(self, *args) -> None:
        volume = self.volume_button.get_value() * 100
        self._app.send_message(MessageType.SET_VOLUME, {"volume": volume})

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

    @Gtk.Template.Callback()
    def albums_view_item_activated_cb(
        self, icon_view: Gtk.IconView, path: Gtk.TreePath
    ) -> None:
        store = icon_view.get_model()
        store_iter = store.get_iter(path)
        uri = store.get_value(store_iter, ALBUM_STORE_URI_COLUMN)
        self._app.send_message(MessageType.PLAY_ALBUM, {"uri": uri})

    @Gtk.Template.Callback()
    def key_press_event_cb(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        # See /usr/include/gtk-3.0/gdk/gdkkeysyms.h for key definitions
        mod1_mask = Gdk.ModifierType.MOD1_MASK
        control_mask = Gdk.ModifierType.CONTROL_MASK
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        keyval = event.keyval
        if modifiers == mod1_mask:
            if keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]:
                self.central_view.set_visible_child_name("playing_page")
                return True
            elif keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self.central_view.set_visible_child_name("albums_page")
                return True
        elif modifiers == control_mask:
            if keyval in [Gdk.KEY_space, Gdk.KEY_KP_Space]:
                self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)
            elif keyval == Gdk.KEY_n:
                self._app.send_message(MessageType.PLAY_NEXT_TRACK)
            elif keyval == Gdk.KEY_p:
                self._app.send_message(MessageType.PLAY_PREV_TRACK)
        return False
