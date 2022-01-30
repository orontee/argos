import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk

from .message import Message, MessageType
from .model import PlaybackState


LOGGER = logging.getLogger(__name__)

IMAGE_SIZE = 300
# TODO use widget size

MENU_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app_menu">
    <section>
        <item>
            <attribute name="label">Play random album</attribute>
            <attribute name="action">app.play_random_album</attribute>
            <attribute name="icon">media-playlist-shuffle-symbolic</attribute>
        </item>
        <item>
            <attribute name="label">Play favorite playlist</attribute>
            <attribute name="action">app.play_favorite_playlist</attribute>
            <attribute name="icon">starred-symbolic</attribute>
        </item>
    </section>
  </menu>
</interface>
"""

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


@Gtk.Template(filename='window.ui')
class Window(Gtk.ApplicationWindow):
    __gtype_name__ = 'ArgosUIWindow'

    image = Gtk.Template.Child()
    play_image = Gtk.Template.Child()
    pause_image = Gtk.Template.Child()

    track_name_label = Gtk.Template.Child()
    artist_name_label = Gtk.Template.Child()

    volume_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()

    def __init__(self, *,
                 message_queue: asyncio.Queue,
                 loop: asyncio.AbstractEventLoop,
                 application):
        Gtk.Window.__init__(self, application=application)
        self.set_title("Argos")
        self.set_wmclass("Argos", "Argos")
        self._message_queue = message_queue
        self._loop = loop

        builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        menu = builder.get_object("app_menu")

        self.menu_button.set_menu_model(menu)

        self._volume_button_value_changed_id = \
            self.volume_button.connect("value_changed",
                                       self.volume_button_value_changed_cb)

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
                      artist_name: Optional[str]) -> None:
        if track_name:
            track_name = GLib.markup_escape_text(track_name)
            track_name_text = f"""<span size="xx-large"><b>{track_name}</b></span>"""
        else:
            track_name_text = ""

        self.track_name_label.set_markup(track_name_text)
        self.track_name_label.show_now()

        if artist_name:
            artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = f"""<span size="x-large">{artist_name}</span>"""
        else:
            artist_name_text = ""

        self.artist_name_label.set_markup(artist_name_text)
        self.artist_name_label.show_now()

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
