# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import time
import json
import traceback
import binascii
from threading import Timer

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.downloadutils import DownloadUtils, save_user_details
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import Service, PlaybackService, sendProgress
from resources.lib.kodi_utils import HomeWindow
from resources.lib.widgets import checkForNewContent, set_background_image, set_random_movies
from resources.lib.websocket_client import WebSocketClient
from resources.lib.menu_functions import set_library_window_values
from resources.lib.context_monitor import ContextMonitor
from resources.lib.server_detect import checkServer

settings = xbmcaddon.Addon()

# clear user and token when logging in
home_window = HomeWindow()
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log = SimpleLogging('service')
monitor = xbmc.Monitor()

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

# set up all the services
monitor = Service()
playback_service = PlaybackService(monitor)

home_window = HomeWindow()
last_progress_update = time.time()
last_content_check = time.time()
last_background_update = 0
last_random_movie_update = 0
websocket_client = WebSocketClient()

# session id
# TODO: this is used to append to the end of PLAY urls, this is to stop mark watched from overriding the Emby ones
home_window.setProperty("session_id", str(time.time()))



# start the WebSocket Client running

remote_control = settings.getSetting('remoteControl') == "true"
if remote_control:
    websocket_client.start()

# Start the context menu monitor
context_monitor = None
context_menu = settings.getSetting('override_contextmenu') == "true"
if context_menu:
    context_monitor = ContextMonitor()
    context_monitor.start()

background_interval = int(settings.getSetting('background_interval'))
newcontent_interval = int(settings.getSetting('newcontent_interval'))
random_movie_list_interval = 300

# monitor.abortRequested() is causes issues, it currently triggers for all addon cancelations which causes
# the service to exit when a user cancels an addon load action. This is a bug in Kodi.
# I am switching back to xbmc.abortRequested approach until kodi is fixed or I find a work arround
prev_user_id = home_window.getProperty("userid")

while not xbmc.abortRequested:

    try:
        if xbmc.Player().isPlaying():
            # if playing every 10 seconds updated the server with progress
            if (time.time() - last_progress_update) > 10:
                last_progress_update = time.time()
                sendProgress(monitor)

        else:
            user_changed = False
            if prev_user_id != home_window.getProperty("userid"):
                log.debug("user_change_detected")
                prev_user_id = home_window.getProperty("userid")
                user_changed = True

            if random_movie_list_interval != 0 and user_changed or (time.time() - last_random_movie_update) > random_movie_list_interval:
                last_random_movie_update = time.time()
                set_random_movies()

            if newcontent_interval != 0 and user_changed or (time.time() - last_content_check) > newcontent_interval:
                last_content_check = time.time()
                checkForNewContent()

            if background_interval != 0 and user_changed or (time.time() - last_background_update) > background_interval:
                last_background_update = time.time()
                set_library_window_values(user_changed)
                set_background_image(user_changed)

            if remote_control and user_changed:
                websocket_client.stop_client()
                websocket_client = WebSocketClient()
                websocket_client.start()

    except Exception as error:
        log.error("Exception in Playback Monitor: {0}", error)
        log.error("{0}", traceback.format_exc())

    xbmc.sleep(1000)

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
