from gi.repository import GObject

from argos.model.utils import WithThreadSafePropertySetter


class MixerModel(WithThreadSafePropertySetter, GObject.Object):
    """Model gathering volume related properties.

    Setters are provided to change properties from any thread.

    """

    volume = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    mute = GObject.Property(type=bool, default=False)

    def set_volume(self, value: int) -> None:
        self.set_property_in_gtk_thread("volume", value)

    def set_mute(self, value: bool) -> None:
        self.set_property_in_gtk_thread("mute", value)
