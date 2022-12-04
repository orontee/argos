import logging
from typing import Optional

from gi.repository import Gio, GObject, Gtk

from argos.widgets.utils import ALBUM_SORT_CHOICES

LOGGER = logging.getLogger(__name__)


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

    main_page_state = GObject.Property(type=bool, default=True)
    search_activated = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application):
        super().__init__()

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

        if not application.props.start_maximized:
            self.set_show_close_button(True)

            # On LXDE with Openbox window manager, showing close
            # button also decorate title bar with minimize, maximize
            # buttons whatever the Openbox configuration for the
            # application is...

        self.connect("notify::main-page-state", self.on_main_page_state_changed)
        self.connect("notify::search-activated", self.on_search_activated_changed)
        self.search_button_toggled_handler_id = (
            self.search_button.connect("toggled", self.on_search_button_toggled)
            if self.search_button
            else None
        )

    def toggle_search_entry_focus_maybe(self) -> None:
        if not self.search_button or not self.search_activated:
            return

        if self.title_stack.get_visible_child_name() == "search_entry_page":
            self.title_stack.set_visible_child_name("switcher_page")
            self.search_entry.props.text = ""
            if self.search_button.get_active():
                with self.search_button.handler_block(
                    self.search_button_toggled_handler_id
                ):
                    self.search_button.set_active(False)
        else:
            self.title_stack.set_visible_child_name("search_entry_page")
            self.search_entry.grab_focus()
            if not self.search_button.get_active():
                with self.search_button.handler_block(
                    self.search_button_toggled_handler_id
                ):
                    self.search_button.set_active(True)

    def on_search_button_toggled(self, _1: Gtk.ToggleButton) -> None:
        self.toggle_search_entry_focus_maybe()

    def on_main_page_state_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        if self.props.main_page_state:
            self.back_button.set_visible(False)
            self.title_stack.set_visible(True)
            self.sort_button.set_visible(self.props.search_activated)
            if self.search_button is not None:
                self.search_button.set_visible(self.props.search_activated)
        else:
            self.back_button.set_visible(True)
            self.title_stack.set_visible(False)
            self.sort_button.set_visible(False)
            if self.search_button is not None:
                self.search_button.set_visible(False)

    def on_search_activated_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.title_stack.set_visible_child_name("switcher_page")

        self.sort_button.set_visible(self.props.search_activated)

        if not self.search_button:
            return

        self.search_button.set_active(False)
        self.search_button.set_visible(self.props.search_activated)
