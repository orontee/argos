import asyncio
import gettext
import logging
from functools import partial
from threading import Thread
from typing import Any, Dict, Optional, Set

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from .widgets.about import AboutDialog
from .widgets.preferences import PreferencesWindow

from .accessor import WithModelAccessor
from .download import ImageDownloader
from .http import MopidyHTTPClient
from .message import Message, MessageType
from .model import Model, PlaybackState
from .time import TimePositionTracker
from .utils import configure_logger
from .window import ArgosWindow
from .ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


class Application(Gtk.Application, WithModelAccessor):
    def __init__(self, application_id: str, *args, **kwargs):
        Gtk.Application.__init__(
            self,
            *args,
            application_id=application_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs,
        )
        self._loop = asyncio.get_event_loop()
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._nm = Gio.NetworkMonitor.get_default()

        self._model = Model(network_available=self._nm.get_network_available())

        self.settings = Gio.Settings(application_id)
        mopidy_base_url = self.settings.get_string("mopidy-base-url")
        connection_retry_delair = self.settings.get_int("connection-retry-delay")
        favorite_playlist_uri = self.settings.get_string("favorite-playlist-uri")

        self.window = None
        self.prefs_window = None

        self._ws = MopidyWSConnection(
            message_queue=self._message_queue,
            mopidy_base_url=mopidy_base_url,
            connection_retry_delay=connection_retry_delair,
        )
        self._http = MopidyHTTPClient(
            ws=self._ws,
            favorite_playlist_uri=favorite_playlist_uri,
        )
        self._download = ImageDownloader(
            message_queue=self._message_queue,
            mopidy_base_url=mopidy_base_url,
        )
        self._time_position_tracker = TimePositionTracker(
            model=self._model, message_queue=self._message_queue, http=self._http
        )

        self._nm.connect("network-changed", self.on_network_changed)

        self._start_fullscreen: Optional[bool] = None
        self._start_maximized: Optional[bool] = None
        self._disable_tooltips: Optional[bool] = None

        self.settings.connect(
            "changed::mopidy-base-url", self.on_mopidy_base_url_changed
        )
        self.settings.connect(
            "changed::favorite-playlist-uri", self.on_favorite_playlist_uri_changed
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
            "fullscreen",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Start with fullscreen window"),
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

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        configure_logger(options)
        self._start_fullscreen = "fullscreen" in options
        self._start_maximized = "maximized" in options and "fullscreen" not in options
        self._disable_tooltips = "no-tooltips" in options

        self.activate()
        return 0

    def do_activate(self):
        if not self.window:
            LOGGER.debug("Instantiating application window")
            self.window = ArgosWindow(
                application=self,
                disable_tooltips=self._disable_tooltips,
            )
            self.window.set_default_icon_name("media-optical")
            # Run an event loop in a dedicated thread and reserve main
            # thread to Gtk processing loop
            t = Thread(target=self._start_event_loop, daemon=True)
            t.start()

        if self._start_fullscreen:
            self.window.fullscreen()

        if self._start_maximized:
            self.window.maximize()

        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        show_about_dialog_action = Gio.SimpleAction.new("show_about_dialog", None)
        show_about_dialog_action.connect("activate", self.show_about_dialog_cb)
        self.add_action(show_about_dialog_action)

        show_prefs_action = Gio.SimpleAction.new("show_preferences", None)
        show_prefs_action.connect("activate", self.show_prefs_activate_cb)
        self.add_action(show_prefs_action)

        play_random_album_action = Gio.SimpleAction.new("play_random_album", None)
        play_random_album_action.connect("activate", self.play_random_album_activate_cb)
        self.add_action(play_random_album_action)

        play_favorite_playlist_action = Gio.SimpleAction.new(
            "play_favorite_playlist", None
        )
        play_favorite_playlist_action.connect(
            "activate", self.play_favorite_playlist_activate_cb
        )
        self.add_action(play_favorite_playlist_action)

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
            type = message.type

            LOGGER.debug(f"Processing {type} message")

            # Commands
            if type == MessageType.TOGGLE_PLAYBACK_STATE:
                current_state = self._model.state
                if current_state == PlaybackState.PLAYING:
                    await self._http.pause()
                elif current_state == PlaybackState.PAUSED:
                    await self._http.resume()
                elif current_state == PlaybackState.STOPPED:
                    await self._http.play()

            elif type == MessageType.PLAY_PREV_TRACK:
                await self._http.previous()

            elif type == MessageType.PLAY_NEXT_TRACK:
                await self._http.next()

            elif type == MessageType.PLAY_ALBUM:
                uri = message.data.get("uri")
                await self._http.play_album(uri=uri)

            elif type == MessageType.PLAY_FAVORITE_PLAYLIST:
                await self._http.play_favorite_playlist()

            elif type == MessageType.SEEK:
                time_position = round(message.data.get("time_position"))
                await self._http.seek(time_position)

            elif type == MessageType.SET_VOLUME:
                volume = round(message.data.get("volume"))
                await self._http.set_volume(volume)

            elif type == MessageType.LIST_PLAYLISTS:
                playlists = await self._http.list_playlists()
                if self.prefs_window and playlists:
                    GLib.idle_add(
                        partial(
                            self.prefs_window.update_favorite_playlist_completion,
                            playlists=playlists,
                        )
                    )

            # Events (from websocket)
            elif type == MessageType.TRACK_PLAYBACK_STARTED:
                tl_track = message.data.get("tl_track", {})
                async with self.model_accessor as model:
                    model.update_from(tl_track=tl_track)

            elif type == MessageType.TRACK_PLAYBACK_PAUSED:
                async with self.model_accessor as model:
                    model.update_from(raw_state="paused")

            elif type == MessageType.TRACK_PLAYBACK_RESUMED:
                async with self.model_accessor as model:
                    model.update_from(raw_state="playing")

            elif type == MessageType.TRACK_PLAYBACK_ENDED:
                async with self.model_accessor as model:
                    model.clear_tl()

                auto_populate = self.settings.get_boolean("auto-populate-tracklist")
                if not auto_populate:
                    continue

                eot_tlid = await self._http.get_eot_tlid()
                if not eot_tlid:
                    LOGGER.info("Will populate track list with random album")
                    await self._http.play_album()

            elif type == MessageType.PLAYBACK_STATE_CHANGED:
                raw_state = message.data.get("new_state")
                async with self.model_accessor as model:
                    model.update_from(raw_state=raw_state)

            elif type == MessageType.MUTE_CHANGED:
                mute = message.data.get("mute")
                async with self.model_accessor as model:
                    model.update_from(mute=mute)

            elif type == MessageType.VOLUME_CHANGED:
                volume = message.data.get("volume")
                async with self.model_accessor as model:
                    model.update_from(volume=volume)

            elif type == MessageType.TRACKLIST_CHANGED:
                async with self.model_accessor as model:
                    model.clear_tl()
                self._time_position_tracker.time_position_synced()

            elif type == MessageType.SEEKED:
                time_position = message.data.get("time_position")
                async with self.model_accessor as model:
                    model.update_from(time_position=time_position)
                self._time_position_tracker.time_position_synced()

            # Events (internal)
            elif type == MessageType.IMAGE_AVAILABLE:
                track_uri = message.data.get("track_uri")
                image_path = message.data.get("image_path")
                if self._model.track_uri == track_uri:
                    async with self.model_accessor as model:
                        model.update_from(image_path=image_path)

            elif type == MessageType.MODEL_CHANGED:
                changed = message.data.get("changed", [])
                await self._handle_model_changed(changed)

            elif type == MessageType.MOPIDY_WEBSOCKET_CONNECTED:
                connected = message.data.get("connected", False)
                # don't use None since accessor won't update model
                async with self.model_accessor as model:
                    model.update_from(connected=connected)

            elif type == MessageType.NETWORK_AVAILABLE_CHANGED:
                network_available = message.data.get("network_available")
                async with self.model_accessor as model:
                    model.update_from(network_available=network_available)

            elif type == MessageType.ALBUM_IMAGES_UPDATED:
                if self.window:
                    GLib.idle_add(self.window.update_album_icons)

            else:
                LOGGER.warning(
                    f"Unhandled message type {type!r} " f"with data {message.data!r}"
                )

    async def _handle_model_changed(self, changed: Set[str]) -> None:
        """Propage model changes."""
        if "network_available" in changed or "connected" in changed:
            if self._model.network_available and self._model.connected:
                LOGGER.debug("Network available and connected")
                await self._identify_playing_state()
                await self._browse_albums()
            else:
                LOGGER.debug("Network not available")
                async with self.model_accessor as model:
                    model.clear_tl()

        if "image_path" in changed:
            if self.window:
                GLib.idle_add(
                    self.window.update_playing_track_image, self._model.image_path
                )

        if (
            "track_name" in changed
            or "artist_name" in changed
            or "track_length" in changed
        ):
            if self.window:
                GLib.idle_add(
                    partial(
                        self.window.update_labels,
                        track_name=self._model.track_name,
                        artist_name=self._model.artist_name,
                        track_length=self._model.track_length,
                    )
                )

            track_uri = self._model.track_uri
            if not track_uri:
                return

            images = await self._http.get_images([track_uri])
            if not images:
                return

            track_images = images.get(track_uri)
            if track_images and len(track_images) > 0:
                image_uri = track_images[0]["uri"]
                filepath = await self._download.fetch_image(image_uri)
                if filepath is not None:
                    await self._message_queue.put(
                        Message(
                            MessageType.IMAGE_AVAILABLE,
                            {"track_uri": track_uri, "image_path": filepath},
                        )
                    )

        if "volume" in changed or "mute" in changed:
            if self.window:
                GLib.idle_add(
                    partial(
                        self.window.update_volume,
                        mute=self._model.mute,
                        volume=self._model.volume,
                    )
                )

        if "state" in changed:
            if self.window:
                GLib.idle_add(
                    partial(self.window.update_play_button, state=self._model.state)
                )

        if "time_position" in changed:
            if self.window:
                GLib.idle_add(
                    partial(
                        self.window.update_time_position_scale,
                        time_position=self._model.time_position,
                    )
                )

        if "albums" in changed:
            if self.window:
                GLib.idle_add(
                    partial(self.window.update_albums_list, albums=self._model.albums)
                )
                await self._fetch_album_images()

    async def _identify_playing_state(self) -> None:
        LOGGER.debug("Identifying playing state...")
        raw_state = await self._http.get_state()
        mute = await self._http.get_mute()
        volume = await self._http.get_volume()
        tl_track = await self._http.get_current_tl_track()
        time_position = await self._http.get_time_position()
        self._time_position_tracker.time_position_synced()

        async with self.model_accessor as model:
            model.update_from(
                raw_state=raw_state,
                mute=mute,
                volume=volume,
                time_position=time_position,
                tl_track=tl_track,
            )

    async def _browse_albums(self) -> None:
        LOGGER.debug("Starting to  browse albums...")
        albums = await self._http.browse_albums()
        if not albums:
            return

        album_uris = [a["uri"] for a in albums]
        images = await self._http.get_images(album_uris)
        if not images:
            return

        for a in albums:
            album_uri = a["uri"]
            if album_uri not in images or len(images[album_uri]) == 0:
                continue

            image_uri = images[album_uri][0]["uri"]
            a["image_uri"] = image_uri
            filepath = self._download.get_image_filepath(image_uri)
            a["image_path"] = filepath

        async with self.model_accessor as model:
            model.update_from(albums=albums)

    async def _fetch_album_images(self) -> None:
        LOGGER.debug("Starting album image download...")
        albums = self._model.albums
        image_uris = [a.image_uri for a in albums.values() if a.image_uri]
        await self._download.fetch_images(image_uris)

    def send_message(
        self, message_type: MessageType, data: Dict[str, Any] = None
    ) -> None:
        message = Message(message_type, data or {})
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, message)

    def on_network_changed(
        self, network_monitor: Gio.NetworkMonitor, network_available: bool
    ) -> None:
        self.send_message(
            MessageType.NETWORK_AVAILABLE_CHANGED,
            {"network_available": network_available},
        )

    def on_mopidy_base_url_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        mopidy_base_url = self.settings.get_string(key)
        self._ws.set_mopidy_base_url(mopidy_base_url)
        self._download.set_mopidy_base_url(mopidy_base_url)

    def on_favorite_playlist_uri_changed(
        self,
        settings: Gio.Settings,
        key: str,
    ) -> None:
        favorite_playlist_uri = settings.get_string(key)
        self._http.set_favorite_playlist_uri(favorite_playlist_uri)

    def show_about_dialog_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is None:
            return

        about_dialog = AboutDialog()
        about_dialog.set_transient_for(self.window)
        about_dialog.run()
        about_dialog.destroy()

    def show_prefs_activate_cb(self, action: Gio.SimpleAction, parameter: None) -> None:
        if self.window is None:
            return

        self.prefs_window = PreferencesWindow(application=self, settings=self.settings)
        self.prefs_window.set_transient_for(self.window)
        self.prefs_window.connect("destroy", self.prefs_window_destroy_cb)

        self.prefs_window.present()

    def prefs_window_destroy_cb(self, window: Gtk.Window) -> None:
        self.prefs_window = None

    def play_random_album_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self.send_message(MessageType.PLAY_ALBUM)

    def play_favorite_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self.send_message(MessageType.PLAY_FAVORITE_PLAYLIST)
