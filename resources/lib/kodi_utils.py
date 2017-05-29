import xbmc
import xbmcgui
import xbmcplugin

import sys
import json

from simple_logging import SimpleLogging

log = SimpleLogging(__name__)


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
        # log.debug('HomeWindow: getProperty |%s| -> |%s|' % (key, value))
        return value

    def setProperty(self, key, value):
        key = self.id_string % key
        # log.debug('HomeWindow: setProperty |%s| -> |%s|' % (key, value))
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        key = self.id_string % key
        # log.debug('HomeWindow: clearProperty |%s|' % key)
        self.window.clearProperty(key)


def addMenuDirectoryItem(label, path, folder=True, thumbnail=None):
    li = xbmcgui.ListItem(label, path=path)
    if thumbnail is None:
        thumbnail = "special://home/addons/plugin.video.embycon/icon.png"
    li.setIconImage(thumbnail)
    li.setThumbnailImage(thumbnail)
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
        log.info("Version : " + str(version) + " - " + str(versionData))
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data : " + str(result))

    return version
