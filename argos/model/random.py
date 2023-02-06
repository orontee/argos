import gettext
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from argos.model.album import AlbumModel
from argos.model.directory import DirectoryModel
from argos.model.library import LibraryModel
from argos.model.track import TrackModel

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)


RANDOM_TRACKS_CHOICE_STRATEGY = {
    "random_album_tracks": _("Random album"),
    "random_disc_tracks": _("Random disc"),
}


class RandomTracksChoiceState(Enum):
    INIT = 0
    FOUND = 1
    EMPTY_LIBRARY = 2
    FAILED = 3


@dataclass
class RandomTracksChoice:
    strategy: str
    state: RandomTracksChoiceState = field(default=RandomTracksChoiceState.INIT)
    track_uris: List[str] = field(default_factory=list)
    source_album_uri: str = field(default="")
    source_album_disc_no: Optional[int] = field(default=None)


def choose_random_tracks(
    library: LibraryModel,
    strategy: str,
) -> RandomTracksChoice:
    result = RandomTracksChoice(strategy)
    if strategy in ("random_album_tracks", "random_disc_tracks"):
        _select_random_album_tracks(library, result)
    else:
        LOGGER.debug(f"Random choice strategy {strategy!r} not implemented")
        result.state = RandomTracksChoiceState.FAILED

    return result


def _select_random_album_tracks(library: LibraryModel, result: RandomTracksChoice):

    candidates: List[str] = []

    def visitor(a: AlbumModel, d: DirectoryModel) -> None:
        if not a.props.backend.props.exclude_albums_from_random_choice and (
            result.strategy != "random_disc_tracks" or a.num_discs > 0
        ):
            candidates.append(a.uri)

    library.visit_albums(visitor=visitor)
    if len(candidates) == 0:
        result.state = RandomTracksChoiceState.EMPTY_LIBRARY
        LOGGER.warning("No album candidates for random selection!")
        return

    try:
        result.source_album_uri = random.choice(candidates)
    except IndexError:
        result.state = RandomTracksChoiceState.FAILED
        LOGGER.warning("Failed to randomly choose tracks!!")
    else:
        album = library.get_album(result.source_album_uri)
        if album is None:
            result.state = RandomTracksChoiceState.FAILED
        elif result.strategy == "random_album_tracks":
            result.track_uris = [t.uri for t in album.tracks]
            result.state = RandomTracksChoiceState.FOUND
        elif result.strategy == "random_disc_tracks":
            result.source_album_disc_no = random.randrange(1, album.num_discs + 1)
            # guaranteed to be >0 through exclusion predicate

            LOGGER.debug(
                f"Will select tracks from disc number {result.source_album_disc_no}"
            )

            result.track_uris = [
                t.uri for t in album.tracks if t.disc_no == result.source_album_disc_no
            ]
            result.state = RandomTracksChoiceState.FOUND
