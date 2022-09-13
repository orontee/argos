import logging
from typing import Optional

from gi.repository import Gio, GObject

LOGGER = logging.getLogger(__name__)


class MopidyBackend(GObject.Object):

    settings_key = GObject.Property(type=str)
    static_albums = GObject.Property(type=bool, default=True)
    activated = GObject.Property(type=bool, default=False)

    def __init__(
        self,
        settings: Gio.Settings,
        *,
        settings_key: str,
        static_albums: bool = True,
        activated: bool = False,
    ):
        super().__init__()

        self.props.settings_key = settings_key
        self.props.static_albums = static_albums
        self.activated = activated

        activated = settings.get_boolean(self.props.settings_key)
        self.props.activated = activated
        settings.connect(
            f"changed::{self.props.settings_key}", self._on_settings_changed
        )

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        raise NotImplementedError

    def _on_settings_changed(self, settings: Gio.Settings, key: str) -> None:
        assert self.props.settings_key == key
        activated = settings.get_boolean(key)
        self.props.activated = activated
        if activated:
            LOGGER.debug(f"Backend {self} activated")
        else:
            LOGGER.debug(f"Backend {self} deactivated")

    def __str__(self) -> str:
        return self.__class__.__name__


class MopidyLocalBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(settings, settings_key="mopidy-local", activated=True)

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "local:directory":
            return "local:directory?type=album"
        return None


class MopidyBandcampBackend(MopidyBackend):
    def __init__(
        self,
        settings: Gio.Settings,
    ):
        super().__init__(settings, settings_key="mopidy-bandcamp")

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "bandcamp:browse":
            return "bandcamp:collection"
        return None


class MopidyJellyfinBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(settings, settings_key="mopidy-jellyfin")

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri == "jellyfin:":
            return "jellyfin:albums"
        return None


class MopidyPodcastBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(
            settings,
            settings_key="mopidy-podcast",
            static_albums=False,
        )

    def get_albums_uri(self, directory_uri: Optional[str]) -> Optional[str]:
        if directory_uri and directory_uri.startswith("podcast+file://"):
            return directory_uri
        return None
