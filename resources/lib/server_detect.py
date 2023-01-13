from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import socket
import json
import time

import xbmcaddon
import xbmcgui
import xbmc

from .kodi_utils import HomeWindow
from .jellyfin import API
from .lazylogger import LazyLogger
from .utils import (
    datetime_from_string, translate_string, save_user_details,
    load_user_details, get_current_datetime, get_saved_users
)

log = LazyLogger(__name__)

__addon__ = xbmcaddon.Addon()
__addon_name__ = __addon__.getAddonInfo('name')


def check_connection_speed():
    log.debug("check_connection_speed")

    settings = xbmcaddon.Addon()
    speed_test_data_size = int(settings.getSetting("speed_test_data_size"))
    test_data_size = speed_test_data_size * 1000000
    user_details = load_user_details()

    api = API(
        settings.getSetting('server_address'),
        user_details.get('user_id'),
        user_details.get('token')
    )

    progress_dialog = xbmcgui.DialogProgress()
    message = 'Testing with {0} MB of data'.format(speed_test_data_size)
    progress_dialog.create("JellyCon connection speed test", message)
    start_time = time.time()

    log.debug("Starting Connection Speed Test")
    response = api.speedtest(test_data_size)

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


def get_server_details():
    log.debug("Getting Server Details from Network")
    servers = []

    message = b"who is JellyfinServer?"
    multi_group = ("<broadcast>", 7359)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    log.debug("MutliGroup: {0}".format(multi_group))
    log.debug("Sending UDP Data: {0}".format(message))

    progress = xbmcgui.DialogProgress()
    progress.create('{} : {}'.format(__addon_name__, translate_string(30373)))
    progress.update(0, translate_string(30374))
    xbmc.sleep(1000)
    server_count = 0

    try:
        sock.sendto(message, multi_group)
        while True:
            try:
                server_count += 1
                progress.update(server_count * 10, '{}: {}'.format(translate_string(30375), server_count))
                xbmc.sleep(1000)
                data, addr = sock.recvfrom(1024)
                servers.append(json.loads(data))
            except:  # noqa
                break
    except Exception as e:
        log.error("UPD Discovery Error: {0}".format(e))

    progress.close()

    log.debug("Found Servers: {0}".format(servers))
    return servers


def check_server(force=False, change_user=False, notify=False):
    log.debug("checkServer Called")

    settings = xbmcaddon.Addon()
    something_changed = False

    # Initialize api object
    api = API()

    if force is False:
        # if not forcing use server details from settings
        api.server = settings.getSetting('server_address')

    # if the server is not set then try to detect it
    if not api.server:

        # scan for local server
        server_info = get_server_details()

        addon = xbmcaddon.Addon()
        server_icon = addon.getAddonInfo('icon')

        server_list = []
        for server in server_info:
            server_item = xbmcgui.ListItem(server.get("Name", translate_string(30063)))
            sub_line = server.get("Address")
            server_item.setLabel2(sub_line)
            server_item.setProperty("address", server.get("Address"))
            art = {"Thumb": server_icon}
            server_item.setArt(art)
            server_list.append(server_item)

        if len(server_list) > 0:
            return_index = xbmcgui.Dialog().select('{} : {}'.format(__addon_name__, translate_string(30166)),
                                                   server_list,
                                                   useDetails=True)
            if return_index != -1:
                api.server = server_info[return_index]["Address"]

        if not api.server:
            return_index = xbmcgui.Dialog().yesno(__addon_name__, '{}\n{}'.format(translate_string(30282), translate_string(30370)))
            if not return_index:
                xbmc.executebuiltin("ActivateWindow(Home)")
                return

            while True:
                kb = xbmc.Keyboard()
                kb.setHeading(translate_string(30372))
                if api.server:
                    kb.setDefault(api.server)
                else:
                    kb.setDefault("http://")
                kb.doModal()
                if kb.isConfirmed():
                    api.server = kb.getText()
                else:
                    xbmc.executebuiltin("ActivateWindow(Home)")
                    return

                progress = xbmcgui.DialogProgress()
                progress.create('{} : {}'.format(__addon_name__, translate_string(30376)))
                progress.update(0, translate_string(30377))
                result = api.get('/System/Info/Public')
                progress.close()

                if result:
                    xbmcgui.Dialog().ok('{} : {}'.format(__addon_name__, translate_string(30167)),
                                        api.server)
                    break
                else:
                    return_index = xbmcgui.Dialog().yesno('{} : {}'.format(__addon_name__, translate_string(30135)),
                                                          api.server,
                                                          translate_string(30371))
                    if not return_index:
                        xbmc.executebuiltin("ActivateWindow(Home)")
                        return

        log.debug("Selected server: {0}".format(api.server))
        settings.setSetting("server_address", api.server)
        something_changed = True

    # do we need to change the user
    current_username = settings.getSetting('username')
    user_details = load_user_details()
    home_window = HomeWindow()
    home_window.set_property('user_name', current_username)

    # if asked or we have no current user then show user selection screen
    if something_changed or change_user or len(current_username) == 0 or not user_details:

        # stop playback when switching users
        xbmc.Player().stop()

        # Initialize auth variable
        auth = {}

        # Check if quick connect is active on the server, initiate connection
        quick = api.get('/QuickConnect/Initiate')
        code = quick.get('Code')
        secret = quick.get('Secret')
        users, user_selection = user_select(api, current_username, code)

        if user_selection > -1:
            # The user made a selection in the dialog
            something_changed = True
            selected_user = users[user_selection]
            quick_connect = selected_user.getProperty("quickconnect") == "true"
            count = 0
            if quick_connect:
                # Try to authenticate to server with secret code 10 times
                while count < 10:
                    log.debug('Checking for quick connect auth: attempt {}'.format(count))
                    check = api.get('/QuickConnect/Connect?secret={}'.format(secret))
                    if check.get('Authenticated'):
                        break
                    count += 1
                    xbmc.sleep(1000)

                auth = api.post('/Users/AuthenticateWithQuickConnect',
                                {'secret': secret})

                # If authentication was successful, save the username
                if auth:
                    selected_user_name = auth['User'].get('Name')
                else:
                    # Login failed, we don't want to change anything
                    something_changed = False
                    log.info("There was an error logging in with quick connect")

            else:
                selected_user_name = selected_user.getLabel()
                secured = selected_user.getProperty("secure") == "true"
                manual = selected_user.getProperty("manual") == "true"

                # If using a manual login, ask for username
                if manual:
                    kb = xbmc.Keyboard()
                    kb.setHeading(translate_string(30005))
                    if current_username:
                        kb.setDefault(current_username)
                    kb.doModal()
                    if kb.isConfirmed():
                        selected_user_name = kb.getText()
                        log.debug("Manual entered username: {0}".format(selected_user_name))
                    else:
                        return

                home_window.set_property('user_name', selected_user_name)
                settings.setSetting('username', selected_user_name)
                user_details = load_user_details()

                if not user_details:
                    # Ask for password if user has one
                    password = ''
                    if secured and not user_details.get('token'):
                        kb = xbmc.Keyboard()
                        kb.setHeading(translate_string(30006))
                        kb.setHiddenInput(True)
                        kb.doModal()
                        if kb.isConfirmed():
                            password = kb.getText()

                    auth_payload = {'username': selected_user_name, 'pw': password}
                    auth = api.authenticate(auth_payload)
                    if not auth:
                        # Login failed, we don't want to change anything
                        something_changed = False
                        log.info('There was an error logging in with user {}'.format(selected_user_name))
                        xbmcgui.Dialog().ok(__addon_name__, translate_string(30446))

        if something_changed:
            home_window = HomeWindow()
            home_window.clear_property("jellycon_widget_reload")
            if auth:
                token = auth.get('AccessToken')
                user_id = auth.get('User').get('Id')
            else:
                token = user_details.get('token')
                user_id = user_details.get('user_id')
            save_user_details(selected_user_name, user_id, token)
            xbmc.executebuiltin("ActivateWindow(Home)")
            if "estuary_jellycon" in xbmc.getSkinDir():
                xbmc.executebuiltin("SetFocus(9000, 0, absolute)")
            xbmc.executebuiltin("ReloadSkin()")


def user_select(api, current_username, code):
    '''
    Display user selection screen
    '''
    # Retrieve list of public users from server
    public = api.get('/Users/Public')

    # Get list of saved users
    saved_users = get_saved_users()

    # Combine public and saved users
    for user in saved_users:
        name = user.get('Name')
        # Check if saved user is in public list
        if name not in [x.get('Name', '') for x in public]:
            # If saved user is not already in list, add it
            public.append(user)

    # Build user display
    selected_id = -1
    users = []
    # If quick connect is active, make it the first entry
    if code:
        user_item = xbmcgui.ListItem(code)
        user_image = "DefaultUser.png"
        art = {"Thumb": user_image}
        user_item.setArt(art)
        user_item.setLabel2(translate_string(30443))
        user_item.setProperty('quickconnect', "true")
        users.append(user_item)

    for user in public:
        user_item = create_user_listitem(api.server, user)
        if user_item:
            users.append(user_item)
        name = user.get("Name")

        # Highlight currently logged in user
        if current_username == name:
            selected_id = len(users) - 1

    if current_username:
        selection_title = translate_string(30180) + " (" + current_username + ")"
    else:
        selection_title = translate_string(30180)

    # Add manual login item
    user_item = xbmcgui.ListItem(translate_string(30365))
    art = {"Thumb": "DefaultUser.png"}
    user_item.setArt(art)
    user_item.setLabel2(translate_string(30366))
    user_item.setProperty("secure", "true")
    user_item.setProperty("manual", "true")
    users.append(user_item)

    user_selection = xbmcgui.Dialog().select(
        selection_title,
        users,
        preselect=selected_id,
        autoclose=60000,
        useDetails=True)

    return (users, user_selection)


def create_user_listitem(server, user):
    '''
    Create a user listitem for the user selection screen
    '''
    config = user.get("Configuration")
    now = get_current_datetime()
    if config is not None:
        name = user.get("Name")
        time_ago = ""
        last_active = user.get("LastActivityDate")
        # Calculate how long it's been since the user was last active
        if last_active:
            last_active_date = datetime_from_string(last_active)
            ago = now - last_active_date
            # Check days
            if ago.days > 0:
                time_ago += ' {}d'.format(ago.days)
            # Check minutes
            if ago.seconds > 60:
                hours = 0
                # Check hours
                if ago.seconds > 3600:
                    hours = int(ago.seconds/3600)
                    time_ago += ' {}h'.format(hours)
                minutes = int((ago.seconds - (hours * 3600)) / 60)
                time_ago += ' {}m'.format(minutes)
            time_ago = time_ago.strip()
            if not time_ago:
                time_ago = "Active: now"
            else:
                time_ago = "Active: {} ago".format(time_ago)

        user_item = xbmcgui.ListItem(name)

        # If the user doesn't have a profile image, user the default
        if 'PrimaryImageTag' not in user:
            user_image = "DefaultUser.png"
        else:
            user_id = user.get('Id')
            tag = user.get('PrimaryImageTag')
            user_image = '{}/Users/{}/Images/Primary?Format=original&tag={}'.format(
                server, user_id, tag
            )

        art = {"Thumb": user_image}
        user_item.setArt(art)

        sub_line = time_ago

        if user.get("HasPassword", False) is True:
            user_item.setProperty("secure", "true")
        else:
            user_item.setProperty("secure", "false")

        user_item.setProperty("manual", "false")
        user_item.setLabel2(sub_line)

        return user_item
    return None
