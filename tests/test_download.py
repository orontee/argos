import asyncio
import logging
import pathlib
import unittest
from unittest.mock import AsyncMock, Mock, call, mock_open, patch

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

import argos.session
from argos.download import ImageDownloader


class TestGetImageFilePath(unittest.TestCase):
    def setUp(self):
        app = Mock()
        self.downloader = ImageDownloader(app)

    def test_get_image_filepath_for_empty_uri(self):
        self.assertIsNone(self.downloader.get_image_filepath(""))

    def test_get_image_filepath_for_local_uri(self):
        self.assertTrue(
            str(self.downloader.get_image_filepath("/local/file")).endswith(
                "argos/images/file"
            )
        )

    def test_get_image_filepath_for_https_uri(self):
        self.assertTrue(
            str(self.downloader.get_image_filepath("https://host/file.jpg")).endswith(
                "argos/images/host%2Ffile.jpg"
            )
        )

    def test_get_image_filepath_for_http_uri(self):
        self.assertTrue(
            str(self.downloader.get_image_filepath("http://host/file.jpg")).endswith(
                "argos/images/host%2Ffile.jpg"
            )
        )

    def test_get_image_filepath_for_unsupported_scheme(self):
        with self.assertLogs("argos", logging.WARNING) as logs:
            self.assertIsNone(
                self.downloader.get_image_filepath("sftp://host/file.jpg")
            )

        self.assertEqual(len(logs.output), 1)


class TestImageDownloader(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_image_without_base_url(self):
        app = Mock()
        app.props.settings.get_string.return_value = None
        # get_string is the way to get mopidy-base-url setting

        downloader = ImageDownloader(app)
        image_path = await downloader.fetch_image(
            "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg"
        )
        self.assertIsNone(image_path)

    async def test_fetch_image_with_unsupported_scheme(self):
        app = Mock()
        app.props.settings.get_string.return_value = "https://a.mopidy.server"
        # get_string is the way to get mopidy-base-url setting

        downloader = ImageDownloader(app)
        with self.assertLogs("argos"):
            image_path = await downloader.fetch_image("sftp://host/file.jpg")

        self.assertIsNone(image_path)

    async def test_fetch_image_with_existing_file(self):
        app = Mock()
        app.props.settings.get_string.return_value = "https://a.mopidy.server"
        # get_string is the way to get mopidy-base-url setting

        expected_image_path_end = (
            "/argos/images/b23fb74538aa914239bde443f7343632-220x220.jpeg"
        )

        downloader = ImageDownloader(app)
        with patch.object(
            pathlib.Path, "exists", lambda p: str(p).endswith(expected_image_path_end)
        ):
            image_path = await downloader.fetch_image(
                "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg"
            )

        self.assertTrue(str(image_path).endswith(expected_image_path_end))


class TestImageDownloaderWithTestServer(AioHTTPTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()

        base_url = str(self.server.make_url("/"))
        app = Mock()
        app.props.version = "0.0.1-test"
        app.props.settings.get_string.return_value = base_url
        # get_string is the way to get mopidy-base-url setting

        app.http_session_manager = argos.session.HTTPSessionManager(app)
        async with app.http_session_manager.get_session() as session:
            self.addAsyncCleanup(session.close)

        self.downloader = ImageDownloader(app)

    async def get_application(self):
        async def answer(request):
            return web.Response(text="image content")

        async def broken_answer(request):
            resp = web.Response(status=500)
            return resp

        app = web.Application()
        app.router.add_get(
            "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg", answer
        )
        app.router.add_get(
            "/local/b23fb74538aa914239bde443f7343632-220x220-broken.jpeg", broken_answer
        )
        return app

    async def test_fetch_image(self):
        expected_image_path_end = (
            "/argos/images/b23fb74538aa914239bde443f7343632-220x220.jpeg"
        )

        with patch.object(
            pathlib.Path,
            "exists",
            lambda p: not str(p).endswith(expected_image_path_end),
        ):
            open_mock = mock_open()
            with patch("pathlib.Path.open", open_mock):
                image_path = await self.downloader.fetch_image(
                    "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg"
                )

        self.assertTrue(str(image_path).endswith(expected_image_path_end))
        open_mock.assert_called_once()
        handle = open_mock()
        handle.write.assert_called_once_with(b"image content")

    async def test_fetch_image_with_broken_client(self):
        expected_image_path_end = (
            "/argos/images/b23fb74538aa914239bde443f7343632-220x220-broken.jpeg"
        )

        with patch.object(
            pathlib.Path,
            "exists",
            lambda p: not str(p).endswith(expected_image_path_end),
        ):
            open_mock = mock_open()
            with patch("pathlib.Path.open", open_mock):
                with self.assertLogs("argos", logging.ERROR) as logs:
                    image_path = await self.downloader.fetch_image(
                        "/local/b23fb74538aa914239bde443f7343632-220x220-broken.jpeg"
                    )

        self.assertIsNone(image_path)
        self.assertEqual(len(logs.output), 1)

    async def test_fetch_images(self):
        self.downloader.fetch_image = AsyncMock()
        await self.downloader.fetch_images(
            [
                "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg",
                "/local/b23fb74538aa914239bde443f7343633-220x220.jpeg",
            ]
        )
        await asyncio.sleep(0)

        self.downloader.fetch_image.assert_has_calls(
            [
                call("/local/b23fb74538aa914239bde443f7343632-220x220.jpeg"),
                call("/local/b23fb74538aa914239bde443f7343633-220x220.jpeg"),
            ]
        )
