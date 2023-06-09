import json
import pathlib
import unittest
from copy import copy

from argos.controllers.visitors import (
    AlbumMetadataCollector,
    LengthAcc,
    PlaylistTrackNameFix,
)
from argos.dto import PlaylistDTO, TrackDTO, cast_seq_of
from argos.model.helper import ModelHelper


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent.parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestLengthAcc(unittest.TestCase):
    def test_call(self):
        track_dto = TrackDTO.factory(load_json_data("track.json"))
        tracks_dto = {"uri": [track_dto] * 3}
        visitor = LengthAcc()
        ModelHelper().parse_tracks(tracks_dto, visitors=[visitor])
        self.assertEqual(visitor.length["uri"], 3 * 270000)

    def test_call_wrong_uri(self):
        track_dto = TrackDTO.factory(load_json_data("track.json"))
        tracks_dto = {"uri": [track_dto] * 3}
        visitor = LengthAcc()
        ModelHelper().parse_tracks(tracks_dto, visitors=[visitor])
        self.assertEqual(visitor.length["otheruri"], 0)

    def test_call_with_unkown_length(self):
        track_dto = TrackDTO.factory(load_json_data("track.json"))
        other_track_dto = copy(track_dto)
        other_track_dto.length = None
        tracks_dto = {"uri": [track_dto, other_track_dto, track_dto]}
        visitor = LengthAcc()
        ModelHelper().parse_tracks(tracks_dto, visitors=[visitor])
        self.assertEqual(visitor.length["uri"], -1)


class TestAlbumMetadataCollector(unittest.TestCase):
    def test_call(self):
        album_tracks_dto = cast_seq_of(TrackDTO, load_json_data("album_tracks.json"))
        album_uri = "local:album:md5:a6c9ed72dadf106f79834a7a3884d7ea"
        visitor = AlbumMetadataCollector()
        ModelHelper().parse_tracks({album_uri: album_tracks_dto}, visitors=[visitor])
        self.assertEqual(visitor.artist_name(album_uri), "Claude Nougaro")
        self.assertEqual(visitor.num_tracks(album_uri), 10)
        # Not the right track number but the one extracted by Mopidy-Local!
        self.assertEqual(visitor.num_discs(album_uri), 12)
        self.assertEqual(visitor.date(album_uri), "2011-11-07")
        self.assertEqual(
            visitor.release_mbid(album_uri), "51a830b2-bdeb-49e9-8274-7e83e9aa57ec"
        )
        self.assertEqual(visitor.last_modified(album_uri), 1615839524606)


class TestPlaylistTrackNameFix(unittest.TestCase):
    def test_call(self):
        playlist_dto = PlaylistDTO.factory(load_json_data("playlist.json"))
        tracks_dto = {
            "http://direct.franceinter.fr/live/franceinter-midfi.mp3": [
                TrackDTO.factory(
                    {
                        "__model__": "Track",
                        "uri": "http://direct.franceinter.fr/live/franceinter-midfi.mp3",
                        "name": "franceinter-midfi.mp3",
                    }
                )
            ],
            "http://direct.franceculture.fr/live/franceculture-midfi.mp3": [
                TrackDTO.factory(
                    {
                        "__model__": "Track",
                        "uri": "http://direct.franceculture.fr/live/franceculture-midfi.mp3"
                        # name not specified
                    }
                )
            ],
        }
        visitor = PlaylistTrackNameFix(playlist_dto)
        parsed_tracks = ModelHelper().parse_tracks(tracks_dto, visitors=[visitor])
        self.assertEqual(
            parsed_tracks["http://direct.franceinter.fr/live/franceinter-midfi.mp3"][
                0
            ].name,
            "France Inter",
        )
        self.assertEqual(
            parsed_tracks[
                "http://direct.franceculture.fr/live/franceculture-midfi.mp3"
            ][0].name,
            "France Culture",
        )
