#!/usr/bin/env python
from __future__ import absolute_import, print_function

try:
    # Python 2.x
    import ConfigParser as configparser
except ImportError:
    # Python 3.x
    import configparser

import atexit
import logging
import logging.handlers
import os
import socket
import sys

from mcrunner.daemon import Daemon
from mcrunner.server import MinecraftServer, ServerNotRunningException, ServerStartException


# Statuses returned to MCRunner clients to indicate the type of response to various commands
COMMAND_RESPONSE_STATUSES = {
    'MESSAGE': '0',
    'DONE': '1'
}

MCRUNNERD_COMMAND_DELIMITER = '|+|'


class MCRunner(Daemon):

    """
    MCRunner daemon class (mcrunnerd).

    On startup, the mcrunnerd daemon creates a unix socket which facilitates communication
    between the daemon process and MCRunner client frontends. MCRunner clients use the
    socket for primitive communication to start and stop Minecraft
    """

    sock_file = None
    logger = None

    servers = None

    def __init__(self, *args, **kwargs):
        self.config_file = kwargs.pop('config_file', '/etc/mcrunner/mcrunner.conf')
        self.pid_file = kwargs.pop('pid_file', '/tmp/mcrunner.pid')

        super(MCRunner, self).__init__(self.pid_file, *args, **kwargs)

    def load_config(self):
        """
        Load config from file.
        """
        self.servers = {}

        config = configparser.ConfigParser()
        config.read(self.config_file)

        for section in config.sections():
            if section == 'mcrunnerd':
                self.log_file = config.get(section, 'logfile')
            elif section == 'mcrunner':
                self.sock_file = config.get(section, 'url')
            elif section.startswith('server:'):
                _, name = section.split('server:')
                self.servers[name] = MinecraftServer(
                    name,
                    config.get(section, 'path'),
                    config.get(section, 'jar'),
                    config.get(section, 'opts')
                )

    def socket_server(self):
        """
        Create and initialize unix socket at the path stored in configuration.
        """
        try:
            os.unlink(self.sock_file)
        except OSError:
            pass

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.sock_file)
        sock.listen(1)

        return sock

    def create_logger(self):
        """
        Create simple logger.
        """
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.handlers.RotatingFileHandler(self.log_file, maxBytes=2000000, backupCount=10)
        handler.setFormatter(formatter)

        logger = logging.getLogger(__name__)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        return logger

    def get_status(self):
        """
        Return a string representation of all server statuses.
        """
        response = []

        for server_name, server in self.servers.items():
            response.append('%s: %s' % (server_name, server.get_status()))

        return True, '\n'.join(response)

    def start_minecraft_server(self, name):
        """
        Attempt to start a server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            return True, 'Minecraft server "%s" not defined' % name

        self.logger.info('Starting Minecraft server "%s"', name)

        try:
            server.start()
        except ServerStartException as e:
            return True, 'Could not start server! stderr:\n\n%s' % str(e)

        return True, 'Starting Minecraft server "%s"' % name

    def stop_minecraft_server(self, name):
        """
        Attempt to stop a server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            return True, 'Minecraft server "%s" not defined' % name

        self.logger.info('Stopping Minecraft server "%s"', name)

        try:
            server.stop()
        except ServerNotRunningException:
            message = 'Minecraft server "%s" not running' % name

            self.logger.info(message)
            return True, message

        return True, 'Stopping Minecraft server "%s"' % name

    def send_command(self, name, command):
        """
        Send command string to server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            return True, 'Minecraft server "%s" not defined' % name

        self.logger.info('Sending command to server "%s": "%s"', name, command)

        try:
            server.run_command(command)
        except ServerNotRunningException:
            message = 'Minecraft server "%s" not running' % name

            self.logger.info(message)
            return True, message

        return True, 'Sent command to Minecraft server "%s": "%s"' % (name, command)

    def handle_socket_data(self, data):
        """
        Handles socket data from an mcrunner client and returns a two-tuple
        of a bool indicating whether a response is warranted and the message string
        of the response if any.
        """
        parts = data.split(MCRUNNERD_COMMAND_DELIMITER)

        if parts[0] == 'status':
            return self.get_status()
        elif parts[0] == 'start':
            return self.start_minecraft_server(parts[1])
        elif parts[0] == 'stop':
            return self.stop_minecraft_server(parts[1])
        elif parts[0] == 'command':
            return self.send_command(parts[1], parts[2])

        return False, ''

    def on_exit(self):
        """
        Exit signal handler, attempt to shut down all Minecraft servers.
        """
        for server_name in self.servers:
            self.stop_minecraft_server(server_name)

    def run(self):
        """
        Main daemon runloop function. Handles receiving and responding to MCRunner
        client commands.
        """
        atexit.register(self.on_exit)

        self.load_config()

        self.logger = self.create_logger()

        self.logger.info('Starting mcrunnerd')
        sock = self.socket_server()
        self.logger.info('mcrunnerd started')

        while True:
            try:
                self.logger.debug('Awaiting socket connection')
                conn, client_address = sock.accept()
                self.logger.debug('Established socket connection')

                try:
                    data = conn.recv(1000)

                    self.logger.debug('Handling socket data')
                    should_respond, message = self.handle_socket_data(data)
                    self.logger.debug('Socket data handled')

                    if should_respond:
                        self.logger.debug('Responding')

                        conn.sendall(COMMAND_RESPONSE_STATUSES['MESSAGE'])
                        conn.sendall(message)

                        self.logger.debug('Responded')
                    else:
                        conn.sendall(COMMAND_RESPONSE_STATUSES['DONE'])
                finally:
                    conn.close()

                    self.logger.debug('Closing socket connection')
            except socket.error:
                self.logger.exception('Error during socket connection')
            except SystemExit:
                self.logger.info('Stopping mcrunnerd')
                break

        self.logger.info('mcrunnerd stopped')


def _output(string):
    sys.stdout.write('%s\n' % string)


def main():
    daemon = MCRunner()

    if len(sys.argv) == 1:
        _output("Usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)

    first_arg = sys.argv[1]

    if len(sys.argv) == 2:
        if first_arg == 'start':
            daemon.start()
        elif first_arg == 'stop':
            daemon.stop()
        elif first_arg == 'restart':
            daemon.restart()
        else:
            _output('Unknown command: %s' % first_arg)
            sys.exit(2)
    else:
        _output("Usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)


if __name__ == "__main__":
    main()
