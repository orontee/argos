import logging
from typing import Optional

LOGGER = logging.getLogger(__name__)


class MopidyBackend:
    def __init__(
        self,
        *,
        settings_key: str,
        static_albums: bool = True,
    ):
        self._settings_key = settings_key
        self._static_albums = static_albums

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        raise NotImplementedError

    @property
    def settings_key(self) -> str:
        return self._settings_key

    @property
    def static_albums(self) -> bool:
        return self._static_albums

    def __str__(self) -> str:
        return self.__class__.__name__


class MopidyLocalBackend(MopidyBackend):
    def __init__(self):
        super().__init__(settings_key="mopidy-local")

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "local:directory":
            return "local:directory?type=album"
        return None


class MopidyBandcampBackend(MopidyBackend):
    def __init__(self):
        super().__init__(settings_key="mopidy-bandcamp")

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "bandcamp:browse":
            return "bandcamp:collection"
        return None


class MopidyJellyfinBackend(MopidyBackend):
    def __init__(self):
        super().__init__(settings_key="mopidy-jellyfin")

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "jellyfin:":
            return "jellyfin:albums"
        return None


class MopidyPodcastBackend(MopidyBackend):
    def __init__(self):
        super().__init__(settings_key="mopidy-podcast", static_albums=False)

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri and directory_uri.startswith("podcast+file://"):
            return directory_uri
        return None
