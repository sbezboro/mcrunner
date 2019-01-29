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
import pwd
import socket
import sys

from mcrunner import __version__
from mcrunner.connection import ServerSocketConnection
from mcrunner.daemon import Daemon
from mcrunner.exceptions import (
    ConfigException,
    MCRunnerException,
    ServerNotRunningException,
    ServerStartException,
)
from mcrunner.server import MinecraftServer
from mcrunner.server_status import ServerStatus

logger = logging.getLogger(__name__)

MCRUNNERD_COMMAND_DELIMITER = '|+|'


class MCRunner(Daemon):

    """
    MCRunner daemon class (mcrunnerd).

    On startup, the mcrunnerd daemon creates a unix socket which facilitates communication
    between the daemon process and MCRunner client frontends. MCRunner clients use the
    socket for primitive communication to start and stop Minecraft
    """

    CONFIG_DEFAULTS = {
        'user': None
    }

    log_file = None
    user = None
    sock_file = None

    servers = None

    def __init__(self, *args, **kwargs):
        self.config_file = kwargs.pop('config_file', '/etc/mcrunner/mcrunner.conf')
        self.pid_file = kwargs.pop('pid_file', '/tmp/mcrunner.pid')

        if not os.path.exists(self.config_file):
            raise ConfigException('Config file missing: %s' % self.config_file)

        self.load_config()

        self.setup_logger()

        self.set_uid()

        super(MCRunner, self).__init__(self.pid_file, *args, **kwargs)

    def load_config(self):
        """
        Load config from file.
        """
        self.servers = {}

        config = configparser.ConfigParser(defaults=self.CONFIG_DEFAULTS)
        config.read(self.config_file)

        for section in config.sections():
            if section == 'mcrunnerd':
                self.log_file = config.get(section, 'logfile')
                self.user = config.get(section, 'user')
            elif section == 'mcrunner':
                self.sock_file = config.get(section, 'url')
            elif section.startswith('server:'):
                _, name = section.split('server:')

                items = config.items(section)

                items_dict = dict(items)

                # convert bool values
                for k, v in items_dict.items():
                    if isinstance(v, str):
                        if v.lower() in ('false', 'no', 'off'):
                            items_dict[k] = False
                        elif v.lower() in ('true', 'yes', 'on'):
                            items_dict[k] = True

                self.servers[name] = MinecraftServer(
                    name,
                    items_dict.pop('path'),
                    items_dict.pop('jar'),
                    items_dict.pop('opts'),
                    **items_dict
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

    def setup_logger(self):
        """
        Setup root logger for use in all modules.
        """
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.handlers.RotatingFileHandler(self.log_file, maxBytes=2000000, backupCount=10)
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def get_status(self, connection):
        """
        Return a string representation of all server statuses.
        """
        response = []

        for server_name, server in self.servers.items():
            response.append('%s: %s' % (server_name, server.get_status().value))

        connection.send_message('\n'.join(response))

    def start_minecraft_server(self, name, connection=None):
        """
        Attempt to start a server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            if connection:
                connection.send_message('Minecraft server "%s" not defined.' % name)
            return

        try:
            server.start(connection=connection)
        except ServerStartException:
            pass

    def stop_minecraft_server(self, name, connection=None):
        """
        Attempt to stop a server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            if connection:
                connection.send_message('Minecraft server "%s" not defined' % name)
            return

        try:
            server.stop(connection=connection)
        except ServerNotRunningException:
            pass

    def send_command(self, name, command, connection):
        """
        Send command string to server of a given name.
        """
        server = self.servers.get(name)
        if not server:
            connection.send_message('Minecraft server "%s" not defined' % name)
            return

        logger.info('Sending command to server "%s": "%s"', name, command)

        try:
            server.run_command(command, connection=connection)
        except ServerNotRunningException:
            message = 'Minecraft server "%s" not running' % name

            logger.warning(message)
            connection.send_message(message)
        else:
            connection.send_message('Sent command to Minecraft server "%s": "%s"' % (name, command))

    def handle_socket_data(self, data, connection):
        """
        Handles socket data from an mcrunner client and returns a two-tuple
        of a bool indicating whether a response is warranted and the message string
        of the response if any.
        """
        parts = data.split(MCRUNNERD_COMMAND_DELIMITER)

        if parts[0] == 'status':
            self.get_status(connection)
        elif parts[0] == 'start':
            self.start_minecraft_server(parts[1], connection=connection)
        elif parts[0] == 'stop':
            self.stop_minecraft_server(parts[1], connection=connection)
        elif parts[0] == 'restart':
            self.stop_minecraft_server(parts[1], connection=connection)
            self.start_minecraft_server(parts[1], connection=connection)
        elif parts[0] == 'command':
            self.send_command(parts[1], parts[2], connection)

    def on_exit(self):
        """
        Exit signal handler, attempt to shut down all Minecraft servers.
        """
        for server_name, server in self.servers.items():
            if server.get_status() == ServerStatus.RUNNING:
                self.stop_minecraft_server(server_name)

    def set_uid(self):
        """
        Set uid for daemon.
        """
        if not self.user:
            return

        try:
            pwnam = pwd.getpwnam(self.user)
        except KeyError:
            logger.error('User not found for setuid: %s' % self.user)
            sys.exit(1)

        uid = pwnam.pw_uid

        current_uid = os.getuid()

        if current_uid == uid:
            # Already running as the correct user
            return

        if current_uid != 0:
            logger.error('Can\'t setuid if not running as root')
            sys.exit(1)

        try:
            os.setuid(uid)
        except OSError:
            logger.error('Could not switch to user %s' % self.user)
            sys.exit(1)

    def run(self):
        """
        Main daemon runloop function. Handles receiving and responding to MCRunner
        client commands.
        """
        atexit.register(self.on_exit)

        self._log_and_output('info', 'Starting mcrunnerd (%s)...' % __version__)

        try:
            sock = self.socket_server()
        except Exception as e:
            self._log_and_output('exception', 'Could not start mcrunnerd: %s' % str(e))
            return

        self._log_and_output('info', 'mcrunnerd (%s) started.' % __version__)

        while True:
            try:
                logger.debug('Awaiting socket connection')
                conn, client_address = sock.accept()

                connection = ServerSocketConnection(conn)

                logger.debug('Established socket connection')

                try:
                    data = connection.receive_message()

                    logger.debug('Handling socket data')
                    self.handle_socket_data(data, connection)
                    logger.debug('Socket data handled')
                finally:
                    logger.debug('Closing socket connection')
                    connection.close()
            except socket.error:
                self._log_and_output('exception', 'Error during socket connection')
            except SystemExit:
                self._log_and_output('info', 'Stopping mcrunnerd (%s)...' % __version__)
                break

        self._log_and_output('info', 'mcrunnerd (%s) stopped.' % __version__)

    def _log_and_output(self, level, message):
        if level in ['debug', 'info', 'warning', 'error', 'exception']:
            getattr(logger, level)(message)

        if level in ['error', 'exception']:
            _error(message)
        elif level != 'debug':
            _output(message)


def _output(string):
    sys.stdout.write('%s\n' % string)


def _error(string):
    sys.stderr.write('%s\n' % string)


def main():
    try:
        daemon = MCRunner()
    except MCRunnerException as e:
        _error(str(e))
        sys.exit(2)

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
