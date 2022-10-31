import datetime
import gettext
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from gi.repository import GdkPixbuf, GLib, Gtk
from gi.repository.GdkPixbuf import Pixbuf

from argos.utils import compute_target_size

LOGGER = logging.getLogger(__name__)

_ = gettext.gettext


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


def set_list_box_header_with_album_separator(
    row: Gtk.ListBoxRow,
    before: Gtk.ListBoxRow,
) -> None:
    current_header = row.get_header()
    if current_header:
        return

    track_box = row.get_child()
    disc_no = track_box.props.disc_no
    num_discs = track_box.props.num_discs
    track_no = track_box.props.track_no

    if num_discs > 1 and track_no == 1:
        pretty_disc_no = _("Disc {0}").format(disc_no)
        markup = f"""<span style="italic">{pretty_disc_no}</span>"""
        label = Gtk.Label()
        label.set_use_markup(True)
        label.set_markup(markup)
        label.show()
        row.set_header(label)
        return

    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.show()
    row.set_header(separator)


def set_list_box_header_with_date_separator(
    row: Gtk.ListBoxRow,
    before: Gtk.ListBoxRow,
) -> None:
    current_header = row.get_header()
    if current_header:
        return

    track_box = row.get_child()
    last_played = (
        track_box.props.last_played if track_box.props.last_played != -1 else None
    )
    last_played_date = (
        datetime.datetime.fromtimestamp(last_played / 1000)
        if last_played is not None
        else None
    )

    if before is not None:
        previous_track_box = before.get_child()
        if previous_track_box is not None:
            previous_last_played = (
                previous_track_box.props.last_played
                if previous_track_box.props.last_played != -1
                else None
            )
        previous_last_played_date = (
            datetime.datetime.fromtimestamp(previous_last_played / 1000)
            if previous_last_played is not None
            else None
        )
    else:
        previous_last_played_date = None

    if last_played_date is not None:
        if previous_last_played_date is None:
            day_changed = True
        else:
            day_changed = (
                (last_played_date.year != previous_last_played_date.year)
                or (last_played_date.month != previous_last_played_date.month)
                or (last_played_date.day != previous_last_played_date.day)
            )

        if day_changed:
            pretty_last_played_date = last_played_date.date().strftime("%x")
            markup = f"""<span style="italic">{pretty_last_played_date}</span>"""

            label = Gtk.Label()
            label.set_use_markup(True)
            label.set_markup(markup)
            label.show()
            row.set_header(label)
            return

    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.show()
    row.set_header(separator)
