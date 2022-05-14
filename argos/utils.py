import logging
from typing import Tuple, Union

LOGGER = logging.getLogger(__name__)

ELIDE_THRESHOLD = 29


def compute_target_size(
    width: int, height: int, *, target_width: int
) -> Union[Tuple[int, int], Tuple[None, None]]:
    """Compute the image size according to given target width."""
    transpose = False
    if height > width:
        width, height = height, width
        transpose = True

    if width <= 0:
        return None, None

    width_scale = target_width / width
    target_height = round(height * width_scale)
    size = (
        (target_width, target_height)
        if not transpose
        else (target_height, target_width)
    )
    return size


def configure_logger(options: dict) -> None:
    """Configure logger."""
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s thread-%(thread)d %(levelname)s: %(name)s - %(message)s"
    )
    ch.setFormatter(formatter)
    level = logging.DEBUG if "debug" in options else logging.INFO
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
        else:
            text = f"{minutes:02d}:{seconds:02d}"
    return text
