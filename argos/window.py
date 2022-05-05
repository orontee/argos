import gettext
import logging

from gi.repository import Gdk, GObject, Gtk

from .message import MessageType
from .widgets import AlbumsWindow, PlayingBox, TopControlsBox, VolumeButton

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/window.ui")
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ArgosWindow"

    top_box = Gtk.Template.Child()

    central_view = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)

        self.set_wmclass("Argos", "Argos")
        self._app = application
        self._model = application.model

        volume_button = VolumeButton(application)
        self.top_box.add(volume_button)

        top_controls_box = TopControlsBox(application)
        self.top_box.add(top_controls_box)

        playing_box = PlayingBox(application)
        self.central_view.add_titled(playing_box, "playing_page", _("Playing"))

        albums_window = AlbumsWindow(application)
        self.central_view.add_titled(albums_window, "albums_page", _("Albums"))

        self._model.connect("notify::track-name", self.notify_attention_needed)
        self._model.connect("notify::artist-name", self.notify_attention_needed)

    def notify_attention_needed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        child = self.central_view.get_child_by_name("playing_page")
        if child:
            LOGGER.debug("Requesting attention for playing page")
            child.set_property("needs-attention", True)

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
