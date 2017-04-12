# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import time
from datetime import datetime

from resources.lib.websocketclient import WebSocketThread
from resources.lib.downloadutils import DownloadUtils
from resources.lib.simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon.service")
download_utils = DownloadUtils()

# auth the service
try:
    download_utils.authenticate()
except Exception, e:
    pass

websocket_thread = WebSocketThread()
websocket_thread.setDaemon(True)
websocket_thread.start()


def hasData(data):
    if data is None or len(data) == 0 or data == "None":
        return False
    else:
        return True


def stopAll(played_information):

    if len(played_information) == 0:
        return
        
    log.info("played_information : " + str(played_information))
    
    for item_url in played_information:
        data = played_information.get(item_url)
        if data is not None:
            log.info("item_url  : " + item_url)
            log.info("item_data : " + str(data))
            
            current_possition = data.get("currentPossition")
            emby_item_id = data.get("item_id")
            
            if hasData(emby_item_id):
                log.info("Playback Stopped at: " + str(int(current_possition * 10000000)))
                websocket_thread.playbackStopped(emby_item_id, str(int(current_possition * 10000000)))
        
    played_information.clear()
    
    
class Service(xbmc.Player):

    played_information = {}
    
    def __init__(self, *args):
        log.info("Starting monitor service: " + str(args))
        self.played_information = {}
        pass
    
    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        stopAll(self.played_information)
        
        current_playing_file = xbmc.Player().getPlayingFile()
        log.info("onPlayBackStarted: " + current_playing_file)
        
        window_handle = xbmcgui.Window(10000)
        emby_item_id = window_handle.getProperty("item_id")
        #emby_item_id = window_handle.getProperty("playback_url_" + current_playing_file)
        log.info("item_id: " + emby_item_id)
        window_handle.setProperty("item_id", "")

        if emby_item_id is None or len(emby_item_id) == 0:
            return
        
        websocket_thread.playbackStarted(emby_item_id)
        
        data = {}
        data["item_id"] = emby_item_id
        self.played_information[current_playing_file] = data
        
        log.info("ADDING_FILE : " + current_playing_file)
        log.info("ADDING_FILE : " + str(self.played_information))

    def onPlayBackEnded(self):
        # Will be called when xbmc stops playing a file
        log.info("EmbyCon Service -> onPlayBackEnded")
        stopAll(self.played_information)

    def onPlayBackStopped(self):
        # Will be called when user stops xbmc playing a file
        log.info("onPlayBackStopped")
        stopAll(self.played_information)

monitor = Service()
last_progress_update = datetime.today()
            
while not xbmc.abortRequested:
    
    if xbmc.Player().isPlaying():
        try:
            # send update
            td = datetime.today() - last_progress_update
            sec_diff = td.seconds
            if sec_diff > 5:
            
                play_time = xbmc.Player().getTime()
                current_file = xbmc.Player().getPlayingFile()
                
                if monitor.played_information.get(current_file) is not None:

                    monitor.played_information[current_file]["currentPossition"] = play_time
            
                if (monitor.played_information.get(current_file) is not None and
                        monitor.played_information.get(current_file).get("item_id") is not None):

                    item_id = monitor.played_information.get(current_file).get("item_id")
                    websocket_thread.sendProgressUpdate(item_id, str(int(play_time * 10000000)))
                    
                last_progress_update = datetime.today()
            
        except Exception, e:
            log.error("Exception in Playback Monitor : " + str(e))
            pass

    xbmc.sleep(1000)
    xbmcgui.Window(10000).setProperty("EmbyCon_Service_Timestamp", str(int(time.time())))
    
# stop the WebSocket client
websocket_thread.stopClient()

log.info("Service shutting down")
