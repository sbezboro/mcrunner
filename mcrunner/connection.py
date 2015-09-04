import struct


class BaseSocketConnection(object):

    def __init__(self, sock_conn):
        self.sock_conn = sock_conn

    def send_message(self, message):
        length = len(message)

        self.sock_conn.sendall(struct.pack('>I', length) + message.encode('utf8'))

    def receive_message(self):
        raw_length = self._receive_data(4)
        if not raw_length:
            return None

        length = struct.unpack('>I', raw_length.encode('utf8'))[0]
        return self._receive_data(length)

    def close(self):
        self.sock_conn.close()

    def _receive_data(self, num):
        result = ''

        while len(result) < num:
            data = self.sock_conn.recv(num - len(result))

            if not data:
                return None

            result += data

        return result


class ClientSocketConnection(BaseSocketConnection):
    pass


class ServerSocketConnection(BaseSocketConnection):

    def close(self):
        self.send_message('')
        super(ServerSocketConnection, self).close()
