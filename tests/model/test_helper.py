import json
import pathlib
import unittest
from unittest.mock import Mock

from argos.dto import TrackDTO
from argos.model.helper import ModelHelper
from argos.model.track import TrackModel


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent.parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestModelHelper(unittest.TestCase):
    def test_parse_tracks(self):
        track_dto = TrackDTO.factory(load_json_data("track.json"))
        tracks_dto = {"local:album:md5:ff5c5b8f60a44e4c7d6f1bb53474e17b": [track_dto]}
        tracks = ModelHelper().parse_tracks(tracks_dto)
        self.assertListEqual([k for k in tracks_dto.keys()], [k for k in tracks.keys()])
        self.assertIsInstance(
            tracks["local:album:md5:ff5c5b8f60a44e4c7d6f1bb53474e17b"][0], TrackModel
        )

    def test_parse_tracks_with_visitor(self):
        track_dto = TrackDTO.factory(load_json_data("track.json"))
        tracks_dto = {"local:album:md5:ff5c5b8f60a44e4c7d6f1bb53474e17b": [track_dto]}
        visitor = Mock()
        ModelHelper().parse_tracks(tracks_dto, visitors=[visitor])
        visitor.assert_called_once_with(
            "local:album:md5:ff5c5b8f60a44e4c7d6f1bb53474e17b", track_dto
        )
