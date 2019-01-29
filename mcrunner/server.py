from __future__ import absolute_import

import logging

try:
    # Python 2.x
    import subprocess32 as subprocess
except ImportError:
    # Python 3.x
    import subprocess

from mcrunner.exceptions import ServerNotRunningException, ServerStartException
from mcrunner.server_status import ServerStatus

logger = logging.getLogger(__name__)

SERVER_STOP_TIMEOUT_SEC = 60


class MinecraftServer(object):

    """
    Minecraft Server class. Interface for communication to the Minecraft
    server jar instance.
    """

    name = None
    path = None
    jar = None
    opts = None

    restart_on_plugin_update = False

    pipe = None
    output = None
    plugin_change_observer = None

    def __init__(self, name, path, jar, opts, **kwargs):
        self.name = name
        self.path = path
        self.jar = jar
        self.opts = opts

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def _start_jar(self, args):
        self.pipe = subprocess.Popen(
            args,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def start(self, connection=None):
        """
        Start the Minecraft server jar.
        """
        args = ['/usr/bin/java']
        args.extend(self.opts.split())
        args.extend([
            '-jar',
            '%s/%s' % (self.path, self.jar)
        ])

        message = 'Starting Minecraft server "%s"...' % self.name
        logger.info(message)
        if connection:
            connection.send_message(message)

        try:
            self._start_jar(args)
        except OSError as e:
            message = 'Could not start server "%s"! Reason: %s' % (self.name, str(e))

            logger.warning(message)
            if connection:
                connection.send_message(message)

            raise ServerStartException(e)

        message = 'Minecraft server "%s" started.' % self.name
        logger.info(message)
        if connection:
            connection.send_message(message)

        if self.restart_on_plugin_update and not self.plugin_change_observer:
            self.plugin_change_observer = self._get_plugin_change_observer()
            if self.plugin_change_observer:
                logger.info('Starting plugin change observer for server "%s"' % self.name)
                self.plugin_change_observer.start()

    def stop(self, connection=None):
        """
        Attempt to stop the running jar.
        """
        if not self.pipe:
            if connection:
                connection.send_message('Minecraft server "%s" not running.' % self.name)

            raise ServerNotRunningException

        message = 'Stopping Minecraft server "%s"...' % self.name
        logger.info(message)
        if connection:
            connection.send_message(message)

        self.run_command('stop')

        try:
            self.pipe.wait(timeout=SERVER_STOP_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            message = 'Server "%s" did not stop within %s seconds. Killing...' % (self.name, SERVER_STOP_TIMEOUT_SEC)
            logger.info(message)
            if connection:
                connection.send_message(message)

            self.pipe.terminate()
        else:
            message = 'Minecraft server "%s" stopped.' % self.name
            logger.info(message)
            if connection:
                connection.send_message(message)

        self.pipe = None

    def restart(self, plugin_update=False):
        """
        Restart the server.
        :param plugin_update: true if the restart is triggered by a plugin update
        :return:
        """
        if plugin_update:
            logger.info('Detected plugin update, beginning automatic restart.')

        try:
            self.stop()
        except ServerNotRunningException:
            # ignore
            pass

        self.start()

    def get_status(self):
        """
        Get the status of the server jar
        """
        try:
            self.run_command('ping')
        except ServerNotRunningException:
            return ServerStatus.STOPPED

        return ServerStatus.RUNNING

    def run_command(self, command, connection=None):
        """
        Attempt to run a command on the server.
        """
        if not self.pipe:
            raise ServerNotRunningException

        try:
            self.pipe.stdin.write('%s\n' % command)
        except Exception:
            raise ServerNotRunningException

    def _get_plugin_change_observer(self):
        try:
            from watchdog.observers import Observer
            from mcrunner.plugin_change import PluginChangeEventHandler
        except ImportError:
            logger.warning('Cannot start plugin change observer, watchdog package not installed.')
            return None

        path = '%s/plugins/' % self.path
        event_handler = PluginChangeEventHandler(self)
        observer = Observer()

        try:
            observer.schedule(event_handler, path, recursive=False)
        except OSError as e:
            logger.warning('Cannot start plugin change observer, reason: %s.' % str(e))
            return None

        return observer
