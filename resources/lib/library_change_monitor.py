from __future__ import division, absolute_import, print_function, unicode_literals

import threading
import time

import xbmc

from .loghandler import LazyLogger
from .widgets import check_for_new_content
from .tracking import timer

log = LazyLogger(__name__)


class LibraryChangeMonitor(threading.Thread):

    last_library_change_check = 0
    library_check_triggered = False
    exit_now = False
    time_between_checks = 10

    def __init__(self):
        threading.Thread.__init__(self)

    def stop(self):
        self.exit_now = True

    @timer
    def check_for_updates(self):
        log.debug("Trigger check for updates")
        self.library_check_triggered = True

    def run(self):
        log.debug("Library Monitor Started")
        monitor = xbmc.Monitor()
        while not self.exit_now and not monitor.abortRequested():

            if self.library_check_triggered and not xbmc.Player().isPlaying():
                log.debug("Doing new content check")
                check_for_new_content()
                self.library_check_triggered = False
                self.last_library_change_check = time.time()

            if self.exit_now or monitor.waitForAbort(self.time_between_checks):
                break

        log.debug("Library Monitor Exited")
