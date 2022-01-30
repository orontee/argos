import asyncio
import logging
from functools import partial
from threading import Thread
from typing import Any, Dict, List

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from .accessor import ModelAccessor
from .download import ImageDownloader
from .http import MopidyHTTPClient
from .message import Message, MessageType
from .model import Model, PlaybackState
from .ui import Window
from .ws import MopidyWSListener

LOGGER = logging.getLogger(__name__)


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        Gtk.Application.__init__(self,
                                 *args,
                                 application_id="org.argos",
                                 **kwargs)
        self._loop = asyncio.get_event_loop()
        self._messages = asyncio.Queue()
        self._model = Model()

        self._http = MopidyHTTPClient()
        self._ws = MopidyWSListener(message_queue=self._messages)
        self._download = ImageDownloader(message_queue=self._messages)

    def do_activate(self):
        self.window = Window(message_queue=self._messages,
                             loop=self._loop,
                             application=self)
        self.window.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        play_random_album_action = Gio.SimpleAction.new("play_random_album", None)
        play_random_album_action.connect("activate",
                                         self.play_random_album_activate_cb)
        self.add_action(play_random_album_action)

        play_favorite_playlist_action = Gio.SimpleAction.new(
            "play_favorite_playlist", None
        )
        play_favorite_playlist_action.connect(
            "activate",
            self.play_favorite_playlist_activate_cb
        )
        self.add_action(play_favorite_playlist_action)

        # Run an event loop in a dedicated thread and reserve main
        # thread to Gtk processing loop
        t = Thread(target=self._start_event_loop, daemon=True)
        t.start()

    def _start_event_loop(self):
        LOGGER.debug("Attaching event loop to calling thread")
        asyncio.set_event_loop(self._loop)

        LOGGER.debug("Starting event loop")
        self._loop.run_until_complete(self._do())
        LOGGER.debug("Event loop stopped")

    async def _do(self):
        await self._reset_model()
        self._loop.create_task(self._process_messages())
        await self._ws.listen()

    async def _process_messages(self):
        LOGGER.debug("Waiting for new messages...")
        while True:
            message = await self._messages.get()
            type = message.type

            LOGGER.debug(f"Processing {type!r} message")

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

            elif type == MessageType.PLAY_RANDOM_ALBUM:
                await self._http.play_random_album()

            elif type == MessageType.PLAY_FAVORITE_PLAYLIST:
                await self._http.play_favorite_playlist()

            elif type == MessageType.SET_VOLUME:
                volume = round(message.data * 100)
                await self._http.set_volume(volume)

            # Events (from websocket)
            elif type == MessageType.TRACK_PLAYBACK_STARTED:
                async with self.model_accessor as model:
                    tl_track = message.data.get("tl_track", {})
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

            elif type == MessageType.PLAYBACK_STATE_CHANGED:
                async with self.model_accessor as model:
                    raw_state = message.data.get("new_state")
                    model.update_from(raw_state=raw_state)

            elif type == MessageType.MUTE_CHANGED:
                async with self.model_accessor as model:
                    mute = message.data.get("mute")
                    model.update_from(mute=mute)

            elif type == MessageType.TRACKLIST_CHANGED:
                async with self.model_accessor as model:
                    model.clear_tl()

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

            else:
                LOGGER.warning(f"Unhandled message type {type!r}")

    @property
    def model_accessor(self) -> ModelAccessor:
        return ModelAccessor(model=self._model, message_queue=self._messages)

    async def _handle_model_changed(self, changed: List[str]) -> None:
        if "image_path" in changed:
            GLib.idle_add(self.window.update_image,
                          self._model.image_path)

        if "track_name" in changed or "artist_name" in changed:
            GLib.idle_add(partial(
                self.window.update_labels,
                track_name=self._model.track_name,
                artist_name=self._model.artist_name))

            track_uri = self._model.track_uri
            if not track_uri:
                return

            track_images = await self._http.get_images(track_uri)
            await self._download.fetch_first_image(track_uri=track_uri,
                                                   track_images=track_images)

        if "volume" in changed or "mute" in changed:
            GLib.idle_add(partial(self.window.update_volume,
                                  mute=self._model.mute,
                                  volume=self._model.volume))

        if "state" in changed:
            GLib.idle_add(partial(self.window.update_play_button,
                                  state=self._model.state))

    async def _reset_model(self) -> None:
        raw_state = await self._http.get_state()
        mute = await self._http.get_mute()
        volume = await self._http.get_volume()
        tl_track = await self._http.get_current_tl_track()

        async with self.model_accessor as model:
            model.update_from(raw_state=raw_state,
                              mute=mute,
                              volume=volume,
                              tl_track=tl_track)

    def play_random_album_activate_cb(self, action, parameter) -> None:
        self._loop.call_soon_threadsafe(
            self._messages.put_nowait,
            Message(MessageType.PLAY_RANDOM_ALBUM)
        )

    def play_favorite_playlist_activate_cb(self, action, parameter) -> None:
        self._loop.call_soon_threadsafe(
            self._messages.put_nowait,
            Message(MessageType.PLAY_FAVORITE_PLAYLIST)
        )
