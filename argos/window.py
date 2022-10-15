import gettext
import logging

from gi.repository import Gdk, Gio, GObject, Gtk

from argos.message import MessageType
from argos.model import PlaybackState
from argos.widgets import (
    AlbumDetailsBox,
    AlbumsWindow,
    PlayingBox,
    PlaylistsBox,
    TitleBar,
)

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/window.ui")
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
        self._model = application.props.model

        self.props.titlebar = TitleBar(application)
        self.props.titlebar.central_view_switcher.set_stack(self.central_view)
        self.props.titlebar.back_button.connect(
            "clicked", self._on_title_back_button_clicked
        )
        self.props.titlebar.search_entry.connect(
            "search-changed", self._on_search_entry_changed
        )
        self.set_titlebar(self.props.titlebar)

        playing_box = PlayingBox(application)
        self.central_view.add_titled(playing_box, "playing_page", _("Playing"))

        self.props.albums_window = AlbumsWindow(application)
        self.props.albums_window.connect("album-selected", self._on_album_selected)
        self.central_view.add_titled(
            self.props.albums_window, "albums_page", _("Library")
        )
        self.props.playlists_box = PlaylistsBox(application)
        self.central_view.add_titled(
            self.props.playlists_box, "playlists_page", _("Playlists")
        )

        self.central_view.connect(
            "notify::visible-child-name", self._on_central_view_changed
        )

        self._album_details_box = AlbumDetailsBox(application)
        self.main_stack.add_named(self._album_details_box, "album_page")

        add_to_tracklist_action = Gio.SimpleAction.new("add-to-tracklist", None)
        self.add_action(add_to_tracklist_action)
        add_to_tracklist_action.connect(
            "activate", self._album_details_box.on_add_to_tracklist_activated
        )

        add_to_playlist_action = Gio.SimpleAction.new("add-to-playlist", None)
        self.add_action(add_to_playlist_action)
        add_to_playlist_action.connect(
            "activate", self._album_details_box.on_add_to_playlist_activated
        )

        playlist_tracks_box = self.props.playlists_box.props.playlist_tracks_box
        add_stream_to_playlist_action = Gio.SimpleAction.new(
            "add-stream-to-playlist", None
        )
        self.add_action(add_stream_to_playlist_action)
        add_stream_to_playlist_action.connect(
            "activate", playlist_tracks_box.on_add_stream_to_playlist_activated
        )

        remove_from_playlist_action = Gio.SimpleAction.new("remove-from-playlist", None)
        remove_from_playlist_action.set_enabled(False)
        self.add_action(remove_from_playlist_action)
        remove_from_playlist_action.connect(
            "activate", playlist_tracks_box.on_remove_from_playlist_activated
        )

        remove_playlist_action = Gio.SimpleAction.new("remove-playlist", None)
        self.add_action(remove_playlist_action)
        remove_playlist_action.connect(
            "activate", self.props.playlists_box.on_remove_playlist_activated
        )

        self.main_stack.connect(
            "notify::visible-child-name", self._on_main_stack_page_changed
        )

        self.central_view.connect(
            "notify::visible-child-name", self._on_central_view_page_changed
        )

        self._model.playback.connect(
            "notify::current-tl-track-tlid", self._on_attention_requested
        )
        self.connect("notify::is-maximized", self._handle_maximized_state_changed)

        playlist_tracks_box.tracks_box.connect(
            "selected-rows-changed", self.on_playlist_tracks_box_selected_rows_changed
        )

        self.show_all()
        self.titlebar.volume_button.hide()

        self.titlebar.props.main_page_state = True

    def is_playing_page_visible(self) -> None:
        playing_page_visible = (
            self.central_view.get_visible_child_name() == "playing_page"
        )
        return playing_page_visible

    def _on_album_selected(self, albums_window: AlbumsWindow, uri: str) -> None:
        LOGGER.debug(f"Album {uri!r} selected")
        self.props.application.send_message(
            MessageType.COMPLETE_ALBUM_DESCRIPTION, {"album_uri": uri}
        )

        self._album_details_box.set_property("uri", uri)
        self._album_details_box.show_now()
        self.main_stack.set_visible_child_name("album_page")

    def _handle_maximized_state_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.titlebar.set_show_close_button(not self.props.is_maximized)

    def _on_central_view_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        albums_page_visible = (
            self.central_view.get_visible_child_name() == "albums_page"
        )
        self.titlebar.props.search_activated = albums_page_visible

    def _on_main_stack_page_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        main_page_visible = self.main_stack.get_visible_child_name() == "main_page"
        self.titlebar.props.main_page_state = main_page_visible

        albums_page_visible = (
            self.central_view.get_visible_child_name() == "albums_page"
        )
        album_page_visible = self.main_stack.get_visible_child_name() == "album_page"
        self.titlebar.props.search_activated = (
            albums_page_visible and not album_page_visible
        )

    def _on_central_view_page_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        playing_page_visible = (
            self.central_view.get_visible_child_name() == "playing_page"
        )
        if not playing_page_visible:
            return

        child = self.central_view.get_child_by_name("playing_page")
        if child:
            self.central_view.child_set_property(child, "needs-attention", False)

    def _on_title_back_button_clicked(self, _1: Gtk.Button) -> None:
        self.main_stack.set_visible_child_name("main_page")

    def _on_search_entry_changed(self, search_entry: Gtk.SearchEntry) -> None:
        filtering_text = search_entry.props.text
        self.props.albums_window.set_filtering_text(filtering_text)

    def _on_attention_requested(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        playing_page_visible = (
            self.central_view.get_visible_child_name() == "playing_page"
        )
        if playing_page_visible:
            return

        if self._model.playback.state != PlaybackState.PLAYING:
            return

        child = self.central_view.get_child_by_name("playing_page")
        if child:
            LOGGER.debug("Requesting attention for playing page")
            self.central_view.child_set_property(child, "needs-attention", True)

    def set_central_view_visible_child(self, name: str) -> None:
        child = self.central_view.get_child_by_name(name)
        if not child:
            LOGGER.warning(f"Unexpected stack child name {name!r}")
            return

        self.central_view.set_visible_child(child)

        if self.main_stack.get_visible_child_name() != "main_page":
            self.main_stack.set_visible_child_name("main_page")

    def on_playlist_tracks_box_selected_rows_changed(self, *args) -> None:
        remove_from_playlist_action = self.lookup_action("remove-from-playlist")
        if not remove_from_playlist_action:
            return

        enabled = self._model.network_available and self._model.connected
        playlist_tracks_box = self.props.playlists_box.props.playlist_tracks_box
        selected_rows = playlist_tracks_box.tracks_box.get_selected_rows()
        remove_from_playlist_action.set_enabled(enabled and len(selected_rows) > 0)

    @Gtk.Template.Callback()
    def key_press_event_cb(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        # See /usr/include/gtk-3.0/gdk/gdkkeysyms.h for key definitions
        mod1_mask = Gdk.ModifierType.MOD1_MASK
        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        mod1_and_shift_mask = mod1_mask | shift_mask
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        keyval = event.keyval
        if modifiers in [mod1_mask, mod1_and_shift_mask]:
            if keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]:
                self.set_central_view_visible_child("playing_page")
                return True
            elif keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self.set_central_view_visible_child("albums_page")
                return True
            elif keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]:
                self.set_central_view_visible_child("playlists_page")
                return True
        elif modifiers == control_mask:
            if keyval in [Gdk.KEY_space, Gdk.KEY_KP_Space]:
                self.props.application.send_message(MessageType.TOGGLE_PLAYBACK_STATE)
                return True
            elif keyval == Gdk.KEY_n:
                self.props.application.send_message(MessageType.PLAY_NEXT_TRACK)
                return True
            elif keyval == Gdk.KEY_p:
                self.props.application.send_message(MessageType.PLAY_PREV_TRACK)
                return True
            elif keyval == Gdk.KEY_f:
                self.props.titlebar.toggle_search_entry_focus_maybe()
                return True
            elif keyval == Gdk.KEY_r:
                self.props.application.send_message(MessageType.PLAY_RANDOM_ALBUM)
                return True
        elif not modifiers:
            if keyval == Gdk.KEY_Escape:
                if self.props.titlebar.search_entry.has_focus():
                    self.props.titlebar.toggle_search_entry_focus_maybe()
                    return True
        return False
