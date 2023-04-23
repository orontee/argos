import datetime
import locale
import unittest

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


class TestComputeTargetSize(unittest.TestCase):
    def test_normal_cases(self):
        self.assertEqual(compute_target_size(200, 100, max_size=50), (50, 25))
        self.assertEqual(compute_target_size(100, 200, max_size=50), (25, 50))

    def test_corner_cases(self):
        self.assertEqual(compute_target_size(-200, 100, max_size=50), (None, None))
        self.assertEqual(compute_target_size(200, -100, max_size=50), (None, None))
        self.assertEqual(compute_target_size(200, 100, max_size=0), (None, None))
        self.assertEqual(compute_target_size(0, 100, max_size=50), (None, None))
        self.assertEqual(compute_target_size(200, 100, max_size=-50), (None, None))


class TestElideMaybe(unittest.TestCase):
    def test_short_string(self):
        self.assertEqual(elide_maybe("test"), "test")

    def test_long_string(self):
        long_string = "Test elide of a long string just to be sure "
        elided_long_string = elide_maybe(long_string)
        self.assertLess(len(elided_long_string), len(long_string))
        self.assertEqual(elided_long_string[-1], "…")
        self.assertTrue(long_string.startswith(elided_long_string[:-1]))


class TestDateToString(unittest.TestCase):
    def test_numeric_date(self):
        date = datetime.datetime.fromisoformat("2023-01-30")
        with LocaleManager("C"):
            self.assertEqual(date_to_string(date), "01/30/23")

    def test_today_and_yesterday(self):
        now = datetime.datetime.now()
        one_day = datetime.timedelta(days=1)
        self.assertEqual(date_to_string(now), "Today")
        self.assertEqual(date_to_string(now - one_day), "Yesterday")

    @unittest.skipIf(
        unknown_locale("fr_FR.UTF-8"), reason="French locale must be installed on host"
    )
    def test_numeric_date_with_locale(self):
        date = datetime.datetime.fromisoformat("2023-01-30")
        with LocaleManager("fr_FR.UTF-8"):
            self.assertEqual(date_to_string(date), "30/01/2023")


class TestMsToText(unittest.TestCase):
    def test_ms_to_text(self):
        self.assertEqual(ms_to_text(-1), "--:--")
        self.assertEqual(ms_to_text(1000), "00:01")
        self.assertEqual(ms_to_text(61 * 1000), "01:01")
        self.assertEqual(ms_to_text(70 * 60 * 1000), "1:10:00")
        self.assertEqual(ms_to_text(24 * 60 * 60 * 1000), "More than one day")
