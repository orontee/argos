import logging

from gi.repository import Gtk, GObject

from .volumebutton import VolumeButton

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/title_bar.ui")
class TitleBar(Gtk.HeaderBar):
    __gtype_name__ = "TitleBar"

    back_button: Gtk.Button = Gtk.Template.Child()
    app_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    central_view_switcher: Gtk.StackSwitcher = Gtk.Template.Child()

    main_stack = GObject.Property(type=Gtk.Stack)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        if application.props.disable_tooltips:
            self.back_button.props.has_tooltip = False

        builder = Gtk.Builder.new_from_resource("/app/argos/Argos/ui/app_menu.ui")
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

    @Gtk.Template.Callback()
    def on_back_button_clicked(self, _1: Gtk.Button) -> None:
        self.props.main_stack.set_visible_child_name("main_page")
