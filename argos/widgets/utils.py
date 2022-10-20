import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from gi.repository import GdkPixbuf, GLib, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from argos.utils import compute_target_size

LOGGER = logging.getLogger(__name__)


def default_image_pixbuf(icon_name: str, target_width: int) -> Pixbuf:
    pixbuf = Gtk.IconTheme.get_default().load_icon(icon_name, target_width, 0)
    original_width, original_height = pixbuf.get_width(), pixbuf.get_height()
    width, height = compute_target_size(
        original_width,
        original_height,
        target_width=target_width,
    )
    if (original_width, original_height) == (width, height):
        return pixbuf

    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


@lru_cache
def scale_album_image(image_path: Path, *, target_width: int) -> Optional[Pixbuf]:
    pixbuf = None
    try:
        pixbuf = Pixbuf.new_from_file(str(image_path))
    except GLib.Error as error:
        LOGGER.warning(f"Failed to read image at {str(image_path)!r}: {error}")

    if pixbuf is None:
        return None

    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=target_width,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


def set_list_box_header_with_separator(
    row: Gtk.ListBoxRow,
    before: Gtk.ListBoxRow,
) -> None:
    current_header = row.get_header()
    if current_header:
        return

    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.show()
    row.set_header(separator)
