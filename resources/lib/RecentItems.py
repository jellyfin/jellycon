#################################################################################################
# Recent Info Updater
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


class RecentInfoUpdaterThread(threading.Thread):

    logLevel = 0
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C RecentInfoUpdaterThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C RecentInfoUpdaterThread -> " + msg)
                
    def run(self):
        self.logMsg("Started")
        
        self.updateRecent()
        lastRun = datetime.today()
        lastProfilePath = xbmc.translatePath('special://profile')
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            profilePath = xbmc.translatePath('special://profile')
            
            updateInterval = 60
            if (xbmc.Player().isPlaying()):
                updateInterval = 300
                
            if(secTotal > updateInterval or lastProfilePath != profilePath):
                self.updateRecent()
                lastRun = datetime.today()

            lastProfilePath = profilePath
            
            xbmc.sleep(3000)
                        
        self.logMsg("Exited")
        
    def updateRecent(self):
        self.logMsg("updateRecent Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userid = downloadUtils.getUserId()
        
        self.logMsg("UserName : " + userName + " UserID : " + userid)
        
        self.logMsg("Updating Recent Movie List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=30&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview,CriticRatingSummary&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json"
         
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent Movie Json Data : " + str(result), level=2)
        
        result = result.get("Items")
        if(result == None):
            result = []
            
        WINDOW = xbmcgui.Window( 10000 )

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
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestMovieMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
            
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Path", playUrl)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Rating", str(rating))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Mpaa", str(officialrating))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Runtime", str(runtime))
            
            WINDOW.setProperty("LatestMovieMB3.Enabled", "true")
            
            item_count = item_count + 1
            
        #Updating Recent Unplayed Movie List
        self.logMsg("Updating Recent Unplayed Movie List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/Latest?Limit=30&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview,CriticRatingSummary&IsPlayed=false&IncludeItemTypes=Movie&format=json"
         
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent Unplayed Movie Json Data : " + str(result), level=2)
        
        if(result == None):
            result = []
            
        WINDOW = xbmcgui.Window( 10000 )

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
            
            if (item.get("ImageTags") != None and item.get("ImageTags").get("Thumb") != None):
              realthumb = downloadUtils.getArtwork(item, "Thumb3")
            else:
              realthumb = fanart
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
            self.logMsg("LatestUnplayedMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
            
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Path", playUrl)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Art(medium_fanart)", medium_fanart)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".RealThumb", realthumb)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Rating", str(rating))
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Mpaa", str(officialrating))
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("LatestUnplayedMovieMB3." + str(item_count) + ".Runtime", str(runtime))
            
            WINDOW.setProperty("LatestUnplayedMovieMB3.Enabled", "true")
            
            item_count = item_count + 1
        
        #Updating Recent TV Show List
        self.logMsg("Updating Recent TV Show List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=30&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json"
        
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent TV Show Json Data : " + str(result), level=2)
        
        result = result.get("Items")
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = "00"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "Episode" or item.get("Type") == "Season":
               series_id = item.get("SeriesId")
                      
            poster = downloadUtils.getArtwork(item, "SeriesPrimary")
            thumbnail = downloadUtils.getArtwork(item, "Primary")      
            logo = downloadUtils.getArtwork(item, "Logo")          
            fanart = downloadUtils.getArtwork(item, "Backdrop")
            banner = downloadUtils.getArtwork(item, "Banner")
            if item.get("SeriesThumbImageTag") != None:
              seriesthumbnail = downloadUtils.getArtwork(item, "Thumb3")
            else:
              seriesthumbnail = fanart
              
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".SeriesThumb", seriesthumbnail)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Plot", plot)
            
            WINDOW.setProperty("LatestEpisodeMB3.Enabled", "true")
            
            item_count = item_count + 1
            
        #Updating Recent Unplayed TV Show List
        self.logMsg("Updating Recent Unplayed TV Show List")
                                                                                           
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/Latest?Limit=30&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&IsPlayed=false&GroupItems=false&IncludeItemTypes=Episode&format=json"
        
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent Unplayed TV Show Json Data : " + str(result), level=2)
        
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = "00"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "Episode" or item.get("Type") == "Season":
               series_id = item.get("SeriesId")
                      
            poster = downloadUtils.getArtwork(item, "SeriesPrimary")
            thumbnail = downloadUtils.getArtwork(item, "Primary") 
            logo = downloadUtils.getArtwork(item, "Logo")           
            fanart = downloadUtils.getArtwork(item, "Backdrop")
            medium_fanart = downloadUtils.getArtwork(item, "Backdrop3")
            banner = downloadUtils.getArtwork(item, "Banner")
            if item.get("SeriesThumbImageTag") != None:
              seriesthumbnail = downloadUtils.getArtwork(item, "Thumb3")
            else:
              seriesthumbnail = fanart
              
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("LatestUnplayedEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".SeriesThumb", seriesthumbnail)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.medium_fanart)", medium_fanart)
            
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("LatestUnplayedEpisodeMB3." + str(item_count) + ".Plot", plot)
            
            WINDOW.setProperty("LatestUnplayedEpisodeMB3.Enabled", "true")
            
            item_count = item_count + 1
            
        #Updating Recent MusicList
        self.logMsg("Updating Recent MusicList")
    
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=MusicAlbum&format=json"
    
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent MusicList Json Data : " + str(result), level=2)
    
        result = result.get("Items")
        if(result == None):
          result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            artist = "Missing Artist"
            if(item.get("AlbumArtist") != None):
                artist = item.get("AlbumArtist").encode('utf-8')   

            year = "0000"
            if(item.get("ProductionYear") != None):
              year = str(item.get("ProductionYear"))
            plot = "Missing Plot"
            if(item.get("Overview") != None):
              plot = item.get("Overview").encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "MusicAlbum":
               parentId = item.get("ParentLogoItemId")
            
            thumbnail = downloadUtils.getArtwork(item, "Primary")
            logo = downloadUtils.getArtwork(item, "Logo")
            fanart = downloadUtils.getArtwork(item, "Backdrop")
            banner = downloadUtils.getArtwork(item, "Banner")
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Artist = " + artist, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Year = " + year, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(banner)  = " + banner, level=2)  
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Artist", artist)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Year", year)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(banner)", banner)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Plot", plot)
            
            WINDOW.setProperty("LatestAlbumMB3.Enabled", "true")
            
            item_count = item_count + 1

        #Updating Recent Photo
        self.logMsg("Updating Recent Photo")
    
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Photo&format=json"
    
        jsonData = downloadUtils.downloadUrl(recentUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("Recent Photo Json Data : " + str(result), level=2)
    
        result = result.get("Items")
        if(result == None):
          result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            
            plot = "Missing Plot"
            if(item.get("Overview") != None):
              plot = item.get("Overview").encode('utf-8')

            item_id = item.get("Id") 
            
            thumbnail = downloadUtils.getArtwork(item, "Primary")
            logo = downloadUtils.getArtwork(item, "Logo")
            fanart = downloadUtils.getArtwork(item, "Backdrop")
            banner = downloadUtils.getArtwork(item, "Banner")
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Art(banner)  = " + banner, level=2)  
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestPhotoMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Art(banner)", banner)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestPhotoMB3." + str(item_count) + ".Plot", plot)
            
            WINDOW.setProperty("LatestPhotoMB3.Enabled", "true")
            
            item_count = item_count + 1
            