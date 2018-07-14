import threading
import sys
import xbmc
import xbmcgui

from simple_logging import SimpleLogging
from resources.lib.functions import show_menu

log = SimpleLogging(__name__)


class ContextMonitor(threading.Thread):

    stop_monitor = False

    def run(self):

        #condition_command = "(Window.IsVisible(DialogContextMenu.xml) + !String.IsEmpty(ListItem.Property(id)) + String.StartsWith(ListItem.Path,plugin://plugin.video.embycon))"
        condition_command = ("Window.IsVisible(DialogContextMenu.xml) + " +
                             "[Window.IsActive(Home) | " +
                             "[!String.IsEmpty(ListItem.Property(id) + " +
                             "String.StartsWith(ListItem.Path,plugin://plugin.video.embycon)]]")

        monitor = xbmc.Monitor()
        log.debug("ContextMonitor Thread Started")

        while not xbmc.abortRequested:

            if xbmc.getCondVisibility(condition_command):
                log.debug("ContextMonitor Found Context Menu!!!!!!")
                xbmc.executebuiltin("Dialog.Close(contextmenu, true)")

                item_id = xbmc.getInfoLabel('ListItem.Property(id)')
                if item_id:
                    log.debug("ContextMonitor Item ID: {0}", item_id)
                    params = {}
                    params["item_id"] = item_id
                    show_menu(params)

            xbmc.sleep(200)

        log.debug("ContextMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_monitor = True
