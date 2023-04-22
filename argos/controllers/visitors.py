import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from argos.dto import PlaylistDTO, TrackDTO

LOGGER = logging.getLogger(__name__)


class LengthAcc:
    """Visitor accumulating track length by uri.

    See ``argos.utils.parse_tracks()``.

    """

    def __init__(self):
        self.length: Dict[str, int] = defaultdict(int)

    def __call__(self, uri: str, track_dto: TrackDTO) -> None:
        if self.length[uri] != -1 and track_dto.length is not None:
            self.length[uri] += track_dto.length
        else:
            self.length[uri] = -1


class AlbumMetadataCollector:
    """Visitor identifying album metadatas.

    The identified metadata are: The album artist name, the number of
    tracks, the number of discs and the publication date.

    The album artist name is defined to be the name of the first
    artist in the ``artists`` property of an album; If not defined,
    the names of the artists of the album tracks are collected and the
    most common name is returned.

    See ``argos.utils.parse_tracks()``."""

    def __init__(self):
        self._name: Dict[str, str] = {}
        self._track_names: Dict[str, List[str]] = defaultdict(list)
        self._num_tracks: Dict[str, int] = {}
        self._num_discs: Dict[str, int] = {}
        self._date: Dict[str, str] = {}
        self._last_modified: Dict[str, float] = {}
        self._release_mbid: Dict[str, str] = {}

    def __call__(self, uri: str, track_dto: TrackDTO) -> None:
        album_dto = track_dto.album
        if album_dto is None:
            return

        if uri not in self._name:
            if len(album_dto.artists) > 0:
                self._name[uri] = album_dto.artists[0].name
            else:
                self._track_names[uri] += [a.name for a in track_dto.artists]

        if uri not in self._num_tracks:
            if album_dto.num_tracks is not None:
                self._num_tracks[uri] = album_dto.num_tracks

        if uri not in self._num_discs:
            if album_dto.num_discs is not None:
                self._num_discs[uri] = album_dto.num_discs

        if uri not in self._date:
            if album_dto.date is not None:
                self._date[uri] = album_dto.date

        if uri not in self._release_mbid:
            if album_dto.musicbrainz_id is not None:
                self._release_mbid[uri] = album_dto.musicbrainz_id

        if track_dto.last_modified is not None:
            current_last_modified = self._last_modified.get(uri, None)
            if current_last_modified is None:
                self._last_modified[uri] = track_dto.last_modified
            else:
                self._last_modified[uri] = max(
                    track_dto.last_modified, current_last_modified
                )

    def artist_name(self, album_uri: str) -> str:
        if album_uri in self._name:
            return self._name.get(album_uri, "")

        count = Counter(self._track_names[album_uri])
        ranking = count.most_common(1)
        return ranking[0][0] if len(ranking) > 0 else ""

    def num_tracks(self, album_uri: str) -> Optional[int]:
        return self._num_tracks.get(album_uri)

    def num_discs(self, album_uri: str) -> Optional[int]:
        return self._num_discs.get(album_uri)

    def date(self, album_uri: str) -> Optional[str]:
        return self._date.get(album_uri)

    def release_mbid(self, album_uri: str) -> Optional[str]:
        return self._release_mbid.get(album_uri)

    def last_modified(self, album_uri: str) -> Optional[float]:
        return self._last_modified.get(album_uri)


class PlaylistTrackNameFix:
    """Visitor fixing name of playlist tracks.

    Some playlist specify track names, this visitor ensures that names
    specified in playlists are used.

    """

    def __init__(self, playlist: PlaylistDTO):
        self._names: Dict[str, str] = dict()
        self.__index_playlist_track_names(playlist)

    def __index_playlist_track_names(self, playlist: PlaylistDTO) -> None:
        for track_dto in playlist.tracks:
            if not track_dto.name:
                continue

            self._names[track_dto.uri] = track_dto.name

    def __call__(self, uri: str, track_dto: TrackDTO) -> None:
        name = self._names.get(uri, None)
        if name is None:
            return

        track_dto.name = name
