import logging
import unittest

from argos.model.utils import PlaybackState


class TestPlaybackState(unittest.TestCase):
    def test_from_string(self):
        state = PlaybackState.from_string("playing")
        self.assertEqual(state, PlaybackState.PLAYING)

        state = PlaybackState.from_string("paused")
        self.assertEqual(state, PlaybackState.PAUSED)

        state = PlaybackState.from_string("stopped")
        self.assertEqual(state, PlaybackState.STOPPED)

    def test_from_unexpected_string(self):
        with self.assertLogs("argos", level=logging.ERROR) as logs:
            state = PlaybackState.from_string("Playing")
        self.assertEqual(state, PlaybackState.UNKNOWN)
        self.assertEqual(
            logs.output, ["ERROR:argos.model.utils:Unexpected state 'Playing'"]
        )
