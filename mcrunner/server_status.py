from __future__ import absolute_import

from enum import Enum


class ServerStatus(Enum):
    STARTING = 'Starting'
    RUNNING = 'Running'
    STOPPED = 'Stopped'
