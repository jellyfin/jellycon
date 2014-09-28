#################################################################################################
# Start of ThemeMusic Thread
# plays theme music when applicable
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
import urllib2
import random

from Utils import PlayUtils
from DownloadUtils import DownloadUtils

#define our global download utils
downloadUtils = DownloadUtils()

class ThemeMusicThread(threading.Thread):

    playingTheme = False
    themeId = ''
    volume = ''
    themeMap = {}
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C ThemeMusicThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C ThemeMusicThread -> " + msg)
    
    def run(self):
        self.logMsg("Started")
        self.updateThemeMusic()
        lastRun = datetime.today()
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        themeRefresh = 2
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if (secTotal > themeRefresh):
                self.updateThemeMusic()
                lastRun = datetime.today()    
                
            xbmc.sleep(2000)
            
        self.logMsg("Exited")

      
    def updateThemeMusic(self):
        self.logMsg("updateThemeMusic Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
         
        newid = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        if newid != self.themeId:
            if self.isPlayingZone() and self.playingTheme == True:
              if  xbmc.Player().isPlayingAudio():
                self.stop()
        xbmc.sleep(1500)
        id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        if id != newid:
            return
        self.logMsg("updateThemeMusic itemGUID : " + id)
        if self.isPlayingZone() and self.isChangeTheme():
            self.themeId = id 
            themeUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Items/" + id + "/ThemeSongs?format=json"
            self.logMsg("updateThemeMusic themeUrl : " + themeUrl)
            if themeUrl not in self.themeMap:
                jsonData = downloadUtils.downloadUrl(themeUrl, suppress=False, popup=1 )
                theme = json.loads(jsonData)     
               
                if(theme == None):
                    theme = []
                self.logMsg("updateThemeMusic added theme to map : " + themeUrl)    
                self.themeMap[themeUrl] = theme
            elif themeUrl in self.themeMap:
                theme = self.themeMap.get(themeUrl)
                self.logMsg("updateThemeMusic retrieved theme from map : " + themeUrl)
            
            themeItems = theme.get("Items")
            if themeItems != []:
                themePlayUrl = PlayUtils().getPlayUrl(mb3Host + ":" + mb3Port,themeItems[0].get("Id"),themeItems[0])
                self.logMsg("updateThemeMusic themeMusicPath : " + str(themePlayUrl))
                self.playingTheme = True
                self.setVolume(60)
                xbmc.Player().play(themePlayUrl)
                
            elif themeItems == [] and self.playingTheme == True:
                self.stop(True)
        
        if not self.isPlayingZone() and self.playingTheme == True:
            # stop
            if  xbmc.Player().isPlayingAudio():
                self.stop()
    
    
    def stop(self, forceStop = False):
        # Only stop if playing audio
        if xbmc.Player().isPlayingAudio() or forceStop == True:
            self.playingTheme = False
            cur_vol = self.getVolume()
            
            # Calculate how fast to fade the theme, this determines
            # the number of step to drop the volume in
            numSteps = 15
            vol_step = cur_vol / numSteps
            # do not mute completely else the mute icon shows up
            for step in range (0,(numSteps-1)):
                vol = cur_vol - vol_step
                self.setVolume(vol)
                cur_vol = vol
                xbmc.sleep(200)
            xbmc.Player().stop()
            self.setVolume(self.volume)  
        
    # Works out if the currently displayed area on the screen is something
    # that is deemed a zone where themes should be played
    def isPlayingZone(self):
        
        if "plugin://plugin.video.xbmb3c" in xbmc.getInfoLabel( "ListItem.Path" ):
            return True
        
        # Any other area is deemed to be a non play area
        return False 
    
    # Works out if we should change/start a theme
    def isChangeTheme(self):
        id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        if id != "":
            if self.volume == '':
                self.volume = self.getVolume()
            # we have something to start with
            addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c') 
            if addonSettings.getSetting('useThemeMusic') == "true":
              # cool theme music is on continue
              if id == self.themeId:
                  # same as before now do we need to restart 
                  if addonSettings.getSetting('loopThemeMusic') == "true" and xbmc.Player().isPlayingAudio() == False:
                      return True
              if id != self.themeId:
                  # new id return true
                  return True  
              
        # still here return False 
        return False 
    
    # This will return the volume in a range of 0-100
    def getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = json.loads(result)
        if "result" in json_query and json_query['result'].has_key('volume'):
            # Get the volume value
            volume = json_query['result']['volume']

        return volume

    # Sets the volume in the range 0-100
    def setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % newvolume, True)
     
 