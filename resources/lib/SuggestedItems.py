#################################################################################################
# Suggested Updater
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils

_MODE_BASICPLAY=12

#define our global download utils
downloadUtils = DownloadUtils()

class SuggestedUpdaterThread(threading.Thread):

    logLevel = 0
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C SuggestedUpdaterThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C SuggestedUpdaterThread -> " + msg)
            
    def run(self):
        self.logMsg("Started")
        
        self.updateSuggested()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateSuggested()
                lastRun = datetime.today()

            xbmc.sleep(3000)
                        
        self.logMsg("Exited")
        
    def updateSuggested(self):
        self.logMsg("updateSuggested Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userid = downloadUtils.getUserId()
        self.logMsg("updateSuggested UserID : " + userid)
        
        self.logMsg("Updating Suggested List")
        
        suggestedUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Movies/Recommendations?UserId=" + userid + "&categoryLimit=1&ItemLimit=6&format=json" 
        jsonData = downloadUtils.downloadUrl(suggestedUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Suggested Movie Json Data : " + str(result), level=2)
        basemovie = "Missing Base Title"
        
        if(result == None or len(result) == 0):
            return
        
        if (result[0].get("BaselineItemName") != None):
            basemovie = result[0].get("BaselineItemName").encode('utf-8')
            
        result = result[0].get("Items")
        WINDOW = xbmcgui.Window( 10000 )
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
            
            rating = item.get("CommunityRating")
            criticrating = item.get("CriticRating")
            officialrating = item.get("OfficialRating")
            criticratingsummary = ""
            if(item.get("CriticRatingSummary") != None):
                criticratingsummary = item.get("CriticRatingSummary").encode('utf-8')
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')
            year = item.get("ProductionYear")
            if(item.get("RunTimeTicks") != None):
                runtime = str(int(item.get("RunTimeTicks"))/(10000000*60))
            else:
                runtime = "0"

            item_id = item.get("Id")
            thumbnail = downloadUtils.getArtwork(item, "Primary")
            logo = downloadUtils.getArtwork(item, "Logo")
            fanart = downloadUtils.getArtwork(item, "Backdrop")
            medium_fanart = downloadUtils.getArtwork(item, "Backdrop3")
            if item.get("ImageTags").get("Thumb") != None:
              realthumbnail = downloadUtils.getArtwork(item, "Thumb3")
            else:
              realthumbnail = fanart
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Thumb = " + realthumbnail, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
            self.logMsg("SuggestedMovieMB3." + str(item_count) + ".SuggestedMovieTitle  = " + basemovie, level=2)
            
            
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Thumb", realthumbnail)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Path", playUrl)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(medium_fanart)", medium_fanart)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Rating", str(rating))
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Mpaa", str(officialrating))
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Runtime", str(runtime))
            WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".SuggestedMovieTitle", basemovie)
            
            
            WINDOW.setProperty("SuggestedMovieMB3.Enabled", "true")
            
            item_count = item_count + 1
            
            
