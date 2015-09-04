import unittest
import mock

from mcrunner.connection import BaseSocketConnection, ServerSocketConnection


class BaseSocketConnectionTestCase(unittest.TestCase):

    def test_send_message(self):
        mock_sock = mock.MagicMock()
        connection = BaseSocketConnection(mock_sock)

        connection.send_message('some message')

        assert mock_sock.sendall.call_count == 1
        assert mock_sock.sendall.call_args[0] == (b'\x00\x00\x00\x0csome message',)

    def test_receive_message(self):
        mock_sock = mock.MagicMock()
        mock_sock.recv = mock.MagicMock(side_effect=[
            '\x00\x00\x00\x0c',
            'some message'
        ])

        connection = BaseSocketConnection(mock_sock)

        result = connection.receive_message()

        assert result == 'some message'

    def test_receive_message_empty(self):
        mock_sock = mock.MagicMock()
        mock_sock.recv = mock.MagicMock(side_effect=[
            None,
            ''
        ])

        connection = BaseSocketConnection(mock_sock)

        result = connection.receive_message()

        assert result is None

    def test_close(self):
        mock_sock = mock.MagicMock()
        connection = BaseSocketConnection(mock_sock)

        connection.close()

        assert mock_sock.close.call_count == 1


class ServerSocketConnectionTestCase(unittest.TestCase):

    def test_close(self):
        mock_sock = mock.MagicMock()
        connection = ServerSocketConnection(mock_sock)
        connection.send_message = mock.MagicMock()

        connection.close()

        assert mock_sock.close.call_count == 1
        assert connection.send_message.call_count == 1
        assert connection.send_message.call_args[0] == ('',)
