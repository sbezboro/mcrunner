from __future__ import absolute_import


class MCRunnerException(Exception):
    pass


class ConfigException(MCRunnerException):
    pass


class ServerStartException(MCRunnerException):
    pass


class ServerNotRunningException(MCRunnerException):
    pass
