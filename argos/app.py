import asyncio
import gettext
import inspect
import logging
from collections import defaultdict
from threading import Thread
from typing import Any, Dict, Optional

import gi

gi.require_version("Gdk", "3.0")  # noqa
gi.require_version("Gtk", "3.0")  # noqa

from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from argos.controllers import (
    AlbumsController,
    MixerController,
    PlaybackController,
    PlaylistsController,
    TracklistController,
)
from argos.download import ImageDownloader
from argos.http import MopidyHTTPClient
from argos.message import Message, MessageType
from argos.model import Model
from argos.notify import Notifier
from argos.placement import WindowPlacement
from argos.time import TimePositionTracker
from argos.utils import configure_logger
from argos.widgets import AboutDialog, PreferencesWindow, StreamUriDialog
from argos.window import ArgosWindow
from argos.ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class Application(Gtk.Application):

    start_maximized = GObject.Property(type=bool, default=False)
    disable_tooltips = GObject.Property(type=bool, default=False)
    hide_search_button = GObject.Property(type=bool, default=False)

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

        # services
        self._model = Model(self)
        self._ws = MopidyWSConnection(self)
        self._http = MopidyHTTPClient(self)
        self._download = ImageDownloader(self)
        self._time_position_tracker = TimePositionTracker(self)
        self._notifier = Notifier(self)

        self._controllers = (
            PlaybackController(self),
            TracklistController(self),
            AlbumsController(self),
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
            "hide-search-button",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Hide search button"),
            None,
        )

        self._apply_style()

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

        self.props.start_maximized = "maximized" in options
        self.props.disable_tooltips = "no-tooltips" in options
        self.props.hide_search_button = "hide-search-button" in options

        self.activate()
        return 0

    def do_activate(self):
        self._identify_message_consumers_from_controllers()

        if not self.window:
            LOGGER.debug("Instantiating application window")
            self.window = ArgosWindow(self)
            self.window.set_default_icon_name("media-optical")

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

        if self.props.start_maximized:
            self.window.maximize()

        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action_descriptions = [
            ("show-about-dialog", self.show_about_dialog_cb, None),
            ("show-preferences", self.show_prefs_activate_cb, None),
            ("new-playlist", self.new_playlist_activate_cb, None),
            ("play-random-album", self.play_random_album_activate_cb, None),
            ("play-stream", self.play_stream_activate_cb, None),
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
            "play-random-album",
            "play-stream",
            "update-library",
        ]:
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
                self._dispatch_messages(),
                self._time_position_tracker.track(),
            )
        )
        LOGGER.debug("Event loop stopped")

    async def _dispatch_messages(self) -> None:
        LOGGER.debug("Waiting for new messages...")
        while True:
            message = await self._message_queue.get()
            message_type = message.type
            LOGGER.debug(f"Dispatching message of type {message_type}")

            consumers = self._consumers.get(message_type)
            if consumers is None:
                LOGGER.warning(f"No consumer for message of type {message_type}")
                return

            for consumer in consumers:
                await consumer(message)

    def _update_network_actions_state(self) -> None:
        for action_name in [
            "new-playlist",
            "play-random-album",
            "play-stream",
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
        LOGGER.debug("Quit requested by end-user")
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

    def play_random_album_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        LOGGER.debug("Random album play requested by end-user")
        self.send_message(MessageType.PLAY_RANDOM_ALBUM)

    def play_stream_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        LOGGER.debug("Play stream requested by end-user")

        dialog = StreamUriDialog(self)
        response = dialog.run()
        stream_uri = dialog.props.stream_uri if response == Gtk.ResponseType.OK else ""
        dialog.destroy()

        if not stream_uri:
            LOGGER.debug("Aborting playing stream")
            return

        self.send_message(
            MessageType.PLAY_TRACKS,
            {"uris": [stream_uri]},
        )

    def update_library_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        LOGGER.debug("Library update requested by end-user")
        self.send_message(MessageType.BROWSE_ALBUMS)

    def _identify_message_consumers_from_controllers(self) -> None:
        LOGGER.debug("Identifying message consumers")
        self._consumers = defaultdict(list)
        for ctrl in self._controllers:
            for name in dir(ctrl):
                subject = getattr(ctrl, name)
                if callable(subject) and hasattr(subject, "consume_messages"):
                    for message_type in subject.consume_messages:
                        self._consumers[message_type].append(subject)
                        LOGGER.debug(
                            f"New consumer of {message_type}: {inspect.unwrap(subject)}"
                        )
