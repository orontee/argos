import gettext
import logging

from gi.repository import Gdk, GObject, Gtk

from .message import MessageType
from .widgets import AlbumBox, AlbumsWindow, PlayingBox, PlaylistsBox, TitleBar

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/window.ui")
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ArgosWindow"

    main_stack: Gtk.Stack = Gtk.Template.Child()
    central_view: Gtk.Stack = Gtk.Template.Child()

    albums_window = GObject.Property(type=AlbumsWindow)
    playlists_box = GObject.Property(type=PlaylistsBox)
    titlebar = GObject.Property(type=TitleBar)

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)

        self.set_wmclass("Argos", "Argos")
        self._app = application
        self._model = application.model

        self.props.titlebar = TitleBar(application)
        self.props.titlebar.central_view_switcher.set_stack(self.central_view)
        self.props.titlebar.back_button.connect(
            "clicked", self.on_title_back_button_clicked
        )
        self.props.titlebar.search_entry.connect(
            "search-changed", self.on_search_entry_changed
        )
        self.set_titlebar(self.props.titlebar)

        playing_box = PlayingBox(application)
        self.central_view.add_titled(playing_box, "playing_page", _("Playing"))

        self.props.albums_window = AlbumsWindow(application)
        self.props.albums_window.connect("album-selected", self.on_album_selected)
        self.central_view.add_titled(
            self.props.albums_window, "albums_page", _("Albums")
        )
        self.props.playlists_box = PlaylistsBox(application)
        self.central_view.add_titled(
            self.props.playlists_box, "playlists_page", _("Playlists")
        )

        self.central_view.connect(
            "notify::visible-child-name", self.on_central_view_changed
        )

        self._album_box = AlbumBox(application)
        self.main_stack.add_named(self._album_box, "album_page")

        self.main_stack.connect(
            "notify::visible-child-name", self.on_main_stack_page_changed
        )

        self._model.connect("notify::track-name", self.notify_attention_needed)
        self._model.connect("notify::artist-name", self.notify_attention_needed)
        self.connect("notify::is-maximized", self.handle_maximized_state_changed)

        self.show_all()

        self.titlebar.props.main_page_state = True

    def on_album_selected(self, albums_window: AlbumsWindow, uri: str) -> None:
        LOGGER.debug(f"Album {uri!r} selected")
        self._app.send_message(
            MessageType.COMPLETE_ALBUM_DESCRIPTION, {"album_uri": uri}
        )

        self._album_box.set_property("uri", uri)
        self._album_box.show_now()
        self.main_stack.set_visible_child_name("album_page")

    def handle_maximized_state_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.titlebar.set_show_close_button(not self.props.is_maximized)

    def on_central_view_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        albums_page_visible = (
            self.central_view.get_visible_child_name() == "albums_page"
        )
        self.titlebar.props.search_activated = albums_page_visible

    def on_main_stack_page_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        main_page_visible = self.main_stack.get_visible_child_name() == "main_page"
        self.titlebar.props.main_page_state = main_page_visible

        search_activated = (
            main_page_visible
            and self.central_view.get_visible_child_name() == "albums_page"
        )
        self.titlebar.props.search_activated = search_activated

    def on_title_back_button_clicked(self, _1: Gtk.Button) -> None:
        self.main_stack.set_visible_child_name("main_page")

    def on_search_entry_changed(self, search_entry: Gtk.SearchEntry) -> None:
        filtering_text = search_entry.props.text
        self.props.albums_window.set_filtering_text(filtering_text)

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
                if self.main_stack.get_visible_child_name() != "main_page":
                    self.main_stack.set_visible_child_name("main_page")
                return True
            elif keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self.central_view.set_visible_child_name("albums_page")
                if self.main_stack.get_visible_child_name() != "main_page":
                    self.main_stack.set_visible_child_name("main_page")
                return True
            elif keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]:
                self.central_view.set_visible_child_name("playlists_page")
                if self.main_stack.get_visible_child_name() != "main_page":
                    self.main_stack.set_visible_child_name("main_page")
                return True
        elif modifiers == control_mask:
            if keyval in [Gdk.KEY_space, Gdk.KEY_KP_Space]:
                self._app.send_message(MessageType.TOGGLE_PLAYBACK_STATE)
                return True
            elif keyval == Gdk.KEY_n:
                self._app.send_message(MessageType.PLAY_NEXT_TRACK)
                return True
            elif keyval == Gdk.KEY_p:
                self._app.send_message(MessageType.PLAY_PREV_TRACK)
                return True
            elif keyval == Gdk.KEY_f:
                self.props.titlebar.toggle_search_entry_focus_maybe()
                return True
        elif not modifiers:
            if keyval == Gdk.KEY_Escape:
                self.props.titlebar.toggle_search_entry_focus_maybe()
                return True
        return False
