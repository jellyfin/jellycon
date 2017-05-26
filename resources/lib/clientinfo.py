# Gnu General Public License - see LICENSE.TXT

from uuid import uuid4 as uuid4
import xbmcaddon
import xbmc
import xbmcvfs

from kodi_utils import HomeWindow
from simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon." + __name__)

class ClientInformation():

    def getDeviceId(self):
    
        WINDOW = HomeWindow()
        client_id = WINDOW.getProperty("client_id")

        if client_id:
            return client_id

        emby_guid_path = xbmc.translatePath("special://temp/emby_guid").decode('utf-8')
        log.info("emby_guid_path: " + emby_guid_path)
        guid = xbmcvfs.File(emby_guid_path)
        client_id = guid.read()
        guid.close()

        if not client_id:
            client_id = str("%012X" % uuid4())
            log.info("Generating a new guid: " + client_id)
            guid = xbmcvfs.File(emby_guid_path, 'w')
            guid.write(client_id)
            guid.close()

        WINDOW.setProperty("client_id", client_id)
        return client_id
        
    def getVersion(self):
        version = xbmcaddon.Addon(id="plugin.video.embycon").getAddonInfo("version")
        return version

    def getClient(self):
        return 'Kodi EmbyCon'
