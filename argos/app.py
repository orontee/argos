import asyncio
import gettext
import logging
from functools import partial
from threading import Thread
from typing import Any, cast, Dict, List, Optional

import gi

gi.require_version("Gtk", "3.0")  # noqa

from gi.repository import Gio, GLib, GObject, Gtk

from .download import ImageDownloader
from .http import MopidyHTTPClient
from .message import Message, MessageType
from .model import Model, PlaybackState, Track
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

        for signal in (
            "notify::network-available",
            "notify::connected",
            "notify::track-uri",
            "notify::albums-loaded",
        ):
            self._model.connect(signal, self._on_model_changed)

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

    @GObject.Property(type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    @GObject.Property(type=MopidyWSConnection, flags=GObject.ParamFlags.READABLE)
    def ws(self):
        return self._ws

    @GObject.Property(type=MopidyHTTPClient, flags=GObject.ParamFlags.READABLE)
    def http(self):
        return self._http

    @GObject.Property(type=Model, flags=GObject.ParamFlags.READABLE)
    def model(self):
        return self._model

    @property
    def message_queue(self):
        return self._message_queue

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        configure_logger(options)
        self.props.start_maximized = "maximized" in options
        self.props.disable_tooltips = "no-tooltips" in options

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
            ("play_favorite_playlist", self.play_favorite_playlist_activate_cb, None),
            ("quit", self.quit_activate_cb, ("app.quit", ["<Ctrl>Q"])),
        ]
        for action_name, callback, accel in action_descriptions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", callback)
            self.add_action(action)
            if accel is not None:
                self.set_accels_for_action(*accel)

        for action_name in ["play_random_album", "play_favorite_playlist"]:
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
            type = message.type

            LOGGER.debug(f"Processing {type} message")

            # Commands
            if type == MessageType.TOGGLE_PLAYBACK_STATE:
                current_state = self._model.state
                if current_state == PlaybackState.PLAYING:
                    await self._http.pause()
                elif current_state == PlaybackState.PAUSED:
                    await self._http.resume()
                elif (
                    current_state == PlaybackState.STOPPED
                    or current_state == PlaybackState.UNKNOWN
                ):
                    await self._http.play()

            elif type == MessageType.PLAY_PREV_TRACK:
                await self._http.previous()

            elif type == MessageType.PLAY_NEXT_TRACK:
                await self._http.next()

            elif type == MessageType.ADD_TO_TRACKLIST:
                uris = message.data.get("uris")
                await self._http.add_to_tracklist(uris=uris)

            elif type == MessageType.CLEAR_TRACKLIST:
                await self._http.clear_tracklist()

            elif type == MessageType.GET_TRACKLIST:
                await self._get_tracklist()

            elif type == MessageType.PLAY:
                await self._http.play(**message.data)

            elif type == MessageType.PLAY_TRACKS:
                await self._http.play_tracks(**message.data)

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

            elif type == MessageType.FETCH_TRACK_IMAGE:
                track_uri = message.data.get("track_uri", "")
                if track_uri:
                    images = await self._http.get_images([track_uri])
                    image_path = None
                    if images:
                        track_images = images.get(track_uri)
                        if track_images and len(track_images) > 0:
                            image_uri = track_images[0]["uri"]
                            image_path = await self._download.fetch_image(image_uri)
                    if image_path is not None and self._model.track_uri == track_uri:
                        self.update_model_from(image_path=str(image_path))
                    else:
                        self.update_model_from(image_path="")

            elif type == MessageType.FETCH_ALBUM_IMAGES:
                await self._fetch_album_images()

            elif type == MessageType.IDENTIFY_PLAYING_STATE:
                await self._identify_playing_state()

            elif type == MessageType.BROWSE_ALBUMS:
                await self._browse_albums()

            elif type == MessageType.COMPLETE_ALBUM_DESCRIPTION:
                album_uri = message.data.get("album_uri", "")
                if album_uri:
                    await self._describe_album(album_uri)

            elif type == MessageType.SET_CONSUME:
                await self._http.set_consume(**message.data)

            elif type == MessageType.SET_RANDOM:
                await self._http.set_random(**message.data)

            elif type == MessageType.SET_REPEAT:
                await self._http.set_repeat(**message.data)

            elif type == MessageType.SET_SINGLE:
                await self._http.set_single(**message.data)

            # Events (from websocket)
            elif type == MessageType.TRACK_PLAYBACK_STARTED:
                tl_track = message.data.get("tl_track", {})
                self.update_model_from(tl_track=tl_track)

            elif type == MessageType.TRACK_PLAYBACK_PAUSED:
                self.update_model_from(raw_state="paused")

            elif type == MessageType.TRACK_PLAYBACK_RESUMED:
                self.update_model_from(raw_state="playing")

            elif type == MessageType.TRACK_PLAYBACK_ENDED:
                self.model.clear_track_playback_state()

                auto_populate = self.settings.get_boolean("auto-populate-tracklist")
                if not auto_populate:
                    continue

                eot_tlid = await self._http.get_eot_tlid()
                if not eot_tlid:
                    LOGGER.info("Will populate track list with random album")
                    await self._http.play_tracks()

            elif type == MessageType.PLAYBACK_STATE_CHANGED:
                raw_state = message.data.get("new_state")
                self.update_model_from(raw_state=raw_state)

            elif type == MessageType.MUTE_CHANGED:
                mute = message.data.get("mute")
                self.update_model_from(mute=mute)

            elif type == MessageType.VOLUME_CHANGED:
                volume = message.data.get("volume")
                self.update_model_from(volume=volume)

            elif type == MessageType.SEEKED:
                time_position = message.data.get("time_position")
                self.update_model_from(time_position=time_position)
                self._time_position_tracker.time_position_synced()

            elif type == MessageType.TRACKLIST_CHANGED:
                await self._get_tracklist()

            elif type == MessageType.OPTIONS_CHANGED:
                await self._get_options()

            else:
                LOGGER.warning(
                    f"Unhandled message type {type!r} " f"with data {message.data!r}"
                )

    def update_model_from(
        self,
        *,
        raw_state: Any = None,
        mute: Any = None,
        volume: Any = None,
        time_position: Any = None,
        tl_track: Any = None,
        image_path: Any = None,
        albums: List[Any] = None,
        consume: Any = None,
        random: Any = None,
        repeat: Any = None,
        single: Any = None,
    ) -> None:
        state = PlaybackState.from_string(raw_state) if raw_state is not None else None

        values_by_name = {
            "state": state,
            "mute": mute,
            "volume": volume,
            "consume": consume,
            "random": random,
            "repeat": repeat,
            "single": single,
        }
        for name in values_by_name:
            value = values_by_name[name]
            if value is not None:
                self.model.set_property_in_gtk_thread(name, value)

        if tl_track is not None:
            track = tl_track.get("track", {})

            track_uri = track.get("uri", "")
            track_name = track.get("name", "")
            track_length = track.get("length", -1)

            self._model.set_property_in_gtk_thread("track_uri", track_uri)
            self._model.set_property_in_gtk_thread("track_name", track_name)
            self._model.set_property_in_gtk_thread("track_length", track_length)

            artists = track.get("artists", [])
            artist = artists[0] if len(artists) > 0 else {}
            artist_uri = artist.get("uri", "")
            artist_name = artist.get("name", "")
            self._model.set_property_in_gtk_thread("artist_uri", artist_uri)
            self._model.set_property_in_gtk_thread("artist_name", artist_name)

            if time_position is None:
                self._model.set_property_in_gtk_thread("time_position", -1)

        values_by_name = {
            "time_position": time_position,
            "image_path": image_path,
        }
        for name in values_by_name:
            value = values_by_name[name]
            if value is not None:
                self.model.set_property_in_gtk_thread(name, value)

        if albums is not None:
            self.model.set_albums(albums)

    def _update_network_actions_state(self) -> None:
        for action_name in ["play_random_album", "play_favorite_playlist"]:
            action = self.lookup_action(action_name)
            if not action:
                continue

            action.set_enabled(self._model.network_available and self._model.connected)

    async def _identify_playing_state(self) -> None:
        LOGGER.debug("Identifying playing state...")
        raw_state = await self._http.get_state()
        mute = await self._http.get_mute()
        volume = await self._http.get_volume()
        tl_track = await self._http.get_current_tl_track()
        time_position = await self._http.get_time_position()
        consume = await self._http.get_consume()
        random = await self._http.get_random()
        repeat = await self._http.get_repeat()
        single = await self._http.get_single()

        self.update_model_from(
            raw_state=raw_state,
            mute=mute,
            volume=volume,
            time_position=time_position,
            tl_track=tl_track,
            consume=consume,
            random=random,
            repeat=repeat,
            single=single,
        )
        self._time_position_tracker.time_position_synced()

    def _on_model_changed(
        self,
        _1: GObject.GObject,
        spec: GObject.GParamSpec,
    ) -> None:
        name = spec.name
        if name == "track-uri":
            if self.model.track_uri:
                self.send_message(
                    MessageType.FETCH_TRACK_IMAGE, {"track_uri": self.model.track_uri}
                )
        elif name == "connected" or name == "network-available":
            self._update_network_actions_state()
            self._schedule_track_list_update_maybe()
            self._schedule_browse_albums_maybe()
        elif name == "albums-loaded":
            self.send_message(MessageType.FETCH_ALBUM_IMAGES)
        else:
            LOGGER.warning(f"Unexpected model attribute change, {name!r}")

    def _schedule_track_list_update_maybe(self) -> None:
        if self.model.network_available and self.model.connected:
            LOGGER.debug("Will identify playing state since connected to Mopidy server")
            self.send_message(MessageType.IDENTIFY_PLAYING_STATE)
            self.send_message(MessageType.GET_TRACKLIST)
        else:
            LOGGER.debug("Clearing track playback state since not connected")
            self.model.clear_track_playback_state()

    def _schedule_browse_albums_maybe(self) -> None:
        if (
            self.model.network_available
            and self.model.connected
            and not self.model.albums_loaded
        ):
            LOGGER.debug("Will browse albums since connected to Mopidy server")
            self.send_message(MessageType.BROWSE_ALBUMS)

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

        self.update_model_from(albums=albums)

    async def _describe_album(self, uri: str) -> None:
        LOGGER.debug(f"Completing description of album with uri {uri}")

        tracks = await self._http.lookup_library([uri])
        album_tracks = tracks.get(uri) if tracks else None
        if album_tracks and len(album_tracks) > 0:
            album = album_tracks[0].get("album")
            if not album:
                return

            artists = cast(List[Dict[str, Any]], album_tracks[0].get("artists"))
            artist_name = artists[0].get("name") if len(artists) > 0 else None

            num_tracks = album.get("num_tracks")
            num_discs = album.get("num_discs")
            date = album.get("date")
            length = sum([track.get("length", 0) for track in album_tracks])

            parsed_tracks: List[Track] = [
                Track(
                    cast(str, t.get("uri")),
                    cast(str, t.get("name")),
                    cast(int, t.get("track_no")),
                    cast(int, t.get("disc_no", 1)),
                    t.get("length"),
                )
                for t in album_tracks
                if "uri" in t and "track_no" in t and "name" in t
            ]

            self._model.complete_album_description(
                uri,
                artist_name=artist_name,
                num_tracks=num_tracks,
                num_discs=num_discs,
                date=date,
                length=length,
                tracks=parsed_tracks,
            )

    async def _fetch_album_images(self) -> None:
        LOGGER.debug("Starting album image download...")
        albums = self._model.albums
        image_uris = [a.image_uri for a in albums if a.image_uri]
        await self._download.fetch_images(image_uris)

    async def _get_tracklist(self) -> None:
        version = await self._http.get_tracklist_version()
        tracks = await self._http.get_tracklist_tracks()
        self._model.update_tracklist(version, tracks)

    async def _get_options(self) -> None:
        consume = await self._http.get_consume()
        random = await self._http.get_random()
        repeat = await self._http.get_repeat()
        single = await self._http.get_single()

        self.update_model_from(
            consume=consume,
            random=random,
            repeat=repeat,
            single=single,
        )

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

    def play_favorite_playlist_activate_cb(
        self, action: Gio.SimpleAction, parameter: None
    ) -> None:
        self.send_message(MessageType.PLAY_FAVORITE_PLAYLIST)
