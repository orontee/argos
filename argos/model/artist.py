import locale

from gi.repository import GObject


def compare_artist_by_name_func(
    a: "ArtistModel",
    b: "ArtistModel",
    user_data: None,
) -> int:
    names_comp = locale.strcoll(a.sortname, b.sortname)
    if names_comp != 0:
        return names_comp

    names_comp = locale.strcoll(a.name, b.name)
    if names_comp != 0:
        return names_comp

    if a.uri < b.uri:
        return -1
    elif a.uri > b.uri:
        return 1

    return 0


class ArtistInformationModel(GObject.Object):
    """Model for artist information."""

    abstract = GObject.Property(type=str)
    last_modified = GObject.Property(type=GObject.TYPE_DOUBLE, default=-1)


class ArtistModel(GObject.Object):
    """Model for an artist."""

    uri = GObject.Property(type=str)
    name = GObject.Property(type=str)
    sortname = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    image_uri = GObject.Property(type=str)
    artist_mbid = GObject.Property(type=str)
    information = GObject.Property(type=ArtistInformationModel)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.information = ArtistInformationModel()

    def is_complete(self) -> bool:
        return self.artist_mbid != ""
