import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys
import json

from simple_logging import SimpleLogging

log = SimpleLogging(__name__)
addon = xbmcaddon.Addon()

class HomeWindow():
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """

    def __init__(self):
        self.id_string = 'plugin.video.embycon-%s'
        self.window = xbmcgui.Window(10000)

    def getProperty(self, key):
        key = self.id_string % key
        value = self.window.getProperty(key)
        # log.debug('HomeWindow: getProperty |{0}| -> |{1}|', key, value)
        return value

    def setProperty(self, key, value):
        key = self.id_string % key
        # log.debug('HomeWindow: setProperty |{0}| -> |{1}|', key, value)
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        key = self.id_string % key
        # log.debug('HomeWindow: clearProperty |{0}|', key)
        self.window.clearProperty(key)


def addMenuDirectoryItem(label, path, folder=True, art=None):
    li = xbmcgui.ListItem(label, path=path)
    if art is not None:
        li.setArt(art)
        #thumbnail = addon.getAddonInfo('icon')
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder)


def getKodiVersion():
    version = 0.0
    jsonData = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')

    result = json.loads(jsonData)

    try:
        result = result.get("result")
        versionData = result.get("version")
        version = float(str(versionData.get("major")) + "." + str(versionData.get("minor")))
        log.debug("Version: {0} - {1}", version, versionData)
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data: {0}", result)

    return version
