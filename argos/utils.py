import logging
from typing import Optional, Tuple, Union

LOGGER = logging.getLogger(__name__)

ELIDE_THRESHOLD = 29


def compute_target_size(width: int, height: int, *,
                        target_width: int) -> Union[Tuple[int, int],
                                                    Tuple[None, None]]:
    """Compute the image size according to given target width."""
    transpose = False
    if height > width:
        width, height = height, width
        transpose = True

    if width <= 0:
        return None, None

    width_scale = target_width / width
    target_height = round(height * width_scale)
    size = (target_width, target_height) if not transpose \
        else (target_height, target_width)
    LOGGER.debug(f"Resizing {(width, height)!r} to {size!r}")
    return size


def configure_logger(options: dict) -> None:
    """Configure logger."""
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    ch.setFormatter(formatter)
    level = logging.DEBUG if "debug" in options else logging.INFO
    ch.setLevel(level)
    logger = logging.getLogger("argos")
    logger.setLevel(level)
    logger.addHandler(ch)


def elide_maybe(text: str) -> str:
    """Ensure given text isn't longer than threshold."""
    if len(text) > ELIDE_THRESHOLD:
        return text[:ELIDE_THRESHOLD] + "…"
    return text


def ms_to_text(value: Optional[int] = None) -> str:
    "Convert a number of milliseconds to string."
    if not value:
        text = "--:--"
    else:
        second_count = round(value / 1000)
        minutes = second_count // 60
        seconds = second_count % 60
        text = f"{minutes}:{seconds:02d}"
    return text
