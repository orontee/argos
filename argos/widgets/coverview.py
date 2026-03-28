import logging

import cairo
from gi.repository import Gdk, GLib, GObject, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from argos.widgets.utils import default_image_pixbuf

LOGGER = logging.getLogger(__name__)

_MIN_SIZE = 200


class CoverView(Gtk.DrawingArea):
    """Widget rendering an album or track cover.

    The displayed pixbuf rescales while the widget size changes."""

    __gtype_name__ = "CoverView"

    default_pixbuf: Pixbuf
    pixbuf: Pixbuf | None
    _image_surface: cairo.Surface | None

    def __init__(self, default_pixbuf: Pixbuf, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_pixbuf = default_pixbuf
        self.pixbuf = None
        self._image_surface = None

        self.set_size_request(_MIN_SIZE, _MIN_SIZE)
        self.set_visible(True)
        self.set_can_focus(False)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.props.halign = Gtk.Align.CENTER
        self.props.valign = Gtk.Align.CENTER

        self.connect("draw", self.on_draw)

    def set_from_pixbuf(self, pixbuf: Pixbuf | None) -> None:
        self.pixbuf = pixbuf
        self._image_surface = None

        if self.pixbuf is not None:
            self.props.halign = Gtk.Align.FILL
            self.props.valign = Gtk.Align.FILL
        else:
            self.props.halign = Gtk.Align.CENTER
            self.props.valign = Gtk.Align.CENTER

        self.queue_draw()

    def _get_scale_factor(self) -> float:
        assert self.pixbuf is not None
        return min(
            self.get_allocated_width() / self.pixbuf.get_width(),
            self.get_allocated_height() / self.pixbuf.get_height(),
        )

    def on_draw(self, _1: Gtk.Widget, context: cairo.Context):
        if self._image_surface is None:
            self._image_surface = Gdk.cairo_surface_create_from_pixbuf(
                self.pixbuf or self.default_pixbuf, 1, None
            )

        if self.pixbuf is not None:
            scale = min(self._get_scale_factor(), 1)
            pos_x = (self.get_allocated_width() - self.pixbuf.get_width() * scale) / 2
            pos_y = (self.get_allocated_height() - self.pixbuf.get_height() * scale) / 2
            context.scale(scale, scale)
            context.set_source_surface(
                self._image_surface, pos_x / scale, pos_y / scale
            )
            context.paint()
        else:
            pos_x = (self.get_allocated_width() - self.default_pixbuf.get_width()) / 2
            pos_y = (self.get_allocated_height() - self.default_pixbuf.get_height()) / 2
            context.set_source_surface(self._image_surface, pos_x, pos_y)
            context.paint()
