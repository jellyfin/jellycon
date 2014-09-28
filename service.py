import xbmc
import xbmcgui
import xbmcaddon
import urllib
import httplib
import os
import time
import requests
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
base_window = xbmcgui.Window( 10000 )

from ArtworkLoader import ArtworkRotationThread
from WebSocketClient import WebSocketThread
from ClientInformation import ClientInformation
from MenuLoad import LoadMenuOptionsThread

_MODE_BASICPLAY=12

def getAuthHeader():
    addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
    deviceName = addonSettings.getSetting('deviceName')
    deviceName = deviceName.replace("\"", "_") # might need to url encode this as it is getting added to the header and is user entered data
    clientInfo = ClientInformation()
    txt_mac = clientInfo.getMachineId()
    version = clientInfo.getVersion()  
    userid = xbmcgui.Window( 10000 ).getProperty("userid")
    authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
    headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}
    xbmc.log("MBCon Authentication Header : " + str(headers))
    return headers 

# start some worker threads

newWebSocketThread = None
if __addon__.getSetting('useWebSocketRemote') == "true":
    newWebSocketThread = WebSocketThread()
    newWebSocketThread.start()
else:
    xbmc.log("MBCon Service WebSocketRemote Disabled")

newMenuThread = None
if __addon__.getSetting('useMenuLoader') == "true":
    newMenuThread = LoadMenuOptionsThread()
    newMenuThread.start()
else:
    xbmc.log("MBCon Service MenuLoader Disabled")

artworkRotationThread = None    
if __addon__.getSetting('useBackgroundLoader') == "true":
    artworkRotationThread = ArtworkRotationThread()
    artworkRotationThread.start()
else:
    xbmc.log("MBCon Service BackgroundLoader Disabled")

    
def deleteItem (url):
    return_value = xbmcgui.Dialog().yesno(__language__(30091),__language__(30092))
    if return_value:
        xbmc.log('Deleting via URL: ' + url)
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30052), __language__(30053))
        resp = requests.delete(url, data='', headers=getAuthHeader())
        deleteSleep=0
        while deleteSleep<10:
            xbmc.sleep(1000)
            deleteSleep=deleteSleep+1
            progress.update(deleteSleep*10,__language__(30053))
        progress.close()
        xbmc.executebuiltin("Container.Refresh")
        return 1
    else:
        return 0
        
def markWatched(url):
    xbmc.log('MBCon Service -> Marking watched via: ' + url)
    resp = requests.post(url, data='', headers=getAuthHeader())
    
def markUnWatched(url):
    xbmc.log('MBCon Service -> Marking watched via: ' + url)
    resp = requests.delete(url, data='', headers=getAuthHeader())    

def setPosition (url, method):
    xbmc.log('MBCon Service -> Setting position via: ' + url)
    if method == 'POST':
        resp = requests.post(url, data='', headers=getAuthHeader())
    elif method == 'DELETE':
        resp = requests.delete(url, data='', headers=getAuthHeader())
        
def stopTranscoding(url):
    xbmc.log('MBCon Service -> Stopping transcoding: ' + url)
    resp = requests.delete(url, data='', headers=getAuthHeader())    

        
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
            
            watchedurl = data.get("watchedurl")
            positionurl = data.get("positionurl")
            deleteurl = data.get("deleteurl")
            runtime = data.get("runtime")
            currentPossition = data.get("currentPossition")
            item_id = data.get("item_id")
            
            if(currentPossition != None and hasData(runtime) and hasData(positionurl) and hasData(watchedurl)):
                runtimeTicks = int(runtime)
                xbmc.log ("MBCon Service -> runtimeticks:" + str(runtimeTicks))
                percentComplete = (currentPossition * 10000000) / runtimeTicks
                markPlayedAt = float(addonSettings.getSetting("markPlayedAt")) / 100    

                xbmc.log ("MBCon Service -> Percent Complete:" + str(percentComplete) + " Mark Played At:" + str(markPlayedAt))
                if (percentComplete > markPlayedAt):
                
                    gotDeleted = 0
                    if(deleteurl != None and deleteurl != ""):
                        xbmc.log ("MBCon Service -> Offering Delete:" + str(deleteurl))
                        gotDeleted = deleteItem(deleteurl)
                        
                    if(gotDeleted == 0):
                        setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')
                        if(newWebSocketThread != None):
                            newWebSocketThread.playbackStopped(item_id, str(0))
                        markWatched(watchedurl)
                else:
                    #markUnWatched(watchedurl) # this resets the LastPlayedDate and that causes issues with sortby PlayedDate so I removed it for now
                    if(newWebSocketThread != None):
                        newWebSocketThread.playbackStopped(item_id, str(int(currentPossition * 10000000)))
                    setPosition(positionurl + '?PositionTicks=' + str(int(currentPossition * 10000000)), 'DELETE')
                    
    if(newNextUpThread != None):
        newNextUpThread.updateNextUp()
        
    if(artworkRotationThread != None):
        artworkRotationThread.updateActionUrls()
        
    played_information.clear()

    # stop transcoding - todo check we are actually transcoding?
    clientInfo = ClientInformation()
    txt_mac = clientInfo.getMachineId()
    url = ("http://%s:%s/mediabrowser/Videos/ActiveEncodings" % (addonSettings.getSetting('ipaddress'), addonSettings.getSetting('port')))  
    url = url + '?DeviceId=' + txt_mac
    stopTranscoding(url)
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
        watchedurl = WINDOW.getProperty(currentFile+"watchedurl")
        deleteurl = WINDOW.getProperty(currentFile+"deleteurl")
        positionurl = WINDOW.getProperty(currentFile+"positionurl")
        runtime = WINDOW.getProperty(currentFile+"runtimeticks")
        item_id = WINDOW.getProperty(currentFile+"item_id")
        
        # reset all these so they dont get used is xbmc plays a none 
        # xbmb3c MB item
        # WINDOW.setProperty(currentFile+"watchedurl", "")
        # WINDOW.setProperty(currentFile+"deleteurl", "")
        # WINDOW.setProperty(currentFile+"positionurl", "")
        # WINDOW.setProperty(currentFile+"runtimeticks", "")
        # WINDOW.setProperty(currentFile+"item_id", "")
        
        if(item_id == None or len(item_id) == 0):
            return
        
        if(newWebSocketThread != None):
            newWebSocketThread.playbackStarted(item_id)
        
        if (watchedurl != "" and positionurl != ""):
        
            data = {}
            data["watchedurl"] = watchedurl
            data["deleteurl"] = deleteurl
            data["positionurl"] = positionurl
            data["runtime"] = runtime
            data["item_id"] = item_id
            self.played_information[currentFile] = data
            
            xbmc.log("MBCon Service -> ADDING_FILE : " + currentFile)
            xbmc.log("MBCon Service -> ADDING_FILE : " + str(self.played_information))

            # reset in progress possition
            setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')

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

addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
if socket.gethostname() != None and socket.gethostname() != '' and addonSettings.getSetting("deviceName") == 'MBCon':
    addonSettings.setSetting("deviceName", socket.gethostname())

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
            if(secDiff > 10):
                if(monitor.played_information.get(currentFile) != None and monitor.played_information.get(currentFile).get("item_id") != None):
                    item_id =  monitor.played_information.get(currentFile).get("item_id")
                    if(newWebSocketThread != None):
                        newWebSocketThread.sendProgressUpdate(item_id, str(int(playTime * 10000000)))
                lastProgressUpdate = datetime.today()
            
        except Exception, e:
            xbmc.log("MBCon Service -> Exception in Playback Monitor : " + str(e))
            pass

    xbmc.sleep(1000)
    xbmcgui.Window(10000).setProperty("XBMB3C_Service_Timestamp", str(int(time.time())))
    
# stop the WebSocket client
if(newWebSocketThread != None):
    newWebSocketThread.stopClient()

# stop the image proxy
keepServing = False

xbmc.log("MBCon Service -> Service shutting down")

