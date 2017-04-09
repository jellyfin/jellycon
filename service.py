# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import time
from datetime import datetime

from resources.lib.websocketclient import WebSocketThread
from resources.lib.downloadutils import DownloadUtils
from resources.lib.simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon.service")
downloadUtils = DownloadUtils()

# auth the service
try:
    downloadUtils.authenticate()
except Exception, e:
    pass

newWebSocketThread = WebSocketThread()
newWebSocketThread.setDaemon(True)
newWebSocketThread.start()
    
def hasData(data):
    if(data == None or len(data) == 0 or data == "None"):
        return False
    else:
        return True
        
def stopAll(played_information):

    if(len(played_information) == 0):
        return 
        
    log.info("played_information : " + str(played_information))
    
    for item_url in played_information:
        data = played_information.get(item_url)
        if(data != None):
            log.info("item_url  : " + item_url)
            log.info("item_data : " + str(data))
            
            currentPossition = data.get("currentPossition")
            item_id = data.get("item_id")
            
            if(hasData(item_id)):
                log.info("Playback Stopped at: " + str(int(currentPossition * 10000000)))
                newWebSocketThread.playbackStopped(item_id, str(int(currentPossition * 10000000)))
        
    played_information.clear()
    
    
class Service( xbmc.Player ):

    played_information = {}
    
    def __init__( self, *args ):
        log.info("EmbyCon Service -> starting monitor service")
        self.played_information = {}
        pass
    
    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        stopAll(self.played_information)
        
        currentFile = xbmc.Player().getPlayingFile()
        log.info("onPlayBackStarted" + currentFile)
        
        WINDOW = xbmcgui.Window( 10000 )
        item_id = WINDOW.getProperty("playback_url_" + currentFile)
        log.info("item_id: " + item_id)

        # reset all these so they dont get used is xbmc plays a none 
        #WINDOW.setProperty("item_id", "")
        
        if(item_id == None or len(item_id) == 0):
            return
        
        newWebSocketThread.playbackStarted(item_id)
        
        data = {}
        data["item_id"] = item_id
        self.played_information[currentFile] = data
        
        log.info("EmbyCon Service -> ADDING_FILE : " + currentFile)
        log.info("EmbyCon Service -> ADDING_FILE : " + str(self.played_information))

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        log.info("EmbyCon Service -> onPlayBackEnded")
        stopAll(self.played_information)

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        log.info("EmbyCon Service -> onPlayBackStopped")
        stopAll(self.played_information)

monitor = Service()
lastProgressUpdate = datetime.today()
            
while not xbmc.abortRequested:
    
    if xbmc.Player().isPlaying():
        try:
            # send update
            td = datetime.today() - lastProgressUpdate
            secDiff = td.seconds
            if(secDiff > 5):
            
                playTime = xbmc.Player().getTime()
                currentFile = xbmc.Player().getPlayingFile()
                
                if(monitor.played_information.get(currentFile) != None):
                    monitor.played_information[currentFile]["currentPossition"] = playTime            
            
                if(monitor.played_information.get(currentFile) != None and monitor.played_information.get(currentFile).get("item_id") != None):
                    item_id =  monitor.played_information.get(currentFile).get("item_id")
                    newWebSocketThread.sendProgressUpdate(item_id, str(int(playTime * 10000000)))
                    
                lastProgressUpdate = datetime.today()
            
        except Exception, e:
            log.error("EmbyCon Service -> Exception in Playback Monitor : " + str(e))
            pass

    xbmc.sleep(1000)
    xbmcgui.Window(10000).setProperty("EmbyCon_Service_Timestamp", str(int(time.time())))
    
# stop the WebSocket client
newWebSocketThread.stopClient()

log.info("EmbyCon Service -> Service shutting down")
