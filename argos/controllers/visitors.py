import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, cast

LOGGER = logging.getLogger(__name__)


class LengthAcc:
    """Visitor accumulating track length by album.

    See ``argos.utils.parse_tracks()``.

    """

    def __init__(self):
        self.length: Dict[str, int] = defaultdict(int)

    def __call__(self, album_uri: str, track: Dict[str, Any]) -> None:
        if self.length[album_uri] != -1 and "length" in track:
            self.length[album_uri] += int(track["length"])
        else:
            self.length[album_uri] = -1


class AlbumArtistNameIdentifier:
    """Visitor identifying each album artist name.

    See ``argos.utils.parse_tracks()``.

    """

    def __init__(self):
        self._names: Dict[str, str] = {}

    def __call__(self, uri: str, track: Dict[str, Any]) -> None:
        if uri in self._names:
            return

        album: Optional[Dict[str, Dict[str, Any]]] = track.get("album")
        if album is not None:
            album_artists = cast(List[Dict[str, str]], album.get("artists", []))
            if len(album_artists) > 0:
                self._names[uri] = album_artists[0].get("name", "")

    def artist_name(self, album_uri: str) -> str:
        return self._names.get(album_uri, "")
