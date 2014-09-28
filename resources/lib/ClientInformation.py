from uuid import getnode as get_mac
import xbmcaddon

class ClientInformation():

    def getMachineId(self):
        return "%012X"%get_mac()
        
    def getVersion(self):
        version = xbmcaddon.Addon(id="plugin.video.xbmb3c").getAddonInfo("version")
        return version
