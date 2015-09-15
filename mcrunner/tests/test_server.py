import mock
try:
    # Python 2.x
    import subprocess32 as subprocess
except ImportError:
    # Python 3.x
    import subprocess
import unittest

from mcrunner.server import (
    MinecraftServer,
    SERVER_STOP_TIMEOUT_SEC,
    ServerNotRunningException,
)


class MinecraftServerTestCase(unittest.TestCase):

    def _create_server(self):
        self.server = MinecraftServer(
            'name',
            'path/to/jar',
            'craftbukkit.jar',
            '-arg_1 -arg_2'
        )

    def test_start(self):
        self._create_server()

        subprocess.Popen = mock.MagicMock()

        self.server.start()

        assert subprocess.Popen.call_count == 1
        assert subprocess.Popen.call_args[0] == ([
            '/usr/bin/java',
            '-arg_1',
            '-arg_2',
            '-jar',
            'path/to/jar/craftbukkit.jar'
        ],)
        assert subprocess.Popen.call_args[1] == dict(
            cwd='path/to/jar',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def test_stop(self):
        self._create_server()

        self.server.run_command = mock.MagicMock()
        self.server.pipe = mock.MagicMock()

        self.server.stop()

        assert self.server.run_command.call_count == 1
        assert self.server.run_command.call_args[0] == ('stop',)

    def test_stop_not_running(self):
        self._create_server()

        with self.assertRaises(ServerNotRunningException):
            self.server.stop()

    def test_stop_timeout_and_terminate(self):
        self._create_server()

        self.server.run_command = mock.MagicMock()
        self.server.pipe = mock.MagicMock()
        self.server.pipe.wait = mock.MagicMock(side_effect=subprocess.TimeoutExpired('cmd', 1))

        mock_connection = mock.MagicMock()

        self.server.stop(mock_connection)

        assert mock_connection.send_message.call_count == 2
        assert mock_connection.send_message.call_args_list[0][0] == (
            'Stopping server name...',
        )
        assert mock_connection.send_message.call_args_list[1][0] == (
            'Server did not stop within %s seconds. Killing...' % SERVER_STOP_TIMEOUT_SEC,
        )
        assert self.server.pipe.terminate.call_count == 1

    def test_get_status(self):
        self._create_server()

        self.server.run_command = mock.MagicMock()
        self.server.pipe = mock.MagicMock()

        status = self.server.get_status()

        assert status == 'Running'

        assert self.server.run_command.call_count == 1
        assert self.server.run_command.call_args[0] == ('ping',)

    def test_get_status_not_running(self):
        self._create_server()

        status = self.server.get_status()

        assert status == 'Not running'

    def test_run_command(self):
        self._create_server()

        self.server.pipe = mock.MagicMock()

        self.server.run_command('some command')

        assert self.server.pipe.stdin.write.call_count == 1
        assert self.server.pipe.stdin.write.call_args[0] == ('some command\n',)

    def test_run_command_exception(self):
        self._create_server()

        self.server.pipe = mock.MagicMock()
        self.server.pipe.stdin.write.side_effect = Exception

        with self.assertRaises(ServerNotRunningException):
            self.server.run_command('some command')
