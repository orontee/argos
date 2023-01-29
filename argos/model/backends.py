import logging
from typing import Tuple

from gi.repository import GObject

LOGGER = logging.getLogger(__name__)


class MopidyBackend(GObject.Object):

    name = GObject.Property(type=str)
    static_albums = GObject.Property(type=bool, default=True)
    preload_album_tracks = GObject.Property(type=bool, default=True)
    exclude_albums_from_random_choice = GObject.Property(type=bool, default=False)

    def is_responsible_for(self, directory_uri: str) -> bool:
        raise NotImplementedError

    def hides(self, ref_uri: str) -> bool:
        return False

    def __str__(self) -> str:
        return self.__class__.__name__


class MopidyBandcampBackend(MopidyBackend):
    def __init__(
        self,
    ):
        super().__init__(
            name="Mopidy-Bandcamp",
            preload_album_tracks=False,
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("bandcamp:")

    def extract_artist_name(self, album_name: str) -> Tuple[str, str]:
        tokens = album_name.split(" - ", maxsplit=1)
        if len(tokens) == 2:
            return tokens[0], tokens[1]
        return "", album_name


class MopidyPodcastBackend(MopidyBackend):
    def __init__(self):
        super().__init__(
            name="Mopidy-Podcast",
            static_albums=False,
            exclude_albums_from_random_choice=True,
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("podcast+")


class GenericBackend(MopidyBackend):
    def __init__(self):
        super().__init__(name="Generic")

    def is_responsible_for(self, directory_uri: str) -> bool:
        return True if directory_uri != "" else False
