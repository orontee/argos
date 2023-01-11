import logging
from typing import Optional, Tuple

from gi.repository import Gio, GObject

LOGGER = logging.getLogger(__name__)


class MopidyBackend(GObject.Object):

    name = GObject.Property(type=str)
    settings_key = GObject.Property(type=str)
    static_albums = GObject.Property(type=bool, default=True)
    preload_album_tracks = GObject.Property(type=bool, default=True)

    activated = GObject.Property(type=bool, default=False)
    # Default value is per inheriting class and defined in the
    # schema for application settings

    def __init__(
        self,
        settings: Gio.Settings,
        *,
        settings_key: str,
        **kwargs,
    ):
        super().__init__(settings_key=settings_key, **kwargs)

        self.props.activated = settings.get_value(self.props.settings_key)

        settings.connect(
            f"changed::{self.props.settings_key}", self._on_settings_changed
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        raise NotImplementedError

    def hides(self, ref_uri: str) -> bool:
        return False

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
        super().__init__(settings, name="Mopidy-Local", settings_key="mopidy-local")

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("local:")

    def hides(self, ref_uri: str) -> bool:
        if ref_uri == "local:directory?type=track":
            return True
        else:
            return False


class MopidyBandcampBackend(MopidyBackend):
    def __init__(
        self,
        settings: Gio.Settings,
    ):
        super().__init__(
            settings,
            name="Mopidy-Bandcamp",
            settings_key="mopidy-bandcamp",
            preload_album_tracks=False,
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("bandcamp:")

    def extract_artist_name(self, album_name: str) -> Tuple[str, str]:
        tokens = album_name.split(" - ", maxsplit=1)
        if len(tokens) == 2:
            return tokens[0], tokens[1]
        return "", album_name


class MopidyJellyfinBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(
            settings,
            name="Mopidy-Jellyfin",
            settings_key="mopidy-jellyfin",
            preload_album_tracks=False,
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("jellyfin:")


class MopidyPodcastBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(
            settings,
            name="Mopidy-Podcast",
            settings_key="mopidy-podcast",
            static_albums=False,
        )

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("podcast+")


class MopidyFileBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(settings, name="Mopidy-File", settings_key="mopidy-file")

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("file:")


class MopidySomaFMBackend(MopidyBackend):
    def __init__(self, settings: Gio.Settings):
        super().__init__(settings, name="Mopidy-SomaFM", settings_key="mopidy-somafm")

    def is_responsible_for(self, directory_uri: str) -> bool:
        return directory_uri.startswith("somafm:")
