import datetime
import locale

import pytest

from argos.utils import compute_target_size, date_to_string, elide_maybe, ms_to_text


class LocaleManager:
    def __init__(self, localename):
        self.name = localename

    def __enter__(self):
        self.orig = locale.setlocale(locale.LC_CTYPE)
        locale.setlocale(locale.LC_ALL, self.name)

    def __exit__(self, exc_type, exc_value, traceback):
        locale.setlocale(locale.LC_ALL, self.orig)


def unknown_locale(to_check: str):
    try:
        with LocaleManager(to_check):
            return False
    except locale.Error:
        return True


def test_compute_target_size():
    assert compute_target_size(200, 100, max_size=50) == (50, 25)
    assert compute_target_size(100, 200, max_size=50) == (25, 50)
    assert compute_target_size(-200, 100, max_size=50) == (None, None)
    assert compute_target_size(200, -100, max_size=50) == (None, None)
    assert compute_target_size(200, 100, max_size=0) == (None, None)
    assert compute_target_size(0, 100, max_size=50) == (None, None)
    assert compute_target_size(200, 100, max_size=-50) == (None, None)


def test_elide_maybe():
    assert elide_maybe("test") == "test", "a short string shouldn't be elided"

    long_string = "Test elide of a long string just to be sure "
    elided_long_string = elide_maybe(long_string)
    assert len(elided_long_string) < len(long_string), "a long string should be elided"

    assert (
        elided_long_string[-1] == "…"
    ), "elided string must end with horizontal ellipsis"
    assert long_string.startswith(
        elided_long_string[:-1]
    ), "string almost starts with elided string"


def test_date_to_string():
    now = datetime.datetime.now()
    one_day = datetime.timedelta(days=1)

    assert date_to_string(now) == "Today", "today date string shouldn't be numeric"
    assert (
        date_to_string(now - one_day) == "Yesterday"
    ), "yesterday date string shouldn't be numeric"

    date = datetime.datetime.fromisoformat("2023-01-30")
    with LocaleManager("C"):
        assert date_to_string(date) == "01/30/23"


@pytest.mark.skipif(
    unknown_locale("fr_FR.UTF-8"), reason="French locale must be installed on host"
)
def test_date_to_string_with_locale():
    date = datetime.datetime.fromisoformat("2023-01-30")
    with LocaleManager("fr_FR.UTF-8"):
        assert (
            date_to_string(date) == "30/01/2023"
        ), "date string depends on application locale"


def test_ms_to_text():
    assert ms_to_text(-1) == "--:--"
    assert ms_to_text(1000) == "00:01"
    assert ms_to_text(61 * 1000) == "01:01"
    assert ms_to_text(70 * 60 * 1000) == "1:10:00"
    assert ms_to_text(24 * 60 * 60 * 1000) == "More than one day"
