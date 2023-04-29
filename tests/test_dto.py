import json
import logging
import pathlib
import unittest

from argos.dto import (
    AlbumDTO,
    ArtistDTO,
    ImageDTO,
    PlaylistDTO,
    RefDTO,
    RefType,
    TlTrackDTO,
    TrackDTO,
    cast_seq_of,
)


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestImageDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("image.json")

    def test_factory_with_valid_data(self):
        dto = ImageDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(
            dto.uri, "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg"
        )
        self.assertEqual(dto.width, 220)
        self.assertEqual(dto.height, 220)

    def test_factory_with_malformed_image_data(self):
        del self.data["uri"]
        dto = ImageDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = ImageDTO.factory(None)
        self.assertIsNone(dto)


class TestPlaylistDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("playlist.json")

    def test_factory_with_valid_data(self):
        dto = PlaylistDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.uri, "m3u:Radio%20France%20%F0%9F%93%BB.m3u")
        self.assertEqual(dto.name, "Radio France 📻")
        self.assertEqual(len(dto.tracks), 4)
        self.assertEqual(dto.last_modified, 1682184079260)

    def test_factory_with_missing_last_modified(self):
        del self.data["last_modified"]
        dto = PlaylistDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_with_malformed_data(self):
        del self.data["tracks"][0]["uri"]
        dto = PlaylistDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = PlaylistDTO.factory(None)
        self.assertIsNone(dto)


class TestRefDTO(unittest.TestCase):
    def test_factory_with_valid_track_data(self):
        data = load_json_data("track_ref.json")
        dto = RefDTO.factory(data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.type, RefType.TRACK)
        self.assertEqual(
            dto.uri,
            "local:track:Johnny%20Cash/American%20Recordings/01%20Delia%27s%20Gone.flac",
        )
        self.assertEqual(dto.name, None)

    def test_factory_with_named_track_data(self):
        data = load_json_data("track_ref.json")
        data["name"] = "Delia's Gone"
        dto = RefDTO.factory(data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.type, RefType.TRACK)
        self.assertEqual(
            dto.uri,
            "local:track:Johnny%20Cash/American%20Recordings/01%20Delia%27s%20Gone.flac",
        )
        self.assertEqual(dto.name, "Delia's Gone")

    def test_factory_with_valid_playlist_data(self):
        data = load_json_data("playlist_ref.json")
        dto = RefDTO.factory(data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.type, RefType.PLAYLIST)
        self.assertEqual(
            dto.uri, "m3u:American%20Recordings%20%F0%9F%87%BA%F0%9F%87%B8.m3u8"
        )
        self.assertEqual(dto.name, "American Recordings 🇺🇸")

    def test_factory_with_malformed_track_data(self):
        data = load_json_data("track_ref.json")
        del data["type"]
        dto = RefDTO.factory(data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = RefDTO.factory(None)
        self.assertIsNone(dto)


class TestArtistDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("artist.json")

    def test_factory_with_valid_data(self):
        dto = ArtistDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.uri, "local:artist:md5:05f83e3daa5c79119e922ac114e64390")
        self.assertEqual(dto.name, "Johnny Cash")
        self.assertEqual(dto.musicbrainz_id, "d43d12a1-2dc9-4257-a2fd-0a3bb1081b86")
        self.assertEqual(dto.shortname, "")

    def test_factory_with_unamed_artist_data(self):
        del self.data["name"]
        dto = ArtistDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.name, "")

    def test_factory_without_data(self):
        dto = ArtistDTO.factory(None)
        self.assertIsNone(dto)


class TestAlbumDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("album.json")

    def test_factory_with_valid_data(self):
        dto = AlbumDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.uri, "local:album:md5:a6c9ed72dadf106f79834a7a3884d7ea")
        self.assertEqual(dto.name, "L'Essentiel des albums studio 1962-1985")
        self.assertEqual(dto.num_tracks, 10)
        self.assertEqual(dto.num_discs, 12)
        self.assertEqual(dto.date, "2011-11-07")
        self.assertEqual(dto.musicbrainz_id, "51a830b2-bdeb-49e9-8274-7e83e9aa57ec")
        self.assertEqual(len(dto.artists), 1)

    def test_factory_with_malformed_album_data(self):
        del self.data["name"]
        dto = AlbumDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = AlbumDTO.factory(None)
        self.assertIsNone(dto)


class TestTlTrackDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("tltrack.json")

    def test_factory_with_valid_data(self):
        dto = TlTrackDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.tlid, 7488)
        self.assertIsNotNone(dto.track)

    def test_factory_with_malformed_data(self):
        del self.data["tlid"]
        dto = TlTrackDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = TlTrackDTO.factory(None)
        self.assertIsNone(dto)


class TestTrackDTO(unittest.TestCase):
    def setUp(self):
        self.data = load_json_data("track.json")

    def test_factory_with_valid_data(self):
        dto = TrackDTO.factory(self.data)
        self.assertIsNotNone(dto)
        self.assertEqual(
            dto.uri,
            "local:track:Johnny%20Cash/American%20V_%20A%20Hundred%20Highways/04%20If%20You%20Could%20Read%20My%20Mind.flac",
        )
        self.assertEqual(dto.name, "If You Could Read My Mind")
        self.assertEqual(dto.track_no, 4)
        self.assertEqual(dto.disc_no, 1)
        self.assertEqual(dto.date, "2006")
        self.assertEqual(dto.musicbrainz_id, "851877ad-561d-496e-8196-6a52c0ae7a64")
        self.assertEqual(dto.length, 270000)
        self.assertEqual(dto.last_modified, 1678741922000)
        self.assertEqual(len(dto.artists), 1)
        self.assertEqual(len(dto.performers), 0)

    def test_factory_with_malformed_track_data(self):
        del self.data["uri"]
        dto = TrackDTO.factory(self.data)
        self.assertIsNone(dto)

    def test_factory_without_data(self):
        dto = TrackDTO.factory(None)
        self.assertIsNone(dto)


class TestCastSeqOf(unittest.TestCase):
    def test_casting_tracks(self):
        track_data = load_json_data("track.json")
        data = [track_data] * 3
        tracks = cast_seq_of(TrackDTO, data)
        self.assertEqual(len(tracks), 3)

    def test_casting_with_incompatible_class(self):
        track_data = load_json_data("track.json")
        data = [track_data] * 3
        with self.assertLogs("argos", level=logging.WARNING) as logs:
            tltracks = cast_seq_of(TlTrackDTO, data)
        self.assertEqual(len(tltracks), 0)
        self.assertEqual(len(logs.output), 3)

    def test_casting_with_wrong_data(self):
        track_data = load_json_data("track.json")
        data = [track_data, {}]
        with self.assertLogs("argos.dto", logging.WARNING) as logs:
            tracks = cast_seq_of(TrackDTO, data)

        self.assertEqual(len(tracks), 1)
        self.assertEqual(len(logs.output), 1)
