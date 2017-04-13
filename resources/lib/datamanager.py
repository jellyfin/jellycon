# Gnu General Public License - see LICENSE.TXT

import hashlib
import os
import threading
import json as json

import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from utils import getChecksum

log = SimpleLogging("EmbyCon." + __name__)

class DataManager():

    cacheDataResult = None
    dataUrl = None
    cacheDataPath = None
    canRefreshNow = False
        
    def __init__(self, *args):
        log.info("DataManager __init__")     

    def getCacheValidatorFromData(self, result):
        result = result.get("Items")
        if(result == None):
            result = []

        itemCount = 0
        unwatchedItemCount = 0        
        dataHashString = "";
        
        for item in result:
            item_hash_string = getChecksum(item)
            item_hash_string = str(itemCount) + "_" + item.get("Name", "-") + "_" + item_hash_string + "|"
            log.debug("ITEM_HASH: " + item_hash_string)
            dataHashString += item_hash_string
            itemCount = itemCount + 1

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
    
        #  first get the url hash
        m = hashlib.md5()
        m.update(url)
        urlHash = m.hexdigest()
        
        # build cache data path
        __addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
        __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile'))
        if not os.path.exists(os.path.join(__addondir__, "cache")):
            os.makedirs(os.path.join(__addondir__, "cache"))
        cacheDataPath = os.path.join(__addondir__, "cache", urlHash)
        
        log.info("Cache_Data_Manager:" + cacheDataPath)
        
        # are we forcing a reload
        WINDOW = xbmcgui.Window( 10000 )
        force_data_reload = WINDOW.getProperty("force_data_reload")
        WINDOW.setProperty("force_data_reload", "false")
    
        if(os.path.exists(cacheDataPath)) and force_data_reload != "true":
            # load data from cache if it is available and trigger a background
            # verification process to test cache validity   
            log.info("Loading Cached File")
            cachedfie = open(cacheDataPath, 'r')
            jsonData = cachedfie.read()
            cachedfie.close()
            result = self.loadJasonData(jsonData)
            
            # start a worker thread to process the cache validity
            self.cacheDataResult = result
            self.dataUrl = url
            self.cacheDataPath = cacheDataPath
            actionThread = CacheManagerThread()
            actionThread.setCacheData(self)
            actionThread.start()

            log.info("Returning Cached Result")
            return result
        else:
            # no cache data so load the url and save it
            jsonData = DownloadUtils().downloadUrl(url, suppress=False, popup=1)
            log.info("Loading URL and saving to cache")
            cachedfie = open(cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()
            result = self.loadJasonData(jsonData)
            self.cacheManagerFinished = True
            log.info("Returning Loaded Result")        
            return result
        
        
class CacheManagerThread(threading.Thread):

    dataManager = None
    
    def __init__(self, *args):
        threading.Thread.__init__(self, *args)
            
    def setCacheData(self, data):
        self.dataManager = data
    
    def run(self):
    
        log.info("CacheManagerThread Started")
        
        cacheValidatorString = self.dataManager.getCacheValidatorFromData(self.dataManager.cacheDataResult)
        log.info("Cache Validator String (" + cacheValidatorString + ")")
        
        jsonData = DownloadUtils().downloadUrl(self.dataManager.dataUrl, suppress=False, popup=1)
        loadedResult = self.dataManager.loadJasonData(jsonData)
        loadedValidatorString = self.dataManager.getCacheValidatorFromData(loadedResult)
        log.info("Loaded Validator String (" + loadedValidatorString + ")")
        
        # if they dont match then save the data and trigger a content reload
        if(cacheValidatorString != loadedValidatorString):
            log.info("CacheManagerThread Saving new cache data and reloading container")
            cachedfie = open(self.dataManager.cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()

            # we need to refresh but will wait until the main function has finished
            loops = 0
            while(self.dataManager.canRefreshNow == False and loops < 200):
                log.debug("Cache_Data_Manager: Not finished yet")
                xbmc.sleep(100)
                loops = loops + 1
            
            log.info("Sending container refresh (" + str(loops) + ")")
            xbmc.executebuiltin("Container.Refresh")

        log.info("CacheManagerThread Exited")
