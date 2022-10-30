import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional, cast

from argos.model import TrackModel

LOGGER = logging.getLogger(__name__)

_CALL_SIZE = 20


async def call_by_slice(
    func: Callable[[List[str]], Coroutine[Any, Any, Optional[Dict[str, Any]]]],
    *,
    params: List[str],
    call_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Make multiple synchronous calls.

    The argument ``params`` is split in slices of bounded
    length. There's one ``func`` call per slice.

    Args:
        func: Callable that will be called.

        params: List of parameters.

        call_size: Number of parameters to handle through each call.

    Returns:
        Dictionary merging all calls return values.

    """
    call_size = call_size if call_size is not None and call_size > 0 else _CALL_SIZE
    call_count = len(params) // call_size + (0 if len(params) % call_size == 0 else 1)
    result: Dict[str, Any] = {}
    for i in range(call_count):
        ith_result = await func(params[i * call_size : (i + 1) * call_size])
        if ith_result is None:
            break
        result.update(ith_result)
    return result


def parse_tracks(
    tracks: Dict[str, List[Dict[str, Any]]],
    *,
    visitors: Optional[List[Callable[[str, Dict[str, Any]], None]]] = None,
) -> Dict[str, List[TrackModel]]:
    """Parse a track list.

    Args:
        tracks: Track descriptions to parse. It's expected to be the
            result of a call to Mopidy's ``core.library.lookup``
            action.

        visitors: An optional list of callable to be called on each
            visited track.

    Returns:
        Dict of list of ``TrackModel``.

    """
    parsed_tracks: Dict[str, List[TrackModel]] = defaultdict(list)
    for uri in tracks:
        uri_tracks = tracks[uri]
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

            if visitors is not None:
                for visitor in visitors:
                    visitor(uri, t)

            parsed_tracks[uri].append(
                TrackModel(
                    uri=cast(str, t.get("uri", "")),
                    name=cast(str, t.get("name", "")),
                    track_no=cast(int, t.get("track_no", -1)),
                    disc_no=cast(int, t.get("disc_no", 1)),
                    length=t.get("length", -1),
                    album_name=album_name,
                    artist_name=artist_name,
                    last_modified=t.get("last_modified", -1),
                )
            )
    return parsed_tracks
