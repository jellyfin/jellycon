import hashlib
import os
import threading
import json as json

import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc

from DownloadUtils import DownloadUtils

class DataManager():

    cacheDataResult = None
    dataUrl = None
    cacheDataPath = None
    canRefreshNow = False
    logLevel = 0
        
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)         
        
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("EmbyCon DataManager -> " + msg)

    def getCacheValidatorFromData(self, result):
        result = result.get("Items")
        if(result == None):
            result = []

        itemCount = 0
        unwatchedItemCount = 0        
        dataHashString = "";
        
        for item in result:
            userData = item.get("UserData")
            if(userData != None):
                if(item.get("IsFolder") == False):
                    itemCount = itemCount + 1
                    itemPercent = 0.0
                    if userData.get("Played") == False:
                        unwatchedItemCount = unwatchedItemCount + 1
                        
                    # calc the percentage
                    itemPercent = 0.0
                    itemPossition = userData.get("PlaybackPositionTicks")
                    itemRuntime = item.get("RunTimeTicks")
                    if(itemRuntime != None and itemPossition != None):
                        itemPercent = (float(itemPossition) / float(itemRuntime)) * 100
                    
                    itemString = str(itemCount) + "_" + item.get("Name", "name") + "_" + str(int(itemPercent)) + "-" + str(unwatchedItemCount) + "|"
                    self.logMsg(itemString, level=2)
                    dataHashString = dataHashString + itemString
                else:
                    itemCount = itemCount + item.get("RecursiveItemCount", 0)
                    unwatchedItemCount = unwatchedItemCount + userData.get("UnplayedItemCount")
                    PlayedPercentage = userData.get("PlayedPercentage")
                    if PlayedPercentage == None:
                        PlayedPercentage = 0
                    itemString = str(itemCount) + "_" + item.get("Name", "name") + "_" + str(int(PlayedPercentage)) + "-" + str(unwatchedItemCount) + "|"
                    self.logMsg(itemString, level=2)
                    dataHashString = dataHashString + itemString
              
        # hash the data
        dataHashString = dataHashString.encode("UTF-8")
        m = hashlib.md5()
        m.update(dataHashString)
        validatorString = m.hexdigest()
        
        self.logMsg("getCacheValidatorFromData : RawData  : " + dataHashString, level=2)
        self.logMsg("getCacheValidatorFromData : hashData : " + validatorString, level=2)
        
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
        
        self.logMsg("Cache_Data_Manager:" + cacheDataPath)
        
        # are we forcing a reload
        WINDOW = xbmcgui.Window( 10000 )
        force_data_reload = WINDOW.getProperty("force_data_reload")
        WINDOW.setProperty("force_data_reload", "false")
    
        if(os.path.exists(cacheDataPath)) and force_data_reload != "true":
            # load data from cache if it is available and trigger a background
            # verification process to test cache validity   
            self.logMsg("Loading Cached File")
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

            self.logMsg("Returning Cached Result")
            return result
        else:
            # no cache data so load the url and save it
            jsonData = DownloadUtils().downloadUrl(url, suppress=False, popup=1)
            self.logMsg("Loading URL and saving to cache")
            cachedfie = open(cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()
            result = self.loadJasonData(jsonData)
            self.cacheManagerFinished = True
            self.logMsg("Returning Loaded Result")        
            return result
        
        
class CacheManagerThread(threading.Thread):

    dataManager = None
    logLevel = 0
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
            
        threading.Thread.__init__(self, *args)

    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("EmbyCon CacheManagerThread -> " + msg)
            
    def setCacheData(self, data):
        self.dataManager = data
    
    def run(self):
    
        self.logMsg("CacheManagerThread Started")
        
        cacheValidatorString = self.dataManager.getCacheValidatorFromData(self.dataManager.cacheDataResult)
        self.logMsg("Cache Validator String (" + cacheValidatorString + ")")
        
        jsonData = DownloadUtils().downloadUrl(self.dataManager.dataUrl, suppress=False, popup=1)
        loadedResult = self.dataManager.loadJasonData(jsonData)
        loadedValidatorString = self.dataManager.getCacheValidatorFromData(loadedResult)
        self.logMsg("Loaded Validator String (" + loadedValidatorString + ")")
        
        # if they dont match then save the data and trigger a content reload
        if(cacheValidatorString != loadedValidatorString):
            self.logMsg("CacheManagerThread Saving new cache data and reloading container")
            cachedfie = open(self.dataManager.cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()

            # we need to refresh but will wait until the main function has finished
            loops = 0
            while(self.dataManager.canRefreshNow == False and loops < 200):
                #xbmc.log("Cache_Data_Manager: Not finished yet")
                xbmc.sleep(100)
                loops = loops + 1
            
            self.logMsg("Sending container refresh (" + str(loops) + ")")
            xbmc.executebuiltin("Container.Refresh")

        self.logMsg("CacheManagerThread Exited")
