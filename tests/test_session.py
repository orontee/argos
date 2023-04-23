import unittest
from unittest.mock import Mock

from argos.session import HTTPSessionManager


class TestHTTPSessionManager(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        app = Mock()
        app.props.version = "1.0.0"
        cls.application = app

    async def asyncSetUp(self):
        manager = HTTPSessionManager(TestHTTPSessionManager.application)
        async with manager.get_session() as session:
            self.session = session

    async def asyncTearDown(self):
        if self.session is not None:
            await self.session.close()

    async def test_headers(self):
        self.assertIn("User-Agent", self.session.headers)
        self.assertEqual(
            self.session.headers["User-Agent"],
            "Argos/1.0.0 ( https://orontee.github.io/argos/ )",
        )
