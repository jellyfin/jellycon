

import logging
import socket
import json as json
from urlparse import urlparse

import xbmcaddon
import xbmcgui
import xbmc

from downloadutils import DownloadUtils

log = logging.getLogger("EmbyCon." + __name__)
__settings__ = xbmcaddon.Addon(id='plugin.video.embycon')
__language__ = __settings__.getLocalizedString
downloadUtils = DownloadUtils()

def getServerDetails():

    log.info("Getting Server Details from Network")

    MESSAGE = "who is EmbyServer?"
    MULTI_GROUP = ("<broadcast>", 7359)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(6.0)
    
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10) #timeout
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, 1)
    
    log.info("MutliGroup       : " + str(MULTI_GROUP));
    log.info("Sending UDP Data : " + MESSAGE);
    sock.sendto(MESSAGE, MULTI_GROUP)

    servers = []
    
    #while True:
    try:
        data, addr = sock.recvfrom(1024) # buffer size
        servers.append(json.loads(data))       
    except Exception as e:
        log.error("Read UPD responce: %s" % e)
        #break        

    log.info("Found Servers: %s" % servers)
    return servers
  
    
def checkServer(force = False):
    log.info("checkServer Called")
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    
    if(force == False and len(host) != 0 and host != "<none>"):
        log.info("server already set")
        return
    
    serverInfo = getServerDetails()
    
    if(len(serverInfo) == 0):
        log.info("getServerDetails failed")
        xbmc.executebuiltin("ActivateWindow(Home)")
        return
    
    serverNames = []
    for server in serverInfo:
        serverNames.append(server.get("Name", "N/A"))
    return_index = xbmcgui.Dialog().select("Select Server", serverNames)
    
    if(return_index == -1):
        xbmc.executebuiltin("ActivateWindow(Home)")
        return
    
    serverUrl = serverInfo[return_index]["Address"]
    log.info("Selected server: " + serverUrl)
    
    server_address = ""
    server_port = ""
    try:
        url_bits = urlparse(serverUrl)
        server_address = url_bits.hostname
        server_port = str(url_bits.port)
    except Exception as error:
        xbmcgui.Dialog().ok("Error Extracting Server host:port", str(error))
        log.error(str(error))
    
    log.info("detected server info " + server_address + " : " + server_port)
    
    #xbmcgui.Dialog().ok(__language__(30167), __language__(30168), __language__(30169) + server_address, __language__(30030) + server_port)

    # get a list of users
    log.info("Getting user list")
    jsonData = downloadUtils.downloadUrl(server_address + ":" + server_port + "/emby/Users/Public?format=json", authenticate=False)

    log.debug("jsonData : " + str(jsonData))
    result = json.loads(jsonData)
    
    names = []
    userList = []
    for user in result:
        config = user.get("Configuration")
        if(config != None):
            if(config.get("IsHidden") == None or config.get("IsHidden") == False):
                name = user.get("Name")
                userList.append(name)
                if(user.get("HasPassword") == True):
                    name = name + " (Secure)"
                names.append(name)

    log.info("User List : " + str(names))
    log.info("User List : " + str(userList))
    return_value = xbmcgui.Dialog().select(__language__(30200), names)
    
    if(return_value > -1):
        
        selected_user = userList[return_value]
        log.info("Setting Selected User : " + selected_user)
        if __settings__.getSetting("port") != server_port:
            __settings__.setSetting("port", server_port)
        if __settings__.getSetting("ipaddress") != server_address:        
            __settings__.setSetting("ipaddress", server_address)        
        if __settings__.getSetting("username") != selected_user:          
            __settings__.setSetting("username", selected_user)
        
        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.clearProperty("userid")
        WINDOW.clearProperty("AccessToken")

    xbmc.executebuiltin("ActivateWindow(Home)")
    xbmc.executebuiltin("XBMC.ReloadSkin()")
                