# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import time
import traceback

import xbmc
import xbmcaddon

from resources.lib.downloadutils import DownloadUtils, save_user_details
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import Service, PlaybackService, sendProgress
from resources.lib.kodi_utils import HomeWindow
from resources.lib.widgets import set_background_image, set_random_movies
from resources.lib.websocket_client import WebSocketClient
from resources.lib.menu_functions import set_library_window_values
from resources.lib.context_monitor import ContextMonitor
from resources.lib.server_detect import checkServer
from resources.lib.library_change_monitor import LibraryChangeMonitor
from resources.lib.datamanager import clear_old_cache_data
from resources.lib.tracking import set_timing_enabled
from resources.lib.image_server import HttpImageServerThread

settings = xbmcaddon.Addon()

log_timing_data = settings.getSetting('log_timing') == "true"
if log_timing_data:
    set_timing_enabled(True)

# clear user and token when logging in
home_window = HomeWindow()
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log = SimpleLogging('service')
monitor = xbmc.Monitor()

try:
    clear_old_cache_data()
except Exception as error:
    log.error("Error in clear_old_cache_data() : {0}", error)

# wait for 10 seconds for the Kodi splash screen to close
i = 0
while not monitor.abortRequested():
    if i == 100 or not xbmc.getCondVisibility("Window.IsVisible(startup)"):
        break
    i += 1
    xbmc.sleep(100)

checkServer()

download_utils = DownloadUtils()

# auth the service
try:
    download_utils.authenticate()
    download_utils.getUserId()
except Exception as error:
    log.error("Error with initial service auth: {0}", error)


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

# session id
# TODO: this is used to append to the end of PLAY urls, this is to stop mark watched from overriding the Emby ones
# this shold no longer be needed with the fix for ListItem items using the play status from the ListItem instead of the DB
# home_window.setProperty("session_id", str(time.time()))

# start the library update monitor
library_change_monitor = LibraryChangeMonitor()
library_change_monitor.start()

# start the WebSocket Client running
remote_control = settings.getSetting('websocket_enabled') == "true"
websocket_client = WebSocketClient(library_change_monitor)
if remote_control:
    websocket_client.start()

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

# monitor.abortRequested() is causes issues, it currently triggers for all addon cancelations which causes
# the service to exit when a user cancels an addon load action. This is a bug in Kodi.
# I am switching back to xbmc.abortRequested approach until kodi is fixed or I find a work arround
prev_user_id = home_window.getProperty("userid")

while not xbmc.abortRequested:

    try:
        if xbmc.Player().isPlaying():
            last_random_movie_update = time.time() - (random_movie_list_interval - 15)
            # if playing every 10 seconds updated the server with progress
            if (time.time() - last_progress_update) > 10:
                last_progress_update = time.time()
                sendProgress(monitor)

        else:
            screen_saver_active = xbmc.getCondVisibility("System.ScreenSaverActive")

            if not screen_saver_active:
                user_changed = False
                if prev_user_id != home_window.getProperty("userid"):
                    log.debug("user_change_detected")
                    prev_user_id = home_window.getProperty("userid")
                    user_changed = True

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
        log.error("Exception in Playback Monitor: {0}", error)
        log.error("{0}", traceback.format_exc())

    xbmc.sleep(1000)

image_server.stop()

# call stop on the library update monitor
library_change_monitor.stop()

# call stop on the context menu monitor
if context_monitor:
    context_monitor.stop_monitor()

# stop the WebSocket Client
websocket_client.stop_client()

# clear user and token when loggin off
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")
home_window.clearProperty("userimage")

log.debug("Service shutting down")
