import json
import pathlib
import unittest
from unittest.mock import Mock, call

from argos.controllers.utils import call_by_slice


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent.parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestCallBySlice(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        class Counter:
            call_count = 0

            async def func(self, param):
                self.call_count += 1
                return dict([(p, self.call_count) for p in param])

        self.func = Counter().func

    async def test_call_by_slice(self):
        params = ["a", "b", "c", "d", "e", "f"]
        results = await call_by_slice(self.func, params=params)
        self.assertDictEqual(results, {"a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1})

    async def test_call_by_slice_one_by_one(self):
        params = ["a", "b", "c", "d", "e", "f"]
        results = await call_by_slice(self.func, params=params, call_size=1)
        self.assertDictEqual(results, {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6})

    async def test_call_by_slice_two_by_two(self):
        params = ["a", "b", "c", "d", "e", "f"]
        results = await call_by_slice(self.func, params=params, call_size=2)
        self.assertDictEqual(results, {"a": 1, "b": 1, "c": 2, "d": 2, "e": 3, "f": 3})

    async def test_call_by_slice_four_by_four(self):
        params = ["a", "b", "c", "d", "e", "f"]
        results = await call_by_slice(self.func, params=params, call_size=4)
        self.assertDictEqual(results, {"a": 1, "b": 1, "c": 1, "d": 1, "e": 2, "f": 2})

    async def test_call_by_slice_with_notifier(self):
        params = ["a", "b", "c", "d", "e", "f"]
        notifier = Mock()
        results = await call_by_slice(
            self.func, params=params, call_size=4, notifier=notifier
        )
        self.assertDictEqual(results, {"a": 1, "b": 1, "c": 1, "d": 1, "e": 2, "f": 2})
        notifier.assert_has_calls([call(4), call(6)])

    async def test_call_by_slice_with_none(self):
        class Counter:
            call_count = 0

            async def func(self, param):
                if "c" in param:
                    return None

                self.call_count += 1
                return dict([(p, self.call_count) for p in param])

        func = Counter().func
        params = ["a", "b", "c", "d", "e", "f"]
        results = await call_by_slice(func, params=params, call_size=3)
        self.assertDictEqual(results, {})

        results = await call_by_slice(func, params=params, call_size=2)
        self.assertDictEqual(results, {"a": 1, "b": 1})
