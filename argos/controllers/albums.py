import logging
from operator import attrgetter
import random
from typing import Any, cast, Dict, List, TYPE_CHECKING

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from ..download import ImageDownloader
from ..message import consume, Message, MessageType
from .base import ControllerBase
from .utils import parse_tracks

LOGGER = logging.getLogger(__name__)


class AlbumsController(ControllerBase):
    """Albums controller.

    This controller maintains the ``Model.albums`` store.

    """

    logger = LOGGER  # used by consume decorator

    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

        self._model.connect("notify::albums-loaded", self._on_albums_loaded_changed)

    @consume(MessageType.COMPLETE_ALBUM_DESCRIPTION)
    async def complete_album_description(self, message: Message) -> None:
        album_uri = message.data.get("album_uri", "")
        if not album_uri:
            return

        LOGGER.debug(f"Completing description of album with uri {album_uri!r}")

        tracks = await self._http.lookup_library([album_uri])
        if tracks is None:
            return

        album_tracks = tracks.get(album_uri)
        if album_tracks and len(album_tracks) > 0:
            album = album_tracks[0].get("album")
            if not album:
                return

            artists = cast(List[Dict[str, Any]], album_tracks[0].get("artists", []))
            artist_name = artists[0].get("name") if len(artists) > 0 else None
            num_tracks = album.get("num_tracks")
            num_discs = album.get("num_discs")
            date = album.get("date")

            class LengthAcc:
                length = 0

                def __call__(self, t: Dict[str, Any]) -> None:
                    if self.length != -1 and "length" in t:
                        self.length += int(t["length"])
                    else:
                        self.length = -1

            length_acc = LengthAcc()
            parsed_tracks = parse_tracks(tracks, visitor=length_acc)

            parsed_tracks.sort(key=attrgetter("disc_no", "track_no"))

            self._model.complete_album_description(
                album_uri,
                artist_name=artist_name,
                num_tracks=num_tracks,
                num_discs=num_discs,
                date=date,
                length=length_acc.length,
                tracks=parsed_tracks,
            )

    @consume(MessageType.BROWSE_ALBUMS)
    async def browse_albums(self, message: Message) -> None:
        LOGGER.debug("Starting to browse albums...")
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

        self._model.update_albums(albums)

    @consume(MessageType.PLAY_RANDOM_ALBUM)
    async def play_random_album(self, message: Message) -> None:
        if len(self._model.albums) == 0:
            LOGGER.warning("Won't play random album since albums list is empty")
            return

        album = random.choice(self._model.albums)
        LOGGER.debug(f"Album with URI {album.uri!r} choosen")

        await self._http.play_tracks([album.uri])

    @consume(MessageType.FETCH_ALBUM_IMAGES)
    async def fetch_album_images(self, message: Message) -> None:
        LOGGER.debug("Starting album image download...")
        albums = self._model.albums
        image_uris = [albums.get_item(i).image_uri for i in range(albums.get_n_items())]
        await self._download.fetch_images(image_uris)

    def _on_albums_loaded_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.send_message(MessageType.FETCH_ALBUM_IMAGES)
