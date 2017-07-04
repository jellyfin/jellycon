
import json

from kodi_utils import HomeWindow
from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
log = SimpleLogging(__name__)

def getServerId():

    home_screen = HomeWindow()
    server_id = home_screen.getProperty("server_id")
    if server_id:
        log.info("Server ID from stored value: " + server_id)
        return server_id

    downloadUtils = DownloadUtils()
    try:
        url = "{server}/emby/system/info/public"
        jsonData = downloadUtils.downloadUrl(url, suppress=True, authenticate=False)
        result = json.loads(jsonData)
        if result is not None and result.get("Id") is not None:
            server_id = result.get("Id")
            log.info("Server ID from server request: " + server_id)
            home_screen.setProperty("server_id", server_id)
            return server_id
        else:
            return None
    except Exception as error:
        log.info("Could not get Server ID: " + str(error))
        return None








