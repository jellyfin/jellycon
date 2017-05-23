# Gnu General Public License - see LICENSE.TXT

import socket
import json as json
from urlparse import urlparse

import xbmcaddon
import xbmcgui
import xbmc

from websocket import WebSocket
from downloadutils import DownloadUtils
from simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon." + __name__)

__addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
__language__ = __addon__.getLocalizedString
__addon_name__ = __addon__.getAddonInfo('name')
downloadUtils = DownloadUtils()

def getServerDetails():
    log.debug("Getting Server Details from Network")

    MESSAGE = "who is EmbyServer?"
    MULTI_GROUP = ("<broadcast>", 7359)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(6.0)
    
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10) #timeout
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, 1)
    
    log.debug("MutliGroup       : " + str(MULTI_GROUP))
    log.debug("Sending UDP Data : " + MESSAGE)
    sock.sendto(MESSAGE, MULTI_GROUP)

    servers = []

    # while True:
    try:
        data, addr = sock.recvfrom(1024)  # buffer size
        servers.append(json.loads(data))
    except Exception as e:
        log.error("Read UPD responce: %s" % e)
        # break

    log.debug("Found Servers: %s" % servers)
    return servers


def checkServer(force=False, change_user=False, notify=False):
    log.debug("checkServer Called")

    settings = xbmcaddon.Addon(id='plugin.video.embycon')
    port = settings.getSetting('port')
    host = settings.getSetting('ipaddress')
    serverUrl = ""

    if force is False:
        # if not forcing use server details from settings
        if (len(host) != 0) and (host != "<none>") and (len(port) != 0):
            log.debug("Server info from settings:  " + host + " : " + port)
            serverUrl = "http://%s:%s" % (host, port)

    # if the server is not set then try to detect it
    if serverUrl == "":
        serverInfo = getServerDetails()

        if (len(serverInfo) == 0):
            # server detect failed
            log.debug("getServerDetails failed")
            return

        serverNames = []
        for server in serverInfo:
            serverNames.append(server.get("Name", __language__(30063)))
        return_index = xbmcgui.Dialog().select(__language__(30166), serverNames)

        if (return_index == -1):
            xbmc.executebuiltin("ActivateWindow(Home)")
            return

        serverUrl = serverInfo[return_index]["Address"]
        log.debug("Selected server: " + serverUrl)

        # parse the url
        url_bits = urlparse(serverUrl)
        server_address = url_bits.hostname
        server_port = str(url_bits.port)
        log.info("Detected server info " + server_address + " : " + server_port)

        # save the server info
        settings.setSetting("port", server_port)
        settings.setSetting("ipaddress", server_address)

        if notify:
            xbmcgui.Dialog().ok(__language__(30167), __language__(30168), __language__(30169) + server_address, __language__(30030) + server_port)

    # we need to change the user
    current_username = settings.getSetting("username")

    # if asked or we have no current user then show user selection screen
    if change_user or len(current_username) == 0:
        # get a list of users
        log.info("Getting user list")
        jsonData = downloadUtils.downloadUrl(serverUrl + "/emby/Users/Public?format=json", authenticate=False)

        log.debug("jsonData : " + str(jsonData))
        result = json.loads(jsonData)

        names = []
        userList = []
        secured = []
        for user in result:
            config = user.get("Configuration")
            if (config != None):
                if (config.get("IsHidden") is None) or (config.get("IsHidden") is False):
                    name = user.get("Name")
                    userList.append(name)
                    if (user.get("HasPassword") is True):
                        secured.append(True)
                        name = __language__(30060) % name
                    else:
                        secured.append(False)
                    names.append(name)

        if (len(current_username) > 0) and (not any(n == current_username for n in userList)):
            names.insert(0, __language__(30061) % current_username)
            userList.insert(0, current_username)
            secured.insert(0, True)

        names.insert(0, __language__(30062))
        userList.insert(0, '')
        secured.insert(0, True)
        log.debug("User List : " + str(names))
        log.debug("User List : " + str(userList))

        return_value = xbmcgui.Dialog().select(__language__(30180), names)

        if (return_value > -1):
            log.debug("Selected User Index : " + str(return_value))
            if return_value == 0:
                kb = xbmc.Keyboard()
                kb.setHeading(__language__(30005))
                kb.doModal()
                if kb.isConfirmed():
                    selected_user = kb.getText()
                else:
                    selected_user = None
            else:
                selected_user = userList[return_value]

            log.debug("Selected User Name : " + str(selected_user))

            if selected_user:
                # we have a user so save it
                log.debug("Saving Username : " + selected_user)
                settings.setSetting("username", selected_user)
                if secured[return_value] is True:
                    kb = xbmc.Keyboard()
                    kb.setHeading(__language__(30006))
                    kb.setHiddenInput(True)
                    kb.doModal()
                    if kb.isConfirmed():
                        log.debug("Saving Password for Username : " + selected_user)
                        settings.setSetting('password', kb.getText())
                else:
                    settings.setSetting('password', '')

        WINDOW = xbmcgui.Window(10000)
        WINDOW.clearProperty("userid")
        WINDOW.clearProperty("AccessToken")

        xbmc.executebuiltin("ActivateWindow(Home)")
