import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from gi.repository import GdkPixbuf, GLib, Gtk

from .message import Message, MessageType
from .model import PlaybackState


LOGGER = logging.getLogger(__name__)

IMAGE_SIZE = 300
# TODO use widget size


def compute_target_size(width: int, height: int) -> Union[Tuple[int, int],
                                                          Tuple[None, None]]:
    transpose = False
    if width > height:
        width, height = height, width
        transpose = True

    if width <= 0:
        return None, None

    target_width = IMAGE_SIZE
    width_scale = target_width / width
    target_height = round(height * width_scale)
    return (target_width, target_height) if not transpose \
        else (target_height, target_width)


def ms_to_text(value: Optional[int] = None) -> str:
    if not value:
        text = "--:--"
    else:
        second_count = round(value / 1000)
        minutes = second_count // 60
        seconds = second_count % 60
        text = f"{minutes}:{seconds:02d}"
    return text


@Gtk.Template(resource_path='/app/argos/Argos/window.ui')
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ArgosWindow'

    image = Gtk.Template.Child()
    play_image = Gtk.Template.Child()
    pause_image = Gtk.Template.Child()

    track_name_label = Gtk.Template.Child()
    artist_name_label = Gtk.Template.Child()
    track_length_label = Gtk.Template.Child()

    volume_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()

    time_position_scale = Gtk.Template.Child()
    time_position_adjustement = Gtk.Template.Child()
    time_position_label = Gtk.Template.Child()

    def __init__(self, *,
                 message_queue: asyncio.Queue,
                 loop: asyncio.AbstractEventLoop,
                 application):
        Gtk.Window.__init__(self, application=application)
        self.set_title("Argos")
        self.set_wmclass("Argos", "Argos")
        self._message_queue = message_queue
        self._loop = loop

        self._volume_button_value_changed_id = self.volume_button.connect(
                "value_changed",
                self.volume_button_value_changed_cb
            )

    def update_image(self, image_path: Optional[Path]) -> None:
        if not image_path:
            self.image.clear()
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(image_path))
            if pixbuf:
                width, height = compute_target_size(pixbuf.get_width(),
                                                    pixbuf.get_height())
                scaled_pixbuf = pixbuf.scale_simple(
                    width, height, GdkPixbuf.InterpType.BILINEAR
                )
                self.image.set_from_pixbuf(scaled_pixbuf)
            else:
                LOGGER.warning("Failed to read image")
                self.image.clear()

        self.image.show_now()

    def update_labels(self, *,
                      track_name: Optional[str],
                      artist_name: Optional[str],
                      track_length: Optional[int]) -> None:
        if track_name:
            track_name = GLib.markup_escape_text(track_name)
            track_name_text = f"""<span size="xx-large"><b>{track_name}</b></span>"""
        else:
            track_name_text = ""

        self.track_name_label.set_markup(track_name_text)

        if artist_name:
            artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = f"""<span size="x-large">{artist_name}</span>"""
        else:
            artist_name_text = ""

        self.artist_name_label.set_markup(artist_name_text)

        pretty_length = ms_to_text(track_length)
        self.track_length_label.set_text(pretty_length)

        if track_length:
            self.time_position_adjustement.set_upper(track_length)
            self.time_position_scale.set_sensitive(True)
        else:
            self.time_position_adjustement.set_upper(0)
            self.time_position_scale.set_sensitive(False)

        self.update_time_position_scale(time_position=None)
        self.track_name_label.show_now()
        self.artist_name_label.show_now()
        self.track_length_label.show_now()

    def update_time_position_scale(self, *,
                                   time_position: Optional[int]) -> None:
        pretty_time_position = ms_to_text(time_position)
        self.time_position_label.set_text(pretty_time_position)

        if time_position is not None:
            self.time_position_adjustement.set_value(time_position)

        self.time_position_label.show_now()
        self.time_position_scale.show_now()

    def update_volume(self, *,
                      mute: Optional[bool],
                      volume: Optional[int]) -> None:
        if mute:
            volume = 0

        if volume is not None:
            with self.volume_button.handler_block(
                    self._volume_button_value_changed_id
            ):
                self.volume_button.set_value(volume / 100)

            self.volume_button.show_now()

    def update_play_button(self, *, state: PlaybackState) -> None:
        if state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            self.play_button.set_image(self.play_image)
        elif state == PlaybackState.PLAYING:
            self.play_button.set_image(self.pause_image)

    def volume_button_value_changed_cb(self, *args) -> None:
        value = self.volume_button.get_value()
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait,
                                        Message(MessageType.SET_VOLUME, value))

    @Gtk.Template.Callback()
    def prev_button_clicked_cb(self, *args) -> None:
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait,
                                        Message(MessageType.PLAY_PREV_TRACK))

    @Gtk.Template.Callback()
    def play_button_clicked_cb(self, *args) -> None:
        self._loop.call_soon_threadsafe(
            self._message_queue.put_nowait,
            Message(MessageType.TOGGLE_PLAYBACK_STATE)
        )

    @Gtk.Template.Callback()
    def next_button_clicked_cb(self, *args) -> None:
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait,
                                        Message(MessageType.PLAY_NEXT_TRACK))

    @Gtk.Template.Callback()
    def time_position_scale_change_value_cb(self, widget: Gtk.Widget,
                                            scroll_type: Gtk.ScrollType,
                                            value: float) -> None:
        time_position = round(value)
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait,
                                        Message(MessageType.SEEK,
                                                time_position))
