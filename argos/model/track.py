from gi.repository import GObject


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
