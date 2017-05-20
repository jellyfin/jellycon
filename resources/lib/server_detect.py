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

__settings__ = xbmcaddon.Addon(id='plugin.video.embycon')
__language__ = __settings__.getLocalizedString
__addon_name__ = __settings__.getAddonInfo('name')
downloadUtils = DownloadUtils()


def testServer(host, port):
    websocket_url = 'ws://%s:%s/' % (host, port)
    websocket = WebSocket()
    try:
        websocket.connect(websocket_url)
        websocket.close()
        return True
    except:
        return False


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
    
    log.info("MutliGroup       : " + str(MULTI_GROUP))
    log.info("Sending UDP Data : " + MESSAGE)
    sock.sendto(MESSAGE, MULTI_GROUP)

    servers = []

    # while True:
    try:
        data, addr = sock.recvfrom(1024)  # buffer size
        servers.append(json.loads(data))
    except Exception as e:
        log.error("Read UPD responce: %s" % e)
        # break

    log.info("Found Servers: %s" % servers)
    return servers


def checkServer(force=False, change_user=False, notify=False):
    log.info("checkServer Called")
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    serverUrl = ""

    if force is False:
        if (len(host) != 0) and (host != "<none>") and (len(port) != 0):
            log.info("detected server info in settings:  " + host + " : " + port)
            serverUrl = "http://%s:%s" % (host, port)
        if (len(host) == 0) or (host == "<none>") or (len(port) == 0):
            __settings__.openSettings()
            port = __settings__.getSetting('port')
            host = __settings__.getSetting('ipaddress')
            if (len(host) != 0) and (host != "<none>") and (len(port) != 0):
                serverUrl = "http://%s:%s" % (host, port)
            else:
                return
    if serverUrl == "":
        serverInfo = getServerDetails()
        if (len(serverInfo) == 0):
            log.info("getServerDetails failed")
            success = False
            if (len(host) != 0) and (host != "<none>") and (len(port) != 0):
                log.info("testServer %s:%s" % (host, port))
                success = testServer(host=host, port=port)
            if success:
                serverUrl = "http://%s:%s" % (host, port)
            else:
                xbmcgui.Dialog().ok(heading=__addon_name__, line1=__language__(30204))
                xbmc.executebuiltin("ActivateWindow(Home)")
                return
        if serverUrl == "":
            serverNames = []
            for server in serverInfo:
                serverNames.append(server.get("Name", __language__(30063)))
            return_index = xbmcgui.Dialog().select(__language__(30166), serverNames)

            if (return_index == -1):
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
        xbmcgui.Dialog().ok(heading=__addon_name__, line1=__language__(30202), line2=str(error))
        log.error(str(error))
    
    log.info("detected server info " + server_address + " : " + server_port)
    if notify:
        xbmcgui.Dialog().ok(__language__(30167), __language__(30168), __language__(30169) + server_address, __language__(30030) + server_port)

    if change_user:
        # get a list of users
        log.info("Getting user list")
        jsonData = downloadUtils.downloadUrl(server_address + ":" + server_port + "/emby/Users/Public?format=json", authenticate=False)

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

        username = __settings__.getSetting("username")
        if (len(username) > 0) and (not any(n == username for n in userList)):
            names.insert(0, __language__(30061) % username)
            userList.insert(0, username)
            secured.insert(0, True)
        names.insert(0, __language__(30062))
        userList.insert(0, '')
        secured.insert(0, True)
        log.info("User List : " + str(names))
        log.info("User List : " + str(userList))
        return_value = xbmcgui.Dialog().select(__language__(30180), names)

        if (return_value > -1):
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
            if selected_user:
                log.info("Setting Selected User : " + selected_user)
                if __settings__.getSetting("port") != server_port:
                    __settings__.setSetting("port", server_port)
                if __settings__.getSetting("ipaddress") != server_address:
                    __settings__.setSetting("ipaddress", server_address)
                if __settings__.getSetting("username") != selected_user:
                    __settings__.setSetting("username", selected_user)
                if secured[return_value] is True:
                    kb = xbmc.Keyboard()
                    kb.setHeading(__language__(30006))
                    kb.setHiddenInput(True)
                    kb.doModal()
                    if kb.isConfirmed():
                        __settings__.setSetting('password', kb.getText())
                else:
                    __settings__.setSetting('password', '')

        WINDOW = xbmcgui.Window(10000)
        WINDOW.clearProperty("userid")
        WINDOW.clearProperty("AccessToken")

        xbmc.executebuiltin("Container.Refresh")
