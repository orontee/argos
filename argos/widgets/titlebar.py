import logging

from gi.repository import Gtk, GObject

from .volumebutton import VolumeButton

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/title_bar.ui")
class TitleBar(Gtk.HeaderBar):
    __gtype_name__ = "TitleBar"

    back_button: Gtk.Button = Gtk.Template.Child()
    app_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    central_view_switcher: Gtk.StackSwitcher = Gtk.Template.Child()
    search_button: Gtk.ToggleButton = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    title_stack: Gtk.Stack = Gtk.Template.Child()

    main_page_state = GObject.Property(type=bool, default=True)
    search_activated = GObject.Property(type=bool, default=False)

    filtered_model = GObject.Property(type=Gtk.TreeModelFilter, default=None)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        if application.props.disable_tooltips:
            self.back_button.props.has_tooltip = False

        builder = Gtk.Builder.new_from_resource(
            "/io/github/orontee/Argos/ui/app_menu.ui"
        )
        menu_model = builder.get_object("app-menu")
        self.app_menu_button.set_menu_model(menu_model)

        volume_button = VolumeButton(application)
        self.pack_end(volume_button)

        if not application.props.start_maximized:
            self.set_show_close_button(True)

            # On LXDE with Openbox window manager, showing close
            # button also decorate title bar with minimize, maximize
            # buttons whatever the Openbox configuration for the
            # application is...

        self.connect("notify::main-page-state", self.on_main_page_state_changed)
        self.connect("notify::search-activated", self.on_search_activated_changed)
        self.search_button_toggled_handler_id = self.search_button.connect(
            "toggled", self.on_search_button_toggled
        )

    def toggle_search_entry_focus_maybe(self) -> None:
        if not self.search_activated:
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
        self.back_button.set_visible(not self.props.main_page_state)
        self.title_stack.set_visible(self.props.main_page_state)

    def on_search_activated_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.title_stack.set_visible_child_name("switcher_page")
        self.search_button.set_active(False)
        self.search_button.set_sensitive(self.props.search_activated)
        self.search_entry.props.text = ""
