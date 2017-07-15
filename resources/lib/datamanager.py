# Gnu General Public License - see LICENSE.TXT

import hashlib
import os
import threading
import json

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

    def getCacheValidatorFromData(self, result):
        key = 'Items'
        results = result.get(key)
        if results is None:
            key = 'SearchHints'
            results = result.get(key)
            if results is None:
                results = []

        itemCount = 0
        dataHashString = ""

        for item in results:
            item_hash_string = getChecksum(item)
            item_hash_string = str(itemCount) + "_" + key + "_" + item.get("Name", "-") + "_" + item_hash_string + "|"
            log.debug("ITEM_HASH: " + item_hash_string)
            dataHashString += item_hash_string
            itemCount += 1

        # hash the data
        dataHashString = dataHashString.encode("UTF-8")
        m = hashlib.md5()
        m.update(dataHashString)
        validatorString = m.hexdigest()

        log.debug("getCacheValidatorFromData : RawData  : " + dataHashString)
        log.debug("getCacheValidatorFromData : hashData : " + validatorString)

        return validatorString

    def loadJasonData(self, jsonData):
        return json.loads(jsonData)

    def GetContent(self, url):

        __addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
        use_cache_system = __addon__.getSetting('cacheEmbyData') == "true"

        if use_cache_system == False:
            # dont use cache system at all, just get the result and return
            log.debug("GetContent - Not using cache system")
            jsonData = DownloadUtils().downloadUrl(url, suppress=False, popup=1)
            result = self.loadJasonData(jsonData)
            log.debug("Returning Loaded Result")
            return result

        # first get the url hash
        m = hashlib.md5()
        m.update(url)
        urlHash = m.hexdigest()

        # build cache data path

        __addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
        if not os.path.exists(os.path.join(__addondir__, "cache")):
            os.makedirs(os.path.join(__addondir__, "cache"))
        cacheDataPath = os.path.join(__addondir__, "cache", urlHash)

        log.debug("Cache_Data_Manager:" + cacheDataPath)

        # are we forcing a reload
        WINDOW = HomeWindow()
        force_data_reload = WINDOW.getProperty("force_data_reload") == "true"
        WINDOW.clearProperty("force_data_reload")

        if os.path.exists(cacheDataPath) and not force_data_reload:
            # load data from cache if it is available and trigger a background
            # verification process to test cache validity   
            log.debug("Loading Cached File")
            with open(cacheDataPath, 'r') as f:
                result = self.loadJasonData(f.read())

            # start a worker thread to process the cache validity
            self.cacheDataResult = result
            self.dataUrl = url
            self.cacheDataPath = cacheDataPath
            actionThread = CacheManagerThread()
            actionThread.setCacheData(self)
            actionThread.start()

            log.debug("Returning Cached Result")
            return result
        else:
            # no cache data so load the url and save it
            jsonData = DownloadUtils().downloadUrl(url, suppress=False, popup=1)
            log.debug("Loading URL and saving to cache")
            with open(cacheDataPath, 'w') as f:
                f.write(jsonData)
            result = self.loadJasonData(jsonData)
            self.cacheManagerFinished = True
            log.debug("Returning Loaded Result")
            return result


class CacheManagerThread(threading.Thread):
    dataManager = None

    def __init__(self, *args):
        threading.Thread.__init__(self, *args)

    def setCacheData(self, data):
        self.dataManager = data

    def run(self):

        log.debug("CacheManagerThread Started")

        cacheValidatorString = self.dataManager.getCacheValidatorFromData(self.dataManager.cacheDataResult)
        log.debug("Cache Validator String (" + cacheValidatorString + ")")

        jsonData = DownloadUtils().downloadUrl(self.dataManager.dataUrl, suppress=False, popup=1)
        loadedResult = self.dataManager.loadJasonData(jsonData)
        loadedValidatorString = self.dataManager.getCacheValidatorFromData(loadedResult)
        log.debug("Loaded Validator String (" + loadedValidatorString + ")")

        # if they dont match then save the data and trigger a content reload
        if (cacheValidatorString != loadedValidatorString):
            log.debug("CacheManagerThread Saving new cache data and reloading container")
            with open(self.dataManager.cacheDataPath, 'w') as f:
                f.write(jsonData)

            # we need to refresh but will wait until the main function has finished
            loops = 0
            while (self.dataManager.canRefreshNow == False and loops < 200 and not xbmc.Monitor().abortRequested()):
                log.debug("Cache_Data_Manager: Not finished yet")
                xbmc.sleep(100)
                loops = loops + 1

            log.debug("Sending container refresh (" + str(loops) + ")")
            xbmc.executebuiltin("Container.Refresh")

        log.debug("CacheManagerThread Exited")
