# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import time
import traceback

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.lazylogger import LazyLogger
from resources.lib.play_utils import Service, PlaybackService, send_progress
from resources.lib.kodi_utils import HomeWindow
from resources.lib.widgets import set_background_image, set_random_movies
from resources.lib.websocket_client import WebSocketClient
from resources.lib.menu_functions import set_library_window_values
from resources.lib.server_detect import check_server, check_connection_speed
from resources.lib.monitors import LibraryChangeMonitor, ContextMonitor
from resources.lib.datamanager import clear_old_cache_data
from resources.lib.tracking import set_timing_enabled
from resources.lib.image_server import HttpImageServerThread
from resources.lib.playnext import PlayNextService

settings = xbmcaddon.Addon()

log_timing_data = settings.getSetting('log_timing') == "true"
if log_timing_data:
    set_timing_enabled(True)

# clear user and token when logging in
home_window = HomeWindow()
home_window.clear_property("user_name")
home_window.clear_property("AccessToken")
home_window.clear_property("Params")

log = LazyLogger('service')
monitor = xbmc.Monitor()

try:
    clear_old_cache_data()
except Exception as error:
    log.error("Error in clear_old_cache_data() : {0}".format(error))

# wait for 10 seconds for the Kodi splash screen to close
i = 0
while not monitor.abortRequested():
    if i == 100 or not xbmc.getCondVisibility("Window.IsVisible(startup)"):
        break
    i += 1
    xbmc.sleep(100)

check_server()

image_server = HttpImageServerThread()
image_server.start()

# set up all the services
monitor = Service()
playback_service = PlaybackService(monitor)

home_window = HomeWindow()
last_progress_update = time.time()
last_content_check = time.time()
last_background_update = 0
last_random_movie_update = 0

# start the library update monitor
library_change_monitor = LibraryChangeMonitor()
library_change_monitor.start()

# start the WebSocket Client running
remote_control = settings.getSetting('websocket_enabled') == "true"
websocket_client = WebSocketClient(library_change_monitor)
if remote_control:
    websocket_client.start()

play_next_service = None
play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))
if play_next_trigger_time > 0:
    play_next_service = PlayNextService(monitor)
    play_next_service.start()

# Start the context menu monitor
context_monitor = None
context_menu = settings.getSetting('override_contextmenu') == "true"
if context_menu:
    context_monitor = ContextMonitor()
    context_monitor.start()

background_interval = int(settings.getSetting('background_interval'))
newcontent_interval = int(settings.getSetting('new_content_check_interval'))
random_movie_list_interval = int(settings.getSetting('random_movie_refresh_interval'))
random_movie_list_interval = random_movie_list_interval * 60

enable_logging = settings.getSetting('log_debug') == "true"
if enable_logging:
    xbmcgui.Dialog().notification(settings.getAddonInfo('name'),
                                  "Debug logging enabled!",
                                  time=8000,
                                  icon=xbmcgui.NOTIFICATION_WARNING)

prev_user = home_window.get_property("user_name")
first_run = True
home_window.set_property('exit', 'False')

while home_window.get_property('exit') == 'False':

    try:
        if xbmc.Player().isPlaying():
            last_random_movie_update = time.time() - (random_movie_list_interval - 15)
            # if playing every 10 seconds updated the server with progress
            if (time.time() - last_progress_update) > 10:
                last_progress_update = time.time()
                send_progress()

        else:
            screen_saver_active = xbmc.getCondVisibility("System.ScreenSaverActive")

            if not screen_saver_active:
                user_changed = False
                if prev_user != home_window.get_property("user_name"):
                    log.debug("user_change_detected")
                    prev_user = home_window.get_property("user_name")
                    user_changed = True

                if user_changed or first_run:
                    settings = xbmcaddon.Addon()
                    server_speed_check_data = settings.getSetting("server_speed_check_data")
                    server_speed_check_data = settings.getSetting("server_speed_check_data")
                    server_host = settings.getSetting('server_address')
                    if server_host is not None and server_host != "" and server_host != "<none>" and server_host not in server_speed_check_data:
                        message = "This is the first time you have connected to this server.\nDo you want to run a connection speed test?"
                        response = xbmcgui.Dialog().yesno("First Connection", message)
                        if response:
                            speed = check_connection_speed()
                            if speed > 0:
                                settings.setSetting("server_speed_check_data", server_host + "-" + str(speed))
                        else:
                            settings.setSetting("server_speed_check_data", server_host + "-skipped")

                if user_changed or (random_movie_list_interval != 0 and (time.time() - last_random_movie_update) > random_movie_list_interval):
                    last_random_movie_update = time.time()
                    set_random_movies()

                if user_changed or (newcontent_interval != 0 and (time.time() - last_content_check) > newcontent_interval):
                    last_content_check = time.time()
                    library_change_monitor.check_for_updates()

                if user_changed or (background_interval != 0 and (time.time() - last_background_update) > background_interval):
                    last_background_update = time.time()
                    set_library_window_values(user_changed)
                    set_background_image(user_changed)

                if remote_control and user_changed:
                    websocket_client.stop_client()
                    websocket_client = WebSocketClient(library_change_monitor)
                    websocket_client.start()

            elif screen_saver_active:
                last_random_movie_update = time.time() - (random_movie_list_interval - 15)
                if background_interval != 0 and ((time.time() - last_background_update) > background_interval):
                    last_background_update = time.time()
                    set_background_image(False)

    except Exception as error:
        log.error("Exception in Playback Monitor: {0}".format(error))
        log.error("{0}".format(traceback.format_exc()))

    first_run = False
    xbmc.sleep(1000)

image_server.stop()

# stop the WebSocket Client
websocket_client.stop_client()

# call stop on the library update monitor
library_change_monitor.stop()

# stop the play next episode service
if play_next_service:
    play_next_service.stop_service()

# call stop on the context menu monitor
if context_monitor:
    context_monitor.stop_monitor()

# clear user and token when logging off
home_window.clear_property("user_name")
home_window.clear_property("AccessToken")
home_window.clear_property("userimage")

log.debug("Service shutting down")
