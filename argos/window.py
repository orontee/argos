import gettext
import logging
from typing import Optional, Union

from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from argos.widgets import (
    AlbumDetailsBox,
    LibraryWindow,
    PlayingBox,
    PlaylistsBox,
    TitleBar,
    TracksView,
)
from argos.widgets.playlistselectiondialog import PlaylistSelectionDialog
from argos.widgets.titlebar import TitleBarState

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/window.ui")
class ArgosWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "ArgosWindow"

    main_box: Gtk.Box = Gtk.Template.Child()
    central_view: Gtk.Stack = Gtk.Template.Child()

    library_window = GObject.Property(type=LibraryWindow)
    playing_box = GObject.Property(type=PlayingBox)
    playlists_box = GObject.Property(type=PlaylistsBox)
    titlebar = GObject.Property(type=TitleBar)
    is_fullscreen = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)

        self.set_wmclass("Argos", "Argos")
        self._model = application.props.model
        self._settings: Gio.Settings = application.props.settings

        self.props.titlebar = TitleBar(application, window=self)
        self._setup_titlebar(self.props.titlebar)
        self.set_titlebar(self.props.titlebar)

        self.props.playing_box = PlayingBox(application)
        self.central_view.add_titled(
            self.props.playing_box, "playing_page", _("Playing")
        )

        self.props.library_window = LibraryWindow(application)
        self.central_view.add_titled(
            self.props.library_window, "library_page", _("Library")
        )
        self.props.playlists_box = PlaylistsBox(application)
        self.central_view.add_titled(
            self.props.playlists_box, "playlists_page", _("Playlists")
        )

        self.central_view.connect(
            "notify::visible-child-name", self._on_central_view_or_library_page_changed
        )

        goto_playing_page_action = Gio.SimpleAction.new("goto-playing-page", None)
        self.add_action(goto_playing_page_action)
        goto_playing_page_action.connect(
            "activate", self.on_goto_playing_page_activated
        )

        add_to_tracklist_action = Gio.SimpleAction.new(
            "add-to-tracklist", GLib.VariantType("s")
        )
        self.add_action(add_to_tracklist_action)
        add_to_tracklist_action.connect("activate", self.on_add_to_tracklist_activated)

        add_to_playlist_action = Gio.SimpleAction.new(
            "add-to-playlist", GLib.VariantType("s")
        )
        self.add_action(add_to_playlist_action)
        add_to_playlist_action.connect("activate", self.on_add_to_playlist_activated)

        play_selection_action = Gio.SimpleAction.new(
            "play-selection", GLib.VariantType("s")
        )
        self.add_action(play_selection_action)
        play_selection_action.connect("activate", self.on_play_selection_activated)

        add_stream_to_playlist_action = Gio.SimpleAction.new(
            "add-stream-to-playlist", None
        )
        self.add_action(add_stream_to_playlist_action)
        add_stream_to_playlist_action.connect(
            "activate", self.props.playlists_box.on_add_stream_to_playlist_activated
        )

        remove_from_playlist_action = Gio.SimpleAction.new("remove-from-playlist", None)
        remove_from_playlist_action.set_enabled(False)
        self.add_action(remove_from_playlist_action)
        remove_from_playlist_action.connect(
            "activate", self.props.playlists_box.on_remove_from_playlist_activated
        )

        remove_playlist_action = Gio.SimpleAction.new("remove-playlist", None)
        self.add_action(remove_playlist_action)
        remove_playlist_action.connect(
            "activate", self.props.playlists_box.on_remove_playlist_activated
        )

        album_sort_id = self._settings.get_string("album-sort")
        sort_albums_action = Gio.SimpleAction.new_stateful(
            "sort-albums",
            GLib.VariantType("s"),
            GLib.Variant("s", album_sort_id),
        )
        self.add_action(sort_albums_action)
        sort_albums_action.connect(
            "activate", self.props.library_window.on_sort_albums_activated
        )

        self.props.library_window.library_stack.connect(
            "notify::visible-child-name", self._on_central_view_or_library_page_changed
        )
        self.props.library_window.connect(
            "notify::directory-uri", self._on_central_view_or_library_page_changed
        )

        self.props.playlists_box.tracks_box.connect(
            "selected-rows-changed", self.on_playlist_tracks_box_selected_rows_changed
        )

        self.show_all()

        self.titlebar.set_state(TitleBarState.FOR_PLAYING_PAGE, force=True)
        information_service_activated = self._settings.get_boolean(
            "information-service"
        )
        album_details_box = self.props.library_window.props.album_details_box
        album_details_box.information_button.set_visible(information_service_activated)

    def _setup_titlebar(self, titlebar: TitleBar) -> None:
        titlebar.central_view_switcher.set_stack(self.central_view)
        titlebar.back_button.connect("clicked", self._on_title_back_button_clicked)
        titlebar.search_entry.connect("search-changed", self._on_search_entry_changed)

    def is_playing_page_visible(self) -> None:
        playing_page_visible = (
            self.central_view.get_visible_child_name() == "playing_page"
        )
        return playing_page_visible

    def _on_central_view_or_library_page_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self._update_titlebar_state()

    def _update_titlebar_state(self) -> None:
        central_child_name = self.central_view.get_visible_child_name()

        if central_child_name == "playing_page":
            self.titlebar.set_state(TitleBarState.FOR_PLAYING_PAGE)
        elif central_child_name == "library_page":
            if self.props.library_window.is_directory_page_visible():
                if self.props.library_window.props.directory_uri == "":
                    self.titlebar.set_state(
                        TitleBarState.FOR_LIBRARY_PAGE_ON_ROOT_DIRECTORY
                    )
                else:
                    self.titlebar.set_state(TitleBarState.FOR_LIBRARY_PAGE_ON_DIRECTORY)
            else:
                self.titlebar.set_state(TitleBarState.FOR_LIBRARY_PAGE_ON_ALBUM)
        elif central_child_name == "playlists_page":
            self.titlebar.set_state(TitleBarState.FOR_PLAYLISTS_PAGE)

    def _on_title_back_button_clicked(self, _1: Gtk.Button) -> None:
        self.props.library_window.goto_parent_state()

    def _on_search_entry_changed(self, search_entry: Gtk.SearchEntry) -> None:
        filtering_text = search_entry.props.text
        self.props.library_window.set_filtering_text(filtering_text)

    def set_central_view_visible_child(self, name: str) -> None:
        child = self.central_view.get_child_by_name(name)
        if not child:
            LOGGER.warning(f"Unexpected stack child name {name!r}")
            return

        self.central_view.set_visible_child(child)

    def on_goto_playing_page_activated(
        self,
        _1: Gio.SimpleAction,
        _2: GLib.Variant,
    ) -> None:
        self.set_central_view_visible_child("playing_page")

    def on_playlist_tracks_box_selected_rows_changed(self, *args) -> None:
        remove_from_playlist_action = self.lookup_action("remove-from-playlist")
        if not remove_from_playlist_action:
            return

        enabled = self._model.network_available and self._model.connected
        playlist_tracks_box = self.props.playlists_box.tracks_box
        selected_rows = playlist_tracks_box.get_selected_rows()
        remove_from_playlist_action.set_enabled(enabled and len(selected_rows) > 0)

    def _identify_emitter(
        self, target: str
    ) -> Optional[Union[AlbumDetailsBox, PlaylistsBox, TracksView]]:
        if target == "album-details-box":
            return self.props.library_window.props.album_details_box
        elif target == "playlists-box":
            return self.props.playlists_box
        elif target == "tracks-view":
            return self.props.library_window.props.tracks_view
        return None

    def on_add_to_playlist_activated(
        self,
        action: Gio.SimpleAction,
        target: GLib.Variant,
    ) -> None:
        emiter = self._identify_emitter(target.get_string())
        if emiter is None:
            return

        track_uris = emiter.track_selection_to_uris()
        if len(track_uris) == 0:
            LOGGER.debug("Nothing to add to playlist")
            return

        playlist_selection_dialog = PlaylistSelectionDialog(self.props.application)
        response = playlist_selection_dialog.run()
        playlist_uri = (
            playlist_selection_dialog.props.playlist_uri
            if response == Gtk.ResponseType.OK
            else ""
        )
        playlist_selection_dialog.destroy()

        if not playlist_uri:
            LOGGER.debug("Aborting adding tracks to playlist")
            return

        self.props.application.activate_action(
            "save-playlist",
            GLib.Variant(
                "(ssasas)",
                (
                    playlist_uri,
                    "",
                    track_uris,
                    [],
                ),
            ),
        )

    def on_add_to_tracklist_activated(
        self,
        action: Gio.SimpleAction,
        target: GLib.Variant,
    ) -> None:
        emiter = self._identify_emitter(target.get_string())
        if emiter is None:
            return

        track_uris = emiter.track_selection_to_uris()
        if len(track_uris) > 0:
            self.props.application.activate_action(
                "add-to-tracklist", GLib.Variant("as", track_uris)
            )

    def on_play_selection_activated(
        self,
        action: Gio.SimpleAction,
        target: GLib.Variant,
    ) -> None:
        emiter = self._identify_emitter(target.get_string())
        if emiter is None:
            return

        track_uris = emiter.track_selection_to_uris()
        if len(track_uris) > 0:
            self.props.application.activate_action(
                "play-tracks", GLib.Variant("as", track_uris)
            )

    @Gtk.Template.Callback()
    def on_window_state_event(
        self,
        widget: Gtk.Widget,
        event: Gdk.EventWindowState,
    ) -> bool:
        if event.changed_mask != Gdk.WindowState.FULLSCREEN:
            return False

        is_fullscreen = event.new_window_state & Gdk.WindowState.FULLSCREEN

        if is_fullscreen:
            if not self.props.titlebar.is_visible():
                LOGGER.error("Titlebar is not visible anymore!!")
                self.unfullscreen()
                return True

        self.props.is_fullscreen = is_fullscreen

        return True

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
                self.set_central_view_visible_child("library_page")
                return True
            elif keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]:
                self.set_central_view_visible_child("playlists_page")
                return True
            elif keyval in [Gdk.KEY_Up, Gdk.KEY_KP_Up]:
                if self.central_view.get_visible_child_name() == "library_page":
                    self.props.library_window.goto_parent_state()
                return True
        elif modifiers == control_mask:
            if keyval in [Gdk.KEY_space, Gdk.KEY_KP_Space]:
                self.props.application.activate_action("toggle-playback-state")
                return True
            elif keyval == Gdk.KEY_n:
                self.props.application.activate_action("play-next-track")
                return True
            elif keyval == Gdk.KEY_p:
                self.props.application.activate_action("play-prev-track")
                return True
            elif keyval == Gdk.KEY_f:
                self.props.titlebar.toggle_search_entry_focus_maybe()
                return True
            elif keyval == Gdk.KEY_r:
                self.props.application.activate_action("play-random-tracks")
                return True
        elif not modifiers:
            if keyval == Gdk.KEY_Escape:
                if self.props.titlebar.search_entry.has_focus():
                    self.props.titlebar.toggle_search_entry_focus_maybe()
                    return True
            elif keyval == Gdk.KEY_F11:
                if self.props.is_fullscreen:
                    self.unfullscreen()
                else:
                    self.fullscreen()
                return True
            elif keyval in [Gdk.KEY_Delete, Gdk.KEY_KP_Delete]:
                visible_page_name = self.central_view.get_visible_child_name()
                if visible_page_name == "playing_page":
                    self.props.playing_box.remove_selected_tracks_from_tracklist()
                    return True
                elif visible_page_name == "playlists_page":
                    self.props.playlists_box.remove_selected_tracks_from_playlist()
                    return True
        return False
