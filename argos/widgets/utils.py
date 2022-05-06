import logging
from pathlib import Path
from typing import Optional

from gi.repository import GdkPixbuf, GLib, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from ..utils import compute_target_size

LOGGER = logging.getLogger(__name__)


def default_album_image_pixbuf(target_width: int) -> Pixbuf:
    pixbuf = Gtk.IconTheme.get_default().load_icon(
        "media-optical-cd-audio-symbolic", target_width, 0
    )
    width, height = compute_target_size(
        pixbuf.get_width(),
        pixbuf.get_height(),
        target_width=target_width,
    )
    scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return scaled_pixbuf


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
