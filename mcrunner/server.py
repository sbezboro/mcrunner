try:
    # Python 2.x
    import subprocess32 as subprocess
except ImportError:
    # Python 3.x
    import subprocess


SERVER_STOP_TIMEOUT_SEC = 60


class ServerStartException(Exception):
    pass


class ServerNotRunningException(Exception):
    pass


class MinecraftServer(object):

    """
    Minecraft Server class. Interface for communication to the Minecraft
    server jar instance.
    """

    name = None
    path = None
    jar = None
    opts = None
    pipe = None

    output = None

    def __init__(self, name, path, jar, opts):
        self.name = name
        self.path = path
        self.jar = jar
        self.opts = opts

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
        args = [
            '/usr/bin/java',
            '-jar',
            '%s/%s' % (self.path, self.jar)
        ]

        args.extend(self.opts.split())

        if connection:
            connection.send_message('Starting server %s...' % self.name)

        self._start_jar(args)

        if connection:
            connection.send_message('Server %s started.' % self.name)

    def stop(self, connection=None):
        """
        Attempt to stop the running jar.
        """
        if not self.pipe:
            raise ServerNotRunningException

        if connection:
            connection.send_message('Stopping server %s...' % self.name)

        self.run_command('stop')

        if connection:
            try:
                self.pipe.wait(timeout=SERVER_STOP_TIMEOUT_SEC)
            except subprocess.TimeoutExpired:
                connection.send_message('Server did not stop within %s seconds. Killing...' % SERVER_STOP_TIMEOUT_SEC)
                self.pipe.terminate()
            else:
                connection.send_message('Server %s stopped.' % self.name)

    def get_status(self):
        """
        Get the status of the server jar.
        Returns either 'Running' or 'Not running'
        """
        try:
            self.run_command('ping')
        except ServerNotRunningException:
            return 'Not running'

        return 'Running'

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
