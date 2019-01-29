import unittest

import mock

from mcrunner.plugin_change import PluginChangeEventHandler
from mcrunner.server_status import ServerStatus


class PluginChangeTestCase(unittest.TestCase):

    def setUp(self):
        self.server = mock.MagicMock()
        self.handler = PluginChangeEventHandler(self.server)

    def test_check_and_restart_valid(self):
        self.server.get_status = mock.MagicMock(return_value=ServerStatus.RUNNING)

        event = mock.MagicMock(
            is_directory=False,
            src_path='file.jar',
        )

        self.handler._check_and_restart(event)

        assert self.server.restart.call_count == 1

    def test_on_created(self):
        event = mock.MagicMock()
        self.handler.on_created(event)

    def test_on_deleted(self):
        event = mock.MagicMock()
        self.handler.on_deleted(event)

    def test_on_modified(self):
        event = mock.MagicMock()
        self.handler.on_modified(event)
