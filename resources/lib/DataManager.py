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
                        itemPossition = userData.get("PlaybackPositionTicks")
                        itemRuntime = item.get("RunTimeTicks")
                        if(itemRuntime != None and itemPossition != None):
                            itemPercent = float(itemPossition) / float(itemRuntime)
                    else:
                        itemPercent == 100.0
                    
                    dataHashString = dataHashString + str(itemCount) + "_" + item.get("Name", "name") + "_" + "{0:09.6f}".format(itemPercent) + "-" + str(unwatchedItemCount) + "|"
                else:
                    itemCount = itemCount + item.get("RecursiveItemCount")
                    unwatchedItemCount = unwatchedItemCount + userData.get("UnplayedItemCount")
                    PlayedPercentage = userData.get("PlayedPercentage")
                    if PlayedPercentage == None:
                        PlayedPercentage = 0
                    dataHashString = dataHashString + str(itemCount) + "_" + item.get("Name", "name") + "_" + "{0:09.6f}".format(PlayedPercentage) + "-" + str(unwatchedItemCount) + "|"
              
        # hash the data
        dataHashString = dataHashString.encode("UTF-8")
        m = hashlib.md5()
        m.update(dataHashString)
        validatorString = m.hexdigest()
        
        #xbmc.log("Cache_Data_Manager: getCacheValidatorFromData : RawData  : " + dataHashString)
        xbmc.log("Cache_Data_Manager: getCacheValidatorFromData : hashData : " + validatorString)
        
        return validatorString

    def loadJasonData(self, jsonData):
        return json.loads(jsonData)        
        
    def GetContent(self, url):
    
        #  first get the url hash
        m = hashlib.md5()
        m.update(url)
        urlHash = m.hexdigest()
        
        # build cache data path
        __addon__ = xbmcaddon.Addon(id='plugin.video.mbcon')
        __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile'))
        if not os.path.exists(os.path.join(__addondir__, "cache")):
            os.makedirs(os.path.join(__addondir__, "cache"))
        cacheDataPath = os.path.join(__addondir__, "cache", urlHash)
        
        xbmc.log("Cache_Data_Manager:" + cacheDataPath)
        
        # are we forcing a reload
        WINDOW = xbmcgui.Window( 10000 )
        force_data_reload = WINDOW.getProperty("force_data_reload")
        WINDOW.setProperty("force_data_reload", "false")
    
        if(os.path.exists(cacheDataPath)) and force_data_reload != "true":
            # load data from cache if it is available and trigger a background
            # verification process to test cache validity        
            xbmc.log("Cache_Data_Manager: Loading Cached File")
            cachedfie = open(cacheDataPath, 'r')
            jsonData = cachedfie.read()
            cachedfie.close()
            result = self.loadJasonData(jsonData)
            
            # start a worker thread to process the cache validity
            actionThread = CacheManagerThread()
            actionThread.setCacheData(result, url, cacheDataPath)
            actionThread.start()

            xbmc.log("Cache_Data_Manager: Returning Cached Result")
            return result
        else:
            # no cache data so load the url and save it
            jsonData = DownloadUtils().downloadUrl(url, suppress=False, popup=1)
            xbmc.log("Cache_Data_Manager: Loading URL and saving to cache")
            cachedfie = open(cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()
            result = self.loadJasonData(jsonData)
            xbmc.log("Cache_Data_Manager: Returning Loaded Result")            
            return result
        
        
class CacheManagerThread(threading.Thread):

    cacheDataResult = None
    dataUrl = None
    cacheDataPath = None
    
    def setCacheData(self, cacheData, url, path):
        self.cacheDataResult = cacheData
        self.dataUrl = url
        self.cacheDataPath = path
    
    def run(self):
    
        dataManager = DataManager()
        xbmc.log("Cache_Data_Manager: CacheManagerThread Started")
        
        cacheValidatorString = dataManager.getCacheValidatorFromData(self.cacheDataResult)
        xbmc.log("Cache_Data_Manager: Cache Validator String (" + cacheValidatorString + ")")
        
        jsonData = DownloadUtils().downloadUrl(self.dataUrl, suppress=False, popup=1)
        loadedResult = dataManager.loadJasonData(jsonData)
        loadedValidatorString = dataManager.getCacheValidatorFromData(loadedResult)
        xbmc.log("Cache_Data_Manager: loaded Validator String (" + loadedValidatorString + ")")
        
        # if they dont match then save the data and trigger a content reload
        if(cacheValidatorString != loadedValidatorString):
            xbmc.log("Cache_Data_Manager: CacheManagerThread Saving new cache data and reloading container")
            cachedfie = open(self.cacheDataPath, 'w')
            cachedfie.write(jsonData)
            cachedfie.close()
            xbmc.executebuiltin("Container.Refresh")

        xbmc.log("Cache_Data_Manager: CacheManagerThread Exited")
