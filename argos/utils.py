import datetime
import gettext
import logging
from typing import Tuple, Union

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ELIDE_THRESHOLD = 29


def compute_target_size(
    width: int, height: int, *, max_size: int
) -> Union[Tuple[int, int], Tuple[None, None]]:
    """Compute the image size according to given max size."""
    transpose = False
    if height > width:
        width, height = height, width
        transpose = True

    if max_size <= 0 or width <= 0 or height <= 0:
        return None, None

    width_scale = max_size / width
    target_height = round(height * width_scale)
    size = (max_size, target_height) if not transpose else (target_height, max_size)
    return size


def configure_logger(level: int = logging.INFO) -> None:
    """Configure logger."""
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "{asctime} {threadName} {levelname}: {name} - {message}", style="{"
    )
    ch.setFormatter(formatter)
    ch.setLevel(level)
    logger = logging.getLogger("argos")
    logger.setLevel(level)
    logger.addHandler(ch)

    logger = logging.getLogger("argos.time")
    logger.setLevel(logging.INFO)


def elide_maybe(text: str) -> str:
    """Ensure given text isn't longer than threshold."""
    if len(text) > ELIDE_THRESHOLD:
        return text[:ELIDE_THRESHOLD] + "…"
    return text


def ms_to_text(value: int) -> str:
    """Convert a number of milliseconds to string.

    By convention the value -1 is interpreted as unknown number of
    milliseconds.

    """
    if value == -1:
        text = "--:--"
    else:
        second_count = round(value / 1000)
        minutes = second_count // 60
        seconds = second_count % 60

        if minutes > 60:
            hours = minutes // 60
            minutes = minutes % 60
            text = f"{hours}:{minutes:02d}:{seconds:02d}"
            if hours > 24:
                text = _("More than one day")
        else:
            text = f"{minutes:02d}:{seconds:02d}"
    return text


def date_to_string(d: datetime.datetime) -> str:
    """Convert a datetime to string."""
    date = d.date()
    if date == datetime.date.today():
        return _("Today")
    if (datetime.date.today() - date).days == 1:
        return _("Yesterday")

    return d.date().strftime("%x")
