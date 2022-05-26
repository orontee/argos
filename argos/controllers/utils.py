import logging
from typing import cast, Any, Callable, Dict, List, Optional

from ..model import TrackModel

LOGGER = logging.getLogger(__name__)


def parse_tracks(
    tracks: Dict[str, List[Dict[str, Any]]],
    *,
    visitor: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[TrackModel]:
    """Parse a track list.

    Args:
        tracks: Track descriptions to parse. It's expected to be the
            result of a call to Mopidy's ``core.library.lookup``
            action.

        visitor: An optional callable to be called on each visited
            track.

    Returns:
        List of ``TrackModel``.

    """
    parsed_tracks: List[TrackModel] = []
    for track_uri in tracks:
        uri_tracks = tracks[track_uri]
        for t in uri_tracks:
            assert "__model__" in t and t["__model__"] == "Track"

            album: Optional[Dict[str, Dict[str, str]]] = t.get("album")
            if album is not None:
                assert "__model__" in album and album["__model__"] == "Album"
                album_name = album.get("name", "")
            else:
                album_name = ""

            artists: Optional[List[Dict[str, str]]] = t.get("artists")
            if artists and len(artists) > 0:
                assert "__model__" in artists[0] and artists[0]["__model__"] == "Artist"
                artist_name = artists[0].get("name", "")
            else:
                artist_name = ""

            if visitor is not None:
                visitor(t)

            parsed_tracks.append(
                TrackModel(
                    uri=cast(str, t.get("uri", "")),
                    name=cast(str, t.get("name", "")),
                    track_no=cast(int, t.get("track_no", -1)),
                    disc_no=cast(int, t.get("disc_no", 1)),
                    length=t.get("length", -1),
                    album_name=album_name,
                    artist_name=artist_name,
                )
            )
    return parsed_tracks
