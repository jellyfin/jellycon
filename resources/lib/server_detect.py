# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

import socket
import json
from six.moves.urllib.parse import urlparse
import requests
import ssl
import time
import hashlib
from datetime import datetime

import xbmcaddon
import xbmcgui
import xbmc
from kodi_six.utils import py2_decode

from .kodi_utils import HomeWindow
from .downloadutils import DownloadUtils, save_user_details, load_user_details
from .loghandler import LazyLogger
from .translation import string_load
from .utils import datetime_from_string
from .clientinfo import ClientInformation

log = LazyLogger(__name__)

__addon__ = xbmcaddon.Addon()
__addon_name__ = __addon__.getAddonInfo('name')


def check_connection_speed():
    log.debug("check_connection_speed")

    settings = xbmcaddon.Addon()
    verify_cert = settings.getSetting('verify_cert') == 'true'
    http_timeout = int(settings.getSetting("http_timeout"))
    speed_test_data_size = int(settings.getSetting("speed_test_data_size"))
    test_data_size = speed_test_data_size * 1000000

    du = DownloadUtils()
    server = du.get_server()

    url = server + "/playback/bitratetest?size=%s" % test_data_size

    head = du.get_auth_header(True)
    head["User-Agent"] = "JellyCon-" + ClientInformation().get_version()

    request_details = {
        "stream": True,
        "headers": head
    }

    if not verify_cert:
        request_details["verify"] = False

    progress_dialog = xbmcgui.DialogProgress()
    message = 'Testing with {0} MB of data'.format(speed_test_data_size)
    progress_dialog.create("JellyCon connection speed test", message)
    start_time = time.time()

    log.debug("Starting Connection Speed Test")

    response = requests.get(url, **request_details)

    last_percentage_done = 0
    total_data_read = 0
    if response.status_code == 200:
        for data in response.iter_content(chunk_size=10240):
            total_data_read += len(data)
            percentage_done = int(float(total_data_read) / float(test_data_size) * 100.0)
            if last_percentage_done != percentage_done:
                progress_dialog.update(percentage_done)
                last_percentage_done = percentage_done
    else:
        log.error("HTTP response error: {0} {1}".format(response.status_code, response.content))
        error_message = "HTTP response error: %s\n%s" % (response.status_code, response.content)
        xbmcgui.Dialog().ok("Speed Test Error", error_message)
        return -1

    total_data_read_kbits = (total_data_read * 8) / 1000
    total_time = time.time() - start_time
    speed = int(total_data_read_kbits / total_time)
    log.debug("Finished Connection Speed Test, speed: {0} total_data: {1}, total_time: {2}".format(speed, total_data_read, total_time))

    progress_dialog.close()
    del progress_dialog

    heading = "Speed Test Result : {0:,} Kbs".format(speed)
    message = "Do you want to set this speed as your max stream bitrate for playback?\n"
    message += "{0:,} MB over {1} sec".format(int((total_data_read / 1000000)), total_time)

    response = xbmcgui.Dialog().yesno(heading, message)
    if response:
        settings.setSetting("max_stream_bitrate", str(speed))

    return speed


def check_safe_delete_available():
    log.debug("check_safe_delete_available")

    du = DownloadUtils()
    result = du.download_url("{server}/Plugins")
    if result:
        log.debug("Server Plugin List: {0}".format(result))

        safe_delete_found = False
        for plugin in result:
            if plugin["Name"] == "Safe Delete":
                safe_delete_found = True
                break

        log.debug("Safe Delete Plugin Available: {0}".format(safe_delete_found))
        home_window = HomeWindow()
        if safe_delete_found:
            home_window.set_property("safe_delete_plugin_available", "true")
        else:
            home_window.clear_property("safe_delete_plugin_available")

    else:
        log.debug("Error getting server plugin list")


def get_server_details():
    log.debug("Getting Server Details from Network")
    servers = []

    message = b"who is JellyfinServer?"
    multi_group = ("<broadcast>", 7359)
    # multi_group = ("127.0.0.1", 7359)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    log.debug("MutliGroup: {0}".format(multi_group))
    log.debug("Sending UDP Data: {0}".format(message))

    progress = xbmcgui.DialogProgress()
    progress.create('{} : {}'.format(__addon_name__, string_load(30373)))
    progress.update(0, string_load(30374))
    xbmc.sleep(1000)
    server_count = 0

    # while True:
    try:
        sock.sendto(message, multi_group)
        while True:
            try:
                server_count += 1
                progress.update(server_count * 10, '{}: {}'.format(string_load(30375), server_count))
                xbmc.sleep(1000)
                data, addr = sock.recvfrom(1024)
                servers.append(json.loads(data))
            except:
                break
    except Exception as e:
        log.error("UPD Discovery Error: {0}".format(e))

    progress.close()

    log.debug("Found Servers: {0}".format(servers))
    return servers


def check_server(force=False, change_user=False, notify=False):
    log.debug("checkServer Called")

    settings = xbmcaddon.Addon()
    server_url = ""
    something_changed = False
    du = DownloadUtils()

    if force is False:
        # if not forcing use server details from settings
        svr = du.get_server()
        if svr is not None:
            server_url = svr

    # if the server is not set then try to detect it
    if server_url == "":

        # scan for local server
        server_info = get_server_details()

        addon = xbmcaddon.Addon()
        server_icon = addon.getAddonInfo('icon')

        server_list = []
        for server in server_info:
            server_item = xbmcgui.ListItem(server.get("Name", string_load(30063)))
            sub_line = server.get("Address")
            server_item.setLabel2(sub_line)
            server_item.setProperty("address", server.get("Address"))
            art = {"Thumb": server_icon}
            server_item.setArt(art)
            server_list.append(server_item)

        if len(server_list) > 0:
            return_index = xbmcgui.Dialog().select('{} : {}'.format(__addon_name__, string_load(30166)),
                                                   server_list,
                                                   useDetails=True)
            if return_index != -1:
                server_url = server_info[return_index]["Address"]

        if not server_url:
            return_index = xbmcgui.Dialog().yesno(__addon_name__, '{}\n{}'.format(string_load(30282), string_load(30370)))
            if not return_index:
                xbmc.executebuiltin("ActivateWindow(Home)")
                return

            while True:
                kb = xbmc.Keyboard()
                kb.setHeading(string_load(30372))
                if server_url:
                    kb.setDefault(server_url)
                else:
                    kb.setDefault("http://<server address>:8096")
                kb.doModal()
                if kb.isConfirmed():
                    server_url = kb.getText()
                else:
                    xbmc.executebuiltin("ActivateWindow(Home)")
                    return

                public_lookup_url = "%s/System/Info/Public?format=json" % (server_url)

                log.debug("Testing_Url: {0}".format(public_lookup_url))
                progress = xbmcgui.DialogProgress()
                progress.create('{} : {}'.format(__addon_name__, string_load(30376)))
                progress.update(0, string_load(30377))
                result = du.download_url(public_lookup_url, authenticate=False)
                progress.close()

                if result:
                    xbmcgui.Dialog().ok('{} : {}'.format(__addon_name__, string_load(30167)),
                                        server_url)
                    break
                else:
                    return_index = xbmcgui.Dialog().yesno('{} : {}'.format(__addon_name__, string_load(30135)),
                                                          server_url,
                                                          string_load(30371))
                    if not return_index:
                        xbmc.executebuiltin("ActivateWindow(Home)")
                        return

        log.debug("Selected server: {0}".format(server_url))
        settings.setSetting("server_address", server_url)
        something_changed = True

    # do we need to change the user
    user_details = load_user_details(settings)
    current_username = user_details.get("username", "")
    current_username = py2_decode(current_username)

    # if asked or we have no current user then show user selection screen
    if something_changed or change_user or len(current_username) == 0:

        # stop playback when switching users
        xbmc.Player().stop()
        du = DownloadUtils()

        # get a list of users
        log.debug("Getting user list")
        result = du.download_url(server_url + "/Users/Public?format=json", authenticate=False)

        log.debug("jsonData: {0}".format(py2_decode(result)))

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
                        log.debug("LastActivityDate: {0}".format(last_active_date))
                        ago = datetime.now() - last_active_date
                        log.debug("LastActivityDate: {0}".format(ago))
                        days = divmod(ago.seconds, 86400)
                        hours = divmod(days[1], 3600)
                        minutes = divmod(hours[1], 60)
                        log.debug("LastActivityDate: {0} {1} {2}".format(days[0], hours[0], minutes[0]))
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
                        log.debug("LastActivityDate: {0}".format(time_ago))

                    user_item = xbmcgui.ListItem(name)
                    user_image = du.get_user_artwork(user, 'Primary')
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

            log.debug("Selected User Name: {0} : {1}".format(return_value, selected_user_name))

            if manual:
                kb = xbmc.Keyboard()
                kb.setHeading(string_load(30005))
                if current_username:
                    kb.setDefault(current_username)
                kb.doModal()
                if kb.isConfirmed():
                    selected_user_name = kb.getText()
                    log.debug("Manual entered username: {0}".format(selected_user_name))
                else:
                    return

            if secured:
                # we need a password, check the settings first
                m = hashlib.md5()
                m.update(selected_user_name.encode())
                hashed_username = m.hexdigest()
                saved_password = settings.getSetting("saved_user_password_" + hashed_username)
                allow_password_saving = settings.getSetting("allow_password_saving") == "true"

                # if not saving passwords but have a saved ask to clear it
                if not allow_password_saving and saved_password:
                    clear_password = xbmcgui.Dialog().yesno(string_load(30368), string_load(30369))
                    if clear_password:
                        settings.setSetting("saved_user_password_" + hashed_username, "")

                if saved_password:
                    log.debug("Saving username and password: {0}".format(selected_user_name))
                    log.debug("Using stored password for user: {0}".format(hashed_username))
                    save_user_details(settings, selected_user_name, saved_password)

                else:
                    kb = xbmc.Keyboard()
                    kb.setHeading(string_load(30006))
                    kb.setHiddenInput(True)
                    kb.doModal()
                    if kb.isConfirmed():
                        log.debug("Saving username and password: {0}".format(selected_user_name))
                        save_user_details(settings, selected_user_name, kb.getText())

                        # should we save the password
                        if allow_password_saving:
                            save_password = xbmcgui.Dialog().yesno(string_load(30363), string_load(30364))
                            if save_password:
                                log.debug("Saving password for fast user switching: {0}".format(hashed_username))
                                settings.setSetting("saved_user_password_" + hashed_username, kb.getText())
            else:
                log.debug("Saving username with no password: {0}".format(selected_user_name))
                save_user_details(settings, selected_user_name, "")

        if something_changed:
            home_window = HomeWindow()
            home_window.clear_property("userid")
            home_window.clear_property("AccessToken")
            home_window.clear_property("userimage")
            home_window.clear_property("jellycon_widget_reload")
            du = DownloadUtils()
            du.authenticate()
            du.get_user_id()
            xbmc.executebuiltin("ActivateWindow(Home)")
            if "estuary_jellycon" in xbmc.getSkinDir():
                xbmc.executebuiltin("SetFocus(9000, 0, absolute)")
            xbmc.executebuiltin("ReloadSkin()")
