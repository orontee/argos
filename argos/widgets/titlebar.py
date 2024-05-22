import logging
from enum import IntEnum
from typing import Optional

from gi.repository import Gio, GObject, Gtk

from argos.widgets.utils import ALBUM_SORT_CHOICES

LOGGER = logging.getLogger(__name__)


class TitleBarState(IntEnum):
    FOR_PLAYING_PAGE = 0
    FOR_LIBRARY_PAGE_ON_ROOT_DIRECTORY = 1
    FOR_LIBRARY_PAGE_ON_DIRECTORY = 2
    FOR_LIBRARY_PAGE_ON_ALBUM = 3
    FOR_PLAYLISTS_PAGE = 4


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/title_bar.ui")
class TitleBar(Gtk.HeaderBar):
    __gtype_name__ = "TitleBar"

    back_button: Gtk.Button = Gtk.Template.Child()
    app_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    central_view_switcher: Gtk.StackSwitcher = Gtk.Template.Child()
    search_button: Optional[Gtk.ToggleButton] = Gtk.Template.Child()
    sort_button: Gtk.MenuButton = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    title_stack: Gtk.Stack = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application, *, window: Gtk.ApplicationWindow):
        super().__init__()

        self._window = window

        self._state: TitleBarState = TitleBarState.FOR_PLAYING_PAGE

        if application.props.disable_tooltips:
            self.back_button.props.has_tooltip = False
            self.sort_button.props.has_tooltip = False
            if self.search_button is not None:
                self.search_button.props.has_tooltip = False

        sort_menu = Gio.Menu()
        for id, name in ALBUM_SORT_CHOICES.items():
            sort_menu.append(name, f"win.sort-albums::{id}")
        self.sort_button.set_menu_model(sort_menu)

        builder = Gtk.Builder.new_from_resource(
            "/io/github/orontee/Argos/ui/app_menu.ui"
        )
        menu_model = builder.get_object("app-menu")
        self.app_menu_button.set_menu_model(menu_model)

        if self.search_button is not None:
            self.search_button.set_visible(False)

        self.sort_button.set_visible(False)
        # See on_search_activated_changed()

        if application.props.hide_search_button:
            self.remove(self.search_button)
            self.search_button = None

        self.set_decoration_layout(":close")
        self.set_show_close_button(True)
        # On LXDE with Openbox window manager, showing close
        # button also decorate title bar with minimize, maximize
        # buttons whatever the Openbox configuration for the
        # application is...

        self.search_button_toggled_handler_id = (
            self.search_button.connect("toggled", self.on_search_button_toggled)
            if self.search_button
            else None
        )
        self._window.connect("notify::is-fullscreen", self.on_is_fullscreen_changed)

    def toggle_search_entry_focus_maybe(self) -> None:
        if not self.search_button:
            return

        if self.title_stack.get_visible_child_name() == "search_entry_page":
            self._hide_search_entry()
        else:
            if self._state not in (
                TitleBarState.FOR_LIBRARY_PAGE_ON_ROOT_DIRECTORY,
                TitleBarState.FOR_LIBRARY_PAGE_ON_DIRECTORY,
            ):
                return

            self.title_stack.set_visible_child_name("search_entry_page")
            self.search_entry.grab_focus()
            if not self.search_button.get_active():
                with self.search_button.handler_block(
                    self.search_button_toggled_handler_id
                ):
                    self.search_button.set_active(True)

    def _hide_search_entry(self) -> None:
        if not self.search_button:
            return

        self.title_stack.set_visible_child_name("switcher_page")
        if self.search_button.get_active():
            with self.search_button.handler_block(
                self.search_button_toggled_handler_id
            ):
                self.search_button.set_active(False)

    def on_search_button_toggled(self, _1: Gtk.ToggleButton) -> None:
        self.toggle_search_entry_focus_maybe()

    def set_state(self, state: TitleBarState, *, force: bool = False) -> None:
        LOGGER.debug(
            f"Transitioning from {self._state.name} to {state.name} (force: {force})"
        )
        must_hide_search_entry: bool = False
        if (
            all(
                [
                    s
                    in (
                        TitleBarState.FOR_LIBRARY_PAGE_ON_ROOT_DIRECTORY,
                        TitleBarState.FOR_LIBRARY_PAGE_ON_DIRECTORY,
                    )
                    for s in (self._state, state)
                ]
            )
            and self.search_entry.props.text != ""
        ):
            LOGGER.debug("Clearing non empty search entry")
            self.search_entry.props.text = ""
            must_hide_search_entry = True

        if force or self._state != state:
            self._state = state
            if state in (
                TitleBarState.FOR_PLAYING_PAGE,
                TitleBarState.FOR_PLAYLISTS_PAGE,
            ):
                self.back_button.set_visible(False)
                self.title_stack.set_visible(True)
                self.sort_button.set_visible(False)
                if self.search_button is not None:
                    self.search_button.set_visible(False)
                must_hide_search_entry = True
            elif state in (
                TitleBarState.FOR_LIBRARY_PAGE_ON_ROOT_DIRECTORY,
                TitleBarState.FOR_LIBRARY_PAGE_ON_DIRECTORY,
            ):
                self.back_button.set_visible(True)
                self.back_button.set_sensitive(
                    state == TitleBarState.FOR_LIBRARY_PAGE_ON_DIRECTORY
                )
                self.title_stack.set_visible(True)
                self.sort_button.set_visible(True)
                if self.search_button is not None:
                    self.search_button.set_visible(True)
            elif state == TitleBarState.FOR_LIBRARY_PAGE_ON_ALBUM:
                self.back_button.set_visible(True)
                self.back_button.set_sensitive(True)
                self.title_stack.set_visible(True)
                self.sort_button.set_visible(False)
                if self.search_button is not None:
                    self.search_button.set_visible(False)
                must_hide_search_entry = True

        if must_hide_search_entry or self.search_entry.props.text == "":
            self._hide_search_entry()
        else:
            if self.search_entry.props.text != "":
                self.toggle_search_entry_focus_maybe()

    def on_is_fullscreen_changed(self, window: GObject.Object, _1: GObject.ParamSpec):
        is_fullscreen = window.props.is_fullscreen
        self.set_decoration_layout(":close" if not is_fullscreen else "")
