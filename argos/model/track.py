from gi.repository import GObject


class TrackModel(GObject.Object):
    """Model for a track.

    All properties are read-only.

    """

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    track_no = GObject.Property(type=int)
    disc_no = GObject.Property(type=int)
    length = GObject.Property(type=int)
