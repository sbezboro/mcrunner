#!/usr/bin/env python
from __future__ import absolute_import, print_function

try:
    # Python 2.x
    import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser

import socket
import sys

from mcrunner.mcrunnerd import COMMAND_RESPONSE_STATUSES, MCRUNNERD_COMMAND_DELIMITER


class Controller(object):

    """
    Controller class. Used to interface with an mcrunnerd process to control
    Minecraft servers.
    """

    sock_file = None
    attached = False
    screen = None

    def __init__(self, *args, **kwargs):
        self.config_file = kwargs.get('config_file', '/etc/mcrunner/mcrunner.conf')

        self.load_config()

    def socket_client(self):
        """
        Create a socket client and attempt to connect to the mcrunnerd unix socket.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.sock_file)

        return sock

    def load_config(self):
        """
        Load config from file.
        """
        config = ConfigParser.ConfigParser()
        config.read(self.config_file)

        for section in config.sections():
            if section == 'mcrunner':
                self.sock_file = config.get(section, 'url')

    def send_mcrunnerd_package(self, package):
        """
        Send a mcrunnerd package to the mcrunnerd unix socket.
        """
        try:
            sock = self.socket_client()
        except socket.error:
            print('Could not connect to socket - is mcrunnerd running?')
            return

        try:
            sock.sendall(package)
        except Exception as e:
            print('Error sending mcrunnerd package: %s' % e)
        else:
            # get command status
            data = sock.recv(1)

            if data == COMMAND_RESPONSE_STATUSES['MESSAGE']:
                data = sock.recv(1000)
                print(data)
        finally:
            sock.close()

    def handle_mcrunnerd_action(self, action):
        """
        Handle simple actions and send to mcrunnerd instance.
        """
        self.send_mcrunnerd_package('%s' % action)

    def handle_server_action(self, action, server, command=None):
        """
        Handle server actions/commands and send to mcrunnerd instance.
        """
        if command:
            self.send_mcrunnerd_package('{action}{delimiter}{server}{delimiter}{command}'.format(
                action=action,
                server=server,
                command=command,
                delimiter=MCRUNNERD_COMMAND_DELIMITER
            ))
        else:
            self.send_mcrunnerd_package('{action}{delimiter}{server}'.format(
                action=action,
                server=server,
                delimiter=MCRUNNERD_COMMAND_DELIMITER
            ))


def main():
    controller = Controller()

    if len(sys.argv) == 1:
        print('Usage: %s <command> [arguments]' % sys.argv[0])
        sys.exit(2)

    if sys.argv[1] == 'status':
        controller.handle_mcrunnerd_action(sys.argv[1])
    elif sys.argv[1] in ('start', 'stop'):
        if len(sys.argv) == 2:
            print('Usage: %s %s <server_name>' % (sys.argv[0], sys.argv[1]))
            sys.exit(2)

        server = sys.argv[2]

        controller.handle_server_action(sys.argv[1], server)
    elif sys.argv[1] == 'command':
        if len(sys.argv) == 2:
            print('Usage: %s %s <server_name> <command>' % (sys.argv[0], sys.argv[1]))
            sys.exit(2)

        if len(sys.argv) == 3:
            print('Usage: %s %s %s <command>' % (sys.argv[0], sys.argv[1], sys.argv[2]))
            sys.exit(2)

        controller.handle_server_action(sys.argv[1], sys.argv[2], command=sys.argv[3])
    else:
        print("Unknown command: %s" % sys.argv[1])
        sys.exit(2)


if __name__ == '__main__':
    main()
