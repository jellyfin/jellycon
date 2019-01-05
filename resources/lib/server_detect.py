# Gnu General Public License - see LICENSE.TXT

import socket
import json
from urlparse import urlparse
import time
import hashlib
from datetime import datetime

import xbmcaddon
import xbmcgui
import xbmc

from kodi_utils import HomeWindow
from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from translation import string_load
from utils import datetime_from_string

log = SimpleLogging(__name__)

__addon__ = xbmcaddon.Addon()
__addon_name__ = __addon__.getAddonInfo('name')
downloadUtils = DownloadUtils()


def getServerDetails():
    log.debug("Getting Server Details from Network")
    servers = []

    MESSAGE = "who is EmbyServer?"
    MULTI_GROUP = ("<broadcast>", 7359)
    #MULTI_GROUP = ("127.0.0.1", 7359)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)  # timeout
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, 1)

    log.debug("MutliGroup: {0}", MULTI_GROUP)
    log.debug("Sending UDP Data: {0}", MESSAGE)

    # while True:
    try:
        sock.sendto(MESSAGE, MULTI_GROUP)
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                servers.append(json.loads(data))
            except:
                break
    except Exception as e:
        log.error("UPD Discovery Error: {0}", e)
        # break

    log.debug("Found Servers: {0}", servers)
    return servers


def checkServer(force=False, change_user=False, notify=False):
    log.debug("checkServer Called")

    settings = xbmcaddon.Addon()
    serverUrl = ""
    something_changed = False

    if force is False:
        # if not forcing use server details from settings
        svr = downloadUtils.getServer()
        if svr is not None:
            serverUrl = svr

    # if the server is not set then try to detect it
    if serverUrl == "":
        serverInfo = getServerDetails()

        serverNames = []
        for server in serverInfo:
            serverNames.append(server.get("Name", string_load(30063)))
        if serverNames:
            return_index = xbmcgui.Dialog().select(string_load(30166), serverNames)
        else:
            xbmcgui.Dialog().ok(__addon_name__, string_load(30282))
            return_index = -1

        if (return_index == -1):
            xbmc.executebuiltin("ActivateWindow(Home)")
            return

        serverUrl = serverInfo[return_index]["Address"]
        log.debug("Selected server: {0}", serverUrl)

        # parse the url
        url_bits = urlparse(serverUrl)
        server_address = url_bits.hostname
        server_port = str(url_bits.port)
        server_protocol = url_bits.scheme
        log.debug("Detected server info {0} - {1} - {2}", server_protocol, server_address, server_port)

        # save the server info
        settings.setSetting("port", server_port)
        settings.setSetting("ipaddress", server_address)

        if server_protocol == "https":
            settings.setSetting("use_https", "true")
        else:
            settings.setSetting("use_https", "false")

        something_changed = True
        if notify:
            xbmcgui.Dialog().ok(string_load(30167), string_load(30168),
                                string_load(30169) + server_address, string_load(30001) + server_port)

    # we need to change the user
    current_username = settings.getSetting("username")
    current_username = unicode(current_username, "utf-8")

    # if asked or we have no current user then show user selection screen
    if change_user or len(current_username) == 0:

        # stop playback when switching users
        xbmc.Player().stop()

        # get a list of users
        log.debug("Getting user list")
        json_data = downloadUtils.downloadUrl(serverUrl + "/emby/Users/Public?format=json", authenticate=False)

        log.debug("jsonData: {0}", json_data)
        try:
            result = json.loads(json_data)
        except:
            result = None

        if result is None:
            xbmcgui.Dialog().ok(string_load(30135),
                                string_load(30201),
                                string_load(30169) + serverUrl)

        else:
            selected_id = -1
            users = []
            for user in result:
                config = user.get("Configuration")
                if config is not None:
                    if config.get("IsHidden", False) is False:
                        name = user.get("Name")
                        admin = user.get("Policy", {}).get("IsAdministrator", False)

                        time_ago = ""
                        last_active = user.get("LastActivityDate")
                        if last_active:
                            last_active_date = datetime_from_string(last_active)
                            log.debug("LastActivityDate: {0}", last_active_date)
                            ago = datetime.now() - last_active_date
                            log.debug("LastActivityDate: {0}", ago)
                            days = divmod(ago.seconds, 86400)
                            hours = divmod(days[1], 3600)
                            minutes = divmod(hours[1], 60)
                            log.debug("LastActivityDate: {0} {1} {2}", days[0], hours[0], minutes[0])
                            if days[0]:
                                time_ago += " %sd" % days[0]
                            if hours[0]:
                                time_ago += " %sh" % hours[0]
                            if minutes[0]:
                                time_ago += " %sm" % minutes[0]
                            time_ago = time_ago.strip()
                            if not time_ago:
                                time_ago = "Active: now"
                            else:
                                time_ago = "Active: %s ago" % time_ago
                            log.debug("LastActivityDate: {0}", time_ago)

                        user_item = xbmcgui.ListItem(name)
                        user_image = downloadUtils.get_user_artwork(user, 'Primary')
                        if not user_image:
                            user_image = "DefaultUser.png"
                        art = {"Thumb": user_image}
                        user_item.setArt(art)
                        user_item.setLabel2("TEST")

                        sub_line = time_ago

                        if user.get("HasPassword", False) is True:
                            sub_line += ", Password"
                            user_item.setProperty("secure", "true")

                            m = hashlib.md5()
                            m.update(name)
                            hashed_username = m.hexdigest()
                            saved_password = settings.getSetting("saved_user_password_" + hashed_username)
                            if saved_password:
                                sub_line += ": Saved"

                        else:
                            user_item.setProperty("secure", "false")

                        if admin:
                            sub_line += ", Admin"
                        else:
                            sub_line += ", User"

                        user_item.setProperty("manual", "false")
                        user_item.setLabel2(sub_line)
                        users.append(user_item)

                        if current_username == name:
                            selected_id = len(users) - 1

            if current_username:
                selection_title = string_load(30180) + " (" + current_username + ")"
            else:
                selection_title = string_load(30180)

            # add manual login
            user_item = xbmcgui.ListItem(string_load(30365))
            art = {"Thumb": "DefaultUser.png"}
            user_item.setArt(art)
            user_item.setLabel2(string_load(30366))
            user_item.setProperty("secure", "true")
            user_item.setProperty("manual", "true")
            users.append(user_item)

            return_value = xbmcgui.Dialog().select(selection_title,
                                                   users,
                                                   preselect=selected_id,
                                                   autoclose=20000,
                                                   useDetails=True)

            if return_value > -1 and return_value != selected_id:

                something_changed = True
                selected_user = users[return_value]
                secured = selected_user.getProperty("secure") == "true"
                manual = selected_user.getProperty("manual") == "true"
                selected_user_name = selected_user.getLabel()

                log.debug("Selected User Name: {0} : {1}", return_value, selected_user_name)

                if manual:
                    kb = xbmc.Keyboard()
                    kb.setHeading(string_load(30005))
                    if current_username:
                        kb.setDefault(current_username)
                    kb.doModal()
                    if kb.isConfirmed():
                        selected_user_name = kb.getText()
                        log.debug("Manual entered username: {0}", selected_user_name)
                    else:
                        return

                if secured:
                    # we need a password, check the settings first
                    m = hashlib.md5()
                    m.update(selected_user_name)
                    hashed_username = m.hexdigest()
                    saved_password = settings.getSetting("saved_user_password_" + hashed_username)
                    allow_password_saving = settings.getSetting("allow_password_saving") == "true"

                    # if not saving passwords but have a saved ask to clear it
                    if not allow_password_saving and saved_password:
                        clear_password = xbmcgui.Dialog().yesno(string_load(30368), string_load(30369))
                        if clear_password:
                            settings.setSetting("saved_user_password_" + hashed_username, "")

                    if saved_password:
                        log.debug("Saving username and password: {0}", selected_user_name)
                        log.debug("Using stored password for user: {0}", hashed_username)
                        settings.setSetting("username", selected_user_name)
                        settings.setSetting('password', saved_password)
                    else:
                        kb = xbmc.Keyboard()
                        kb.setHeading(string_load(30006))
                        kb.setHiddenInput(True)
                        kb.doModal()
                        if kb.isConfirmed():
                            log.debug("Saving username and password: {0}", selected_user_name)
                            settings.setSetting("username", selected_user_name)
                            settings.setSetting('password', kb.getText())

                            # should we save the password
                            if allow_password_saving:
                                save_password = xbmcgui.Dialog().yesno(string_load(30363), string_load(30364))
                                if save_password:
                                    log.debug("Saving password for fast user switching: {0}", hashed_username)
                                    settings.setSetting("saved_user_password_" + hashed_username, kb.getText())
                else:
                    log.debug("Saving username with no password: {0}", selected_user_name)
                    settings.setSetting("username", selected_user_name)
                    settings.setSetting('password', '')

        if something_changed:
            home_window = HomeWindow()
            home_window.clearProperty("userid")
            home_window.clearProperty("AccessToken")
            home_window.clearProperty("userimage")
            home_window.setProperty("embycon_widget_reload", str(time.time()))
            download_utils = DownloadUtils()
            download_utils.authenticate()
            download_utils.getUserId()
            xbmc.executebuiltin("ActivateWindow(Home)")
            xbmc.executebuiltin("ReloadSkin()")
