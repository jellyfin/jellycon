#################################################################################################
# WebSocket Client thread
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
import urllib
import socket
import websocket
import logging

from clientinfo import ClientInformation
from downloadutils import DownloadUtils

log = logging.getLogger("EmbyCon." + __name__)

class WebSocketThread(threading.Thread):

    client = None
    keepRunning = True
    
    def __init__(self, *args):    
        log.info("EmbyCon WebSocketThread")
        
        threading.Thread.__init__(self, *args)
    
    def playbackStarted(self, itemId):
        if(self.client != None):
            try:
                log.info("Sending Playback Started")
                messageData = {}
                messageData["MessageType"] = "PlaybackStart"
                messageData["Data"] = itemId + "|true|audio,video"
                messageString = json.dumps(messageData)
                log.info("Message Data : " + messageString)
                self.client.send(messageString)
            except Exception, e:
                log.debug("Exception : " + str(e))
        else:
            log.info("Sending Playback Started NO Object ERROR")
            
    def playbackStopped(self, itemId, ticks):
        if(self.client != None):
            try:
                log.info("Sending Playback Stopped : " + str(ticks))
                messageData = {}
                messageData["MessageType"] = "PlaybackStopped"
                messageData["Data"] = itemId + "|" + str(ticks)
                messageString = json.dumps(messageData)
                self.client.send(messageString)
            except Exception, e:
                log.error("Exception : " + str(e))            
        else:
            log.info("Sending Playback Stopped NO Object ERROR")
            
    def sendProgressUpdate(self, itemId, ticks):
        if(self.client != None):
            try:
                log.info("Sending Progress Update : " + str(ticks))
                messageData = {}
                messageData["MessageType"] = "PlaybackProgress"
                messageData["Data"] = itemId + "|" + str(ticks) + "|false|false"
                messageString = json.dumps(messageData)
                log.info("Message Data : " + messageString)
                self.client.send(messageString)
            except Exception, e:
                log.error("Exception : " + str(e))              
        else:
            log.info("Sending Progress Update NO Object ERROR")
            
    def stopClient(self):
        # stopping the client is tricky, first set keep_running to false and then trigger one 
        # more message by requesting one SessionsStart message, this causes the 
        # client to receive the message and then exit
        if(self.client != None):
            log.info("Stopping Client")
            self.keepRunning = False
            self.client.keep_running = False
            self.client.close()           
            log.info("Stopping Client : KeepRunning set to False")
            '''
            try:
                self.keepRunning = False
                self.client.keep_running = False
                log.debug("Stopping Client")
                log.debug("Calling Ping")
                self.client.sock.ping()
                
                log.debug("Calling Socket Shutdown()")
                self.client.sock.sock.shutdown(socket.SHUT_RDWR)
                log.debug("Calling Socket Close()")
                self.client.sock.sock.close()
                log.debug("Stopping Client Done")
                log.debug("Calling Ping")
                self.client.sock.ping()     
                               
            except Exception, e:
                log.debug("Exception : " + str(e))      
            '''
        else:
            log.info("Stopping Client NO Object ERROR")
            
    def on_message(self, ws, message):
        log.info("Message : " + str(message))
        result = json.loads(message)
        
        messageType = result.get("MessageType")
        playCommand = result.get("PlayCommand")
        data = result.get("Data")
        
        if(messageType != None and messageType == "Play" and data != None):
            itemIds = data.get("ItemIds")
            playCommand = data.get("PlayCommand")
            if(playCommand != None and playCommand == "PlayNow"):
            
                startPositionTicks = data.get("StartPositionTicks")
                log.info("Playing Media With ID : " + itemIds[0])
                
                addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
                mb3Host = addonSettings.getSetting('ipaddress')
                mb3Port = addonSettings.getSetting('port')                   
                
                url =  mb3Host + ":" + mb3Port + ',;' + itemIds[0]
                if(startPositionTicks == None):
                    url  += ",;" + "-1"
                else:
                    url  += ",;" + str(startPositionTicks)
                    
                playUrl = "plugin://plugin.video.embycon/?url=" + url + '&mode=PLAY'
                playUrl = playUrl.replace("\\\\","smb://")
                playUrl = playUrl.replace("\\","/")                
                
                xbmc.Player().play(playUrl)
                
        elif(messageType != None and messageType == "Playstate"):
            command = data.get("Command")
            if(command != None and command == "Stop"):
                log.info("Playback Stopped")
                xbmc.executebuiltin('xbmc.activatewindow(10000)')
                xbmc.Player().stop()
                
            if(command != None and command == "Seek"):
                seekPositionTicks = data.get("SeekPositionTicks")
                log.info("Playback Seek : " + str(seekPositionTicks))
                seekTime = (seekPositionTicks / 1000) / 10000
                xbmc.Player().seekTime(seekTime)

    def on_error(self, ws, error):
        log.info("Error : " + str(error))

    def on_close(self, ws):
        log.info("Closed")

    def on_open(self, ws):
        try:
            clientInfo = ClientInformation()
            machineId = clientInfo.getMachineId()
            version = clientInfo.getVersion()
            messageData = {}
            messageData["MessageType"] = "Identity"
            
            addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
            deviceName = addonSettings.getSetting('deviceName')
            deviceName = deviceName.replace("\"", "_")
        
            messageData["Data"] = "XBMC|" + machineId + "|" + version + "|" + deviceName
            messageString = json.dumps(messageData)
            log.info("Opened : " + str(messageString))
            ws.send(messageString)
            
            downloadUtils = DownloadUtils()
            
            # get session ID
            addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
            mb3Host = addonSettings.getSetting('ipaddress')
            mb3Port = addonSettings.getSetting('port')
            
            url = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Sessions?DeviceId=" + machineId + "&format=json"
            log.info("Session URL : " + url);
            jsonData = downloadUtils.downloadUrl(url)
            log.info("Session JsonData : " + jsonData)
            result = json.loads(jsonData)
            log.info("Session JsonData : " + str(result))
            sessionId = result[0].get("Id")
            log.info("Session Id : " + str(sessionId))
            
            url = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Sessions/Capabilities?Id=" + sessionId + "&PlayableMediaTypes=Video&SupportedCommands=Play&SupportsMediaControl=True"
            postData = {}
            postData["Id"] = sessionId;
            postData["PlayableMediaTypes"] = "Video";
            stringdata = json.dumps(postData)
            log.info("Capabilities URL : " + url);
            log.info("Capabilities Data : " + stringdata)
            downloadUtils.downloadUrl(url, postBody=stringdata, type="POST")
            
        except Exception, e:
            log.error("Exception : " + str(e))                
        
    def run(self):
    
        while(self.keepRunning and xbmc.abortRequested == False):
        
            addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
            mb3Host = addonSettings.getSetting('ipaddress')
            mb3Port = addonSettings.getSetting('port')
            
            addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
            logLevel = int(addonSettings.getSetting('logLevel'))              
            if(logLevel == 2):
                websocket.enableTrace(True)
            
            if(mb3Host != None and len(mb3Host) > 0):

                try:
                
                    wsPort = mb3Port
                    log.info("WebSocketPortNumber = " + str(wsPort))
                        
                    downloadUtils = DownloadUtils()
                    authHeaders = downloadUtils.getAuthHeader()
                    flatHeaders = []
                    for header in authHeaders:
                        flatHeaders.append(header + ": " + authHeaders[header])
                    log.info("Flat Header : " + str(flatHeaders))
                    
                    # Make a call to /System/Info. WebSocketPortNumber is the port hosting the web socket.
                    webSocketUrl = "ws://" +  mb3Host + ":" + str(wsPort) + "/mediabrowser"
                    log.info("WebSocket URL : " + webSocketUrl)
                    self.client = websocket.WebSocketApp(webSocketUrl,
                                                header = flatHeaders,
                                                on_message = self.on_message,
                                                on_error = self.on_error,
                                                on_close = self.on_close)
                                                
                    self.client.on_open = self.on_open
                
                    log.info("Client Starting")
                    if(self.keepRunning):
                        self.client.run_forever()
                except:
                    log.info("Error thrown in Web Socket Setup")
            
            if(self.keepRunning and xbmc.abortRequested == False):
                log.info("Client Needs To Restart")
                xbmc.sleep(5000)
            
        log.info("Thread Exited")
        
        
        
        
