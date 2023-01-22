import locale

from gi.repository import GObject


def compare_tracks_by_name_func(
    a: "TrackModel",
    b: "TrackModel",
    user_data: None,
) -> int:
    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    artist_names_comp = locale.strcoll(a.artist_name, b.artist_name)
    if artist_names_comp != 0:
        return artist_names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


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
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)
