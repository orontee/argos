from gi.repository import GObject

from argos.dto import TrackDTO


class TrackModel(GObject.Object):
    """Model for a track.

    Most properties are read-only.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    track_no = GObject.Property(type=int)
    disc_no = GObject.Property(type=int)
    length = GObject.Property(type=int)
    album_name = GObject.Property(type=str)
    artist_name = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)
    last_played = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)

    @staticmethod
    def factory(dto: TrackDTO) -> "TrackModel":
        track = TrackModel(
            uri=dto.uri,
            name=dto.name,
            track_no=dto.track_no if dto.track_no is not None else -1,
            disc_no=dto.disc_no if dto.disc_no is not None else 1,
            length=dto.length if dto.length is not None else -1,
            artist_name=dto.artists[0].name if len(dto.artists) > 0 else "",
            album_name=dto.album.name if dto.album is not None else "",
            last_modified=dto.last_modified if dto.last_modified is not None else -1,
        )
        return track
