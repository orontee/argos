import logging
from typing import Any, cast, Dict, List, TYPE_CHECKING

from gi.repository import GObject

if TYPE_CHECKING:
    from ..app import Application
from ..download import ImageDownloader
from ..message import Message, MessageType
from ..model import TrackModel
from .base import ControllerBase

LOGGER = logging.getLogger(__name__)


class AlbumsController(ControllerBase):
    def __init__(self, application: "Application"):
        super().__init__(application)

        self._download: ImageDownloader = application.props.download

        self._model.connect("notify::albums-loaded", self._on_albums_loaded_changed)

    async def process_message(
        self, message_type: MessageType, message: Message
    ) -> None:
        if message_type == MessageType.BROWSE_ALBUMS:
            await self._browse_albums()

        elif message_type == MessageType.FETCH_ALBUM_IMAGES:
            await self._fetch_album_images()

        elif message_type == MessageType.COMPLETE_ALBUM_DESCRIPTION:
            album_uri = message.data.get("album_uri", "")
            if album_uri:
                await self._describe_album(album_uri)

    async def _browse_albums(self) -> None:
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

    async def _fetch_album_images(self) -> None:
        LOGGER.debug("Starting album image download...")
        albums = self._model.albums
        image_uris = [albums.get_item(i).image_uri for i in range(albums.get_n_items())]
        await self._download.fetch_images(image_uris)

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

            parsed_tracks: List[TrackModel] = [
                TrackModel(
                    uri=cast(str, t.get("uri")),
                    name=cast(str, t.get("name")),
                    track_no=cast(int, t.get("track_no")),
                    disc_no=cast(int, t.get("disc_no", 1)),
                    length=t.get("length"),
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

    def _on_albums_loaded_changed(
        self,
        _1: GObject.GObject,
        _2: GObject.GParamSpec,
    ) -> None:
        self.send_message(MessageType.FETCH_ALBUM_IMAGES)
