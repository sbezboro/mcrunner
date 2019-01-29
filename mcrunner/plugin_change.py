from __future__ import absolute_import

from watchdog.events import FileSystemEventHandler

from mcrunner.server_status import ServerStatus


class PluginChangeEventHandler(FileSystemEventHandler):

    server = None

    def __init__(self, server):
        super(PluginChangeEventHandler, self).__init__()
        self.server = server

    def _check_and_restart(self, event):
        if (not event.is_directory and
                event.src_path.endswith('.jar') and
                self.server.get_status() == ServerStatus.RUNNING):
            self.server.restart(plugin_update=True)

    def on_created(self, event):
        super(PluginChangeEventHandler, self).on_created(event)
        self._check_and_restart(event)

    def on_deleted(self, event):
        super(PluginChangeEventHandler, self).on_deleted(event)
        # TODO: fix this when server pending startup status is detected
        # self._check_and_restart(event)

    def on_modified(self, event):
        super(PluginChangeEventHandler, self).on_modified(event)
        self._check_and_restart(event)
