import asyncio
import gettext
import logging
import random
from functools import partial
from threading import Thread
from time import sleep
from typing import Any, Dict, List, Optional, Sequence

import gi

gi.require_version("Gdk", "3.0")  # noqa
gi.require_version("Gtk", "3.0")  # noqa

from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from argos.controllers import (
    AlbumsController,
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
        self.prefs_window = None

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

        self._controllers = (
            PlaybackController(self),
            TracklistController(self),
            AlbumsController(self),
            LibraryController(self),
            MixerController(self),
            PlaylistsController(self),
        )

        self._model.connect("notify::network-available", self._on_connection_changed)
        self._model.connect("notify::connected", self._on_connection_changed)

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

        self.props.start_fullscreen = self._settings.get_boolean("start-fullscreen")

        self._apply_style()

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

    @property
    def message_queue(self) -> asyncio.Queue:
        return self._message_queue

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def _apply_style(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/io/github/orontee/Argos/ui/stylesheet.css")
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

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

        if "maximized" in options:
            LOGGER.warning("The maximized command line option is deprecated!")

        self.activate()
        return 0

    def do_activate(self):
        if not self.window:
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
            ("show-about-dialog", self.show_about_dialog_activate_cb, None),
            ("show-preferences", self.show_preferences_activate_cb, None),
            ("new-playlist", self.new_playlist_activate_cb, None),
            ("play-random-tracks", self.play_random_tracks_activate_cb, None),
            ("add-stream", self.add_stream_activate_cb, None),
            ("update-library", self.update_library_activate_cb, None),
            ("quit", self.quit_activate_cb, ("app.quit", ["<Ctrl>Q"])),
        ]
        for action_name, callback, accel in action_descriptions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", callback)
            self.add_action(action)
            if accel is not None:
                self.set_accels_for_action(*accel)

        for action_name in [
            "new-playlist",
            "play-random-tracks",
            "add-stream",
            "update-library",
        ]:
            action = self.lookup_action(action_name)
            if not action:
                continue

            action.set_enabled(self._model.network_available and self._model.connected)

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
            "play-random-tracks",
            "add-stream",
            "update-library",
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

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)

    def show_about_dialog_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        if self.window is None:
            return

        about_dialog = AboutDialog()
        about_dialog.set_transient_for(self.window)
        about_dialog.run()
        about_dialog.destroy()

    def show_preferences_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        if self.window is None:
            return

        self.prefs_window = PreferencesWindow(self)
        self.prefs_window.set_transient_for(self.window)
        self.prefs_window.connect("destroy", self.prefs_window_destroy_cb)

        self.prefs_window.present()

    def prefs_window_destroy_cb(self, window: Gtk.Window) -> None:
        if self.prefs_window:
            self.prefs_window.destroy()

        self.prefs_window = None

    def quit_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        LOGGER.debug("Quit requested by end-user")

        self._stop_event_loop()

        if self.window is not None:
            self.window.destroy()

    def new_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        name = _("New playlist")
        LOGGER.debug(f"Creation of new playlist {name!r} requested by end-user")

        if self.window is not None:
            self.window.set_central_view_visible_child("playlists_page")

        self.send_message(MessageType.CREATE_PLAYLIST, {"name": name})

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

        self.send_message(
            MessageType.ADD_TO_TRACKLIST, {"uris": track_uris, "play": play}
        )

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

        self.send_message(
            MessageType.ADD_TO_TRACKLIST,
            {"uris": [stream_uri], "play": play},
        )

    def update_library_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        LOGGER.debug("Library update requested by end-user")

        data: Dict[str, Any] = {"force": True}
        if self.window is not None:
            directory_uri = self.window.library_window.props.directory_uri
            data["uri"] = directory_uri

        self.send_message(MessageType.BROWSE_DIRECTORY, data=data)
