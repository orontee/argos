import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Mapping, Optional, Sequence

from argos.dto import TrackDTO
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
    tracks_dto: Mapping[str, Sequence[TrackDTO]],
    *,
    visitors: Optional[Sequence[Callable[[str, TrackDTO], None]]] = None,
) -> Dict[str, List[TrackModel]]:
    """Parse a track list.

    Args:
        tracks_dto: Track data transfer objects to parse.

        visitors: An optional list of callable to be called on each
            visited track.

    Returns:
        Dict of list of ``TrackModel``.

    """
    parsed_tracks: Dict[str, List[TrackModel]] = defaultdict(list)
    for uri in tracks_dto:
        for track_dto in tracks_dto[uri]:
            if visitors is not None:
                for visitor in visitors:
                    visitor(uri, track_dto)

            parsed_tracks[uri].append(TrackModel.factory(track_dto))

    return parsed_tracks
