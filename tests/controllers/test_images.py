import unittest
from unittest.mock import AsyncMock, Mock

from argos.controllers.images import ImagesController
from argos.message import Message, MessageType


class TestImagesController(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_images(self):
        app = Mock()
        app.props.download.fetch_images = AsyncMock()
        controller = ImagesController(app)
        msg = Message(
            MessageType.FETCH_IMAGES,
            data={
                "image_uris": [
                    "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg",
                    "/local/b23fb74538aa914239bde443f7343633-220x220.jpeg",
                ]
            },
        )
        await controller.fetch_images(msg)
        app.props.download.fetch_images.assert_called_once_with(
            [
                "/local/b23fb74538aa914239bde443f7343632-220x220.jpeg",
                "/local/b23fb74538aa914239bde443f7343633-220x220.jpeg",
            ]
        )
