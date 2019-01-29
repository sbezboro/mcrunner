import mock
try:
    # Python 2.x
    import subprocess32 as subprocess
except ImportError:
    # Python 3.x
    import subprocess
import unittest

from mcrunner.exceptions import ServerStartException
from mcrunner.server import (
    MinecraftServer,
    SERVER_STOP_TIMEOUT_SEC,
    ServerNotRunningException,
    ServerStatus
)


class MinecraftServerTestCase(unittest.TestCase):

    def _create_server(self):
        self.server = MinecraftServer(
            'name',
            'path/to/jar',
            'craftbukkit.jar',
            '-arg_1 -arg_2',
            missing_key='val',
            restart_on_plugin_update=False,
        )

    def test_start(self):
        self._create_server()

        assert not hasattr(self.server, 'missing_key')
        assert self.server.restart_on_plugin_update is False

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

    def test_start_os_error(self):
        self._create_server()

        error = OSError('File not found')

        subprocess.Popen = mock.MagicMock(side_effect=error)

        with self.assertRaises(ServerStartException) as exc:
            self.server.start()

        assert str(exc.exception) == 'File not found'

    def test_start_with_plugin_change_observer(self):
        self._create_server()
        self.server.restart_on_plugin_update = True

        subprocess.Popen = mock.MagicMock()

        observer = mock.MagicMock()

        self.server._get_plugin_change_observer = mock.MagicMock(return_value=observer)

        self.server.start()

        assert observer.start.call_count == 1

    def test_start_with_plugin_change_observer_none(self):
        self._create_server()
        self.server.restart_on_plugin_update = True

        subprocess.Popen = mock.MagicMock()

        self.server._get_plugin_change_observer = mock.MagicMock(return_value=None)

        self.server.start()

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
        pipe = mock.MagicMock()
        self.server.pipe = pipe
        self.server.pipe.wait = mock.MagicMock(side_effect=subprocess.TimeoutExpired('cmd', 1))

        self.server.stop()

        assert pipe.terminate.call_count == 1

    def test_stop_timeout_and_terminate_with_connection(self):
        self._create_server()

        self.server.run_command = mock.MagicMock()
        pipe = mock.MagicMock()
        self.server.pipe = pipe
        self.server.pipe.wait = mock.MagicMock(side_effect=subprocess.TimeoutExpired('cmd', 1))

        mock_connection = mock.MagicMock()

        self.server.stop(mock_connection)

        assert mock_connection.send_message.call_count == 2
        assert mock_connection.send_message.call_args_list[0][0] == (
            'Stopping Minecraft server "name"...',
        )
        assert mock_connection.send_message.call_args_list[1][0] == (
            'Server "name" did not stop within %s seconds. Killing...' % SERVER_STOP_TIMEOUT_SEC,
        )
        assert pipe.terminate.call_count == 1

    def test_restart(self):
        self._create_server()

        subprocess.Popen = mock.MagicMock()

        self.server.restart(plugin_update=False)
        self.server.restart(plugin_update=True)

        assert subprocess.Popen.call_count == 2

    def test_get_status(self):
        self._create_server()

        self.server.run_command = mock.MagicMock()
        self.server.pipe = mock.MagicMock()

        status = self.server.get_status()

        assert status == ServerStatus.RUNNING

        assert self.server.run_command.call_count == 1
        assert self.server.run_command.call_args[0] == ('ping',)

    def test_get_status_not_running(self):
        self._create_server()

        status = self.server.get_status()

        assert status == ServerStatus.STOPPED

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

    def test_get_plugin_change_observer(self):
        self._create_server()

        observer = mock.MagicMock()

        with mock.patch('watchdog.observers.Observer', return_value=observer):
            assert self.server._get_plugin_change_observer()

        assert observer.schedule.call_count == 1

    def test_get_plugin_change_observer_error(self):
        self._create_server()

        observer = mock.MagicMock()
        observer.schedule = mock.MagicMock(side_effect=OSError('file not found'))

        with mock.patch('watchdog.observers.Observer', return_value=observer):
            assert self.server._get_plugin_change_observer() is None
