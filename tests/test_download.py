import logging
import unittest
from unittest.mock import Mock

from argos.download import ImageDownloader


class TestImageDownloader(unittest.TestCase):
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
            self.assertIsNone(self.downloader.get_image_filepath("ssh://host/file.jpg"))

        self.assertEqual(len(logs.output), 1)
