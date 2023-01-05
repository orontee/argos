import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, List, Optional, Protocol, Sequence, Type, TypeVar

LOGGER = logging.getLogger(__name__)


class RefType(Enum):
    ALBUM = "album"
    ARTIST = "artist"
    DIRECTORY = "directory"
    PLAYLIST = "playlist"
    TRACK = "track"


T = TypeVar(
    "T",
    "RefDTO",
    "ArtistDTO",
    "AlbumDTO",
    "TrackDTO",
    "ImageDTO",
    "PlaylistDTO",
    "TlTrackDTO",
)


def cast_seq_of(klass: Type[T], data: Any) -> List[T]:
    objects: List[T] = []
    try:
        for d in data:
            obj = klass.factory(d)  # noqa
            if obj is None:
                LOGGER.warning(f"Failed to build {klass!r} from {d!r}")
                continue

            objects.append(obj)
    except TypeError:
        return []

    return objects


@dataclass(frozen=True)
class RefDTO:
    """Data transfer object to represent URI references.

    See
    https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Ref.
    """

    type: RefType
    uri: str
    name: str

    @staticmethod
    def factory(data: Any) -> Optional["RefDTO"]:
        if data is None:
            return None

        try:
            type = RefType(data.get("type"))
        except ValueError:
            type = None
        uri = data.get("uri")
        name = data.get("name")

        if type is None or uri is None or name is None:
            return None

        return RefDTO(type, uri, name)


@dataclass(frozen=True)
class ArtistDTO:
    """Data transfer object to represent an artist.

    https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Artist
    """

    uri: str
    name: str
    shortname: str
    musicbrainz_id: str

    @staticmethod
    def factory(data: Any) -> Optional["ArtistDTO"]:
        if data is None:
            return None

        uri = data.get("uri", "")
        # it was observed that some podcasts don't have a URI for their artists
        name = data.get("name", "")
        # it was observed that somafm tracks may not have a name for their artists
        if uri is None or name is None:
            return None

        shortname = data.get("shortname", "")
        musicbrainz_id = data.get("musicbrainz_id", "")

        return ArtistDTO(uri, name, shortname, musicbrainz_id)


@dataclass(frozen=True)
class AlbumDTO:
    """Data transfer object to represent an album.

    See https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Album

    """

    uri: str
    name: str
    date: str
    musicbrainz_id: str
    num_tracks: Optional[int]
    num_discs: Optional[int]
    artists: List[ArtistDTO] = field(default_factory=list)

    @staticmethod
    def factory(data: Any) -> Optional["AlbumDTO"]:
        if data is None:
            return None

        uri = data.get("uri", "")
        # it was observed that some somafm tracks don't have a URI for their album
        name = data.get("name")
        if uri is None or name is None:
            return None

        musicbrainz_id = data.get("musicbrainz_id", "")
        date = data.get("date", "")
        num_tracks = data.get("num_tracks")
        num_discs = data.get("num_discs")

        dto = AlbumDTO(
            uri,
            name,
            date,
            musicbrainz_id,
            num_tracks=num_tracks,
            num_discs=num_discs,
        )

        for artist_data in data.get("artists", []):
            artist_dto = ArtistDTO.factory(artist_data)
            if artist_dto is None:
                return None

            dto.artists.append(artist_dto)

        return dto


@dataclass
class TrackDTO:
    """Data transfer object to represent a track.

    See https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Track

    """

    uri: str
    name: str
    album: Optional[AlbumDTO]
    genre: str
    date: str
    bitrate: int
    comment: str
    musicbrainz_id: str
    track_no: Optional[int]
    disc_no: Optional[int]
    length: Optional[int]
    last_modified: Optional[int]
    artists: List[ArtistDTO] = field(default_factory=list)
    composers: List[ArtistDTO] = field(default_factory=list)
    performers: List[ArtistDTO] = field(default_factory=list)

    @staticmethod
    def factory(data: Any) -> Optional["TrackDTO"]:
        if data is None:
            return None

        uri = data.get("uri")
        name = data.get("name", "")

        if uri is None or name is None:
            return None

        album = AlbumDTO.factory(data.get("album"))
        genre = data.get("genre", "")
        date = data.get("date", "")
        bitrate = data.get("bitrate", -1)
        comment = data.get("comment", "")
        musicbrainz_id = data.get("musicbrainz_id", "")
        track_no = data.get("track_no")
        disc_no = data.get("disc_no")
        length = data.get("length")
        last_modified = data.get("last_modified")

        dto = TrackDTO(
            uri,
            name,
            album,
            genre,
            date,
            bitrate,
            comment,
            musicbrainz_id,
            track_no=track_no,
            disc_no=disc_no,
            length=length,
            last_modified=last_modified,
        )

        for artist_data in data.get("artists", []):
            artist_dto = ArtistDTO.factory(artist_data)
            if artist_dto is None:
                return None

            dto.artists.append(artist_dto)

        for composer_data in data.get("composers", []):
            composer_dto = ArtistDTO.factory(composer_data)
            if composer_dto is None:
                return None

            dto.composers.append(composer_dto)

        for performer_data in data.get("performers", []):
            performer_dto = ArtistDTO.factory(performer_data)
            if performer_dto is None:
                return None

            dto.performers.append(performer_dto)

        return dto


@dataclass(frozen=True)
class PlaylistDTO:
    """Data transfer object to represent a playlist.

    https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Playlist
    """

    uri: str
    name: str
    last_modified: int

    tracks: List[TrackDTO] = field(default_factory=list)

    @staticmethod
    def factory(data: Any) -> Optional["PlaylistDTO"]:
        if data is None:
            return None

        uri = data.get("uri")
        name = data.get("name")
        last_modified = data.get("last_modified")
        if uri is None or name is None or last_modified is None:
            return None

        dto = PlaylistDTO(uri, name, last_modified)
        for track_data in data.get("tracks", []):
            track_dto = TrackDTO.factory(track_data)
            if track_dto is None:
                return None

            dto.tracks.append(track_dto)

        return dto


@dataclass(frozen=True)
class ImageDTO:
    """Data transfer object to represent an image.

    See https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Image
    """

    uri: str
    width: Optional[int]
    height: Optional[int]

    @staticmethod
    def factory(data: Any) -> Optional["ImageDTO"]:
        if data is None:
            return None

        uri = data.get("uri")
        if uri is None:
            return None

        width = data.get("width")
        height = data.get("height")

        return ImageDTO(uri, width, height)


@dataclass(frozen=True)
class TlTrackDTO:
    """Data transfer object to represent a tracklist track.

    See https://docs.mopidy.com/en/latest/api/models/#mopidy.models.TlTrack
    """

    tlid: int
    track: TrackDTO

    @staticmethod
    def factory(data: Any) -> Optional["TlTrackDTO"]:
        if data is None:
            return None

        tlid = data.get("tlid")
        track = TrackDTO.factory(data.get("track"))

        if tlid is None or track is None:
            return None

        return TlTrackDTO(tlid, track)
