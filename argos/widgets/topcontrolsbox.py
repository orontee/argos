import logging

from gi.repository import Gtk

LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/app/argos/Argos/ui/top_controls_box.ui")
class TopControlsBox(Gtk.Box):
    __gtype_name__ = "TopControlsBox"

    play_favorite_playlist_button: Gtk.Button = Gtk.Template.Child()
    play_random_album_button: Gtk.Button = Gtk.Template.Child()
    app_menu_button: Gtk.MenuButton = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._disable_tooltips = application._disable_tooltips

        builder = Gtk.Builder.new_from_resource("/app/argos/Argos/ui/app_menu.ui")
        menu_model = builder.get_object("app-menu")
        self.app_menu_button.set_use_popover(True)
        self.app_menu_button.set_menu_model(menu_model)

        if self._disable_tooltips:
            for widget in (
                self.play_favorite_playlist_button,
                self.play_random_album_button,
            ):
                widget.props.has_tooltip = False
