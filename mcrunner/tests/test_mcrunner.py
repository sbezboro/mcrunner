import mock
import socket
import sys
import tempfile
import unittest

from mcrunner import mcrunner
from mcrunner.mcrunner import Controller
from mcrunner.mcrunnerd import MCRUNNERD_COMMAND_DELIMITER


TEST_CONFIG = b"""
[mcrunner]
url=/tmp/mcrunner.sock

[empty_section]
"""


class MCRunnerControllerTestCase(unittest.TestCase):

    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile()
        self.config_file.write(TEST_CONFIG)
        self.config_file.flush()

    def tearDown(self):
        self.config_file.close()

    def test_socket_client(self):
        controller = Controller(config_file=self.config_file.name)

        with mock.patch('socket.socket') as MockSocket:
            sock = controller.socket_client()

        assert sock == MockSocket.return_value
        assert MockSocket.call_args[0] == (socket.AF_UNIX, socket.SOCK_STREAM)

    def test_load_config(self):
        controller = Controller(config_file=self.config_file.name)

        assert controller.sock_file == '/tmp/mcrunner.sock'

    def test_load_empty_config(self):
        self.config_file.close()
        self.config_file = tempfile.NamedTemporaryFile()

        controller = Controller(config_file=self.config_file.name)

        assert controller.sock_file == None

    def test_send_mcrunnerd_package(self):
        controller = Controller(config_file=self.config_file.name)

        controller.socket_client = mock.MagicMock()

        mock_connection = mock.MagicMock()
        mock_connection.receive_message = mock.MagicMock(side_effect=[
            'some sample response message',
            None  # socket closed
        ])

        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with mock.patch('mcrunner.mcrunner.ClientSocketConnection', return_value=mock_connection):
                controller.send_mcrunnerd_package('some_package')

        assert mock_connection.send_message.call_count == 1
        assert mock_connection.send_message.call_args[0] == ('some_package',)

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('some sample response message',)

        assert mock_connection.close.call_count == 1

    def test_send_mcrunnerd_package_with_socket_error(self):
        controller = Controller(config_file=self.config_file.name)

        controller.socket_client = mock.MagicMock(side_effect=socket.error)

        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            controller.send_mcrunnerd_package('some_package')

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Could not connect to socket - is mcrunnerd running?',)

    def test_send_mcrunnerd_package_with_sendall_error(self):
        controller = Controller(config_file=self.config_file.name)

        controller.socket_client = mock.MagicMock()

        socket_error = socket.error('bad send')

        mock_connection = mock.MagicMock()
        mock_connection.send_message = mock.MagicMock(side_effect=socket_error)

        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with mock.patch('mcrunner.mcrunner.ClientSocketConnection', return_value=mock_connection):
                controller.send_mcrunnerd_package('some_package')

        assert mock_connection.send_message.call_count == 1
        assert mock_connection.send_message.call_args[0] == ('some_package',)

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Error sending mcrunnerd package: %s' % str(socket_error),)

        assert mock_connection.close.call_count == 1

    def test_handle_mcrunnerd_action(self):
        controller = Controller(config_file=self.config_file.name)
        controller.send_mcrunnerd_package = mock.MagicMock()

        controller.handle_mcrunnerd_action('package')

        assert controller.send_mcrunnerd_package.call_count == 1
        assert controller.send_mcrunnerd_package.call_args[0] == ('package',)

    def test_handle_server_action(self):
        controller = Controller(config_file=self.config_file.name)
        controller.send_mcrunnerd_package = mock.MagicMock()

        controller.handle_server_action('action', 'server_1')

        assert controller.send_mcrunnerd_package.call_count == 1
        assert controller.send_mcrunnerd_package.call_args[0] == (
            'action{delim}server_1'.format(delim=MCRUNNERD_COMMAND_DELIMITER),
        )

    def test_handle_server_action_with_command(self):
        controller = Controller(config_file=self.config_file.name)
        controller.send_mcrunnerd_package = mock.MagicMock()

        controller.handle_server_action('action', 'server_1', command='some command')

        assert controller.send_mcrunnerd_package.call_count == 1
        assert controller.send_mcrunnerd_package.call_args[0] == (
            'action{delim}server_1{delim}some command'.format(delim=MCRUNNERD_COMMAND_DELIMITER),
        )


class MCRunnerMainTestCase(unittest.TestCase):

    def test_output(self):
        with mock.patch.object(sys.stdout, 'write') as mock_write:
            mcrunner._output('test')

        assert mock_write.call_count == 1
        assert mock_write.call_args[0] == ('test\n',)

    @mock.patch.object(sys, 'argv', ['mcrunner'])
    def test_too_few_args(self):
        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with self.assertRaises(SystemExit):
                mcrunner.main()

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Usage: mcrunner <command> [arguments]',)

    @mock.patch.object(sys, 'argv', ['mcrunner', 'status'])
    def test_status(self):
        mock_controller = mock.MagicMock()

        with mock.patch('mcrunner.mcrunner.Controller', return_value=mock_controller):
            mcrunner.main()

        assert mock_controller.handle_mcrunnerd_action.call_count == 1
        assert mock_controller.handle_mcrunnerd_action.call_args[0] == ('status',)

    @mock.patch.object(sys, 'argv', ['mcrunner', 'start'])
    def test_start_too_few_args(self):
        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with self.assertRaises(SystemExit):
                mcrunner.main()

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Usage: mcrunner start <server_name>',)

    @mock.patch.object(sys, 'argv', ['mcrunner', 'start', 'server_1'])
    def test_start(self):
        mock_controller = mock.MagicMock()

        with mock.patch('mcrunner.mcrunner.Controller', return_value=mock_controller):
            mcrunner.main()

        assert mock_controller.handle_server_action.call_count == 1
        assert mock_controller.handle_server_action.call_args[0] == ('start', 'server_1')

    @mock.patch.object(sys, 'argv', ['mcrunner', 'command'])
    def test_command_too_few_args_no_server(self):
        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with self.assertRaises(SystemExit):
                mcrunner.main()

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Usage: mcrunner command <server_name> <command>',)

    @mock.patch.object(sys, 'argv', ['mcrunner', 'command', 'server_1'])
    def test_command_too_few_args(self):
        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with self.assertRaises(SystemExit):
                mcrunner.main()

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Usage: mcrunner command server_1 <command>',)

    @mock.patch.object(sys, 'argv', ['mcrunner', 'command', 'server_1', 'say something'])
    def test_command(self):
        mock_controller = mock.MagicMock()

        with mock.patch('mcrunner.mcrunner.Controller', return_value=mock_controller):
            mcrunner.main()

        assert mock_controller.handle_server_action.call_count == 1
        assert mock_controller.handle_server_action.call_args == ((
            'command',
            'server_1',
        ), {
            'command': 'say something'
        })

    @mock.patch.object(sys, 'argv', ['mcrunner', 'bad_command'])
    def test_bad_arguments(self):
        with mock.patch('mcrunner.mcrunner._output') as mock_print:
            with self.assertRaises(SystemExit):
                mcrunner.main()

        assert mock_print.call_count == 1
        assert mock_print.call_args[0] == ('Unknown command: bad_command',)
