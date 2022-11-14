from __future__ import division, absolute_import, print_function, unicode_literals

import threading
import time

import xbmc
from .functions import show_menu
from .lazylogger import LazyLogger
from .widgets import check_for_new_content
from .tracking import timer

log = LazyLogger(__name__)


class ContextMonitor(threading.Thread):

    stop_thread = False

    def run(self):

        item_id = None
        series_id = None
        item_name = None
        log.debug("ContextMonitor Thread Started")

        while not xbmc.Monitor().abortRequested() and not self.stop_thread:

            if xbmc.getCondVisibility("Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)"):
                xbmc.sleep(1000)
            else:
                if xbmc.getCondVisibility("Window.IsVisible(contextmenu)"):
                    if item_id:
                        xbmc.executebuiltin("Dialog.Close(contextmenu,true)")
                        params = {}
                        params["item_id"] = item_id
                        params["series_id"] = series_id
                        params["item_name"] = item_name
                        show_menu(params)

                container_id = xbmc.getInfoLabel("System.CurrentControlID")
                item_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(id)")
                series_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(series_id)")
                item_name = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(name)")

                xbmc.sleep(100)

        log.debug("ContextMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_thread = True


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
