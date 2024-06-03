import asyncio
import gettext
import logging
import random
from functools import partial
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Any, Dict, List, Optional, Sequence

import xdg.BaseDirectory  # type: ignore
from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from argos.controllers import (
    AlbumsController,
    ControllerBase,
    ImagesController,
    LibraryController,
    MixerController,
    PlaybackController,
    PlaylistsController,
    TracklistController,
)
from argos.download import ImageDownloader
from argos.http import MopidyHTTPClient
from argos.info import InformationService
from argos.message import Message, MessageDispatchTask, MessageType
from argos.model import Model
from argos.notify import Notifier
from argos.placement import WindowPlacement
from argos.session import HTTPSessionManager
from argos.time import TimePositionTracker
from argos.utils import configure_logger
from argos.widgets import (
    AboutDialog,
    PlaylistCreationDialog,
    PreferencesWindow,
    StreamUriDialog,
    TracklistRandomDialog,
)
from argos.window import ArgosWindow
from argos.ws import MopidyWSConnection
from argos.wseventhandler import MopidyWSEventHandler

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class Application(Gtk.Application):

    start_fullscreen = GObject.Property(type=bool, default=False)
    disable_tooltips = GObject.Property(type=bool, default=False)
    hide_search_button = GObject.Property(type=bool, default=False)
    hide_close_button = GObject.Property(type=bool, default=False)
    version = GObject.Property(type=str)

    def __init__(self, *args, **kwargs):
        super().__init__(
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            *args,
            **kwargs,
        )
        random.seed()

        self._loop = asyncio.get_event_loop()
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._tasks: List[asyncio.Task] = []

        self._nm = Gio.NetworkMonitor.get_default()

        self._settings = Gio.Settings(self.props.application_id)

        self.window = None

        def _exception_handler(
            loop: asyncio.AbstractEventLoop,
            context: Dict[str, Any],
        ) -> None:
            LOGGER.error(
                f"""Unhandled exception in event loop: {context.get("message")}""",
                exc_info=context.get("exception"),
            )

        self._loop.set_exception_handler(_exception_handler)

        # services
        self._model = Model(self)
        self._http_session_manager = HTTPSessionManager(self)
        self._ws_event_handler = MopidyWSEventHandler(self)
        self._ws = MopidyWSConnection(self)
        self._http = MopidyHTTPClient(self)
        self._download = ImageDownloader(self)
        self._information = InformationService(self)
        self._notifier = Notifier(self)

        self._controllers = Gio.ListStore.new(ControllerBase)
        self._controllers.append(PlaybackController(self))
        self._controllers.append(TracklistController(self))
        self._controllers.append(AlbumsController(self))
        self._controllers.append(ImagesController(self))
        self._controllers.append(LibraryController(self))
        self._controllers.append(MixerController(self))
        self._controllers.append(PlaylistsController(self))

        self._model.connect("notify::network-available", self._on_connection_changed)
        self._model.connect("notify::connected", self._on_connection_changed)

        prefer_dark_theme = self._settings.get_boolean("prefer-dark-theme")
        screen_settings = Gtk.Settings.get_default()
        screen_settings.props.gtk_application_prefer_dark_theme = prefer_dark_theme
        self._settings.connect(
            "changed::prefer-dark-theme", self._on_prefer_dark_theme_changed
        )

        self.add_main_option(
            "debug",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Enable debug logs"),
            None,
        )
        self.add_main_option(
            "maximized",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "DEPRECATED",
            None,
        )
        self.add_main_option(
            "no-tooltips",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Disable tooltips"),
            None,
        )
        self.add_main_option(
            "hide-search-button",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Hide search button"),
            None,
        )
        self.add_main_option(
            "hide-close-button",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Hide close button"),
            None,
        )

        self.props.start_fullscreen = self._settings.get_boolean("start-fullscreen")

    @GObject.Property(type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    @GObject.Property(type=HTTPSessionManager, flags=GObject.ParamFlags.READABLE)
    def http_session_manager(self):
        return self._http_session_manager

    @GObject.Property(type=MopidyWSEventHandler, flags=GObject.ParamFlags.READABLE)
    def ws_event_handler(self):
        return self._ws_event_handler

    @GObject.Property(type=MopidyWSConnection, flags=GObject.ParamFlags.READABLE)
    def ws(self):
        return self._ws

    @GObject.Property(type=MopidyHTTPClient, flags=GObject.ParamFlags.READABLE)
    def http(self):
        return self._http

    @GObject.Property(type=ImageDownloader, flags=GObject.ParamFlags.READABLE)
    def download(self):
        return self._download

    @GObject.Property(type=InformationService, flags=GObject.ParamFlags.READABLE)
    def information(self):
        return self._information

    @GObject.Property(type=Model, flags=GObject.ParamFlags.READABLE)
    def model(self):
        return self._model

    @GObject.Property(type=Notifier, flags=GObject.ParamFlags.READABLE)
    def notifier(self):
        return self._notifier

    @GObject.Property(type=Gio.ListStore, flags=GObject.ParamFlags.READABLE)
    def controllers(self):
        return self._controllers

    @property
    def message_queue(self) -> asyncio.Queue:
        return self._message_queue

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def _apply_application_style(self):
        LOGGER.debug("Applying application style")
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/io/github/orontee/Argos/ui/stylesheet.css")
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _apply_user_style(self):
        config_path = Path(xdg.BaseDirectory.save_config_path("argos"))
        user_style_path = config_path / "style.css"
        LOGGER.debug(f"Looking for user style at {user_style_path.absolute()!r}")
        if not user_style_path.exists():
            LOGGER.debug("No user style to apply")
            return

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(user_style_path.absolute()))
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        LOGGER.debug("User style applied")

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if "debug" in options:
            level = logging.DEBUG
            self._loop.set_debug(True)
        else:
            level = logging.INFO

        configure_logger(level)

        self.props.disable_tooltips = "no-tooltips" in options
        self.props.hide_search_button = "hide-search-button" in options
        self.props.hide_close_button = "hide-close-button" in options

        if "maximized" in options:
            LOGGER.warning("The maximized command line option is deprecated!")

        self.activate()
        return 0

    def do_activate(self):
        if not self.window:
            self._apply_application_style()
            self._apply_user_style()

            LOGGER.debug("Instantiating application window")
            self.window = ArgosWindow(self)
            self.window.set_default_icon_name("media-optical")
            self.window.connect("delete-event", self._on_window_delete_event)

            WindowPlacement(self)

            # Run an event loop in a dedicated thread and reserve main
            # thread to Gtk processing loop
            t = Thread(
                target=self._start_event_loop,
                daemon=True,
                name="EventLoopThread",
            )
            t.start()

            self._model.props.network_available = self._nm.get_network_available()

            if self.props.start_fullscreen:
                self.window.fullscreen()

        self.window.present()
        self.show_welcome_dialog_maybe()

    def show_welcome_dialog_maybe(self) -> None:
        if self._model.connected:
            return

        user_configured_base_url = (
            self._settings.get_user_value("mopidy-base-url") is not None
        )
        if user_configured_base_url:
            return

        welcome_dialog = Gtk.MessageDialog(
            self.window,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            text=_("Welcome!"),
            secondary_text=_(
                "Start by configuring the URL of the music server. The default value expects a server running on the local host and listening to the 6680 port."
            ),
        )
        welcome_dialog.run()
        welcome_dialog.destroy()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action_descriptions = [
            ("show-about-dialog", self.show_about_dialog_activate_cb, None, None),
            ("enable-dark-theme", self.enable_dark_theme_activate_cb, "b", None),
            ("show-preferences", self.show_preferences_activate_cb, None, None),
            ("new-playlist", self.new_playlist_activate_cb, None, None),
            (
                "save-playlist",
                self.save_playlist_activate_cb,
                "(ssasas)",
                None,
            ),
            (
                "delete-playlist",
                self.delete_playlist_activate_cb,
                "s",
                None,
            ),
            ("play", self.play_activate_cb, "i", None),
            (
                "add-to-tracklist",
                self.add_to_tracklist_activate_cb,
                "as",
                None,
            ),
            (
                "remove-from-tracklist",
                self.remove_from_tracklist_activate_cb,
                "ai",
                None,
            ),
            (
                "toggle-playback-state",
                self.toggle_playback_state_activate_cb,
                None,
                None,
            ),
            ("play-tracks", self.play_tracks_activate_cb, "as", None),
            ("play-random-tracks", self.play_random_tracks_activate_cb, None, None),
            ("play-prev-track", self.play_prev_track_activate_cb, None, None),
            ("play-next-track", self.play_next_track_activate_cb, None, None),
            ("add-stream", self.add_stream_activate_cb, None, None),
            ("update-library", self.update_library_activate_cb, "s", None),
            (
                "browse-directory",
                self.browse_directory_activate_cb,
                "(sb)",
                None,
            ),
            (
                "collect-album-information",
                self.collect_album_information_activate_cb,
                "s",
                None,
            ),
            ("seek", self.seek_activate_cb, "i", None),
            ("set-volume", self.set_volume_activate_cb, "d", None),
            ("set-consume", self.set_consume_activate_cb, "b", None),
            ("set-random", self.set_random_activate_cb, "b", None),
            ("set-repeat", self.set_repeat_activate_cb, "b", None),
            ("set-single", self.set_single_activate_cb, "b", None),
            (
                "complete-album-description",
                self.complete_album_description_activate_cb,
                "s",
                None,
            ),
            (
                "complete-playlist-description",
                self.complete_playlist_description_activate_cb,
                "s",
                None,
            ),
            (
                "fetch-images",
                self.fetch_images_activate_cb,
                "as",
                None,
            ),
            (
                "close-window",
                self.window_close_cb,
                None,
                ("app.close-window", ["<Primary>W"]),
            ),
            ("quit", self.quit_activate_cb, None, ("app.quit", ["<Primary>Q"])),
        ]
        for action_name, callback, params_type_desc, accel in action_descriptions:
            params_type = (
                GLib.VariantType(params_type_desc)
                if params_type_desc is not None
                else None
            )
            action = Gio.SimpleAction.new(action_name, params_type)
            action.connect("activate", callback)
            self.add_action(action)
            if accel is not None:
                self.set_accels_for_action(*accel)

        self._update_network_actions_state()

    def _start_event_loop(self) -> None:
        LOGGER.debug("Attaching event loop to calling thread")
        asyncio.set_event_loop(self._loop)

        for coroutine in (
            self._ws.listen(),
            MessageDispatchTask(self)(),
            TimePositionTracker(self)(),
        ):
            task = self._loop.create_task(coroutine)
            self._tasks.append(task)

        LOGGER.debug("Starting event loop")
        self._loop.run_forever()

    def _stop_event_loop(self) -> None:
        LOGGER.debug("Stopping event loop")

        def cancel_tasks(tasks: Sequence[asyncio.Task]) -> None:
            for task in tasks:
                task.cancel()

        self._loop.call_soon_threadsafe(partial(cancel_tasks, self._tasks))
        self._loop.call_soon_threadsafe(self._loop.stop)
        sleep(0.5)

        # Don't try to join loop thread since it's a daemon thread, it'll result
        # in a deadlock... Yes, not that clean...

    def _update_network_actions_state(self) -> None:
        for action_name in [
            "new-playlist",
            "save-playlist",
            "play",
            "add-to-tracklist",
            "remove-from-tracklist",
            "toggle-playback-state",
            "play-tracks",
            "play-random-tracks",
            "play-prev-track",
            "play-next-track",
            "add-stream",
            "update-library",
            "collect-album-information",
            "seek",
            "set-volume",
            "set-consume",
            "set-random",
            "set-repeat",
            "set-single",
        ]:
            action = self.lookup_action(action_name)
            if not action:
                continue

            action.set_enabled(self._model.network_available and self._model.connected)

    def _on_connection_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self._update_network_actions_state()

    def _on_window_delete_event(
        self,
        _1: Gtk.Widget,
        _2: Gdk.Event,
    ) -> bool:
        self._stop_event_loop()

        # Default handler will destroy window
        return False

    def _send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)

    def show_about_dialog_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        if self.window is None:
            return

        about_dialog = AboutDialog(self)
        about_dialog.run()
        about_dialog.destroy()

    def enable_dark_theme_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        enable = parameter.unpack()
        screen_settings = Gtk.Settings.get_default()
        screen_settings.props.gtk_application_prefer_dark_theme = enable

    def show_preferences_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        if self.window is None:
            return

        prefs_window = PreferencesWindow(self)

        def on_prefs_window_delete_event(_1: Gtk.Widget, _2: Gdk.Event) -> bool:
            LOGGER.debug("Hiding preferences window")

            # Default handler will destroy window
            return False

        prefs_window.connect("delete-event", on_prefs_window_delete_event)

        LOGGER.debug("Showing preferences window")
        prefs_window.present()

    def window_close_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is None or not self.window.is_active():
            return

        LOGGER.debug("Window close requested by end-user")

        self._stop_event_loop()
        self.window.destroy()

    def quit_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        LOGGER.debug("Quit requested by end-user")

        self._stop_event_loop()

        if self.window is not None:
            self.window.destroy()

    def new_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        dialog = PlaylistCreationDialog(self)
        dialog.run()
        name = dialog.props.playlist_name
        dialog.destroy()

        if not name:
            LOGGER.debug("Abort creation of playlist")
            return

        LOGGER.debug(f"Creation of playlist {name!r} requested by end-user")

        if self.window is not None:
            self.window.set_central_view_visible_child("playlists_page")

        self._send_message(MessageType.CREATE_PLAYLIST, {"name": name})

    def save_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uri, name, add_track_uris, remove_track_uris = parameter.unpack()

        self._send_message(
            MessageType.SAVE_PLAYLIST,
            {
                "uri": uri,
                "name": name,
                "add_track_uris": add_track_uris,
                "remove_track_uris": remove_track_uris,
            },
        )

    def delete_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ):
        uri = parameter.unpack()
        self._send_message(MessageType.DELETE_PLAYLIST, {"uri": uri})

    def play_activate_cb(self, action: Gio.SimpleAction, parameter: GLib.Variant):
        tlid = parameter.unpack()
        self._send_message(MessageType.PLAY, {"tlid": tlid})

    def add_to_tracklist_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ):
        uris = parameter.unpack()
        if len(uris) > 0:
            self._send_message(MessageType.ADD_TO_TRACKLIST, {"uris": uris})

    def remove_from_tracklist_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ):
        tlids = parameter.unpack()
        if len(tlids) > 0:
            LOGGER.debug(f"Will remove tracks with identifier {tlids} from tracklist")
            self._send_message(MessageType.REMOVE_FROM_TRACKLIST, {"tlids": tlids})
        else:
            self._send_message(MessageType.CLEAR_TRACKLIST)

    def toggle_playback_state_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self._send_message(MessageType.TOGGLE_PLAYBACK_STATE)

    def play_tracks_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uris = parameter.unpack()
        if len(uris) > 0:
            self._send_message(MessageType.PLAY_TRACKS, {"uris": uris})

    def play_random_tracks_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        LOGGER.debug("Random tracks selection requested by end-user")

        play_immediately = len(self.props.model.tracklist.tracks) == 0

        dialog = TracklistRandomDialog(self, play=play_immediately)
        response = dialog.run()
        track_uris = dialog.track_uris if response == Gtk.ResponseType.OK else []
        play = dialog.props.play
        dialog.destroy()

        if not track_uris:
            LOGGER.debug("Abort selection of random tracks")
            return

        self._send_message(
            MessageType.ADD_TO_TRACKLIST, {"uris": track_uris, "play": play}
        )

    def play_prev_track_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self._send_message(MessageType.PLAY_PREV_TRACK)

    def play_next_track_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self._send_message(MessageType.PLAY_NEXT_TRACK)

    def add_stream_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        LOGGER.debug("Add stream to tracklist requested by end-user")

        dialog = StreamUriDialog(self, with_play_button=True)
        response = dialog.run()
        stream_uri = dialog.props.stream_uri if response == Gtk.ResponseType.OK else ""
        play = dialog.props.play
        dialog.destroy()

        if not stream_uri:
            LOGGER.debug("Abort adding stream")
            return

        self._send_message(
            MessageType.ADD_TO_TRACKLIST,
            {"uris": [stream_uri], "play": play},
        )

    def update_library_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        LOGGER.debug("Library update requested by end-user")

        data: Dict[str, Any] = {"force": True}
        if parameter == "":
            if self.window is not None:
                directory_uri = self.window.library_window.props.directory_uri
                data["uri"] = directory_uri
        else:
            data["uri"] = parameter.unpack()

        self._send_message(MessageType.BROWSE_DIRECTORY, data=data)

    def browse_directory_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uri, force = parameter.unpack()

        data = {"uri": uri, "force": force}
        self._send_message(MessageType.BROWSE_DIRECTORY, data=data)

    def collect_album_information_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uri = parameter.unpack()
        self._send_message(MessageType.COLLECT_ALBUM_INFORMATION, {"album_uri": uri})

    def set_volume_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        volume = parameter.unpack()
        self._send_message(MessageType.SET_VOLUME, {"volume": volume})

    def set_consume_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        consume = parameter.unpack()
        self._send_message(MessageType.SET_CONSUME, {"consume": consume})

    def set_random_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        random = parameter.unpack()
        self._send_message(MessageType.SET_RANDOM, {"random": random})

    def set_repeat_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        repeat = parameter.unpack()
        self._send_message(MessageType.SET_REPEAT, {"repeat": repeat})

    def set_single_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        single = parameter.unpack()
        self._send_message(MessageType.SET_SINGLE, {"single": single})

    def seek_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        time_position = parameter.unpack()
        self._send_message(MessageType.SEEK, {"time_position": time_position})

    def complete_album_description_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uri = parameter.unpack()
        self._send_message(MessageType.COMPLETE_ALBUM_DESCRIPTION, {"album_uri": uri})

    def complete_playlist_description_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        uri = parameter.unpack()
        self._send_message(MessageType.COMPLETE_PLAYLIST_DESCRIPTION, {"uri": uri})

    def fetch_images_activate_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        image_uris = parameter.unpack()
        self._send_message(MessageType.FETCH_IMAGES, data={"image_uris": image_uris})

    def _on_prefer_dark_theme_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        prefer_dark_theme = self._settings.get_boolean("prefer-dark-theme")
        self.activate_action("enable-dark-theme", GLib.Variant("b", prefer_dark_theme))
