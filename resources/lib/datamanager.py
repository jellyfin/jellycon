# Gnu General Public License - see LICENSE.TXT

import hashlib
import os
import threading
import json
import encodings

import xbmcaddon
import xbmc

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from utils import getChecksum
from kodi_utils import HomeWindow

log = SimpleLogging(__name__)

class DataManager():
    cacheDataResult = None
    dataUrl = None
    cacheDataPath = None
    canRefreshNow = False

    def __init__(self, *args):
        log.debug("DataManager __init__")

    def loadJasonData(self, jsonData):
        return json.loads(jsonData)

    def GetContent(self, url):
        jsonData = DownloadUtils().downloadUrl(url)
        result = self.loadJasonData(jsonData)
        return result


