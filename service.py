import xbmc
import xbmcgui
import xbmcaddon
import urllib
import httplib
import os
import time
import socket

import threading
import json
from datetime import datetime
import xml.etree.ElementTree as xml

import mimetypes
from threading import Thread
from urlparse import parse_qs
from urllib import urlretrieve

from random import randint
import random
import urllib2

__cwd__ = xbmcaddon.Addon(id='plugin.video.mbcon').getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.mbcon')
__language__     = __addon__.getLocalizedString
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

from ArtworkLoader import ArtworkRotationThread
from WebSocketClient import WebSocketThread
from MenuLoad import LoadMenuOptionsThread
from DownloadUtils import DownloadUtils

downloadUtils = DownloadUtils()

# auth the service
try:
    downloadUtils.authenticate()
except Exception, e:
    pass

# start some worker threads
newWebSocketThread = WebSocketThread()
newWebSocketThread.start()

newMenuThread = LoadMenuOptionsThread()
newMenuThread.start()

artworkRotationThread = ArtworkRotationThread()
artworkRotationThread.start()
               
def hasData(data):
    if(data == None or len(data) == 0 or data == "None"):
        return False
    else:
        return True
        
def stopAll(played_information):

    if(len(played_information) == 0):
        return 
        
    addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
    xbmc.log ("MBCon Service -> played_information : " + str(played_information))
    
    for item_url in played_information:
        data = played_information.get(item_url)
        if(data != None):
            xbmc.log ("MBCon Service -> item_url  : " + item_url)
            xbmc.log ("MBCon Service -> item_data : " + str(data))
            
            currentPossition = data.get("currentPossition")
            item_id = data.get("item_id")
            
            if(hasData(item_id)):
                xbmc.log("MBCon Service -> Playback Stopped at :" + str(int(currentPossition * 10000000)))
                newWebSocketThread.playbackStopped(item_id, str(int(currentPossition * 10000000)))
                
    artworkRotationThread.updateActionUrls()
        
    played_information.clear()
    
    
class Service( xbmc.Player ):

    played_information = {}
    
    def __init__( self, *args ):
        xbmc.log("MBCon Service -> starting monitor service")
        self.played_information = {}
        pass
    
    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        stopAll(self.played_information)
        
        currentFile = xbmc.Player().getPlayingFile()
        xbmc.log("MBCon Service -> onPlayBackStarted" + currentFile)
        
        WINDOW = xbmcgui.Window( 10000 )
        item_id = WINDOW.getProperty("item_id")
        
        # reset all these so they dont get used is xbmc plays a none 
        WINDOW.setProperty("item_id", "")
        
        if(item_id == None or len(item_id) == 0):
            return
        
        newWebSocketThread.playbackStarted(item_id)
        
        data = {}
        data["item_id"] = item_id
        self.played_information[currentFile] = data
        
        xbmc.log("MBCon Service -> ADDING_FILE : " + currentFile)
        xbmc.log("MBCon Service -> ADDING_FILE : " + str(self.played_information))

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        xbmc.log("MBCon Service -> onPlayBackEnded")
        stopAll(self.played_information)

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        xbmc.log("MBCon Service -> onPlayBackStopped")
        stopAll(self.played_information)

monitor = Service()
lastProgressUpdate = datetime.today()

while not xbmc.abortRequested:
    if xbmc.Player().isPlaying():
        try:
        
            playTime = xbmc.Player().getTime()
            currentFile = xbmc.Player().getPlayingFile()
            
            if(monitor.played_information.get(currentFile) != None):
                monitor.played_information[currentFile]["currentPossition"] = playTime
            
            # send update
            td = datetime.today() - lastProgressUpdate
            secDiff = td.seconds
            if(secDiff > 5):
                if(monitor.played_information.get(currentFile) != None and monitor.played_information.get(currentFile).get("item_id") != None):
                    item_id =  monitor.played_information.get(currentFile).get("item_id")
                    newWebSocketThread.sendProgressUpdate(item_id, str(int(playTime * 10000000)))
                lastProgressUpdate = datetime.today()
            
        except Exception, e:
            xbmc.log("MBCon Service -> Exception in Playback Monitor : " + str(e))
            pass

    xbmc.sleep(1000)
    xbmcgui.Window(10000).setProperty("mbcon_Service_Timestamp", str(int(time.time())))
    
# stop the WebSocket client
newWebSocketThread.stopClient()

xbmc.log("MBCon Service -> Service shutting down")
