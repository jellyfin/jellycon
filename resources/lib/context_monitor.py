import threading
import xbmc

from .loghandler import LazyLogger
from resources.lib.functions import show_menu

log = LazyLogger(__name__)


class ContextMonitor(threading.Thread):

    stop_thread = False

    def run(self):

        item_id = None
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
                        show_menu(params)

                container_id = xbmc.getInfoLabel("System.CurrentControlID")
                item_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(id)")

                xbmc.sleep(100)

        log.debug("ContextMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_thread = True
