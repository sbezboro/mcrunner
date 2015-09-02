import subprocess


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

    def start(self):
        """
        Start the Minecraft server jar.
        """
        args = [
            '/usr/bin/java',
            '-jar',
            '%s/%s' % (self.path, self.jar)
        ]

        args.extend(self.opts.split())

        self.pipe = subprocess.Popen(
            args,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def stop(self):
        """
        Attempt to stop the running jar.
        """
        if not self.pipe:
            raise ServerNotRunningException

        self.run_command('stop')

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

    def run_command(self, command):
        """
        Attempt to run a command on the server.
        """
        if not self.pipe:
            raise ServerNotRunningException

        try:
            self.pipe.stdin.write('%s\n' % command)
        except Exception:
            raise ServerNotRunningException
