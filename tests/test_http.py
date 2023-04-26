import asyncio
import json
import pathlib
import unittest
from unittest.mock import AsyncMock, Mock, call

from argos.http import MopidyHTTPClient


def load_json_data(filename: str):
    path = pathlib.Path(__file__).parent / "data" / filename
    with open(path) as fh:
        data = json.load(fh)
    return data


class TestMopidyHTTPClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = Mock()
        self.app.props.ws = AsyncMock()
        self.client = MopidyHTTPClient(self.app)

    # Tests on core.playback
    async def test_get_state(self):
        self.app.props.ws.send_command.return_value = "playing"
        state = await self.client.get_state()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.get_state"
        )
        self.assertEqual(state, "playing")

    async def test_pause(self):
        await self.client.pause()
        self.app.props.ws.send_command.assert_called_once_with("core.playback.pause")

    async def test_resume(self):
        await self.client.resume()
        self.app.props.ws.send_command.assert_called_once_with("core.playback.resume")

    async def test_play_without_tlid(self):
        await self.client.play()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.play", params={}
        )

    async def test_play(self):
        await self.client.play(48)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.play", params={"tlid": 48}
        )

    async def test_seek(self):
        await self.client.seek(1000)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.seek", params={"time_position": 1000}
        )

    async def test_previous(self):
        await self.client.previous()
        self.app.props.ws.send_command.assert_called_once_with("core.playback.previous")

    async def test_next(self):
        await self.client.next()
        self.app.props.ws.send_command.assert_called_once_with("core.playback.next")

    async def test_get_time_position(self):
        self.app.props.ws.send_command.return_value = 1000
        time_position = await self.client.get_time_position()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.get_time_position"
        )
        self.assertEqual(time_position, 1000)

    async def test_get_current_tl_track(self):
        data = load_json_data("tltrack.json")
        self.app.props.ws.send_command.return_value = data
        tl_track_dto = await self.client.get_current_tl_track()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playback.get_current_tl_track"
        )
        self.assertEqual(tl_track_dto.tlid, 7488)

    # Tests on core.library
    async def test_browse_library(self):
        data = load_json_data("root.json")
        self.app.props.ws.send_command.return_value = data
        root = await self.client.browse_library()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.library.browse", params={"uri": None}, timeout=60
        )
        self.assertEqual(len(root), 6)

    async def test_lookup_library(self):
        data = load_json_data("lookup.json")
        self.app.props.ws.send_command.return_value = data
        uris = [
            "http://direct.franceinter.fr/live/franceinter-midfi.mp3",
            "local:artist:md5:e9c2ccea0d6d00a330cef5dce77f892d",
        ]
        tracks = await self.client.lookup_library(uris)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.library.lookup", params={"uris": uris}, timeout=60
        )
        self.assertEqual(len([k for k in tracks.keys()]), 2)

    async def test_get_images(self):
        data = load_json_data("images.json")
        self.app.props.ws.send_command.return_value = data
        uris = [
            "local:track:Agn%C3%A8s%20Capri/Succ%C3%A8s%20et%20raret%C3%A9s/02%20Adrien.flac",
            "local:track:The%20Duke%20Ellington%20Orchestra%20%26%20The%20Count%20Basie%20Orchestra/Battle%20Royal%20-%20Duke%20Ellington%20meets%20Count%20Basie/04%20Corner%20Pocket%20%5Baka%20Until%20I%20Met%20You%5D.flac",
        ]
        images = await self.client.get_images(uris)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.library.get_images", params={"uris": uris}
        )
        self.assertEqual([k for k in images.keys()], uris)

    # Tests on core.tracklist
    async def test_get_eot_tlid(self):
        self.app.props.ws.send_command.return_value = 7543
        eot_tlid = await self.client.get_eot_tlid()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_eot_tlid"
        )
        self.assertEqual(eot_tlid, 7543)

    async def test_add_to_tracklist(self):
        data = load_json_data("tltracks.json")
        self.app.props.ws.send_command.return_value = data
        tltracks = await self.client.add_to_tracklist(
            ["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"]
        )
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.add",
            params={"uris": ["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"]},
        )
        self.assertEqual(len(tltracks), 17)

    async def test_remove_from_tracklist(self):
        await self.client.remove_from_tracklist([47, 34])
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.remove", params={"criteria": {"tlid": [47, 34]}}
        )

    async def test_clear_track_list(self):
        await self.client.clear_tracklist()
        self.app.props.ws.send_command.assert_called_once_with("core.tracklist.clear")

    async def test_get_tracklist_tracks(self):
        data = load_json_data("tltracks.json")
        self.app.props.ws.send_command.return_value = data
        tltracks = await self.client.get_tracklist_tracks()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_tl_tracks"
        )
        self.assertTrue(len(tltracks) == 17)

    async def test_get_tracklist_version(self):
        self.app.props.ws.send_command.return_value = 54
        version = await self.client.get_tracklist_version()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_version"
        )
        self.assertEqual(version, 54)

    async def test_get_consume(self):
        self.app.props.ws.send_command.return_value = False
        consume = await self.client.get_consume()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_consume"
        )
        self.assertEqual(consume, False)

    async def test_set_consume(self):
        await self.client.set_consume(False)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.set_consume", params={"value": False}
        )

    async def test_get_random(self):
        self.app.props.ws.send_command.return_value = False
        random = await self.client.get_random()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_random"
        )
        self.assertEqual(random, False)

    async def test_set_random(self):
        await self.client.set_random(False)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.set_random", params={"value": False}
        )

    async def test_get_repeat(self):
        self.app.props.ws.send_command.return_value = False
        repeat = await self.client.get_repeat()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_repeat"
        )
        self.assertEqual(repeat, False)

    async def test_set_repeat(self):
        await self.client.set_repeat(True)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.set_repeat", params={"value": True}
        )

    async def test_get_single(self):
        self.app.props.ws.send_command.return_value = True
        single = await self.client.get_single()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.get_single"
        )
        self.assertEqual(single, True)

    async def test_set_single(self):
        await self.client.set_single(False)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.tracklist.set_single", params={"value": False}
        )

    async def test_play_tracks(self):
        self.app.props.ws.send_command.return_value = (None, None, "playing")
        await self.client.play_tracks(["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"])
        self.app.props.ws.send_command.assert_has_calls(
            [
                call("core.tracklist.clear"),
                call(
                    "core.tracklist.add",
                    params={"uris": ["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"]},
                ),
            ]
        )

    async def test_play_tracks_without_uris(self):
        await self.client.play_tracks()
        self.app.props.ws.send_command.assert_not_called()

        await self.client.play_tracks([])
        self.app.props.ws.send_command.assert_not_called()

    async def test_play_tracks_while_stopped(self):
        self.app.props.ws.send_command.return_value = (None, None, "stopped", None)
        await self.client.play_tracks(["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"])
        self.app.props.ws.send_command.assert_has_calls(
            [
                call("core.tracklist.clear"),
                call(
                    "core.tracklist.add",
                    params={"uris": ["m3u:Gainsbarre%F0%9F%9A%AC%EF%B8%8F.m3u8"]},
                ),
                call("core.playback.get_state"),
                call("core.playback.play"),
            ]
        )

    # Tests on core.mixer
    async def test_get_mute(self):
        self.app.props.ws.send_command.return_value = True
        mute = await self.client.get_mute()
        self.app.props.ws.send_command.assert_called_once_with("core.mixer.get_mute")
        self.assertEqual(mute, True)

    async def test_set_mute(self):
        await self.client.set_mute(False)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.mixer.set_mute", params={"mute": False}
        )

    async def test_get_volume(self):
        self.app.props.ws.send_command.return_value = 88
        volume = await self.client.get_volume()
        self.app.props.ws.send_command.assert_called_once_with("core.mixer.get_volume")
        self.assertEqual(volume, 88)

    async def test_set_volume(self):
        await self.client.set_volume(50)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.mixer.set_volume", params={"volume": 50}
        )

    # Tests on core.playlists
    async def test_get_playlists_uri_schemes(self):
        self.app.props.ws.send_command.return_value = ["m3u"]
        schemes = await self.client.get_playlists_uri_schemes()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playlists.get_uri_schemes"
        )
        self.assertEqual(schemes, ["m3u"])

    async def test_list_playlists(self):
        data = [load_json_data("playlist_ref.json")]
        self.app.props.ws.send_command.return_value = data
        playlists = await self.client.list_playlists()
        self.app.props.ws.send_command.assert_called_once_with("core.playlists.as_list")
        self.assertEqual(len(playlists), 1)

    async def test_lookup_playlist(self):
        data = load_json_data("playlist.json")
        self.app.props.ws.send_command.return_value = data
        playlist = await self.client.lookup_playlist(
            "m3u:Radio%20France%20%F0%9F%93%BB.m3u"
        )
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playlists.lookup",
            params={"uri": "m3u:Radio%20France%20%F0%9F%93%BB.m3u"},
        )
        self.assertEqual(playlist.uri, "m3u:Radio%20France%20%F0%9F%93%BB.m3u")

    async def test_create_playlist(self):
        data = load_json_data("playlist.json")
        self.app.props.ws.send_command.return_value = data
        playlist = await self.client.create_playlist("Radio France 📻")
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playlists.create", params={"name": "Radio France 📻"}
        )
        self.assertEqual(playlist.uri, "m3u:Radio%20France%20%F0%9F%93%BB.m3u")

    async def test_save_playlist(self):
        data = load_json_data("playlist.json")
        self.app.props.ws.send_command.return_value = data
        playlist = await self.client.save_playlist(data)
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playlists.save", params={"playlist": data}
        )
        self.assertEqual(playlist.uri, data["uri"])

    async def test_delete_playlist(self):
        self.app.props.ws.send_command.return_value = True
        deleted = await self.client.delete_playlist(
            "m3u:Radio%20France%20%F0%9F%93%BB.m3u"
        )
        self.app.props.ws.send_command.assert_called_once_with(
            "core.playlists.delete",
            params={"uri": "m3u:Radio%20France%20%F0%9F%93%BB.m3u"},
        )
        self.assertEqual(deleted, True)

    # Tests on core.history
    async def test_get_history(self):
        data = load_json_data("history.json")
        self.app.props.ws.send_command.return_value = data
        history = await self.client.get_history()
        self.app.props.ws.send_command.assert_called_once_with(
            "core.history.get_history", timeout=60
        )
        self.assertEqual(len(history), 617)
