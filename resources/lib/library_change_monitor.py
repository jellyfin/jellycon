import threading
import time

import xbmc
import xbmcaddon

from .simple_logging import SimpleLogging
from .widgets import checkForNewContent
from .tracking import timer

log = SimpleLogging(__name__)


class LibraryChangeMonitor(threading.Thread):

    last_library_change_check = 0
    library_check_triggered = False
    exit_now = False

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

            if self.library_check_triggered and (time.time() - self.last_library_change_check) > 60 and not xbmc.Player().isPlaying():
                log.debug("Doing new content check")
                checkForNewContent()
                self.library_check_triggered = False
                self.last_library_change_check = time.time()

            if self.exit_now or monitor.waitForAbort(5):
                break

        log.debug("Library Monitor Exited")
