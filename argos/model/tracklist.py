from typing import Optional

from gi.repository import Gio, GObject

from argos.model.track import TrackModel
from argos.model.utils import WithThreadSafePropertySetter


class TracklistTrackModel(GObject.Object):
    """Model for a track in the tracklist."""

    tlid = GObject.Property(type=int)
    track = GObject.Property(type=TrackModel)


class TracklistModel(WithThreadSafePropertySetter, GObject.Object):
    """Model for the tracklist.

    The tracklist model stores the queue of track to play and the way
    it has to be played (consume tracks, random order, etc).

    Setters are provided to change properties from any thread.

    """

    consume = GObject.Property(type=bool, default=False)
    random = GObject.Property(type=bool, default=False)
    repeat = GObject.Property(type=bool, default=False)
    single = GObject.Property(type=bool, default=False)
    version = GObject.Property(type=int, default=-1)

    tracks: Gio.ListStore

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracks = Gio.ListStore.new(TracklistTrackModel)

    def set_consume(self, value: bool) -> None:
        self.set_property_in_gtk_thread("consume", value)

    def set_random(self, value: bool) -> None:
        self.set_property_in_gtk_thread("random", value)

    def set_repeat(self, value: bool) -> None:
        self.set_property_in_gtk_thread("repeat", value)

    def set_single(self, value: bool) -> None:
        self.set_property_in_gtk_thread("single", value)

    def set_version(self, value: int) -> None:
        self.set_property_in_gtk_thread("version", value)

    def get_tl_track(self, tlid: int) -> Optional[TracklistTrackModel]:
        for i in range(self.tracks.get_n_items()):
            tl_track = self.tracks.get_item(i)
            if tl_track.tlid == tlid:
                return tl_track

        return None
