import asyncio
import gettext
import logging
from threading import Thread
from typing import Any, cast, Dict, Optional, Tuple

import gi

gi.require_version("Gtk", "3.0")  # noqa

from gi.repository import Gio, GLib, GObject, Gtk

from .controllers import (
    AlbumsController,
    ControllerBase,
    PlaybackController,
    PlaylistsController,
    TracklistController,
    MixerController,
)
from .download import ImageDownloader
from .http import MopidyHTTPClient
from .message import Message, MessageType
from .model import Model
from .time import TimePositionTracker
from .utils import configure_logger
from .widgets import AboutDialog, PreferencesWindow
from .window import ArgosWindow
from .ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class Application(Gtk.Application):

    start_maximized = GObject.Property(type=bool, default=False)
    disable_tooltips = GObject.Property(type=bool, default=False)
    single_click = GObject.Property(type=bool, default=False)

    def __init__(self, application_id: str):
        super().__init__(
            application_id=application_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self._loop = asyncio.get_event_loop()
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._nm = Gio.NetworkMonitor.get_default()

        self._settings = Gio.Settings(application_id)

        self.window = None
        self.prefs_window = None

        self._model = Model(self)
        self._ws = MopidyWSConnection(self)
        self._http = MopidyHTTPClient(self)
        self._download = ImageDownloader(self)
        self._time_position_tracker = TimePositionTracker(self)

        self._consumers = cast(
            Tuple[ControllerBase],
            (
                PlaybackController(self),
                TracklistController(self),
                AlbumsController(self),
                MixerController(self),
                PlaylistsController(self),
            ),
        )
        self._model.props.network_available = self._nm.get_network_available()
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
            _("Start with maximized window"),
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
            "single-click",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Use single-click"),
            None,
        )

    @GObject.Property(type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    @GObject.Property(type=MopidyWSConnection, flags=GObject.ParamFlags.READABLE)
    def ws(self):
        return self._ws

    @GObject.Property(type=MopidyHTTPClient, flags=GObject.ParamFlags.READABLE)
    def http(self):
        return self._http

    @GObject.Property(type=ImageDownloader, flags=GObject.ParamFlags.READABLE)
    def download(self):
        return self._download

    @GObject.Property(type=Model, flags=GObject.ParamFlags.READABLE)
    def model(self):
        return self._model

    @property
    def message_queue(self) -> asyncio.Queue:
        return self._message_queue

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        configure_logger(options)
        self.props.start_maximized = "maximized" in options
        self.props.disable_tooltips = "no-tooltips" in options
        self.props.single_click = "single-click" in options

        self.activate()
        return 0

    def do_activate(self):
        if not self.window:
            LOGGER.debug("Instantiating application window")
            self.window = ArgosWindow(self)
            self.window.set_default_icon_name("media-optical")
            # Run an event loop in a dedicated thread and reserve main
            # thread to Gtk processing loop
            t = Thread(target=self._start_event_loop, daemon=True)
            t.start()

        if self.props.start_maximized:
            self.window.maximize()

        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action_descriptions = [
            ("show_about_dialog", self.show_about_dialog_cb, None),
            ("show_preferences", self.show_prefs_activate_cb, None),
            ("play_random_album", self.play_random_album_activate_cb, None),
            ("quit", self.quit_activate_cb, ("app.quit", ["<Ctrl>Q"])),
        ]
        for action_name, callback, accel in action_descriptions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", callback)
            self.add_action(action)
            if accel is not None:
                self.set_accels_for_action(*accel)

        for action_name in ["play_random_album"]:
            action = self.lookup_action(action_name)
            if not action:
                continue

            action.set_enabled(self._model.network_available and self._model.connected)

    def _start_event_loop(self):
        LOGGER.debug("Attaching event loop to calling thread")
        asyncio.set_event_loop(self._loop)

        LOGGER.debug("Starting event loop")
        self._loop.run_until_complete(
            asyncio.gather(
                self._ws.listen(),
                self._process_messages(),
                self._time_position_tracker.track(),
            )
        )
        LOGGER.debug("Event loop stopped")

    async def _process_messages(self) -> None:
        LOGGER.debug("Waiting for new messages...")
        while True:
            message = await self._message_queue.get()
            message_type = message.type
            LOGGER.debug(f"Dispatching message of type {message_type}")

            for consumer in self._consumers:
                await consumer.process_message(message_type, message)

    def _update_network_actions_state(self) -> None:
        for action_name in ["play_random_album"]:
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

    def send_message(
        self, message_type: MessageType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)

    def show_about_dialog_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is None:
            return

        about_dialog = AboutDialog()
        about_dialog.set_transient_for(self.window)
        about_dialog.set_wmclass("Argos", "about")
        about_dialog.run()
        about_dialog.destroy()

    def show_prefs_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is None:
            return

        self.prefs_window = PreferencesWindow(self)
        self.prefs_window.set_transient_for(self.window)
        self.prefs_window.set_wmclass("Argos", "preferences")
        self.prefs_window.connect("destroy", self.prefs_window_destroy_cb)

        self.prefs_window.present()

    def prefs_window_destroy_cb(self, window: Gtk.Window) -> None:
        self.prefs_window = None

    def quit_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is not None:
            self.window.destroy()

    def play_random_album_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self.send_message(MessageType.PLAY_TRACKS)
