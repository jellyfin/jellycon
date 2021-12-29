from __future__ import division, absolute_import, print_function, unicode_literals

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys
import json

from .loghandler import LazyLogger
from .functions import show_menu

log = LazyLogger(__name__)
addon = xbmcaddon.Addon()


class HomeWindow:
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """

    def __init__(self):
        self.id_string = 'plugin.video.jellycon-%s'
        self.window = xbmcgui.Window(10000)

    def get_property(self, key):
        key = self.id_string % key
        value = self.window.getProperty(key)
        return value

    def set_property(self, key, value):
        key = self.id_string % key
        self.window.setProperty(key, value)

    def clear_property(self, key):
        key = self.id_string % key
        self.window.clearProperty(key)


def add_menu_directory_item(label, path, folder=True, art=None):
    li = xbmcgui.ListItem(label, path=path)
    if art is None:
        art = {}
        art["thumb"] = addon.getAddonInfo('icon')
    li.setArt(art)

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder)


def get_kodi_version():

    json_data = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')

    result = json.loads(json_data)

    try:
        result = result.get("result")
        version_data = result.get("version")
        version = float(str(version_data.get("major")) + "." + str(version_data.get("minor")))
        log.debug("Version: {0} - {1}".format(version, version_data))
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data: {0}".format(result))

    return version


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
