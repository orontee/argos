import logging
from typing import Optional, Tuple

LOGGER = logging.getLogger(__name__)


class MopidyBackend:
    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        raise NotImplementedError


class MopidyLocalBackend(MopidyBackend):
    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "local:directory":
            return "local:directory?type=album"
        return None


class MopidyBandcampBackend(MopidyBackend):
    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "bandcamp:browse":
            return "bandcamp:collection"
        return None


class MopidyPodcastBackend(MopidyBackend):
    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri and directory_uri.startswith("podcast+file://"):
            return directory_uri
        return None


class BackendManager:
    def __init__(self):
        self._backends: Tuple[MopidyBackend] = (
            MopidyLocalBackend(),
            MopidyPodcastBackend(),
            MopidyBandcampBackend(),
        )

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        for config in self._backends:
            albums_uri = config.get_albums_uri(directory_uri)
            if albums_uri:
                LOGGER.debug(
                    f"Backend {config.__class__!r} supports URI {albums_uri!r}"
                )
                return config.get_albums_uri(directory_uri)

        LOGGER.warning(f"No known backend supports URI {directory_uri!r}")
        return None
