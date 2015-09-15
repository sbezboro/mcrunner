import logging
import mock
import os
import socket
import sys
import tempfile
import unittest

from mcrunner import mcrunnerd
from mcrunner.mcrunnerd import (
    MCRunner,
    MCRUNNERD_COMMAND_DELIMITER
)
from mcrunner.server import (
    MinecraftServer,
    ServerNotRunningException,
    ServerStartException
)


TEST_CONFIG = b"""
[mcrunnerd]
logfile=/var/log/mcrunner/mcrunnerd.log

[mcrunner]
url=/tmp/mcrunner.sock

[server:survival]
path=/path/to/server1
jar=spigot.jar
opts=-Xms1G -Xmx8G

[server:creative]
path=/path/to/server2
jar=craftbukkit.jar
opts=-Xms8G -Xmx16G

[empty_section]
"""


class MCRunnerTestCase(unittest.TestCase):

    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile()
        self.config_file.write(TEST_CONFIG)
        self.config_file.flush()

        self.pid_file = tempfile.NamedTemporaryFile()

        self.sock_file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        self.config_file.close()
        self.pid_file.close()
        self.sock_file.close()

    def _set_up_daemon_with_recv(self, recv_list):
        self.daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        mock_sock = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_sock.accept = mock.MagicMock(return_value=(
            mock_conn, 'address'
        ))

        self.mock_logger = mock.MagicMock()
        self.daemon.create_logger = mock.MagicMock(return_value=self.mock_logger)

        self.daemon.socket_server = mock.MagicMock(return_value=mock_sock)

        self.mock_connection = mock.MagicMock()
        self.mock_connection.receive_message = mock.MagicMock(side_effect=recv_list)

    def test_load_config(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()

        assert daemon.log_file == '/var/log/mcrunner/mcrunnerd.log'
        assert daemon.sock_file == '/tmp/mcrunner.sock'

        assert len(daemon.servers) == 2

        survival = daemon.servers['survival']
        creative = daemon.servers['creative']

        assert survival.name == 'survival'
        assert survival.path == '/path/to/server1'
        assert survival.jar == 'spigot.jar'
        assert survival.opts == '-Xms1G -Xmx8G'

        assert creative.name == 'creative'
        assert creative.path == '/path/to/server2'
        assert creative.jar == 'craftbukkit.jar'
        assert creative.opts == '-Xms8G -Xmx16G'

    def test_socket_server(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.sock_file = self.sock_file.name

        mock_sock = mock.MagicMock()

        with mock.patch.object(os, 'unlink'):
            with mock.patch('socket.socket', return_value=mock_sock) as MockSocket:
                sock = daemon.socket_server()

        assert MockSocket.call_count == 1
        assert MockSocket.call_args[0] == (socket.AF_UNIX, socket.SOCK_STREAM)

        assert sock == mock_sock
        assert mock_sock.bind.call_count == 1
        assert mock_sock.bind.call_args[0] == (self.sock_file.name,)
        assert mock_sock.listen.call_count == 1
        assert mock_sock.listen.call_args[0] == (1,)

    def test_socket_server_os_error(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.sock_file = self.sock_file.name

        mock_sock = mock.MagicMock()

        with mock.patch.object(os, 'unlink', side_effect=OSError):
            with mock.patch('socket.socket', return_value=mock_sock) as MockSocket:
                sock = daemon.socket_server()

        assert MockSocket.call_count == 1
        assert MockSocket.call_args[0] == (socket.AF_UNIX, socket.SOCK_STREAM)

        assert sock == mock_sock
        assert mock_sock.bind.call_count == 1
        assert mock_sock.bind.call_args[0] == (self.sock_file.name,)
        assert mock_sock.listen.call_count == 1
        assert mock_sock.listen.call_args[0] == (1,)

    def test_create_logger(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()

        with tempfile.NamedTemporaryFile() as f:
            daemon.log_file = f.name
            logger = daemon.create_logger()

        assert isinstance(logger, logging.getLoggerClass())

    def test_get_status(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()

        daemon.servers['survival'].get_status = mock.MagicMock(return_value='some status')
        daemon.servers['creative'].get_status = mock.MagicMock(return_value='some other status')

        mock_connection = mock.MagicMock()

        daemon.get_status(mock_connection)

        status = mock_connection.send_message.call_args[0][0]

        assert 'survival: some status' in status
        assert 'creative: some other status' in status

    def test_start_minecraft_server_exception(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()
        daemon.logger = mock.MagicMock()

        with mock.patch.object(MinecraftServer, 'start', side_effect=ServerStartException):
            daemon.start_minecraft_server('survival')

    def test_start_minecraft_server_invalid(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()
        daemon.logger = mock.MagicMock()

        daemon.start_minecraft_server('bad_server')

    def test_stop_minecraft_server(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()
        daemon.logger = mock.MagicMock()

        daemon.stop_minecraft_server('survival')

    def test_stop_minecraft_server_invalid(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()
        daemon.logger = mock.MagicMock()

        daemon.stop_minecraft_server('bad_server')

    def test_on_exit(self):
        daemon = MCRunner(
            config_file=self.config_file.name,
            pid_file=self.pid_file.name
        )

        daemon.load_config()
        daemon.logger = mock.MagicMock()

        daemon.servers['survival'].stop = mock.MagicMock()
        daemon.servers['creative'].stop = mock.MagicMock()

        daemon.on_exit()

        assert daemon.servers['survival'].stop.call_count == 1
        assert daemon.servers['creative'].stop.call_count == 1

    def test_run_no_message(self):
        self._set_up_daemon_with_recv([
            'some data',
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_connection.receive_message.call_count == 2
        assert self.mock_connection.send_message.call_count == 0

    def test_run_socket_error(self):
        self._set_up_daemon_with_recv([
            socket.error,
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_logger.exception.call_count == 1
        assert self.mock_logger.exception.call_args[0] == ('Error during socket connection',)

    def test_run_status(self):
        self._set_up_daemon_with_recv([
            'status',
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_connection.send_message.call_count == 1

        status = self.mock_connection.send_message.call_args[0][0]

        assert 'survival: Not running' in status
        assert 'creative: Not running' in status

        assert self.mock_connection.close.call_count == 2

    def test_run_with_start_server(self):
        self._set_up_daemon_with_recv([
            'start{}survival'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, '_start_jar') as mock_start:
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert mock_start.call_count == 1

        assert self.mock_connection.send_message.call_count == 2
        assert self.mock_connection.send_message.call_args_list[0][0] == ('Starting server survival...',)
        assert self.mock_connection.send_message.call_args_list[1][0] == ('Server survival started.',)

    def test_run_with_start_invalid_server(self):
        self._set_up_daemon_with_recv([
            'start{}bad_server_name'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Minecraft server "bad_server_name" not defined',)

    def test_run_with_start_server_running(self):
        self._set_up_daemon_with_recv([
            'start{}survival'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'start', side_effect=ServerStartException('exc')) as mock_start:
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert mock_start.call_count == 1

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Could not start server! stderr:\n\nexc',)

    def test_run_with_restart_server(self):
        self._set_up_daemon_with_recv([
            'restart{}survival'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'pipe'):
            with mock.patch.object(MinecraftServer, 'run_command') as mock_run_command:
                with mock.patch.object(MinecraftServer, '_start_jar') as mock_start:
                    with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                        self.daemon.run()

        assert mock_start.call_count == 1
        assert mock_run_command.call_count == 1

        assert self.mock_connection.send_message.call_count == 4
        assert self.mock_connection.send_message.call_args_list[0][0] == ('Stopping server survival...',)
        assert self.mock_connection.send_message.call_args_list[1][0] == ('Server survival stopped.',)
        assert self.mock_connection.send_message.call_args_list[2][0] == ('Starting server survival...',)
        assert self.mock_connection.send_message.call_args_list[3][0] == ('Server survival started.',)

    def test_run_with_stop_server(self):
        self._set_up_daemon_with_recv([
            'stop{}survival'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'pipe'):
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert self.mock_connection.send_message.call_count == 2
        assert self.mock_connection.send_message.call_args_list[0][0] == ('Stopping server survival...',)
        assert self.mock_connection.send_message.call_args_list[1][0] == ('Server survival stopped.',)

    def test_run_with_stop_invalid_server(self):
        self._set_up_daemon_with_recv([
            'stop{}bad_server_name'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Minecraft server "bad_server_name" not defined',)

    def test_run_with_stop_server_not_running(self):
        self._set_up_daemon_with_recv([
            'stop{}survival'.format(MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'stop', side_effect=ServerNotRunningException) as mock_stop:
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert mock_stop.call_count == 1

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Minecraft server "survival" not running',)

    def test_run_with_command(self):
        self._set_up_daemon_with_recv([
            'command{delim}survival{delim}say test'.format(delim=MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'pipe'):
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Sent command to Minecraft server "survival": "say test"',)

    def test_run_with_command_invalid_server(self):
        self._set_up_daemon_with_recv([
            'command{delim}bad_server_name{delim}say test'.format(delim=MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
            self.daemon.run()

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Minecraft server "bad_server_name" not defined',)

    def test_run_with_command_not_running(self):
        self._set_up_daemon_with_recv([
            'command{delim}survival{delim}say test'.format(delim=MCRUNNERD_COMMAND_DELIMITER),
            SystemExit
        ])

        with mock.patch.object(MinecraftServer, 'run_command', side_effect=ServerNotRunningException) as mock_command:
            with mock.patch('mcrunner.mcrunnerd.ServerSocketConnection', return_value=self.mock_connection):
                self.daemon.run()

        assert mock_command.call_count == 1
        assert mock_command.call_args[0] == ('say test',)

        assert self.mock_connection.send_message.call_count == 1
        assert self.mock_connection.send_message.call_args[0] == ('Minecraft server "survival" not running',)


class MCRunnerMainTestCase(unittest.TestCase):

    def test_output(self):
        with mock.patch.object(sys.stdout, 'write') as mock_write:
            mcrunnerd._output('test')

        assert mock_write.call_count == 1
        assert mock_write.call_args[0] == ('test\n',)

    @mock.patch.object(sys, 'argv', ['mcrunnerd'])
    def test_too_few_args(self):
        with mock.patch('mcrunner.mcrunnerd._output') as mock_output:
            with self.assertRaises(SystemExit):
                mcrunnerd.main()

        assert mock_output.call_count == 1
        assert mock_output.call_args[0] == ('Usage: mcrunnerd start|stop|restart',)

    @mock.patch.object(sys, 'argv', ['mcrunnerd', 'blah', 'blah'])
    def test_too_many_args(self):
        with mock.patch('mcrunner.mcrunnerd._output') as mock_output:
            with self.assertRaises(SystemExit):
                mcrunnerd.main()

        assert mock_output.call_count == 1
        assert mock_output.call_args[0] == ('Usage: mcrunnerd start|stop|restart',)

    @mock.patch.object(sys, 'argv', ['mcrunnerd', 'start'])
    def test_start(self):
        mock_daemon = mock.MagicMock()

        with mock.patch('mcrunner.mcrunnerd.MCRunner', return_value=mock_daemon):
            mcrunnerd.main()

        assert mock_daemon.start.call_count == 1

    @mock.patch.object(sys, 'argv', ['mcrunnerd', 'stop'])
    def test_stop(self):
        mock_daemon = mock.MagicMock()

        with mock.patch('mcrunner.mcrunnerd.MCRunner', return_value=mock_daemon):
            mcrunnerd.main()

        assert mock_daemon.stop.call_count == 1

    @mock.patch.object(sys, 'argv', ['mcrunnerd', 'restart'])
    def test_restart(self):
        mock_daemon = mock.MagicMock()

        with mock.patch('mcrunner.mcrunnerd.MCRunner', return_value=mock_daemon):
            mcrunnerd.main()

        assert mock_daemon.restart.call_count == 1

    @mock.patch.object(sys, 'argv', ['mcrunnerd', 'bad_command'])
    def test_bad_command(self):
        with mock.patch('mcrunner.mcrunnerd._output') as mock_output:
            with self.assertRaises(SystemExit):
                mcrunnerd.main()

        assert mock_output.call_count == 1
        assert mock_output.call_args[0] == ('Unknown command: bad_command',)
